"""
Vanisher Directory Manager

Manages vanisher directories for code execution.
Vanisher directories are temporary workspaces that can be used
for writing, updating, and running code.
"""

import os
import logging
import shutil
from pathlib import Path
from typing import Dict, Any

from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class VanisherManager:
    """Manages operations on vanisher directories."""

    def __init__(self):
        """Initialize the vanisher manager."""
        self.workspace_path = Path(os.getenv('WORKSPACE_PATH', '/app/WORKSPACE'))
        self.vanisher_path = self.workspace_path / 'vanishers'

        # Ensure vanisher directory exists
        self.vanisher_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"VanisherManager initialized with workspace: {self.workspace_path}")

    def get_vanisher_dir(self, name: str) -> Path:
        """Get the path to a vanisher directory, creating it if needed.

        Args:
            name: Name of the vanisher directory

        Returns:
            Path to the vanisher directory
        """
        vanisher_dir = self.vanisher_path / name
        vanisher_dir.mkdir(parents=True, exist_ok=True)
        return vanisher_dir

    def resolve_file_path(self, vanisher_name: str, filename: str) -> Path:
        """Resolve a file path within a vanisher directory.

        Args:
            vanisher_name: Name of the vanisher directory
            filename: Name of the file

        Returns:
            Full path to the file
        """
        vanisher_dir = self.get_vanisher_dir(vanisher_name)
        return vanisher_dir / filename

    def list_vanishers(self) -> Dict[str, Any]:
        """List all vanisher directories.

        Returns:
            Dictionary with list of vanisher directories
        """
        try:
            vanishers = []

            if self.vanisher_path.exists():
                for item in self.vanisher_path.iterdir():
                    if item.is_dir():
                        files = list(item.glob('*'))
                        vanishers.append({
                            'name': item.name,
                            'path': str(item),
                            'file_count': len([f for f in files if f.is_file()])
                        })

            return {
                'success': True,
                'count': len(vanishers),
                'vanishers': vanishers
            }

        except Exception as e:
            handle_exception(e, context={'function': 'list_vanishers'})
            return {
                'success': False,
                'error': str(e),
                'vanishers': []
            }

    def list_files(self, vanisher_name: str) -> Dict[str, Any]:
        """List all files in a vanisher directory.

        Args:
            vanisher_name: Name of the vanisher directory

        Returns:
            Dictionary with list of files
        """
        try:
            vanisher_dir = self.get_vanisher_dir(vanisher_name)
            files = []

            for item in vanisher_dir.rglob('*'):
                if item.is_file():
                    rel_path = item.relative_to(vanisher_dir)
                    files.append({
                        'name': str(rel_path),
                        'path': str(item),
                        'size': item.stat().st_size
                    })

            return {
                'success': True,
                'vanisher': vanisher_name,
                'count': len(files),
                'files': files
            }

        except Exception as e:
            handle_exception(e, context={
                'function': 'list_files',
                'vanisher_name': vanisher_name
            })
            return {
                'success': False,
                'error': str(e),
                'files': []
            }

    def delete_vanisher(self, name: str) -> Dict[str, Any]:
        """Delete a vanisher directory and all its contents.

        Args:
            name: Name of the vanisher directory

        Returns:
            Dictionary with deletion result
        """
        try:
            vanisher_dir = self.vanisher_path / name

            if not vanisher_dir.exists():
                return {
                    'success': False,
                    'error': f'Vanisher directory not found: {name}'
                }

            shutil.rmtree(vanisher_dir)

            return {
                'success': True,
                'message': f'Deleted vanisher directory: {name}'
            }

        except Exception as e:
            handle_exception(e, context={
                'function': 'delete_vanisher',
                'name': name
            })
            return {
                'success': False,
                'error': str(e)
            }
