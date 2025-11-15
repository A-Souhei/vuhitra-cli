"""File path completer for @ prefix autocomplete.

This module provides a custom completer that shows file and directory
suggestions when the user types '@' followed by a path.
"""

import os
from pathlib import Path
from typing import Iterable
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class FilePathCompleter(Completer):
    """Completer for file paths with @ prefix.

    When user types '@', this completer shows all files and directories
    in the working directory (recursively), including hidden files.
    """

    def __init__(self, working_dir: str = None, max_depth: int = 5):
        """Initialize the file path completer.

        Args:
            working_dir: Working directory to scan (defaults to current dir)
            max_depth: Maximum recursion depth for directory scanning
        """
        self.working_dir = Path(working_dir or os.getcwd())
        self.max_depth = max_depth
        self._cache = None
        self._cache_timestamp = 0

    def _get_all_paths(self) -> list:
        """Get all file and directory paths recursively.

        Returns:
            List of relative paths from working directory
        """
        paths = []

        def scan_directory(directory: Path, depth: int = 0):
            """Recursively scan directory for files and subdirs."""
            if depth > self.max_depth:
                return

            try:
                for item in directory.iterdir():
                    # Calculate relative path from working directory
                    try:
                        rel_path = item.relative_to(self.working_dir)
                        rel_path_str = str(rel_path)

                        # Add this path
                        paths.append({
                            'path': rel_path_str,
                            'is_dir': item.is_dir(),
                            'is_file': item.is_file(),
                        })

                        # If directory, recurse into it
                        if item.is_dir():
                            scan_directory(item, depth + 1)

                    except (ValueError, OSError):
                        # Skip paths that can't be made relative or accessed
                        continue

            except PermissionError:
                # Skip directories we can't access
                pass

        # Start scanning from working directory
        scan_directory(self.working_dir)

        return paths

    def _should_refresh_cache(self) -> bool:
        """Check if cache should be refreshed.

        Returns:
            True if cache should be refreshed
        """
        # Refresh cache every 5 seconds or if not initialized
        import time
        current_time = time.time()
        if self._cache is None or (current_time - self._cache_timestamp) > 5:
            return True
        return False

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Get completion suggestions for the current input.

        Args:
            document: The current document
            complete_event: Completion event

        Yields:
            Completion objects for matching paths
        """
        text = document.text_before_cursor

        # Only provide completions if text contains '@'
        if '@' not in text:
            return

        # Find the last '@' in the text
        last_at_index = text.rfind('@')

        # Get the text after the '@'
        prefix_text = text[last_at_index + 1:]

        # Refresh cache if needed
        if self._should_refresh_cache():
            self._cache = self._get_all_paths()
            import time
            self._cache_timestamp = time.time()

        # Filter paths that match the prefix
        for path_info in self._cache:
            path = path_info['path']
            is_dir = path_info['is_dir']

            # Check if path starts with the prefix (case-insensitive)
            if path.lower().startswith(prefix_text.lower()):
                # Calculate display text
                display_suffix = '/' if is_dir else ''
                display_text = f"@{path}{display_suffix}"

                # Add metadata to display
                if is_dir:
                    display_meta = "directory"
                else:
                    display_meta = "file"

                # Create completion
                yield Completion(
                    text=path,  # Just the path part (without @)
                    start_position=-len(prefix_text),
                    display=display_text,
                    display_meta=display_meta,
                )


class CombinedCompleter(Completer):
    """Combines multiple completers into one.

    This completer delegates to different completers based on the context.
    - If text contains '@', use FilePathCompleter
    - Otherwise, use the default command completer
    """

    def __init__(self, command_completer: Completer, file_path_completer: FilePathCompleter):
        """Initialize the combined completer.

        Args:
            command_completer: Completer for commands (e.g., WordCompleter)
            file_path_completer: Completer for file paths with @ prefix
        """
        self.command_completer = command_completer
        self.file_path_completer = file_path_completer

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """Get completion suggestions from appropriate completer.

        Args:
            document: The current document
            complete_event: Completion event

        Yields:
            Completion objects from the appropriate completer
        """
        text = document.text_before_cursor

        # If text contains '@', use file path completer
        if '@' in text:
            yield from self.file_path_completer.get_completions(document, complete_event)
        else:
            # Otherwise, use command completer
            yield from self.command_completer.get_completions(document, complete_event)
