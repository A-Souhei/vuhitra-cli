"""
Directory Operations

Provides tools for creating, managing, and manipulating directories.
"""

import shutil
import logging
from pathlib import Path
from typing import Dict, Any

from mirror_vanisher import MirrorVanisherManager
from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class DirectoryOperationsTools:
    """Tools for directory creation and management."""

    def __init__(self, manager: MirrorVanisherManager):
        """Initialize directory operations tools.

        Args:
            manager: Mirror+Vanisher manager instance
        """
        self.manager = manager
        logger.info("DirectoryOperationsTools initialized")

    def create_directory(self, path: str, directory_path: str, parents: bool = True) -> Dict[str, Any]:
        """Create a new directory.

        Args:
            path: Working directory (mirror+vanisher)
            directory_path: Path to the new directory relative to working directory
            parents: Whether to create parent directories if they don't exist

        Returns:
            Directory creation result
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            target_dir = resolved_path / directory_path

            if target_dir.exists():
                return {'success': False, 'error': f'Directory already exists: {directory_path}'}

            target_dir.mkdir(parents=parents, exist_ok=False)

            return {
                'success': True,
                'directory_path': str(target_dir),
                'relative_path': directory_path,
                'parents_created': parents
            }

        except Exception as e:
            handle_exception(e, context={'function': 'create_directory', 'path': path, 'dir': directory_path})
            return {'success': False, 'error': str(e)}

    def create_directory_structure(self, path: str, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Create a directory structure from a dictionary specification.

        Args:
            path: Working directory (mirror+vanisher)
            structure: Dictionary defining directory structure
                      {'dir1': {}, 'dir2': {'subdir1': {}, 'subdir2': {}}}

        Returns:
            Directory structure creation result
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            created_dirs = []

            def create_recursive(base: Path, struct: Dict):
                for name, subdirs in struct.items():
                    dir_path = base / name
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(str(dir_path.relative_to(resolved_path)))
                    if isinstance(subdirs, dict) and subdirs:
                        create_recursive(dir_path, subdirs)

            create_recursive(resolved_path, structure)

            return {
                'success': True,
                'created_directories': created_dirs,
                'count': len(created_dirs),
                'base_path': str(resolved_path)
            }

        except Exception as e:
            handle_exception(e, context={'function': 'create_directory_structure', 'path': path})
            return {'success': False, 'error': str(e)}

    def delete_directory(self, path: str, directory_path: str, recursive: bool = False, backup: bool = True) -> Dict[str, Any]:
        """Delete a directory.

        Args:
            path: Working directory (mirror+vanisher)
            directory_path: Path to the directory relative to working directory
            recursive: Whether to delete directory contents recursively
            backup: Whether to create a backup before deleting

        Returns:
            Directory deletion result
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            target_dir = resolved_path / directory_path

            if not target_dir.exists():
                return {'success': False, 'error': f'Directory not found: {directory_path}'}

            if not target_dir.is_dir():
                return {'success': False, 'error': f'Path is not a directory: {directory_path}'}

            backup_path = None
            if backup and recursive:
                # Create backup archive
                from datetime import datetime
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_dir = resolved_path / '.backups'
                backup_dir.mkdir(exist_ok=True)
                backup_name = f'{target_dir.name}_deleted_{timestamp}'
                backup_path = shutil.make_archive(
                    str(backup_dir / backup_name),
                    'zip',
                    str(target_dir.parent),
                    target_dir.name
                )

            # Delete directory
            if recursive:
                shutil.rmtree(target_dir)
            else:
                target_dir.rmdir()  # Only works if directory is empty

            return {
                'success': True,
                'deleted_directory': str(target_dir),
                'relative_path': directory_path,
                'backup_archive': backup_path if backup_path else None,
                'recursive': recursive
            }

        except Exception as e:
            handle_exception(e, context={'function': 'delete_directory', 'path': path, 'dir': directory_path})
            return {'success': False, 'error': str(e)}

    def copy_directory(self, path: str, source_dir: str, dest_dir: str, overwrite: bool = False) -> Dict[str, Any]:
        """Copy a directory to a new location.

        Args:
            path: Working directory (mirror+vanisher)
            source_dir: Source directory path relative to working directory
            dest_dir: Destination directory path relative to working directory
            overwrite: Whether to overwrite if destination exists

        Returns:
            Directory copy result
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            source = resolved_path / source_dir
            destination = resolved_path / dest_dir

            if not source.exists():
                return {'success': False, 'error': f'Source directory not found: {source_dir}'}

            if not source.is_dir():
                return {'success': False, 'error': f'Source path is not a directory: {source_dir}'}

            if destination.exists():
                if not overwrite:
                    return {
                        'success': False,
                        'error': f'Destination directory already exists: {dest_dir}. Use overwrite=true to replace it.'
                    }
                else:
                    shutil.rmtree(destination)

            # Copy directory
            shutil.copytree(source, destination)

            # Count files
            file_count = sum(1 for _ in destination.rglob('*') if _.is_file())

            return {
                'success': True,
                'source_path': str(source),
                'destination_path': str(destination),
                'source_relative': source_dir,
                'destination_relative': dest_dir,
                'file_count': file_count
            }

        except Exception as e:
            handle_exception(e, context={'function': 'copy_directory', 'path': path})
            return {'success': False, 'error': str(e)}

    def move_directory(self, path: str, source_dir: str, dest_dir: str, overwrite: bool = False) -> Dict[str, Any]:
        """Move a directory to a new location.

        Args:
            path: Working directory (mirror+vanisher)
            source_dir: Source directory path relative to working directory
            dest_dir: Destination directory path relative to working directory
            overwrite: Whether to overwrite if destination exists

        Returns:
            Directory move result
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            source = resolved_path / source_dir
            destination = resolved_path / dest_dir

            if not source.exists():
                return {'success': False, 'error': f'Source directory not found: {source_dir}'}

            if not source.is_dir():
                return {'success': False, 'error': f'Source path is not a directory: {source_dir}'}

            if destination.exists():
                if not overwrite:
                    return {
                        'success': False,
                        'error': f'Destination directory already exists: {dest_dir}. Use overwrite=true to replace it.'
                    }
                else:
                    shutil.rmtree(destination)

            # Move directory
            shutil.move(str(source), str(destination))

            # Count files
            file_count = sum(1 for _ in destination.rglob('*') if _.is_file())

            return {
                'success': True,
                'old_path': str(source),
                'new_path': str(destination),
                'source_relative': source_dir,
                'destination_relative': dest_dir,
                'file_count': file_count
            }

        except Exception as e:
            handle_exception(e, context={'function': 'move_directory', 'path': path})
            return {'success': False, 'error': str(e)}

    def list_directory_contents(self, path: str, directory_path: str = '.', recursive: bool = False, files_only: bool = False) -> Dict[str, Any]:
        """List contents of a directory.

        Args:
            path: Working directory (mirror+vanisher)
            directory_path: Directory to list (default: current directory)
            recursive: Whether to list recursively
            files_only: Whether to list only files (exclude directories)

        Returns:
            Directory contents listing
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            target_dir = resolved_path / directory_path

            if not target_dir.exists():
                return {'success': False, 'error': f'Directory not found: {directory_path}'}

            if not target_dir.is_dir():
                return {'success': False, 'error': f'Path is not a directory: {directory_path}'}

            contents = []
            if recursive:
                items = target_dir.rglob('*')
            else:
                items = target_dir.iterdir()

            for item in items:
                if files_only and not item.is_file():
                    continue

                contents.append({
                    'name': item.name,
                    'path': str(item.relative_to(resolved_path)),
                    'type': 'file' if item.is_file() else 'directory',
                    'size': item.stat().st_size if item.is_file() else None
                })

            return {
                'success': True,
                'directory': str(target_dir),
                'relative_path': directory_path,
                'contents': contents,
                'count': len(contents),
                'recursive': recursive
            }

        except Exception as e:
            handle_exception(e, context={'function': 'list_directory_contents', 'path': path, 'dir': directory_path})
            return {'success': False, 'error': str(e)}
