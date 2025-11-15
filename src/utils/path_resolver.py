"""Path resolver for @ prefix paths.

This module provides utilities to resolve @ prefix paths to actual file paths
relative to the working directory.
"""

import os
from pathlib import Path
from typing import Tuple, List
from src.errors_handler import handle_exception


class PathResolver:
    """Resolves @ prefix paths to actual file paths."""

    def __init__(self, working_dir: str = None):
        """Initialize the path resolver.

        Args:
            working_dir: Working directory for path resolution. If None, uses current dir.
        """
        self.working_dir = Path(working_dir or os.getcwd())

    def is_at_prefix_path(self, path: str) -> bool:
        """Check if a path uses the @ prefix.

        Args:
            path: Path to check

        Returns:
            True if path starts with @, False otherwise
        """
        return path.strip().startswith('@')

    def resolve_at_path(self, path: str) -> Tuple[bool, str, str]:
        """Resolve an @ prefix path to actual file path.

        Args:
            path: Path with @ prefix (e.g., '@howto.md' or '@docs/')

        Returns:
            Tuple of (success, resolved_path, error_message)
            - If success: (True, resolved_path, "")
            - If error: (False, "", error_message)
        """
        # Remove @ prefix
        if not self.is_at_prefix_path(path):
            return False, "", f"Path does not start with @: {path}"

        relative_path = path.strip()[1:]  # Remove '@'

        if not relative_path:
            return False, "", "No path specified after @"

        # Resolve path relative to working directory
        full_path = self.working_dir / relative_path

        # Check if path exists
        if not full_path.exists():
            return False, "", f"Path not found: {relative_path} (resolved to: {full_path})"

        return True, str(full_path), ""

    def resolve_path(self, path: str) -> Tuple[bool, str, str]:
        """Resolve a path (with or without @ prefix).

        Args:
            path: Path to resolve

        Returns:
            Tuple of (success, resolved_path, error_message)
        """
        if self.is_at_prefix_path(path):
            return self.resolve_at_path(path)
        else:
            # Regular path, just return it (let file loaders handle validation)
            return True, path, ""

    def is_directory(self, path: str) -> bool:
        """Check if a resolved path is a directory.

        Args:
            path: Path to check (can have @ prefix)

        Returns:
            True if path is a directory, False otherwise
        """
        success, resolved_path, _ = self.resolve_path(path)
        if not success:
            return False

        return Path(resolved_path).is_dir()

    def is_file(self, path: str) -> bool:
        """Check if a resolved path is a file.

        Args:
            path: Path to check (can have @ prefix)

        Returns:
            True if path is a file, False otherwise
        """
        success, resolved_path, _ = self.resolve_path(path)
        if not success:
            return False

        return Path(resolved_path).is_file()

    def get_directory_files(self, dir_path: str) -> Tuple[bool, List[str], str]:
        """Get all files in a directory (non-recursive).

        Args:
            dir_path: Directory path (can have @ prefix)

        Returns:
            Tuple of (success, file_paths, error_message)
        """
        success, resolved_path, error = self.resolve_path(dir_path)
        if not success:
            return False, [], error

        path = Path(resolved_path)
        if not path.is_dir():
            return False, [], f"Path is not a directory: {dir_path}"

        try:
            files = [str(f) for f in path.iterdir() if f.is_file()]
            return True, files, ""
        except PermissionError as e:
            handle_exception(e, context={
                'function': 'get_directory_files',
                'dir_path': dir_path,
                'resolved_path': resolved_path,
                'error_type': 'PermissionError'
            })
            return False, [], f"Permission denied: {dir_path}"
        except Exception as e:
            handle_exception(e, context={
                'function': 'get_directory_files',
                'dir_path': dir_path,
                'resolved_path': resolved_path,
                'error_type': 'GeneralException'
            })
            return False, [], f"Error reading directory: {str(e)}"


# Global instance
_path_resolver = None


def get_path_resolver(working_dir: str = None) -> PathResolver:
    """Get the global path resolver instance.

    Args:
        working_dir: Working directory for path resolution

    Returns:
        PathResolver instance
    """
    global _path_resolver
    if _path_resolver is None or working_dir is not None:
        _path_resolver = PathResolver(working_dir=working_dir)
    return _path_resolver
