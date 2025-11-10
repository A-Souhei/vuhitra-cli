"""
Tests for Heuristics orchestration.
"""
from unittest.mock import Mock, patch
from services.sandbox.src.heuristics import Heuristics


class TestHeuristics:
    """Test Heuristics functionality."""

    @patch('services.sandbox.src.heuristics.ElasticSearchClient')
    @patch('services.sandbox.src.heuristics.NLPAnalyzer')
    def test_init(self, mock_nlp, mock_es):
        """Test Heuristics initialization."""
        heuristics = Heuristics(es_host="localhost", es_port=9200)
        
        assert heuristics.nlp_analyzer is not None
        assert heuristics.es_client is not None

    @patch('services.sandbox.src.heuristics.ElasticSearchClient')
    @patch('services.sandbox.src.heuristics.NLPAnalyzer')
    @patch('services.sandbox.src.heuristics.threading.Thread')
    def test_process_feedback(self, mock_thread, mock_nlp, mock_es):
        """Test process_feedback starts background thread."""
        heuristics = Heuristics()
        
        feedback_data = {
            "prompt": "test prompt",
            "response": "test response",
            "rating": 5,
            "timestamp": "2024-01-01T00:00:00Z",
            "execution_time_ms": 1000
        }
        
        result = heuristics.process_feedback(feedback_data)
        
        assert result["status"] == "acknowledged"
        assert "message" in result
        mock_thread.assert_called_once()

    @patch('services.sandbox.src.heuristics.ElasticSearchClient')
    @patch('services.sandbox.src.heuristics.NLPAnalyzer')
    def test_analyze_and_store(self, mock_nlp_class, mock_es_class):
        """Test _analyze_and_store method."""
        # Setup mocks
        mock_nlp = Mock()
        mock_nlp.analyze_sentiment.return_value = {"vader_score": 0.5, "spacy_score": 0.3}
        mock_nlp.extract_keywords.return_value = ["test", "keyword"]
        mock_nlp.detect_code.return_value = (False, "")
        mock_nlp.count_words.return_value = 5
        mock_nlp_class.return_value = mock_nlp
        
        mock_es = Mock()
        mock_es.save_feedback.return_value = True
        mock_es_class.return_value = mock_es
        
        heuristics = Heuristics()
        
        feedback_data = {
            "prompt": "test prompt",
            "response": "test response",
            "rating": 5,
            "timestamp": "2024-01-01T00:00:00Z",
            "execution_time_ms": 1000
        }
        
        # Call the method directly
        heuristics._analyze_and_store(feedback_data)
        
        # Verify NLP analysis was performed
        mock_nlp.analyze_sentiment.assert_called()
        mock_nlp.extract_keywords.assert_called()
        mock_nlp.detect_code.assert_called()
        
        # Verify data was saved
        mock_es.save_feedback.assert_called_once()
        saved_data = mock_es.save_feedback.call_args[0][0]
        
        assert "prompt" in saved_data
        assert "prompt_keywords" in saved_data
        assert "prompt_sentiment_vader" in saved_data
        assert "response_keywords" in saved_data
        assert "is_code_response" in saved_data

    @patch('services.sandbox.src.heuristics.ElasticSearchClient')
    @patch('services.sandbox.src.heuristics.NLPAnalyzer')
    def test_health_check(self, mock_nlp_class, mock_es_class):
        """Test health check."""
        mock_nlp = Mock()
        mock_nlp.nlp = Mock()  # spaCy model loaded
        mock_nlp_class.return_value = mock_nlp
        
        mock_es = Mock()
        mock_es.is_connected.return_value = True
        mock_es_class.return_value = mock_es
        
        heuristics = Heuristics()
        
        health = heuristics.health_check()
        
        assert "nlp_ready" in health
        assert "elasticsearch_connected" in health
        assert health["nlp_ready"] is True
        assert health["elasticsearch_connected"] is True
