"""Prompt history management for interactive mode.

This module provides prompt history with auto-complete functionality
using prompt_toolkit.
"""

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
import os


class PromptHistoryManager:
    """Manages prompt history with auto-complete functionality."""

    def __init__(self, history_file: str = None):
        """Initialize the prompt history manager.

        Args:
            history_file: Path to history file. If None, uses default location.
        """
        # Set default history file location
        if history_file is None:
            home_dir = os.path.expanduser("~")
            vuhitra_dir = os.path.join(home_dir, ".vuhitra")
            os.makedirs(vuhitra_dir, exist_ok=True)
            history_file = os.path.join(vuhitra_dir, "prompt_history.txt")

        self.history_file = history_file

        # Custom style for the prompt
        self.style = Style.from_dict({
            'prompt': '#00aa00 bold',
            'prompt-symbol': '#00ffff bold',
        })

        # Initialize the prompt session with history and auto-suggest
        self.session = PromptSession(
            history=FileHistory(self.history_file),
            auto_suggest=AutoSuggestFromHistory(),
            enable_history_search=True,
        )

        # Common commands completer
        self.commands = WordCompleter(
            ['exit', 'quit', 'help', 'clear'],
            ignore_case=True,
            sentence=True
        )

    def get_prompt(self) -> str:
        """Get user input with history and auto-complete.

        Returns:
            User input string.

        Raises:
            KeyboardInterrupt: On Ctrl+C
            EOFError: On Ctrl+D
        """
        try:
            # Create styled prompt
            prompt_text = HTML('<prompt-symbol>❯</prompt-symbol> ')

            # Get input with auto-suggest from history
            user_input = self.session.prompt(
                prompt_text,
                style=self.style,
                completer=self.commands,
                complete_while_typing=True,
                vi_mode=False,  # Use emacs mode (can be configured)
            )

            return user_input.strip()

        except (KeyboardInterrupt, EOFError):
            # Re-raise to let the caller handle
            raise

    def clear_history(self):
        """Clear the prompt history file."""
        if os.path.exists(self.history_file):
            os.remove(self.history_file)

    def get_history_count(self) -> int:
        """Get the number of items in history.

        Returns:
            Number of history items.
        """
        if not os.path.exists(self.history_file):
            return 0

        with open(self.history_file, 'r', encoding='utf-8') as f:
            return sum(1 for _ in f)

    def get_recent_history(self, count: int = 10) -> list:
        """Get recent history items.

        Args:
            count: Number of recent items to return.

        Returns:
            List of recent history items.
        """
        if not os.path.exists(self.history_file):
            return []

        with open(self.history_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Return last 'count' items, stripped
        return [line.strip() for line in lines[-count:]]
