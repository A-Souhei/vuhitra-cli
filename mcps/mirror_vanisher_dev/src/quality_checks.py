"""
Quality Check Tools - Step 7 of the Pillars Methodology

Tools for running linters, formatters, and type checkers.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any

from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class QualityCheckTools:
    """Tools for code quality checks."""

    def __init__(self, manager):
        """Initialize quality check tools."""
        self.manager = manager

    def run_linter(self, path: str, fix: bool = False) -> Dict[str, Any]:
        """Run linter on code.

        Args:
            path: Path to lint
            fix: Auto-fix issues

        Returns:
            Dictionary with linting results
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                resolved_path = Path(path)
                if not resolved_path.exists():
                    return {'success': False, 'error': f'Path not found: {path}'}

            # Detect file type and choose linter
            linter_cmd = self._get_linter_command(resolved_path, fix)

            if not linter_cmd:
                return {
                    'success': False,
                    'error': 'No suitable linter found for this file type'
                }

            # Run linter
            process = subprocess.run(
                linter_cmd,
                cwd=str(resolved_path.parent if resolved_path.is_file() else resolved_path),
                capture_output=True,
                text=True,
                timeout=120
            )

            return {
                'success': process.returncode == 0,
                'linter': linter_cmd[0],
                'exit_code': process.returncode,
                'stdout': process.stdout,
                'stderr': process.stderr,
                'fixed': fix,
                'message': 'Linting passed' if process.returncode == 0 else 'Linting issues found'
            }

        except Exception as e:
            handle_exception(e, context={'function': 'run_linter', 'path': path})
            return {'success': False, 'error': str(e)}

    def _get_linter_command(self, path: Path, fix: bool) -> list:
        """Get appropriate linter command for file type."""
        if path.suffix == '.py':
            # Try ruff first (faster), fall back to flake8
            if self._command_exists('ruff'):
                return ['ruff', 'check', str(path)] + (['--fix'] if fix else [])
            elif self._command_exists('flake8'):
                return ['flake8', str(path)]

        elif path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
            if self._command_exists('eslint'):
                return ['eslint', str(path)] + (['--fix'] if fix else [])

        return None

    def run_formatter(self, path: str, check_only: bool = False) -> Dict[str, Any]:
        """Run code formatter.

        Args:
            path: Path to format
            check_only: Check without modifying

        Returns:
            Dictionary with formatting results
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                resolved_path = Path(path)
                if not resolved_path.exists():
                    return {'success': False, 'error': f'Path not found: {path}'}

            # Detect file type and choose formatter
            formatter_cmd = self._get_formatter_command(resolved_path, check_only)

            if not formatter_cmd:
                return {
                    'success': False,
                    'error': 'No suitable formatter found for this file type'
                }

            # Run formatter
            process = subprocess.run(
                formatter_cmd,
                cwd=str(resolved_path.parent if resolved_path.is_file() else resolved_path),
                capture_output=True,
                text=True,
                timeout=120
            )

            return {
                'success': process.returncode == 0,
                'formatter': formatter_cmd[0],
                'exit_code': process.returncode,
                'stdout': process.stdout,
                'stderr': process.stderr,
                'check_only': check_only,
                'message': 'Formatting correct' if process.returncode == 0 else 'Formatting needed'
            }

        except Exception as e:
            handle_exception(e, context={'function': 'run_formatter', 'path': path})
            return {'success': False, 'error': str(e)}

    def _get_formatter_command(self, path: Path, check_only: bool) -> list:
        """Get appropriate formatter command for file type."""
        if path.suffix == '.py':
            if self._command_exists('ruff'):
                return ['ruff', 'format', str(path)] + (['--check'] if check_only else [])
            elif self._command_exists('black'):
                return ['black', str(path)] + (['--check'] if check_only else [])

        elif path.suffix in ['.js', '.jsx', '.ts', '.tsx', '.json', '.css']:
            if self._command_exists('prettier'):
                return ['prettier', str(path)] + (['--check'] if check_only else ['--write'])

        return None

    def run_type_checker(self, path: str) -> Dict[str, Any]:
        """Run type checker.

        Args:
            path: Path to check

        Returns:
            Dictionary with type checking results
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                resolved_path = Path(path)
                if not resolved_path.exists():
                    return {'success': False, 'error': f'Path not found: {path}'}

            # Detect file type and choose type checker
            checker_cmd = self._get_type_checker_command(resolved_path)

            if not checker_cmd:
                return {
                    'success': False,
                    'error': 'No suitable type checker found for this file type'
                }

            # Run type checker
            process = subprocess.run(
                checker_cmd,
                cwd=str(resolved_path.parent if resolved_path.is_file() else resolved_path),
                capture_output=True,
                text=True,
                timeout=120
            )

            return {
                'success': process.returncode == 0,
                'type_checker': checker_cmd[0],
                'exit_code': process.returncode,
                'stdout': process.stdout,
                'stderr': process.stderr,
                'message': 'Type checking passed' if process.returncode == 0 else 'Type errors found'
            }

        except Exception as e:
            handle_exception(e, context={'function': 'run_type_checker', 'path': path})
            return {'success': False, 'error': str(e)}

    def _get_type_checker_command(self, path: Path) -> list:
        """Get appropriate type checker command for file type."""
        if path.suffix == '.py':
            if self._command_exists('mypy'):
                return ['mypy', str(path)]

        elif path.suffix in ['.ts', '.tsx']:
            if self._command_exists('tsc'):
                return ['tsc', '--noEmit', str(path)]

        return None

    def full_quality_check(self, path: str, fix: bool = False) -> Dict[str, Any]:
        """Run all quality checks (lint + format + types).

        Args:
            path: Path to check
            fix: Auto-fix issues

        Returns:
            Dictionary with all quality check results
        """
        try:
            results = {
                'linter': self.run_linter(path, fix),
                'formatter': self.run_formatter(path, check_only=not fix),
                'type_checker': self.run_type_checker(path)
            }

            all_passed = all(result.get('success', False) for result in results.values())

            return {
                'success': True,
                'all_checks_passed': all_passed,
                'results': results,
                'message': 'All quality checks passed' if all_passed else 'Some quality checks failed'
            }

        except Exception as e:
            handle_exception(e, context={'function': 'full_quality_check', 'path': path})
            return {'success': False, 'error': str(e)}

    def _command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH."""
        try:
            subprocess.run([command, '--version'], capture_output=True, timeout=5)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
