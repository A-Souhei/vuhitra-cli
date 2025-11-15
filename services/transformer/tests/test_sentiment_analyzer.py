"""
Tests for sentiment analyzer module.
"""
import pytest
from src.sentiment_analyzer import SentimentAnalyzer


class TestSentimentAnalyzer:
    """Test SentimentAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return SentimentAnalyzer()

    def test_analyze_positive_sentiment(self, analyzer):
        """Test positive sentiment analysis."""
        text = "I love this! It's wonderful and amazing!"
        result = analyzer.analyze(text)

        assert "label" in result
        assert "score" in result
        assert "compound" in result
        assert result["label"] == "POSITIVE"
        assert result["compound"] > 0
        assert 0 <= result["score"] <= 1

    def test_analyze_negative_sentiment(self, analyzer):
        """Test negative sentiment analysis."""
        text = "This is terrible and awful! I hate it."
        result = analyzer.analyze(text)

        assert result["label"] == "NEGATIVE"
        assert result["compound"] < 0
        assert 0 <= result["score"] <= 1

    def test_analyze_neutral_sentiment(self, analyzer):
        """Test neutral sentiment analysis."""
        text = "The product arrived on time."
        result = analyzer.analyze(text)

        assert "label" in result
        assert "compound" in result
        # Compound should be close to 0 for neutral
        assert -0.3 <= result["compound"] <= 0.3

    def test_analyze_empty_text(self, analyzer):
        """Test with empty text."""
        result = analyzer.analyze("")

        assert result["label"] == "NEUTRAL"
        assert result["compound"] == 0.0
        assert result["score"] == 0.5

    def test_analyze_whitespace_only(self, analyzer):
        """Test with whitespace only."""
        result = analyzer.analyze("   \n\t  ")

        assert result["label"] == "NEUTRAL"
        assert result["compound"] == 0.0

    def test_analyze_long_text(self, analyzer):
        """Test with text longer than 512 characters."""
        # Create text > 512 chars
        long_text = "This is great! " * 100  # ~1500 chars
        result = analyzer.analyze(long_text)

        # Should still work (truncated to 512)
        assert "label" in result
        assert result["label"] == "POSITIVE"

    def test_analyze_batch(self, analyzer):
        """Test batch sentiment analysis."""
        texts = [
            "I love this!",
            "This is terrible!",
            "The meeting is at 3pm."
        ]

        results = analyzer.analyze_batch(texts)

        assert len(results) == 3
        assert results[0]["label"] == "POSITIVE"
        assert results[1]["label"] == "NEGATIVE"
        # Third could be POSITIVE or NEGATIVE depending on model
        assert "label" in results[2]

    def test_analyze_batch_empty_list(self, analyzer):
        """Test batch analysis with empty list."""
        results = analyzer.analyze_batch([])

        assert results == []

    def test_compound_score_range(self, analyzer):
        """Test that compound scores are in correct range."""
        texts = [
            "Excellent!",
            "Terrible!",
            "Okay."
        ]

        for text in texts:
            result = analyzer.analyze(text)
            assert -1.0 <= result["compound"] <= 1.0

    def test_get_model_info(self, analyzer):
        """Test model info retrieval."""
        info = analyzer.get_model_info()

        assert "model_name" in info
        assert "model_type" in info
        assert "task" in info
        assert info["model_type"] == "DistilBERT"
        assert info["task"] == "sentiment-analysis"

    def test_lazy_loading(self):
        """Test that model is lazy loaded."""
        analyzer = SentimentAnalyzer()

        # Model should not be loaded yet
        assert analyzer._analyzer is None

        # Analyze should trigger loading
        analyzer.analyze("test")

        # Now model should be loaded
        assert analyzer._analyzer is not None

    def test_consistency(self, analyzer):
        """Test that same input gives same output."""
        text = "This product is amazing!"

        result1 = analyzer.analyze(text)
        result2 = analyzer.analyze(text)

        assert result1["label"] == result2["label"]
        assert abs(result1["compound"] - result2["compound"]) < 0.01
