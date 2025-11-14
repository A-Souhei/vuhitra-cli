"""
Tests for heuristic chaining functionality.

Tests the ability to:
- Create parent-child relationships between heuristics
- Retrieve full chains
- Format chain context with anti-copying instructions
- Enforce chain depth limits
"""
import pytest
from unittest.mock import Mock, patch

from services.sandbox.src.heuristics import Heuristics
from services.sandbox.src.elasticsearch_client import ElasticSearchClient
from services.sandbox.src.insight_extractor import InsightExtractor


class TestChainMetadataBuilding:
    """Test chain metadata creation in Heuristics class."""

    def test_chain_metadata_disabled(self):
        """Test that chain metadata is empty when chaining is disabled."""
        heuristics = Heuristics()
        heuristics.chaining_enabled = False

        feedback_data = {
            "rating": 5,
            "contexted_heuristic_ids": ["parent_id_123"]
        }

        metadata = heuristics._build_chain_metadata(feedback_data)

        assert metadata["parent_heuristic_id"] is None
        assert metadata["chain_depth"] == 0
        assert metadata["chain_ids"] == []

    def test_chain_metadata_low_rating(self):
        """Test that chains are not created for low ratings."""
        heuristics = Heuristics()
        heuristics.chaining_enabled = True
        heuristics.min_rating_for_chaining = 4

        feedback_data = {
            "rating": 3,
            "contexted_heuristic_ids": ["parent_id_123"]
        }

        metadata = heuristics._build_chain_metadata(feedback_data)

        assert metadata["parent_heuristic_id"] is None
        assert metadata["chain_depth"] == 0

    def test_chain_metadata_no_context(self):
        """Test that root heuristic is created when no context."""
        heuristics = Heuristics()
        heuristics.chaining_enabled = True
        heuristics.min_rating_for_chaining = 4

        feedback_data = {
            "rating": 5,
            "contexted_heuristic_ids": []
        }

        metadata = heuristics._build_chain_metadata(feedback_data)

        assert metadata["parent_heuristic_id"] is None
        assert metadata["chain_depth"] == 0
        assert metadata["chain_ids"] == []

    @patch.object(ElasticSearchClient, 'get_by_id')
    def test_chain_metadata_first_child(self, mock_get_by_id):
        """Test creating first child in chain."""
        # Mock parent document
        mock_get_by_id.return_value = {
            "rating": 5,
            "chain_depth": 0,
            "chain_ids": []
        }

        heuristics = Heuristics()
        heuristics.chaining_enabled = True
        heuristics.min_rating_for_chaining = 4

        feedback_data = {
            "rating": 5,
            "contexted_heuristic_ids": ["parent_id_123"]
        }

        metadata = heuristics._build_chain_metadata(feedback_data)

        assert metadata["parent_heuristic_id"] == "parent_id_123"
        assert metadata["chain_depth"] == 1
        assert metadata["chain_ids"] == ["parent_id_123"]

    @patch.object(ElasticSearchClient, 'get_by_id')
    def test_chain_metadata_deep_chain(self, mock_get_by_id):
        """Test creating chain with multiple ancestors."""
        # Mock parent document with existing chain
        # The parent "middle_id" has root_id as its ancestor
        mock_get_by_id.return_value = {
            "rating": 5,
            "chain_depth": 1,
            "chain_ids": ["root_id"]
        }

        heuristics = Heuristics()
        heuristics.chaining_enabled = True
        heuristics.min_rating_for_chaining = 4

        feedback_data = {
            "rating": 5,
            "contexted_heuristic_ids": ["middle_id"]
        }

        metadata = heuristics._build_chain_metadata(feedback_data)

        assert metadata["parent_heuristic_id"] == "middle_id"
        assert metadata["chain_depth"] == 2
        assert metadata["chain_ids"] == ["root_id", "middle_id"]

    @patch.object(ElasticSearchClient, 'get_by_id')
    def test_chain_depth_limit(self, mock_get_by_id):
        """Test that chain depth limit is enforced."""
        # Mock parent at max depth
        mock_get_by_id.return_value = {
            "rating": 5,
            "chain_depth": 5,
            "chain_ids": ["id1", "id2", "id3", "id4", "id5"]
        }

        heuristics = Heuristics()
        heuristics.chaining_enabled = True
        heuristics.min_rating_for_chaining = 4
        heuristics.max_chain_depth = 5

        feedback_data = {
            "rating": 5,
            "contexted_heuristic_ids": ["id5"]
        }

        metadata = heuristics._build_chain_metadata(feedback_data)

        # Should not create chain link
        assert metadata["parent_heuristic_id"] is None
        assert metadata["chain_depth"] == 0

    @patch.object(ElasticSearchClient, 'get_by_id')
    def test_contexted_ids_stored(self, mock_get_by_id):
        """Test that contexted_heuristic_ids are always stored."""
        mock_get_by_id.return_value = None

        heuristics = Heuristics()
        heuristics.chaining_enabled = True

        feedback_data = {
            "rating": 5,
            "contexted_heuristic_ids": ["id1", "id2", "id3"]
        }

        metadata = heuristics._build_chain_metadata(feedback_data)

        assert metadata["contexted_heuristic_ids"] == ["id1", "id2", "id3"]


