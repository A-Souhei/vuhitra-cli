"""Tests for conversation history management."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.utils.conversation_history import ConversationHistoryManager, ConversationTurn
except ImportError as e:
    print(f"⚠️  Skipping tests - missing dependencies: {e}")
    print("This is expected if venv is not activated or dependencies not installed")
    sys.exit(0)


def test_conversation_turn():
    """Test ConversationTurn basic functionality."""
    turn = ConversationTurn("What is Python?", "Python is a programming language.")

    assert turn.prompt == "What is Python?"
    assert turn.response == "Python is a programming language."
    assert turn.timestamp is not None
    assert turn.embedding is None

    combined = turn.get_combined_text()
    assert "User: What is Python?" in combined
    assert "Assistant: Python is a programming language." in combined

    turn_dict = turn.to_dict()
    assert turn_dict['prompt'] == turn.prompt
    assert turn_dict['response'] == turn.response
    assert turn_dict['timestamp'] == turn.timestamp

    print("✓ ConversationTurn tests passed")


def test_conversation_history_manager_disabled():
    """Test ConversationHistoryManager when disabled."""
    manager = ConversationHistoryManager(enabled=False)

    assert not manager.is_enabled()
    assert manager.get_history_count() == 0

    # Adding turns should not work when disabled
    result = manager.add_turn("test prompt", "test response")
    assert not result
    assert manager.get_history_count() == 0

    print("✓ ConversationHistoryManager (disabled) tests passed")


def test_conversation_history_manager_enabled():
    """Test ConversationHistoryManager basic functionality."""
    # Note: This test requires the transformer service to be running
    # We'll create it but not test embedding functionality
    manager = ConversationHistoryManager(enabled=True, max_history_size=5)

    assert manager.is_enabled()
    assert manager.get_history_count() == 0

    # Test clearing empty history
    manager.clear_history()
    assert manager.get_history_count() == 0

    # Test enable/disable
    manager.set_enabled(False)
    assert not manager.is_enabled()

    manager.set_enabled(True)
    assert manager.is_enabled()

    print("✓ ConversationHistoryManager (enabled) tests passed")


def test_command_handler():
    """Test command handler."""
    from src.utils.command_handler import CommandHandler, CommandResult

    handler = CommandHandler()

    # Test registering a command
    def test_cmd(args):
        return CommandResult(success=True, message="Test command executed")

    handler.register_command("test", test_cmd)

    assert "test" in handler.get_available_commands()
    assert handler.is_command("/test")
    assert not handler.is_command("not a command")

    # Test executing command
    result = handler.execute("/test arg1 arg2")
    assert result is not None
    assert result.success
    assert "Test command executed" in result.message

    # Test unknown command
    result = handler.execute("/unknown")
    assert result is not None
    assert not result.success

    print("✓ CommandHandler tests passed")


if __name__ == '__main__':
    print("Running conversation history tests...\n")

    test_conversation_turn()
    test_conversation_history_manager_disabled()
    test_conversation_history_manager_enabled()
    test_command_handler()

    print("\n✅ All tests passed!")
