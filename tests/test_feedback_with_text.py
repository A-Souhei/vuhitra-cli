"""Tests for feedback collector with custom text input."""

import pytest
from unittest.mock import patch, MagicMock
from src.utils.feedback_collector import FeedbackCollector


class TestFeedbackWithText:
    """Test feedback collector with custom text support."""

    def setup_method(self):
        """Set up test fixtures."""
        self.collector = FeedbackCollector()

    def test_validate_rating_simple(self):
        """Test simple rating without text."""
        rating, feedback_text = self.collector._validate_rating("0")
        assert rating == 0
        assert feedback_text is None

        rating, feedback_text = self.collector._validate_rating("5")
        assert rating == 5
        assert feedback_text is None

    def test_validate_rating_with_text(self):
        """Test rating with custom feedback text."""
        rating, feedback_text = self.collector._validate_rating("0 dogs are omnivorous")
        assert rating == 0
        assert feedback_text == "dogs are omnivorous"

        rating, feedback_text = self.collector._validate_rating("5 great answer!")
        assert rating == 5
        assert feedback_text == "great answer!"

    def test_validate_rating_with_colon_separator(self):
        """Test rating with colon separator."""
        rating, feedback_text = self.collector._validate_rating("0: dogs are omnivorous")
        assert rating == 0
        assert feedback_text == "dogs are omnivorous"

        rating, feedback_text = self.collector._validate_rating("3:needs more detail")
        assert rating == 3
        assert feedback_text == "needs more detail"

    def test_validate_rating_with_hyphen_separator(self):
        """Test rating with hyphen separator."""
        rating, feedback_text = self.collector._validate_rating("0- incorrect fact")
        assert rating == 0
        assert feedback_text == "incorrect fact"

        rating, feedback_text = self.collector._validate_rating("2 - could be better")
        assert rating == 2
        assert feedback_text == "could be better"

    def test_validate_rating_with_semicolon_separator(self):
        """Test rating with semicolon separator."""
        rating, feedback_text = self.collector._validate_rating("0; wrong answer")
        assert rating == 0
        assert feedback_text == "wrong answer"

    def test_validate_rating_invalid(self):
        """Test invalid ratings."""
        rating, feedback_text = self.collector._validate_rating("6")
        assert rating is None
        assert feedback_text is None

        rating, feedback_text = self.collector._validate_rating("-1")
        assert rating is None
        assert feedback_text is None

        rating, feedback_text = self.collector._validate_rating("abc")
        assert rating is None
        assert feedback_text is None

    def test_validate_rating_with_extra_spaces(self):
        """Test rating with extra spaces."""
        rating, feedback_text = self.collector._validate_rating("0   dogs are omnivorous")
        assert rating == 0
        assert feedback_text == "dogs are omnivorous"

        rating, feedback_text = self.collector._validate_rating("5 :  great!")
        assert rating == 5
        assert feedback_text == "great!"

    def test_collect_feedback_with_text(self):
        """Test full feedback collection flow with custom text."""
        with patch('builtins.input', return_value="0 dogs are omnivorous"):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback(
                    "Why do dogs kill small animals?",
                    "Dogs are herbivorous"
                )

                assert feedback_data is not None
                assert feedback_data['rating'] == 0
                assert feedback_data['user_feedback'] == "dogs are omnivorous"
                assert 'timestamp' in feedback_data

    def test_collect_feedback_without_text(self):
        """Test feedback collection without custom text."""
        with patch('builtins.input', return_value="5"):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback(
                    "What is 2+2?",
                    "4"
                )

                assert feedback_data is not None
                assert feedback_data['rating'] == 5
                assert 'user_feedback' not in feedback_data or feedback_data.get('user_feedback') is None

    def test_collect_feedback_disabled(self):
        """Test that feedback is not collected when disabled."""
        with patch.object(self.collector, 'is_enabled', return_value=False):
            feedback_data = self.collector.collect_feedback("test", "test")
            assert feedback_data is None

    def test_collect_feedback_empty_input(self):
        """Test that empty input skips feedback."""
        with patch('builtins.input', return_value=""):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback("test", "test")
                assert feedback_data is None

    def test_collect_feedback_keyboard_interrupt(self):
        """Test that keyboard interrupt is handled gracefully."""
        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback("test", "test")
                assert feedback_data is None
