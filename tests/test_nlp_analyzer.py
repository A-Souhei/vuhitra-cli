"""
Tests for NLP analyzer.
"""
import pytest
from unittest.mock import Mock, patch
from services.sandbox.src.nlp_analyzer import NLPAnalyzer


class TestNLPAnalyzer:
    """Test NLPAnalyzer functionality."""

    def test_analyze_sentiment_vader_fallback(self):
        """Test sentiment analysis with VADER fallback."""
        # Create analyzer with transformer disabled
        with patch('builtins.open', side_effect=FileNotFoundError):
            analyzer = NLPAnalyzer()

        # Should fall back to VADER
        result = analyzer.analyze_sentiment("I love this! It's wonderful and amazing!")
        assert "vader_score" in result
        assert "spacy_score" in result
        assert result["vader_score"] > 0  # VADER should detect positive sentiment

    def test_analyze_sentiment_transformer_success(self):
        """Test sentiment analysis with transformer service."""
        with patch('requests.post') as mock_post:
            # Mock successful transformer response
            mock_response = Mock()
            mock_response.json.return_value = {'compound': 0.95}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response

            analyzer = NLPAnalyzer()
            result = analyzer.analyze_sentiment("I love this!")

            assert "vader_score" in result
            assert result["vader_score"] == 0.95

    def test_analyze_sentiment_transformer_timeout(self):
        """Test sentiment analysis falls back on timeout."""
        with patch('requests.post', side_effect=Exception("Timeout")):
            analyzer = NLPAnalyzer()
            result = analyzer.analyze_sentiment("I love this!")

            # Should fall back to VADER
            assert "vader_score" in result
            assert isinstance(result["vader_score"], float)

    def test_analyze_sentiment_negative(self):
        """Test negative sentiment analysis."""
        analyzer = NLPAnalyzer()
        result = analyzer.analyze_sentiment("This is terrible and awful!")
        assert result["vader_score"] < 0  # Should detect negative sentiment

    def test_load_sentiment_config(self):
        """Test loading sentiment configuration."""
        analyzer = NLPAnalyzer()

        assert hasattr(analyzer, 'sentiment_config')
        assert isinstance(analyzer.sentiment_config, dict)
        assert 'use_transformer' in analyzer.sentiment_config
        assert 'fallback_to_vader' in analyzer.sentiment_config

    def test_extract_keywords(self):
        """Test keyword extraction."""
        analyzer = NLPAnalyzer()

        text = "Python programming is great for data science and machine learning applications"
        keywords = analyzer.extract_keywords(text, top_n=5)

        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        if analyzer.nlp:  # Only if spaCy model is loaded
            assert len(keywords) > 0

    def test_detect_code_with_python(self):
        """Test code detection with Python code."""
        analyzer = NLPAnalyzer()

        code = """
        def hello_world():
            print("Hello, World!")
            return True
        """

        is_code, purpose = analyzer.detect_code(code)

        assert is_code is True
        assert purpose == "function definition"

    def test_detect_code_with_class(self):
        """Test code detection with class definition."""
        analyzer = NLPAnalyzer()

        code = """
        class MyClass:
            def __init__(self):
                self.value = 0
        """

        is_code, purpose = analyzer.detect_code(code)

        assert is_code is True
        assert purpose == "class definition"

    def test_detect_code_with_conditional(self):
        """Test code detection with conditional logic."""
        analyzer = NLPAnalyzer()

        code = """
        if x > 0:
            print("positive")
        else:
            print("negative")
        """

        is_code, purpose = analyzer.detect_code(code)

        assert is_code is True
        assert purpose == "conditional logic"

    def test_detect_code_with_regular_text(self):
        """Test code detection with regular text."""
        analyzer = NLPAnalyzer()

        text = "This is a regular sentence about programming concepts."

        is_code, purpose = analyzer.detect_code(text)

        assert is_code is False
        assert purpose == ""

    def test_count_words(self):
        """Test word counting."""
        analyzer = NLPAnalyzer()

        text = "This is a test sentence with seven words."
        count = analyzer.count_words(text)

        # "This is a test sentence with seven words." = 8 words total
        assert count == 8

    def test_count_words_empty(self):
        """Test word counting with empty string."""
        analyzer = NLPAnalyzer()

        count = analyzer.count_words("")

        assert count == 0
