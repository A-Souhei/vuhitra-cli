"""
Tests for ElasticSearch client.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from services.sandbox.src.elasticsearch_client import ElasticSearchClient


class TestElasticSearchClient:
    """Test ElasticSearchClient functionality."""

    @patch('services.sandbox.src.elasticsearch_client.Elasticsearch')
    def test_init_successful_connection(self, mock_es_class):
        """Test successful initialization and connection."""
        mock_es = Mock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = False
        mock_es_class.return_value = mock_es
        
        client = ElasticSearchClient(host="localhost", port=9200)
        
        assert client.es is not None
        mock_es.ping.assert_called_once()
        mock_es.indices.create.assert_called_once()

    @patch('services.sandbox.src.elasticsearch_client.Elasticsearch')
    def test_init_failed_connection(self, mock_es_class):
        """Test initialization with failed connection."""
        mock_es = Mock()
        mock_es.ping.return_value = False
        mock_es_class.return_value = mock_es
        
        client = ElasticSearchClient()
        
        assert client.es is not None
        mock_es.ping.assert_called_once()

    @patch('services.sandbox.src.elasticsearch_client.Elasticsearch')
    def test_save_feedback_success(self, mock_es_class):
        """Test successful feedback save."""
        mock_es = Mock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = True
        mock_es.index.return_value = {'_id': 'test123'}
        mock_es_class.return_value = mock_es
        
        client = ElasticSearchClient()
        
        data = {
            "prompt": "test prompt",
            "response": "test response",
            "rating": 5
        }
        
        result = client.save_feedback(data)
        
        assert result is True
        mock_es.index.assert_called_once()
        assert "processed_at" in mock_es.index.call_args[1]["document"]

    @patch('services.sandbox.src.elasticsearch_client.Elasticsearch')
    def test_save_feedback_no_connection(self, mock_es_class):
        """Test feedback save with no connection."""
        mock_es_class.side_effect = Exception("Connection failed")
        
        client = ElasticSearchClient()
        
        result = client.save_feedback({"test": "data"})
        
        assert result is False

    @patch('services.sandbox.src.elasticsearch_client.Elasticsearch')
    def test_is_connected(self, mock_es_class):
        """Test connection check."""
        mock_es = Mock()
        mock_es.ping.return_value = True
        mock_es.indices.exists.return_value = True
        mock_es_class.return_value = mock_es
        
        client = ElasticSearchClient()
        
        assert client.is_connected() is True
        
        mock_es.ping.return_value = False
        assert client.is_connected() is False
