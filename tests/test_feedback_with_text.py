"""Tests for feedback collector with custom text input via follow-up question."""

import pytest
from unittest.mock import patch, MagicMock
from src.utils.feedback_collector import FeedbackCollector


class TestFeedbackWithText:
    """Test feedback collector with custom text support (two-step flow)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.collector = FeedbackCollector()

    def test_validate_rating_simple(self):
        """Test simple rating validation."""
        rating = self.collector._validate_rating("0")
        assert rating == 0

        rating = self.collector._validate_rating("5")
        assert rating == 5

    def test_validate_rating_invalid(self):
        """Test invalid ratings."""
        rating = self.collector._validate_rating("6")
        assert rating is None

        rating = self.collector._validate_rating("-1")
        assert rating is None

        rating = self.collector._validate_rating("abc")
        assert rating is None

    def test_collect_feedback_low_rating_with_context(self):
        """Test that low ratings (0-2) trigger follow-up question for context."""
        # First input: rating 0, second input: context
        with patch('builtins.input', side_effect=["0", "dogs are omnivorous"]):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback(
                    "Why do dogs kill small animals?",
                    "Dogs are herbivorous"
                )

                assert feedback_data is not None
                assert feedback_data['rating'] == 0
                assert feedback_data['user_feedback'] == "dogs are omnivorous"
                assert 'timestamp' in feedback_data

    def test_collect_feedback_low_rating_without_context(self):
        """Test that user can skip context even on low rating."""
        # First input: rating 0, second input: empty (skip context)
        with patch('builtins.input', side_effect=["0", ""]):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback(
                    "Test prompt",
                    "Test response"
                )

                assert feedback_data is not None
                assert feedback_data['rating'] == 0
                assert 'user_feedback' not in feedback_data or not feedback_data.get('user_feedback')

    def test_collect_feedback_rating_1_triggers_context_question(self):
        """Test that rating 1 also triggers context question (rating <= 2)."""
        with patch('builtins.input', side_effect=["1", "needs more detail"]):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback("test", "test")

                assert feedback_data is not None
                assert feedback_data['rating'] == 1
                assert feedback_data['user_feedback'] == "needs more detail"

    def test_collect_feedback_rating_2_triggers_context_question(self):
        """Test that rating 2 also triggers context question (rating <= 2)."""
        with patch('builtins.input', side_effect=["2", "incorrect fact"]):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback("test", "test")

                assert feedback_data is not None
                assert feedback_data['rating'] == 2
                assert feedback_data['user_feedback'] == "incorrect fact"

    def test_collect_feedback_high_rating_no_context_question(self):
        """Test that high ratings (3-5) don't trigger follow-up question."""
        # Only one input needed - rating 5
        with patch('builtins.input', return_value="5"):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback(
                    "What is 2+2?",
                    "4"
                )

                assert feedback_data is not None
                assert feedback_data['rating'] == 5
                assert 'user_feedback' not in feedback_data or not feedback_data.get('user_feedback')

    def test_collect_feedback_rating_3_no_context_question(self):
        """Test that rating 3 (neutral) doesn't trigger context question."""
        with patch('builtins.input', return_value="3"):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback("test", "test")

                assert feedback_data is not None
                assert feedback_data['rating'] == 3
                assert 'user_feedback' not in feedback_data or not feedback_data.get('user_feedback')

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

    def test_collect_feedback_keyboard_interrupt_on_rating(self):
        """Test that keyboard interrupt on rating input is handled gracefully."""
        with patch('builtins.input', side_effect=KeyboardInterrupt()):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback("test", "test")
                assert feedback_data is None

    def test_collect_feedback_keyboard_interrupt_on_context(self):
        """Test that keyboard interrupt on context input is handled gracefully."""
        # First input: rating 0 (triggers context question), second: keyboard interrupt
        with patch('builtins.input', side_effect=["0", KeyboardInterrupt()]):
            with patch.object(self.collector, 'is_enabled', return_value=True):
                feedback_data = self.collector.collect_feedback("test", "test")

                # Should still return feedback data, just without context
                assert feedback_data is not None
                assert feedback_data['rating'] == 0
                assert 'user_feedback' not in feedback_data or not feedback_data.get('user_feedback')
