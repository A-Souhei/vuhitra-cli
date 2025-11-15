"""Command handler system for special CLI commands.

This module provides a dynamic command handling system that can be
extended with new commands in the future.
"""

from typing import Callable, Dict, Optional, Any
from src.errors_handler import handle_exception


class CommandResult:
    """Result of a command execution."""

    def __init__(self, success: bool, message: str = "", data: Any = None):
        """Initialize command result.

        Args:
            success: Whether the command executed successfully
            message: Optional message to display to user
            data: Optional data returned by the command
        """
        self.success = success
        self.message = message
        self.data = data


class CommandHandler:
    """Handles special CLI commands with /command syntax."""

    def __init__(self):
        """Initialize the command handler."""
        self.commands: Dict[str, Callable] = {}
        self._register_default_commands()

    def _register_default_commands(self):
        """Register default built-in commands."""
        # No default commands yet - will be populated by CLI
        pass

    def register_command(self, command_name: str, handler: Callable) -> None:
        """Register a new command handler.

        Args:
            command_name: Name of the command (without the / prefix)
            handler: Callable that handles the command
                     Should accept (args: list) and return CommandResult
        """
        self.commands[command_name] = handler

    def is_command(self, text: str) -> bool:
        """Check if the text is a command.

        Args:
            text: User input text

        Returns:
            True if text starts with / and matches a registered command
        """
        if not text.startswith('/'):
            return False

        # Extract command name (first word after /)
        parts = text[1:].split()
        if not parts:
            return False

        command_name = parts[0]
        return command_name in self.commands

    def execute(self, text: str) -> Optional[CommandResult]:
        """Execute a command.

        Args:
            text: User input text (should start with /)

        Returns:
            CommandResult if command was executed, None if not a valid command
        """
        if not text.startswith('/'):
            return None

        # Parse command and arguments
        parts = text[1:].split()
        if not parts:
            return CommandResult(
                success=False,
                message="Invalid command format. Use /command [args]"
            )

        command_name = parts[0]
        args = parts[1:]

        # Check if command exists
        if command_name not in self.commands:
            return CommandResult(
                success=False,
                message=f"Unknown command: /{command_name}"
            )

        # Execute command
        try:
            handler = self.commands[command_name]
            return handler(args)
        except Exception as e:
            handle_exception(e, context={
                'function': 'execute_command',
                'command': command_name,
                'args': args
            })
            return CommandResult(
                success=False,
                message=f"Error executing command: {str(e)}"
            )

    def get_available_commands(self) -> list:
        """Get list of available commands.

        Returns:
            List of registered command names
        """
        return list(self.commands.keys())

    def get_help_text(self) -> str:
        """Get help text for all available commands.

        Returns:
            Formatted help text
        """
        if not self.commands:
            return "No commands available."

        lines = ["Available commands:"]
        for cmd in sorted(self.commands.keys()):
            lines.append(f"  /{cmd}")

        return "\n".join(lines)
