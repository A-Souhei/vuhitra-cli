"""
File Operations Tools

Provides tools for creating, updating, and managing files.
"""

import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from mirror_vanisher import MirrorVanisherManager
from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class FileOperationsTools:
    """Tools for file creation, modification, and management."""

    def __init__(self, manager: MirrorVanisherManager):
        """Initialize file operations tools.

        Args:
            manager: Mirror+Vanisher manager instance
        """
        self.manager = manager
        logger.info("FileOperationsTools initialized")

    def create_file(self, path: str, file_path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
        """Create a new file with the specified content.

        Args:
            path: Working directory (mirror+vanisher)
            file_path: Path to the new file relative to working directory
            content: File content to write
            overwrite: Whether to overwrite if file exists

        Returns:
            Creation result with file path and status
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            target_file = resolved_path / file_path

            # Check if file exists
            if target_file.exists() and not overwrite:
                return {
                    'success': False,
                    'error': f'File already exists: {file_path}. Use overwrite=true to replace it.'
                }

            # Create parent directories if needed
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Write content to file
            target_file.write_text(content, encoding='utf-8')

            return {
                'success': True,
                'file_path': str(target_file),
                'relative_path': file_path,
                'size_bytes': len(content.encode('utf-8')),
                'lines': content.count('\n') + 1,
                'action': 'overwritten' if (target_file.exists() and overwrite) else 'created'
            }

        except Exception as e:
            handle_exception(e, context={'function': 'create_file', 'path': path, 'file': file_path})
            return {'success': False, 'error': str(e)}

    def update_file(self, path: str, file_path: str, content: str, backup: bool = True) -> Dict[str, Any]:
        """Update an existing file with new content.

        Args:
            path: Working directory (mirror+vanisher)
            file_path: Path to the file relative to working directory
            content: New content to write
            backup: Whether to create a backup before updating

        Returns:
            Update result with file path and backup info
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            target_file = resolved_path / file_path

            if not target_file.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            backup_path = None
            if backup:
                # Create backup with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = target_file.with_suffix(f'{target_file.suffix}.backup_{timestamp}')
                shutil.copy2(target_file, backup_path)

            # Update file
            old_size = target_file.stat().st_size
            target_file.write_text(content, encoding='utf-8')
            new_size = len(content.encode('utf-8'))

            return {
                'success': True,
                'file_path': str(target_file),
                'relative_path': file_path,
                'old_size_bytes': old_size,
                'new_size_bytes': new_size,
                'backup_path': str(backup_path) if backup_path else None,
                'lines': content.count('\n') + 1
            }

        except Exception as e:
            handle_exception(e, context={'function': 'update_file', 'path': path, 'file': file_path})
            return {'success': False, 'error': str(e)}

    def append_to_file(self, path: str, file_path: str, content: str) -> Dict[str, Any]:
        """Append content to an existing file.

        Args:
            path: Working directory (mirror+vanisher)
            file_path: Path to the file relative to working directory
            content: Content to append

        Returns:
            Append result with file path and size info
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            target_file = resolved_path / file_path

            if not target_file.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            old_size = target_file.stat().st_size

            # Append content
            with target_file.open('a', encoding='utf-8') as f:
                f.write(content)

            new_size = target_file.stat().st_size

            return {
                'success': True,
                'file_path': str(target_file),
                'relative_path': file_path,
                'old_size_bytes': old_size,
                'new_size_bytes': new_size,
                'appended_bytes': new_size - old_size
            }

        except Exception as e:
            handle_exception(e, context={'function': 'append_to_file', 'path': path, 'file': file_path})
            return {'success': False, 'error': str(e)}

    def delete_file(self, path: str, file_path: str, backup: bool = True) -> Dict[str, Any]:
        """Delete a file with optional backup.

        Args:
            path: Working directory (mirror+vanisher)
            file_path: Path to the file relative to working directory
            backup: Whether to create a backup before deleting

        Returns:
            Deletion result with backup info
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            target_file = resolved_path / file_path

            if not target_file.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            backup_path = None
            if backup:
                # Create backup with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_dir = resolved_path / '.backups'
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / f'{target_file.name}.deleted_{timestamp}'
                shutil.copy2(target_file, backup_path)

            # Delete file
            file_size = target_file.stat().st_size
            target_file.unlink()

            return {
                'success': True,
                'deleted_file': str(target_file),
                'relative_path': file_path,
                'size_bytes': file_size,
                'backup_path': str(backup_path) if backup_path else None
            }

        except Exception as e:
            handle_exception(e, context={'function': 'delete_file', 'path': path, 'file': file_path})
            return {'success': False, 'error': str(e)}

    def copy_file(self, path: str, source_file: str, dest_file: str, overwrite: bool = False) -> Dict[str, Any]:
        """Copy a file to a new location.

        Args:
            path: Working directory (mirror+vanisher)
            source_file: Source file path relative to working directory
            dest_file: Destination file path relative to working directory
            overwrite: Whether to overwrite if destination exists

        Returns:
            Copy result with source and destination info
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            source = resolved_path / source_file
            destination = resolved_path / dest_file

            if not source.exists():
                return {'success': False, 'error': f'Source file not found: {source_file}'}

            if destination.exists() and not overwrite:
                return {
                    'success': False,
                    'error': f'Destination file already exists: {dest_file}. Use overwrite=true to replace it.'
                }

            # Create destination parent directories if needed
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source, destination)

            return {
                'success': True,
                'source_path': str(source),
                'destination_path': str(destination),
                'source_relative': source_file,
                'destination_relative': dest_file,
                'size_bytes': destination.stat().st_size
            }

        except Exception as e:
            handle_exception(e, context={'function': 'copy_file', 'path': path})
            return {'success': False, 'error': str(e)}

    def move_file(self, path: str, source_file: str, dest_file: str, overwrite: bool = False) -> Dict[str, Any]:
        """Move a file to a new location.

        Args:
            path: Working directory (mirror+vanisher)
            source_file: Source file path relative to working directory
            dest_file: Destination file path relative to working directory
            overwrite: Whether to overwrite if destination exists

        Returns:
            Move result with source and destination info
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            source = resolved_path / source_file
            destination = resolved_path / dest_file

            if not source.exists():
                return {'success': False, 'error': f'Source file not found: {source_file}'}

            if destination.exists() and not overwrite:
                return {
                    'success': False,
                    'error': f'Destination file already exists: {dest_file}. Use overwrite=true to replace it.'
                }

            # Create destination parent directories if needed
            destination.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(source), str(destination))

            return {
                'success': True,
                'old_path': str(source),
                'new_path': str(destination),
                'source_relative': source_file,
                'destination_relative': dest_file,
                'size_bytes': destination.stat().st_size
            }

        except Exception as e:
            handle_exception(e, context={'function': 'move_file', 'path': path})
            return {'success': False, 'error': str(e)}
