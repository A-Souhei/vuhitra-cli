"""
Testing Tools - Step 6 of the Pillars Methodology

Tools for generating and running tests.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List

from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class TestingTools:
    """Tools for test generation and execution."""

    def __init__(self, manager):
        """Initialize testing tools."""
        self.manager = manager

    def generate_tests(self, file_path: str, test_type: str = 'unit') -> Dict[str, Any]:
        """Generate unit tests for a file/function.

        Args:
            file_path: File to test
            test_type: Type of tests (unit, integration, edge)

        Returns:
            Dictionary with test generation results
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            # Detect test framework
            framework = self._detect_test_framework(path)

            # Generate test file path
            if path.name.startswith('test_'):
                test_file_path = str(path)
            else:
                test_dir = path.parent / 'tests'
                test_file_path = str(test_dir / f'test_{path.name}')

            return {
                'success': True,
                'source_file': file_path,
                'test_file': test_file_path,
                'test_type': test_type,
                'framework': framework,
                'message': f'Test generation template ready for {framework}',
                'recommendations': self._get_test_recommendations(test_type)
            }

        except Exception as e:
            handle_exception(e, context={'function': 'generate_tests', 'file_path': file_path})
            return {'success': False, 'error': str(e)}

    def _detect_test_framework(self, path: Path) -> str:
        """Detect the test framework in use."""
        # Check for Python test frameworks
        if path.suffix == '.py':
            root = path
            while root.parent != root:
                if (root / 'pytest.ini').exists() or (root / 'pyproject.toml').exists():
                    return 'pytest'
                if (root / 'unittest').exists():
                    return 'unittest'
                root = root.parent
            return 'pytest'  # Default for Python

        # Check for JavaScript test frameworks
        elif path.suffix in ['.js', '.ts', '.jsx', '.tsx']:
            root = path
            while root.parent != root:
                if (root / 'jest.config.js').exists():
                    return 'jest'
                if (root / 'mocha.opts').exists():
                    return 'mocha'
                root = root.parent
            return 'jest'  # Default for JS/TS

        return 'unknown'

    def _get_test_recommendations(self, test_type: str) -> List[str]:
        """Get recommendations for test generation."""
        if test_type == 'unit':
            return [
                'Test individual functions in isolation',
                'Mock external dependencies',
                'Cover normal cases and edge cases',
                'Test error handling'
            ]
        elif test_type == 'integration':
            return [
                'Test component interactions',
                'Use real dependencies where possible',
                'Test data flow between components',
                'Verify system behavior'
            ]
        elif test_type == 'edge':
            return [
                'Test boundary conditions',
                'Test with null/empty inputs',
                'Test with extreme values',
                'Test error scenarios'
            ]
        return []

    def run_tests(self, path: str, test_framework: str = None) -> Dict[str, Any]:
        """Run tests in the directory.

        Args:
            path: Directory or file to test
            test_framework: Test framework (auto-detect if not provided)

        Returns:
            Dictionary with test results
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                # Try as regular path
                resolved_path = Path(path)
                if not resolved_path.exists():
                    return {'success': False, 'error': f'Path not found: {path}'}

            # Auto-detect framework if not provided
            if not test_framework:
                test_framework = self._detect_test_framework(resolved_path)

            # Run tests based on framework
            result = self._run_framework_tests(resolved_path, test_framework)

            return result

        except Exception as e:
            handle_exception(e, context={'function': 'run_tests', 'path': path})
            return {'success': False, 'error': str(e)}

    def _run_framework_tests(self, path: Path, framework: str) -> Dict[str, Any]:
        """Run tests using specific framework."""
        try:
            if framework == 'pytest':
                cmd = ['pytest', str(path), '-v']
            elif framework == 'unittest':
                cmd = ['python', '-m', 'unittest', 'discover', str(path)]
            elif framework == 'jest':
                cmd = ['npm', 'test']
            elif framework == 'mocha':
                cmd = ['npm', 'test']
            else:
                return {
                    'success': False,
                    'error': f'Unsupported test framework: {framework}'
                }

            # Run the command
            process = subprocess.run(
                cmd,
                cwd=str(path.parent),
                capture_output=True,
                text=True,
                timeout=300
            )

            return {
                'success': process.returncode == 0,
                'framework': framework,
                'exit_code': process.returncode,
                'stdout': process.stdout,
                'stderr': process.stderr,
                'message': 'Tests passed' if process.returncode == 0 else 'Tests failed'
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Test execution timed out'
            }
        except FileNotFoundError:
            return {
                'success': False,
                'error': f'Test framework not found: {framework}'
            }

    def verify_changes(self, files_changed: List[str]) -> Dict[str, Any]:
        """Verify changes by running relevant tests.

        Args:
            files_changed: List of changed files

        Returns:
            Dictionary with verification results
        """
        try:
            results = []

            for file_path in files_changed:
                # Find related tests
                path = Path(file_path)
                test_file = path.parent / 'tests' / f'test_{path.name}'

                if test_file.exists():
                    test_result = self.run_tests(str(test_file))
                    results.append({
                        'file': file_path,
                        'test_file': str(test_file),
                        'result': test_result
                    })
                else:
                    results.append({
                        'file': file_path,
                        'test_file': None,
                        'result': {'success': False, 'error': 'No test file found'}
                    })

            all_passed = all(r['result'].get('success', False) for r in results if r['test_file'])

            return {
                'success': True,
                'all_tests_passed': all_passed,
                'results': results,
                'files_tested': len([r for r in results if r['test_file']]),
                'files_without_tests': len([r for r in results if not r['test_file']])
            }

        except Exception as e:
            handle_exception(e, context={'function': 'verify_changes', 'files_changed': files_changed})
            return {'success': False, 'error': str(e)}