class TestChainRetrieval:
    """Test chain retrieval in ElasticSearchClient."""

    @patch('services.sandbox.src.elasticsearch_client.Elasticsearch')
    def test_get_chain_empty(self, mock_es):
        """Test retrieving chain for document with no parents."""
        es_client = ElasticSearchClient()

        # Mock document with no chain
        with patch.object(es_client, 'get_by_id', return_value={
            "prompt": "test",
            "response": "test",
            "rating": 5,
            "chain_ids": []
        }):
            chain = es_client.get_chain("doc_id")
            assert chain == []

    @patch('services.sandbox.src.elasticsearch_client.Elasticsearch')
    def test_get_chain_with_parents(self, mock_es_class):
        """Test retrieving full chain."""
        # Setup mock ES instance
        mock_es_instance = Mock()
        mock_es_instance.ping.return_value = True
        mock_es_instance.indices.exists.return_value = True
        mock_es_class.return_value = mock_es_instance

        es_client = ElasticSearchClient()

        def mock_get(doc_id):
            docs = {
                "child_id": {
                    "rating": 5,
                    "chain_ids": ["root_id", "parent_id"]
                },
                "root_id": {
                    "rating": 4,
                    "prompt": "root prompt"
                },
                "parent_id": {
                    "rating": 5,
                    "prompt": "parent prompt"
                }
            }
            return docs.get(doc_id)

        # Mock mget response
        mock_es_instance.mget.return_value = {
            "docs": [
                {
                    "found": True,
                    "_id": "root_id",
                    "_source": {
                        "rating": 4,
                        "prompt": "root prompt"
                    }
                },
                {
                    "found": True,
                    "_id": "parent_id",
                    "_source": {
                        "rating": 5,
                        "prompt": "parent prompt"
                    }
                }
            ]
        }

        with patch.object(es_client, 'get_by_id', side_effect=mock_get):
            chain = es_client.get_chain("child_id")

            assert len(chain) == 2
            assert chain[0]["_id"] == "root_id"
            assert chain[1]["_id"] == "parent_id"


class TestChainInsightExtraction:
    """Test chain insight extraction in InsightExtractor."""

    def test_extract_chain_insights_no_chain(self):
        """Test that standard extraction is used when no chain."""
        mock_nlp = Mock()
        extractor = InsightExtractor(nlp_model=mock_nlp)

        heuristic = {
            "prompt": "test prompt",
            "response": "test response",
            "rating": 5
        }

        with patch.object(extractor, 'extract_insights', return_value={
            "summary": "test summary"
        }):
            result = extractor.extract_chain_insights(heuristic, [])

            assert "summary" in result
            assert not result.get("has_chain", False)

    def test_format_chain_with_anti_copying_instructions(self):
        """Test that chain formatting uses directive mode for 5-star matches."""
        mock_nlp = Mock()
        extractor = InsightExtractor(nlp_model=mock_nlp)

        primary_heuristic = {
            "rating": 5,
            "prompt": "test prompt",
            "response": "test response"
        }

        chain = [
            {
                "rating": 4,
                "prompt": "parent prompt",
                "response": "parent response"
            }
        ]

        # Mock extract_insights to return controlled data
        def mock_extract_insights(heuristic):
            if heuristic.get("rating") == 5:
                return {
                    "summary": "Current solution",
                    "key_techniques": ["technique1", "technique2"],
                    "entities": [{"text": "Python"}],
                    "confidence_indicators": ["High quality"]
                }
            else:
                return {
                    "summary": "First iteration",
                    "key_techniques": ["old_technique"],
                    "entities": [{"text": "Java"}],
                    "confidence_indicators": []
                }

        with patch.object(extractor, 'extract_insights', side_effect=mock_extract_insights):
            result = extractor.extract_chain_insights(primary_heuristic, chain)

        formatted = result.get("formatted_insight", "")

        # For rating=5, should use directive mode with verified answer
        assert "VERIFIED ANSWER - OUTPUT EXACTLY AS SHOWN" in formatted
        assert "test response" in formatted
        assert "Do not add any explanation" in formatted or "Output only the answer" in formatted

        # Ensure no privacy-leaking information
        assert "rated" not in formatted.lower()
        assert "5/5" not in formatted
        assert "4/5" not in formatted
        assert "Iteration 1" not in formatted


class TestChainEndToEnd:
    """End-to-end tests for heuristic chaining."""

    @patch('services.sandbox.src.elasticsearch_client.Elasticsearch')
    def test_full_chain_workflow(self, mock_es):
        """Test complete workflow: store -> retrieve -> chain."""
        # This would be an integration test
        # Skipping implementation for now as it requires full ES setup
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
