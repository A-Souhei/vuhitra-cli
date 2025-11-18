"""
Code Tools for Python Executor MCP

Provides tools for writing, updating, and running code in vanisher directories.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from vanisher_manager import VanisherManager
from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class CodeTools:
    """Tools for code operations in vanisher directories."""

    def __init__(self, manager: VanisherManager):
        """Initialize code tools.

        Args:
            manager: VanisherManager instance
        """
        self.manager = manager
        logger.info("CodeTools initialized")

    def write_code(
        self,
        vanisher_name: str,
        filename: str,
        code: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Write code to a file in a vanisher directory.

        Creates a new file or overwrites an existing file with the provided code.
        The vanisher directory will be created if it doesn't exist.

        Args:
            vanisher_name: Name of the vanisher directory
            filename: Name of the file to create/write
            code: The code content to write
            language: Optional language hint (python, javascript, shell, etc.)

        Returns:
            Dictionary with operation result
        """
        try:
            file_path = self.manager.resolve_file_path(vanisher_name, filename)

            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the code
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)

            # Detect language if not provided
            if not language:
                language = self._detect_language(filename)

            return {
                'success': True,
                'message': f'Code written to {filename}',
                'vanisher': vanisher_name,
                'filename': filename,
                'path': str(file_path),
                'language': language,
                'size': len(code),
                'lines': code.count('\n') + 1
            }

        except Exception as e:
            handle_exception(e, context={
                'function': 'write_code',
                'vanisher_name': vanisher_name,
                'filename': filename
            })
            return {
                'success': False,
                'error': str(e)
            }

    def update_code(
        self,
        vanisher_name: str,
        filename: str,
        old_code: str,
        new_code: str
    ) -> Dict[str, Any]:
        """Update code in an existing file by replacing a specific section.

        Finds the old_code section and replaces it with new_code.
        This allows for precise code modifications.

        Args:
            vanisher_name: Name of the vanisher directory
            filename: Name of the file to update
            old_code: The code section to find and replace
            new_code: The replacement code

        Returns:
            Dictionary with operation result
        """
        try:
            file_path = self.manager.resolve_file_path(vanisher_name, filename)

            if not file_path.exists():
                return {
                    'success': False,
                    'error': f'File not found: {filename}'
                }

            # Read current content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if old_code exists
            if old_code not in content:
                return {
                    'success': False,
                    'error': 'Old code section not found in file',
                    'hint': 'Make sure the old_code matches exactly (including whitespace)'
                }

            # Count occurrences
            occurrences = content.count(old_code)
            if occurrences > 1:
                return {
                    'success': False,
                    'error': f'Multiple occurrences ({occurrences}) of old_code found',
                    'hint': 'Provide more context to make the match unique'
                }

            # Replace the code
            updated_content = content.replace(old_code, new_code, 1)

            # Write back
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            return {
                'success': True,
                'message': f'Code updated in {filename}',
                'vanisher': vanisher_name,
                'filename': filename,
                'path': str(file_path),
                'old_lines': old_code.count('\n') + 1,
                'new_lines': new_code.count('\n') + 1,
                'size_change': len(new_code) - len(old_code)
            }

        except Exception as e:
            handle_exception(e, context={
                'function': 'update_code',
                'vanisher_name': vanisher_name,
                'filename': filename
            })
            return {
                'success': False,
                'error': str(e)
            }

    def pip_install(
        self,
        vanisher_name: str,
        packages: List[str],
        timeout: int = 300
    ) -> Dict[str, Any]:
        """Install Python packages using pip in a vanisher directory.

        Installs packages into the virtual environment if one exists,
        otherwise uses the system pip. Creates a venv if requested.

        Args:
            vanisher_name: Name of the vanisher directory
            packages: List of package names to install (e.g., ['requests', 'numpy>=1.20'])
            timeout: Installation timeout in seconds (default: 300)

        Returns:
            Dictionary with installation result
        """
        try:
            vanisher_dir = self.manager.get_vanisher_dir(vanisher_name)

            if not packages:
                return {
                    'success': False,
                    'error': 'No packages specified'
                }

            # Detect venv and get pip path
            venv_python = self._detect_venv(vanisher_dir)

            if venv_python:
                # Use pip from venv
                pip_cmd = str(venv_python.parent / 'pip')
            else:
                # Use system pip
                pip_cmd = 'pip'

            # Build install command
            command = [pip_cmd, 'install'] + packages

            # Execute pip install
            result = subprocess.run(
                command,
                cwd=str(vanisher_dir),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            response = {
                'success': result.returncode == 0,
                'vanisher': vanisher_name,
                'packages': packages,
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(command)
            }

            if venv_python:
                response['venv_used'] = True
                response['venv_path'] = str(venv_python.parent.parent)

            return response

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'Installation timed out after {timeout} seconds',
                'vanisher': vanisher_name,
                'packages': packages
            }

        except Exception as e:
            handle_exception(e, context={
                'function': 'pip_install',
                'vanisher_name': vanisher_name,
                'packages': packages
            })
            return {
                'success': False,
                'error': str(e)
            }

    def run_code(
        self,
        vanisher_name: str,
        filename: str,
        args: Optional[List[str]] = None,
        timeout: int = 30,
        env: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Run code from a file in a vanisher directory.

        Executes the code file using the appropriate interpreter based on
        the file extension. Supports Python, JavaScript/Node, and shell scripts.

        Args:
            vanisher_name: Name of the vanisher directory
            filename: Name of the file to run
            args: Optional list of command-line arguments
            timeout: Execution timeout in seconds (default: 30)
            env: Optional environment variables to set

        Returns:
            Dictionary with execution result including stdout and stderr
        """
        try:
            file_path = self.manager.resolve_file_path(vanisher_name, filename)
            vanisher_dir = self.manager.get_vanisher_dir(vanisher_name)

            if not file_path.exists():
                return {
                    'success': False,
                    'error': f'File not found: {filename}'
                }

            # Determine the command based on file extension
            # For Python, check for venv and use it if available
            venv_python = None
            if file_path.suffix.lower() == '.py':
                venv_python = self._detect_venv(vanisher_dir)

            command = self._build_command(file_path, args or [], venv_python=venv_python)

            if not command:
                return {
                    'success': False,
                    'error': f'Unsupported file type: {file_path.suffix}',
                    'hint': 'Supported types: .py, .js, .r, .R, .sh, .bash'
                }

            # Set up environment
            run_env = os.environ.copy()
            if env:
                run_env.update(env)

            # Execute the code
            result = subprocess.run(
                command,
                cwd=str(vanisher_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=run_env
            )

            response = {
                'success': result.returncode == 0,
                'vanisher': vanisher_name,
                'filename': filename,
                'path': str(file_path),
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(command)
            }

            # Indicate if venv was used
            if venv_python:
                response['venv_used'] = True
                response['venv_python'] = str(venv_python)

            return response

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': f'Execution timed out after {timeout} seconds',
                'vanisher': vanisher_name,
                'filename': filename
            }

        except Exception as e:
            handle_exception(e, context={
                'function': 'run_code',
                'vanisher_name': vanisher_name,
                'filename': filename
            })
            return {
                'success': False,
                'error': str(e)
            }

    def _detect_language(self, filename: str) -> str:
        """Detect programming language from filename.

        Args:
            filename: Name of the file

        Returns:
            Detected language name
        """
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.sh': 'shell',
            '.bash': 'shell',
            '.r': 'r',
            '.R': 'r',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp'
        }

        suffix = Path(filename).suffix.lower()
        return ext_map.get(suffix, 'unknown')

    def _detect_venv(self, directory: Path) -> Optional[Path]:
        """Detect virtual environment in directory.

        Checks common venv directory names and returns the Python executable
        if a valid venv is found.

        Args:
            directory: Directory to search for venv

        Returns:
            Path to venv Python executable or None
        """
        # Common venv directory names
        venv_names = ['venv', '.venv', 'env', '.env']

        for venv_name in venv_names:
            venv_dir = directory / venv_name

            if venv_dir.exists() and venv_dir.is_dir():
                # Check for Python executable (Unix-style)
                python_path = venv_dir / 'bin' / 'python'
                if python_path.exists():
                    logger.info(f"Found venv at {venv_dir}")
                    return python_path

                # Check for Python executable (Windows-style)
                python_path = venv_dir / 'Scripts' / 'python.exe'
                if python_path.exists():
                    logger.info(f"Found venv at {venv_dir}")
                    return python_path

        return None

    def _build_command(self, file_path: Path, args: List[str], venv_python: Optional[Path] = None) -> Optional[List[str]]:
        """Build the command to execute a file.

        Args:
            file_path: Path to the file
            args: Command-line arguments
            venv_python: Optional path to venv Python executable

        Returns:
            List of command parts or None if unsupported
        """
        suffix = file_path.suffix.lower()

        if suffix == '.py':
            # Use venv Python if available, otherwise system Python
            python_cmd = str(venv_python) if venv_python else 'python'
            return [python_cmd, str(file_path)] + args
        elif suffix == '.js':
            return ['node', str(file_path)] + args
        elif suffix in ['.sh', '.bash']:
            return ['bash', str(file_path)] + args
        elif suffix in ['.r', '.R']:
            return ['Rscript', str(file_path)] + args
        else:
            return None
