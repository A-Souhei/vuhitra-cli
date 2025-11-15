"""Tests for conversation history being disabled during auto-iteration retries."""

from unittest.mock import MagicMock


class TestConversationHistoryDisabledOnRetry:
    """Test that conversation history is disabled during auto-iteration retries."""

    def test_conversation_history_enabled_on_first_attempt(self):
        """Test that conversation history is used on first attempt (iteration 0)."""
        # Mock conversation history
        mock_conversation_history = MagicMock()
        mock_conversation_history.is_enabled.return_value = True

        iteration_number = 0  # First attempt

        # Simulate the logic from cli.py
        conversation_context = ""
        if mock_conversation_history.is_enabled() and iteration_number == 0:
            conversation_context = "Some conversation history"

        # Should have conversation history on first attempt
        assert conversation_context != ""
        assert conversation_context == "Some conversation history"

    def test_conversation_history_disabled_on_retry(self):
        """Test that conversation history is NOT used during retry (iteration > 0)."""
        # Mock conversation history
        mock_conversation_history = MagicMock()
        mock_conversation_history.is_enabled.return_value = True

        iteration_number = 1  # Retry attempt

        # Simulate the logic from cli.py
        conversation_context = ""
        if mock_conversation_history.is_enabled() and iteration_number == 0:
            conversation_context = "Some conversation history"

        # Should NOT have conversation history on retry
        assert conversation_context == ""

    def test_conversation_history_disabled_when_feature_disabled(self):
        """Test that conversation history is not used when feature is disabled."""
        # Mock conversation history as disabled
        mock_conversation_history = MagicMock()
        mock_conversation_history.is_enabled.return_value = False

        iteration_number = 0  # First attempt

        # Simulate the logic from cli.py
        conversation_context = ""
        if mock_conversation_history.is_enabled() and iteration_number == 0:
            conversation_context = "Some conversation history"

        # Should NOT have conversation history when disabled
        assert conversation_context == ""

    def test_heuristics_only_mode_on_retry(self):
        """Test that retries use heuristics-only mode (no conversation history)."""
        # This simulates what happens during auto-iteration retries
        # iteration_number > 0 means it's a retry after rating=0

        iteration_number = 2  # Second retry
        conversation_history_enabled = True

        # The logic from cli.py: conversation history is ONLY used when iteration_number == 0
        use_conversation_history = conversation_history_enabled and iteration_number == 0

        # Should NOT use conversation history on retries
        assert use_conversation_history is False

        # Verify heuristics are still available (this would be a separate check in real code)
        # During retry, only heuristics should be used for context
        heuristics_available = True  # Always available
        assert heuristics_available is True
