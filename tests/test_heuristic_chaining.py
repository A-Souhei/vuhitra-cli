"""
Tests for heuristic chaining functionality.

Tests the ability to:
- Create parent-child relationships between heuristics
- Retrieve full chains
- Format chain context with anti-copying instructions
- Enforce chain depth limits
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'sandbox'))

from src.heuristics import Heuristics
from src.elasticsearch_client import ElasticSearchClient
from src.insight_extractor import InsightExtractor


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
        mock_get_by_id.return_value = {
            "rating": 5,
            "chain_depth": 2,
            "chain_ids": ["root_id", "middle_id"]
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
        assert metadata["chain_depth"] == 3
        assert metadata["chain_ids"] == ["root_id", "middle_id", "middle_id"]

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

    @patch('src.elasticsearch_client.Elasticsearch')
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

    @patch('src.elasticsearch_client.Elasticsearch')
    def test_get_chain_with_parents(self, mock_es):
        """Test retrieving full chain."""
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
            assert result.get("has_chain") != True

    def test_format_chain_with_anti_copying_instructions(self):
        """Test that chain formatting includes anti-copying instructions."""
        mock_nlp = Mock()
        extractor = InsightExtractor(nlp_model=mock_nlp)

        primary_heuristic = {
            "rating": 5,
            "prompt": "test prompt"
        }

        primary_insights = {
            "summary": "Current solution",
            "key_techniques": ["technique1", "technique2"],
            "entities": [{"text": "Python"}],
            "confidence_indicators": ["High quality"]
        }

        chain_insights = [
            {
                "rating": 4,
                "summary": "First iteration",
                "key_techniques": ["old_technique"],
                "entities": [{"text": "Java"}]
            }
        ]

        formatted = extractor._format_chain_for_injection(
            primary_heuristic,
            primary_insights,
            chain_insights
        )

        # Check for anti-copying instructions
        assert "DO NOT simply copy" in formatted
        assert "INSPIRATION" in formatted or "inspiration" in formatted.lower()
        assert "IMPROVE" in formatted or "improve" in formatted.lower()
        assert "MATCH or EXCEED" in formatted

        # Check for chain evolution
        assert "Iteration 1" in formatted
        assert "Current Best Solution" in formatted

        # Check for rating display
        assert "5/5" in formatted
        assert "4/5" in formatted


class TestChainEndToEnd:
    """End-to-end tests for heuristic chaining."""

    @patch('src.elasticsearch_client.Elasticsearch')
    def test_full_chain_workflow(self, mock_es):
        """Test complete workflow: store -> retrieve -> chain."""
        # This would be an integration test
        # Skipping implementation for now as it requires full ES setup
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
