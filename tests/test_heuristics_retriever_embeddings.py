"""
Tests for the embedding-based HeuristicsRetriever.

These tests work without requiring Docker containers by mocking the transformer service.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from services.sandbox.src.heuristics_retriever import HeuristicsRetriever
from tests.mocks.mock_transformer_service import MockTransformerService, MockResponse, mock_generate_embedding_request


@pytest.fixture
def mock_es_client():
    """Mock Elasticsearch client."""
    mock_es = Mock()
    mock_es.ping.return_value = True
    return mock_es


@pytest.fixture
def mock_es_wrapper():
    """Mock ElasticSearch wrapper with chain support."""
    mock_wrapper = Mock()
    mock_wrapper.get_chain.return_value = []
    return mock_wrapper


@pytest.fixture
def retriever(mock_es_client, mock_es_wrapper):
    """Create a HeuristicsRetriever instance with mocked dependencies."""
    with patch('requests.post') as mock_post:
        # Mock the transformer service embedding endpoint
        def mock_embedding_response(url, json=None, timeout=None):
            if '/api/generate-embedding' in url:
                text = json.get('text', '')
                embedding_data = mock_generate_embedding_request(text)
                return MockResponse(embedding_data, 200)
            return MockResponse({}, 404)
        
        mock_post.side_effect = mock_embedding_response
        
        retriever = HeuristicsRetriever(
            es_client=mock_es_client,
            index_name="test_llm_feedback",
            es_client_wrapper=mock_es_wrapper,
            transformer_host="localhost",
            transformer_port=5050
        )
        
        yield retriever


class TestHeuristicsRetrieverEmbeddings:
    """Test suite for embedding-based heuristics retrieval."""
    
    def test_initialization(self, mock_es_client, mock_es_wrapper):
        """Test that the retriever initializes correctly."""
        retriever = HeuristicsRetriever(
            es_client=mock_es_client,
            index_name="test_index",
            es_client_wrapper=mock_es_wrapper
        )
        
        assert retriever.es == mock_es_client
        assert retriever.index_name == "test_index"
        assert retriever.transformer_url == "http://transformer:5050"
        assert retriever.MIN_SIMILARITY == 0.5
    
    def test_generate_embedding_success(self, retriever):
        """Test successful embedding generation."""
        with patch('requests.post') as mock_post:
            mock_post.return_value = MockResponse({
                'embedding': [0.1] * 384,
                'dimension': 384,
                'model': 'all-MiniLM-L6-v2'
            }, 200)
            
            embedding = retriever._generate_embedding("test prompt")
            
            assert embedding is not None
            assert len(embedding) == 384
            assert all(isinstance(x, (int, float)) for x in embedding)
    
    def test_generate_embedding_failure(self, retriever):
        """Test handling of embedding generation failure."""
        with patch('requests.post') as mock_post:
            mock_post.return_value = MockResponse({}, 500)
            
            embedding = retriever._generate_embedding("test prompt")
            
            assert embedding is None
    
    def test_generate_embedding_network_error(self, retriever):
        """Test handling of network errors."""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = Exception("Connection refused")
            
            embedding = retriever._generate_embedding("test prompt")
            
            assert embedding is None
    
    def test_retrieve_best_match_success(self, retriever):
        """Test successful retrieval of best matching heuristic."""
        # Mock Elasticsearch kNN search response
        mock_response = {
            'hits': {
                'hits': [
                    {
                        '_id': 'doc1',
                        '_score': 0.85,  # High similarity
                        '_source': {
                            'prompt': 'similar prompt',
                            'response': 'good response',
                            'rating': 5
                        }
                    },
                    {
                        '_id': 'doc2',
                        '_score': 0.65,
                        '_source': {
                            'prompt': 'somewhat similar',
                            'response': 'ok response',
                            'rating': 4
                        }
                    }
                ]
            }
        }
        
        retriever.es.search = Mock(return_value=mock_response)
        
        with patch('requests.post') as mock_post:
            mock_post.return_value = MockResponse({
                'embedding': MockTransformerService.generate_embedding("test prompt"),
                'dimension': 384
            }, 200)
            
            result = retriever.retrieve_best_match("test prompt", min_rating=3)
            
            assert result is not None
            assert 'matched_heuristic' in result
            assert 'confidence_score' in result
            assert 'scoring_breakdown' in result
            assert result['matched_heuristic']['_id'] == 'doc1'
            assert result['matched_heuristic']['rating'] == 5
    
    def test_retrieve_best_match_no_candidates(self, retriever):
        """Test when no candidates match the query."""
        mock_response = {
            'hits': {
                'hits': []
            }
        }
        
        retriever.es.search = Mock(return_value=mock_response)
        
        with patch('requests.post') as mock_post:
            mock_post.return_value = MockResponse({
                'embedding': [0.1] * 384,
                'dimension': 384
            }, 200)
            
            result = retriever.retrieve_best_match("test prompt")
            
            assert result is None
    
    def test_retrieve_best_match_below_similarity_threshold(self, retriever):
        """Test when candidates are below similarity threshold."""
        mock_response = {
            'hits': {
                'hits': [
                    {
                        '_id': 'doc1',
                        '_score': 0.3,  # Below threshold (0.5)
                        '_source': {
                            'prompt': 'very different prompt',
                            'response': 'response',
                            'rating': 5
                        }
                    }
                ]
            }
        }
        
        retriever.es.search = Mock(return_value=mock_response)
        
        with patch('requests.post') as mock_post:
            mock_post.return_value = MockResponse({
                'embedding': [0.1] * 384,
                'dimension': 384
            }, 200)
            
            result = retriever.retrieve_best_match("test prompt")
            
            assert result is None
    
    def test_retrieve_best_match_with_chain(self, retriever):
        """Test retrieval with chain enabled."""
        retriever.CHAINING_ENABLED = True
        retriever.INCLUDE_CHAIN_IN_CONTEXT = True
        
        mock_chain = [
            {'_id': 'parent1', 'prompt': 'parent prompt', 'rating': 5},
            {'_id': 'parent2', 'prompt': 'another parent', 'rating': 4}
        ]
        
        retriever.es_client_wrapper.get_chain.return_value = mock_chain
        
        mock_response = {
            'hits': {
                'hits': [
                    {
                        '_id': 'doc1',
                        '_score': 0.85,
                        '_source': {
                            'prompt': 'test',
                            'response': 'response',
                            'rating': 5
                        }
                    }
                ]
            }
        }
        
        retriever.es.search = Mock(return_value=mock_response)
        
        with patch('requests.post') as mock_post:
            mock_post.return_value = MockResponse({
                'embedding': [0.1] * 384,
                'dimension': 384
            }, 200)
            
            result = retriever.retrieve_best_match("test prompt")
            
            assert result is not None
            assert 'chain' in result
            assert len(result['chain']) == 2
    
    def test_retrieve_negative_heuristics_success(self, retriever):
        """Test retrieval of negative heuristics (anti-patterns)."""
        mock_response = {
            'hits': {
                'hits': [
                    {
                        '_id': 'bad_doc1',
                        '_score': 0.75,
                        '_source': {
                            'prompt': 'bad approach',
                            'response': 'failed response',
                            'rating': 1  # Low rating
                        }
                    }
                ]
            }
        }
        
        retriever.es.search = Mock(return_value=mock_response)
        
        with patch('requests.post') as mock_post:
            mock_post.return_value = MockResponse({
                'embedding': [0.1] * 384,
                'dimension': 384
            }, 200)
            
            result = retriever.retrieve_negative_heuristics("test prompt", max_rating=2)
            
            assert result is not None
            assert 'matched_heuristic' in result
            assert 'is_negative' in result
            assert result['is_negative'] is True
            assert result['matched_heuristic']['rating'] == 1
    
    def test_retrieve_negative_with_boost(self, retriever):
        """Test negative heuristic confidence boost."""
        mock_response = {
            'hits': {
                'hits': [
                    {
                        '_id': 'bad_doc1',
                        '_score': 0.6,
                        '_source': {
                            'prompt': 'bad approach',
                            'response': 'failed',
                            'rating': 2
                        }
                    }
                ]
            }
        }
        
        retriever.es.search = Mock(return_value=mock_response)
        
        with patch('requests.post') as mock_post:
            mock_post.return_value = MockResponse({
                'embedding': [0.1] * 384,
                'dimension': 384
            }, 200)
            
            result = retriever.retrieve_negative_heuristics(
                "test prompt",
                negative_weight_boost=0.3
            )
            
            assert result is not None
            # Confidence should be boosted but capped at 1.0
            assert result['confidence_score'] <= 1.0
            assert result['scoring_breakdown']['negative_weight_boost_applied'] == 0.3
    
    def test_scoring_weights(self, retriever):
        """Test that scoring weights are properly configured."""
        assert hasattr(retriever, 'SEMANTIC_WEIGHT')
        assert hasattr(retriever, 'RATING_WEIGHT')
        assert retriever.SEMANTIC_WEIGHT >= 0
        assert retriever.RATING_WEIGHT >= 0
    
    def test_es_not_connected(self):
        """Test behavior when Elasticsearch is not connected."""
        retriever = HeuristicsRetriever(
            es_client=None,
            index_name="test_index"
        )
        
        result = retriever.retrieve_best_match("test prompt")
        assert result is None
    
    def test_embedding_generation_failure_propagates(self, retriever):
        """Test that embedding generation failure is handled gracefully."""
        with patch('requests.post') as mock_post:
            mock_post.return_value = MockResponse({}, 500)
            
            result = retriever.retrieve_best_match("test prompt")
            
            assert result is None
