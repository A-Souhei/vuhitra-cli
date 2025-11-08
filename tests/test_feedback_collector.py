"""
Unit tests for the FeedbackCollector class.

Tests cover:
- Valid ratings (0-5)
- Invalid input (letters, negative numbers, out of range)
- Empty input (pressing Enter)
- Config flag behavior
- Feedback data structure
"""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
from src.utils.feedback_collector import FeedbackCollector


class TestFeedbackCollector(unittest.TestCase):
    """Test suite for FeedbackCollector class."""

    def setUp(self):
        """Set up test fixtures before each test."""
        self.prompt = "What is Python?"
        self.response = "Python is a high-level programming language."

    @patch('src.utils.feedback_collector.ConfigLoader')
    def test_is_enabled_returns_true_when_config_enabled(self, mock_config_loader):
        """Test that is_enabled returns True when feedback is enabled in config."""
        # Mock the config loader to return True for feedback enabled
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = True
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        self.assertTrue(collector.is_enabled())

    @patch('src.utils.feedback_collector.ConfigLoader')
    def test_is_enabled_returns_false_when_config_disabled(self, mock_config_loader):
        """Test that is_enabled returns False when feedback is disabled in config."""
        # Mock the config loader to return False for feedback disabled
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = False
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        self.assertFalse(collector.is_enabled())

    @patch('src.utils.feedback_collector.ConfigLoader')
    @patch('builtins.input', return_value='3')
    @patch('builtins.print')
    def test_collect_feedback_with_valid_rating(self, mock_print, mock_input, mock_config_loader):
        """Test collecting feedback with a valid rating (0-5)."""
        # Mock config to enable feedback
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = True
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        feedback_data = collector.collect_feedback(self.prompt, self.response)

        # Assert feedback data structure
        self.assertIsNotNone(feedback_data)
        self.assertEqual(feedback_data['prompt'], self.prompt)
        self.assertEqual(feedback_data['response'], self.response)
        self.assertEqual(feedback_data['rating'], 3)
        self.assertIn('timestamp', feedback_data)
        # Verify timestamp is ISO format
        datetime.fromisoformat(feedback_data['timestamp'])

    @patch('src.utils.feedback_collector.ConfigLoader')
    @patch('builtins.input', return_value='')
    @patch('builtins.print')
    def test_collect_feedback_with_empty_input(self, mock_print, mock_input, mock_config_loader):
        """Test that empty input (pressing Enter) returns None."""
        # Mock config to enable feedback
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = True
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        feedback_data = collector.collect_feedback(self.prompt, self.response)

        # Should return None for empty input
        self.assertIsNone(feedback_data)

    @patch('src.utils.feedback_collector.ConfigLoader')
    @patch('builtins.input', return_value='abc')
    @patch('builtins.print')
    def test_collect_feedback_with_letters(self, mock_print, mock_input, mock_config_loader):
        """Test that letter input is rejected and shows error message."""
        # Mock config to enable feedback
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = True
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        feedback_data = collector.collect_feedback(self.prompt, self.response)

        # Should return None for invalid input
        self.assertIsNone(feedback_data)
        # Check that "Skipping feedback." was printed
        mock_print.assert_any_call("Skipping feedback.")

    @patch('src.utils.feedback_collector.ConfigLoader')
    @patch('builtins.input', return_value='10')
    @patch('builtins.print')
    def test_collect_feedback_with_out_of_range_high(self, mock_print, mock_input, mock_config_loader):
        """Test that ratings > 5 are rejected."""
        # Mock config to enable feedback
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = True
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        feedback_data = collector.collect_feedback(self.prompt, self.response)

        # Should return None for out of range input
        self.assertIsNone(feedback_data)
        mock_print.assert_any_call("Skipping feedback.")

    @patch('src.utils.feedback_collector.ConfigLoader')
    @patch('builtins.input', return_value='-1')
    @patch('builtins.print')
    def test_collect_feedback_with_negative_number(self, mock_print, mock_input, mock_config_loader):
        """Test that negative ratings are rejected."""
        # Mock config to enable feedback
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = True
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        feedback_data = collector.collect_feedback(self.prompt, self.response)

        # Should return None for negative input
        self.assertIsNone(feedback_data)
        mock_print.assert_any_call("Skipping feedback.")

    @patch('src.utils.feedback_collector.ConfigLoader')
    @patch('builtins.input', return_value='0')
    @patch('builtins.print')
    def test_collect_feedback_with_rating_zero(self, mock_print, mock_input, mock_config_loader):
        """Test that rating 0 (Disappointed) is accepted."""
        # Mock config to enable feedback
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = True
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        feedback_data = collector.collect_feedback(self.prompt, self.response)

        # Should accept 0 as valid rating
        self.assertIsNotNone(feedback_data)
        self.assertEqual(feedback_data['rating'], 0)

    @patch('src.utils.feedback_collector.ConfigLoader')
    @patch('builtins.input', return_value='5')
    @patch('builtins.print')
    def test_collect_feedback_with_rating_five(self, mock_print, mock_input, mock_config_loader):
        """Test that rating 5 (Very satisfied) is accepted."""
        # Mock config to enable feedback
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = True
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        feedback_data = collector.collect_feedback(self.prompt, self.response)

        # Should accept 5 as valid rating
        self.assertIsNotNone(feedback_data)
        self.assertEqual(feedback_data['rating'], 5)

    @patch('src.utils.feedback_collector.ConfigLoader')
    @patch('builtins.input', return_value='3')
    @patch('builtins.print')
    def test_collect_feedback_when_disabled(self, mock_print, mock_input, mock_config_loader):
        """Test that feedback is not collected when disabled in config."""
        # Mock config to disable feedback
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = False
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        feedback_data = collector.collect_feedback(self.prompt, self.response)

        # Should return None when disabled
        self.assertIsNone(feedback_data)
        # Input should not be called when disabled
        mock_input.assert_not_called()

    @patch('src.utils.feedback_collector.ConfigLoader')
    @patch('builtins.input', side_effect=KeyboardInterrupt)
    @patch('builtins.print')
    def test_collect_feedback_with_keyboard_interrupt(self, mock_print, mock_input, mock_config_loader):
        """Test that Ctrl+C during feedback is handled gracefully."""
        # Mock config to enable feedback
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = True
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        feedback_data = collector.collect_feedback(self.prompt, self.response)

        # Should return None and handle interrupt gracefully
        self.assertIsNone(feedback_data)
        # Check that "Skipping feedback." was printed
        mock_print.assert_any_call("\nSkipping feedback.")

    @patch('src.utils.feedback_collector.ConfigLoader')
    @patch('builtins.input', side_effect=EOFError)
    @patch('builtins.print')
    def test_collect_feedback_with_eof(self, mock_print, mock_input, mock_config_loader):
        """Test that EOF during feedback is handled gracefully."""
        # Mock config to enable feedback
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = True
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        feedback_data = collector.collect_feedback(self.prompt, self.response)

        # Should return None and handle EOF gracefully
        self.assertIsNone(feedback_data)
        # Check that "Skipping feedback." was printed
        mock_print.assert_any_call("\nSkipping feedback.")

    @patch('src.utils.feedback_collector.ConfigLoader')
    @patch('builtins.input', return_value='4')
    @patch('builtins.print')
    def test_feedback_data_structure(self, mock_print, mock_input, mock_config_loader):
        """Test that feedback data has the correct structure for ElasticSearch."""
        # Mock config to enable feedback
        mock_instance = MagicMock()
        mock_instance.get_feedback_enabled.return_value = True
        mock_config_loader.return_value = mock_instance

        collector = FeedbackCollector()
        feedback_data = collector.collect_feedback(self.prompt, self.response)

        # Verify all expected fields are present
        expected_fields = ['prompt', 'response', 'rating', 'timestamp']
        for field in expected_fields:
            self.assertIn(field, feedback_data)

        # Verify data types
        self.assertIsInstance(feedback_data['prompt'], str)
        self.assertIsInstance(feedback_data['response'], str)
        self.assertIsInstance(feedback_data['rating'], int)
        self.assertIsInstance(feedback_data['timestamp'], str)

        # Verify rating is in valid range
        self.assertGreaterEqual(feedback_data['rating'], 0)
        self.assertLessEqual(feedback_data['rating'], 5)


if __name__ == '__main__':
    unittest.main()
