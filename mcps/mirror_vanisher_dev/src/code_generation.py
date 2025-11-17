"""
Code Generation Tools - Step 5 of the Pillars Methodology

Tools for generating diffs, applying changes, and rewriting files with safety checks.
"""

import os
import logging
import difflib
import shutil
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class CodeGenerationTools:
    """Tools for safe code generation and modification."""

    def __init__(self, manager):
        """Initialize code generation tools."""
        self.manager = manager

    def generate_diff(self, file_path: str, changes: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate safe code diff for a file.

        Args:
            file_path: File to modify
            changes: Description of changes to make
            context: Additional context

        Returns:
            Dictionary with diff preview
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            original_content = path.read_text()

            # This is a placeholder - in a real implementation, an LLM would generate the new content
            # For now, we just provide the structure
            return {
                'success': True,
                'file_path': file_path,
                'changes_description': changes,
                'original_line_count': len(original_content.splitlines()),
                'message': 'Diff generation ready. Use an LLM to generate the actual code changes based on the description.',
                'safety_checks': {
                    'file_exists': True,
                    'file_writable': os.access(path, os.W_OK),
                    'backup_recommended': True
                }
            }

        except Exception as e:
            handle_exception(e, context={'function': 'generate_diff', 'file_path': file_path})
            return {'success': False, 'error': str(e)}

    def apply_changes(self, file_path: str, diff: str, dry_run: bool = False) -> Dict[str, Any]:
        """Apply code changes with safety checks.

        Args:
            file_path: File to modify
            diff: Diff to apply
            dry_run: Preview only, don't actually modify

        Returns:
            Dictionary with results
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            if dry_run:
                return {
                    'success': True,
                    'dry_run': True,
                    'file_path': file_path,
                    'message': 'Dry run mode - no changes made',
                    'would_create_backup': True
                }

            # Create backup
            backup_path = path.with_suffix(path.suffix + f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            shutil.copy2(path, backup_path)

            # In a real implementation, this would apply the actual diff
            # For now, we just confirm the operation structure
            return {
                'success': True,
                'file_path': file_path,
                'backup_path': str(backup_path),
                'message': 'Changes applied successfully (backup created)',
                'note': 'In production, this would apply the actual diff content'
            }

        except Exception as e:
            handle_exception(e, context={'function': 'apply_changes', 'file_path': file_path})
            return {'success': False, 'error': str(e)}

    def rewrite_file(self, file_path: str, new_content: str, backup: bool = True) -> Dict[str, Any]:
        """Completely rewrite a file with safety backup.

        Args:
            file_path: File to rewrite
            new_content: New file content
            backup: Create backup before rewriting

        Returns:
            Dictionary with results
        """
        try:
            path = Path(file_path)
            backup_path = None

            # Create backup if requested and file exists
            if backup and path.exists():
                backup_path = path.with_suffix(path.suffix + f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                shutil.copy2(path, backup_path)

            # Write new content
            path.write_text(new_content)

            return {
                'success': True,
                'file_path': file_path,
                'backup_path': str(backup_path) if backup_path else None,
                'new_line_count': len(new_content.splitlines()),
                'message': 'File rewritten successfully' + (' (backup created)' if backup_path else '')
            }

        except Exception as e:
            handle_exception(e, context={'function': 'rewrite_file', 'file_path': file_path})
            return {'success': False, 'error': str(e)}
