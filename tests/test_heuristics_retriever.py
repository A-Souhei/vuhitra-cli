"""
Unit tests for HeuristicsRetriever
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'sandbox', 'src'))

from heuristics_retriever import HeuristicsRetriever


class TestHeuristicsRetriever:
    """Test suite for HeuristicsRetriever class"""

    @pytest.fixture
    def mock_es_client(self):
        """Create a mock Elasticsearch client"""
        mock_es = Mock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = True
        return mock_es

    @pytest.fixture
    def mock_nlp(self):
        """Create a mock spaCy NLP model"""
        mock_nlp = Mock()

        # Create mock doc
        mock_doc = Mock()
        mock_doc.has_vector = True

        # Mock tokens
        mock_token1 = Mock()
        mock_token1.lemma_ = "test"
        mock_token1.is_stop = False
        mock_token1.is_punct = False
        mock_token1.text = "test"
        mock_token1.pos_ = "NOUN"

        mock_token2 = Mock()
        mock_token2.lemma_ = "example"
        mock_token2.is_stop = False
        mock_token2.is_punct = False
        mock_token2.text = "example"
        mock_token2.pos_ = "NOUN"

        mock_doc.__iter__ = lambda self: iter([mock_token1, mock_token2])
        mock_doc.similarity = Mock(return_value=0.85)

        mock_nlp.return_value = mock_doc
        return mock_nlp

    @pytest.fixture
    def retriever(self, mock_es_client, mock_nlp):
        """Create a HeuristicsRetriever instance with mocked dependencies"""
        with patch('heuristics_retriever.spacy.load', return_value=mock_nlp):
            retriever = HeuristicsRetriever(mock_es_client, "test_index")
            retriever.nlp = mock_nlp
            return retriever

    def test_initialization(self, mock_es_client, mock_nlp):
        """Test retriever initialization"""
        with patch('heuristics_retriever.spacy.load', return_value=mock_nlp):
            retriever = HeuristicsRetriever(mock_es_client, "test_index")

            assert retriever.es == mock_es_client
            assert retriever.index_name == "test_index"
            assert retriever.nlp is not None

    def test_health_check_all_healthy(self, retriever):
        """Test health check when all components are healthy"""
        health = retriever.health_check()

        assert health['elasticsearch_connected'] is True
        assert health['spacy_loaded'] is True
        assert health['index_exists'] is True

    def test_health_check_es_disconnected(self, retriever):
        """Test health check when Elasticsearch is disconnected"""
        retriever.es.ping.return_value = False

        health = retriever.health_check()

        assert health['elasticsearch_connected'] is False
        assert health['spacy_loaded'] is True

    def test_stage1_keyword_filter(self, retriever):
        """Test Stage 1: Keyword filtering"""
        # Mock ES search response
        mock_response = {
            'hits': {
                'hits': [
                    {
                        '_id': 'doc1',
                        '_score': 10.5,
                        '_source': {
                            'prompt': 'How to test Python code?',
                            'response': 'Use pytest framework',
                            'rating': 5,
                            'prompt_keywords': ['test', 'python', 'code']
                        }
                    },
                    {
                        '_id': 'doc2',
                        '_score': 8.3,
                        '_source': {
                            'prompt': 'Python testing best practices',
                            'response': 'Write unit tests',
                            'rating': 4,
                            'prompt_keywords': ['python', 'testing', 'best']
                        }
                    }
                ]
            }
        }
        retriever.es.search = Mock(return_value=mock_response)

        candidates = retriever._stage1_keyword_filter("How to test Python?", min_rating=3)

        assert len(candidates) == 2
        assert candidates[0]['_id'] == 'doc1'
        assert candidates[0]['rating'] == 5
        assert candidates[1]['_id'] == 'doc2'

    def test_stage2_levenshtein_scoring(self, retriever):
        """Test Stage 2: Levenshtein distance scoring"""
        candidates = [
            {'prompt': 'How to test Python code?', 'rating': 5},
            {'prompt': 'Python testing tutorial', 'rating': 4},
            {'prompt': 'Completely different topic', 'rating': 3}
        ]

        scored = retriever._stage2_levenshtein_scoring("How to test Python?", candidates)

        assert all('levenshtein_score' in c for c in scored)
        # First candidate should have highest similarity (most similar prompt)
        assert scored[0]['levenshtein_score'] > scored[2]['levenshtein_score']

    def test_stage3_semantic_similarity(self, retriever):
        """Test Stage 3: Semantic similarity scoring"""
        candidates = [
            {
                'prompt': 'How to test Python code?',
                'rating': 5,
                'levenshtein_score': 0.85,
                'prompt_keywords': ['test', 'python', 'code']
            }
        ]

        results = retriever._stage3_semantic_similarity("Python testing guide", candidates)

        assert len(results) == 1
        assert 'final_score' in results[0]
        assert 'semantic_score' in results[0]
        assert 'levenshtein_score' in results[0]
        assert 'keyword_score' in results[0]
        assert 'rating_score' in results[0]

        # Check scoring formula
        result = results[0]
        expected_final = (
            HeuristicsRetriever.SEMANTIC_WEIGHT * result['semantic_score'] +
            HeuristicsRetriever.LEVENSHTEIN_WEIGHT * result['levenshtein_score'] +
            HeuristicsRetriever.KEYWORD_WEIGHT * result['keyword_score'] +
            HeuristicsRetriever.RATING_WEIGHT * result['rating_score']
        )
        assert abs(result['final_score'] - expected_final) < 0.001

    def test_calculate_keyword_overlap(self, retriever, mock_nlp):
        """Test keyword overlap calculation"""
        # Create mock prompt doc with keywords
        mock_doc = Mock()
        mock_token1 = Mock()
        mock_token1.lemma_ = "test"
        mock_token1.is_stop = False
        mock_token1.is_punct = False
        mock_token1.text = "test"
        mock_token1.pos_ = "NOUN"

        mock_token2 = Mock()
        mock_token2.lemma_ = "python"
        mock_token2.is_stop = False
        mock_token2.is_punct = False
        mock_token2.text = "python"
        mock_token2.pos_ = "NOUN"

        mock_doc.__iter__ = lambda self: iter([mock_token1, mock_token2])

        candidate_keywords = ['test', 'python', 'code']

        score = retriever._calculate_keyword_overlap(candidate_keywords, mock_doc)

        # Should have 2 overlapping keywords (test, python) out of total 3 unique
        assert score > 0
        assert score <= 1.0

    def test_retrieve_best_match_success(self, retriever):
        """Test successful retrieval of best match"""
        # Mock all stages
        mock_candidates = [{
            '_id': 'doc1',
            'prompt': 'How to test Python?',
            'response': 'Use pytest',
            'rating': 5,
            'prompt_keywords': ['test', 'python']
        }]

        retriever._stage1_keyword_filter = Mock(return_value=mock_candidates)
        retriever._stage2_levenshtein_scoring = Mock(return_value=[
            {**mock_candidates[0], 'levenshtein_score': 0.85}
        ])
        retriever._stage3_semantic_similarity = Mock(return_value=[
            {
                'document': mock_candidates[0],
                'final_score': 0.82,
                'semantic_score': 0.85,
                'levenshtein_score': 0.85,
                'keyword_score': 0.7,
                'rating_score': 1.0
            }
        ])

        result = retriever.retrieve_best_match("Python testing guide")

        assert result is not None
        assert 'matched_heuristic' in result
        assert 'confidence_score' in result
        assert 'scoring_breakdown' in result
        assert result['confidence_score'] == 0.82

    def test_retrieve_best_match_no_candidates(self, retriever):
        """Test retrieval when no candidates are found"""
        retriever._stage1_keyword_filter = Mock(return_value=[])

        result = retriever.retrieve_best_match("Some query")

        assert result is None

    def test_retrieve_best_match_with_min_rating(self, retriever):
        """Test retrieval with custom minimum rating"""
        retriever._stage1_keyword_filter = Mock(return_value=[])

        retriever.retrieve_best_match("Test query", min_rating=4)

        retriever._stage1_keyword_filter.assert_called_once_with("Test query", 4)

    def test_retrieve_best_match_es_not_connected(self):
        """Test retrieval when Elasticsearch is not connected"""
        mock_es = Mock()
        mock_es.ping.return_value = False

        with patch('heuristics_retriever.spacy.load'):
            retriever = HeuristicsRetriever(mock_es, "test_index")
            retriever.es = None  # Simulate disconnected state

            result = retriever.retrieve_best_match("Test query")

            assert result is None

    def test_retrieve_best_match_nlp_not_loaded(self, mock_es_client):
        """Test retrieval when spaCy model is not loaded"""
        with patch('heuristics_retriever.spacy.load', side_effect=Exception("Model not found")):
            retriever = HeuristicsRetriever(mock_es_client, "test_index")

            result = retriever.retrieve_best_match("Test query")

            assert result is None

    def test_empty_prompt_keywords(self, retriever):
        """Test handling of empty prompt with no keywords"""
        # Mock ES response with empty results
        retriever.es.search = Mock(return_value={'hits': {'hits': []}})

        candidates = retriever._stage1_keyword_filter("", min_rating=3)

        assert len(candidates) == 0

    def test_scoring_weights_sum_to_one(self):
        """Test that scoring weights sum to 1.0"""
        total_weight = (
            HeuristicsRetriever.SEMANTIC_WEIGHT +
            HeuristicsRetriever.LEVENSHTEIN_WEIGHT +
            HeuristicsRetriever.KEYWORD_WEIGHT +
            HeuristicsRetriever.RATING_WEIGHT
        )

        assert abs(total_weight - 1.0) < 0.001

    def test_rating_normalization(self, retriever):
        """Test that ratings are properly normalized to 0-1 scale"""
        candidates = [
            {
                'prompt': 'Test prompt',
                'rating': 5,  # Should normalize to 1.0
                'levenshtein_score': 0.8,
                'prompt_keywords': ['test']
            }
        ]

        results = retriever._stage3_semantic_similarity("Test", candidates)

        assert results[0]['rating_score'] == 1.0

    def test_max_candidates_limits(self, retriever):
        """Test that candidate limits are respected"""
        # Test Stage 1 limit
        assert retriever.MAX_STAGE1_CANDIDATES == 100

        # Test Stage 2 limit
        assert retriever.MAX_STAGE2_CANDIDATES == 10

    def test_exception_handling_in_retrieve(self, retriever):
        """Test exception handling in retrieve_best_match"""
        retriever._stage1_keyword_filter = Mock(side_effect=Exception("ES error"))

        result = retriever.retrieve_best_match("Test query")

        # Should return None instead of crashing
        assert result is None
