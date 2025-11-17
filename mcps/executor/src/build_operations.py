"""
Build and Compile Operations

Provides tools for building, compiling, and managing project dependencies.
"""

import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

from mirror_vanisher import MirrorVanisherManager
from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class BuildOperationsTools:
    """Tools for building, compiling, and dependency management."""

    def __init__(self, manager: MirrorVanisherManager):
        """Initialize build operations tools.

        Args:
            manager: Mirror+Vanisher manager instance
        """
        self.manager = manager
        logger.info("BuildOperationsTools initialized")

    def install_pip_packages(self, path: str, packages: List[str], requirements_file: Optional[str] = None, upgrade: bool = False) -> Dict[str, Any]:
        """Install Python packages using pip.

        Args:
            path: Working directory (mirror+vanisher)
            packages: List of package names to install
            requirements_file: Optional requirements.txt file path
            upgrade: Whether to upgrade existing packages

        Returns:
            Installation result with installed packages
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            if requirements_file:
                req_file = resolved_path / requirements_file
                if not req_file.exists():
                    return {'success': False, 'error': f'Requirements file not found: {requirements_file}'}

                command = ['pip3', 'install', '-r', str(req_file)]
                if upgrade:
                    command.append('--upgrade')
            else:
                if not packages:
                    return {'success': False, 'error': 'No packages specified'}

                command = ['pip3', 'install'] + packages
                if upgrade:
                    command.append('--upgrade')

            result = subprocess.run(
                command,
                cwd=str(resolved_path),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout for package installation
            )

            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(command),
                'packages_installed': packages if not requirements_file else 'from requirements.txt'
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Installation timed out after 5 minutes'}
        except Exception as e:
            handle_exception(e, context={'function': 'install_pip_packages', 'path': path})
            return {'success': False, 'error': str(e)}

    def install_npm_packages(self, path: str, packages: Optional[List[str]] = None, package_json: bool = True, dev: bool = False) -> Dict[str, Any]:
        """Install Node.js packages using npm.

        Args:
            path: Working directory (mirror+vanisher)
            packages: Optional list of package names to install
            package_json: Whether to install from package.json
            dev: Whether to install as dev dependencies

        Returns:
            Installation result with installed packages
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            if package_json:
                command = ['npm', 'install']
            else:
                if not packages:
                    return {'success': False, 'error': 'No packages specified'}

                command = ['npm', 'install']
                if dev:
                    command.append('--save-dev')
                command.extend(packages)

            result = subprocess.run(
                command,
                cwd=str(resolved_path),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )

            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(command),
                'packages_installed': packages if packages else 'from package.json'
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Installation timed out after 5 minutes'}
        except Exception as e:
            handle_exception(e, context={'function': 'install_npm_packages', 'path': path})
            return {'success': False, 'error': str(e)}

    def run_build_command(self, path: str, build_command: str, timeout: int = 300) -> Dict[str, Any]:
        """Run a build command (make, gradle, maven, etc.).

        Args:
            path: Working directory (mirror+vanisher)
            build_command: Build command to execute
            timeout: Execution timeout in seconds

        Returns:
            Build result with stdout and stderr
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            result = subprocess.run(
                build_command,
                cwd=str(resolved_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True
            )

            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': build_command,
                'working_directory': str(resolved_path)
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': f'Build timed out after {timeout} seconds'}
        except Exception as e:
            handle_exception(e, context={'function': 'run_build_command', 'path': path, 'command': build_command})
            return {'success': False, 'error': str(e)}

    def compile_python(self, path: str, file_path: str) -> Dict[str, Any]:
        """Compile a Python file to bytecode.

        Args:
            path: Working directory (mirror+vanisher)
            file_path: Path to Python file relative to working directory

        Returns:
            Compilation result
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            py_file = resolved_path / file_path
            if not py_file.exists():
                return {'success': False, 'error': f'Python file not found: {file_path}'}

            command = ['python3', '-m', 'py_compile', str(py_file)]

            result = subprocess.run(
                command,
                cwd=str(resolved_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'file_path': str(py_file),
                'compiled': result.returncode == 0
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Compilation timed out'}
        except Exception as e:
            handle_exception(e, context={'function': 'compile_python', 'path': path, 'file': file_path})
            return {'success': False, 'error': str(e)}

    def create_virtual_env(self, path: str, venv_name: str = 'venv') -> Dict[str, Any]:
        """Create a Python virtual environment.

        Args:
            path: Working directory (mirror+vanisher)
            venv_name: Name of the virtual environment directory

        Returns:
            Virtual environment creation result
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            venv_path = resolved_path / venv_name

            if venv_path.exists():
                return {'success': False, 'error': f'Virtual environment already exists: {venv_name}'}

            command = ['python3', '-m', 'venv', venv_name]

            result = subprocess.run(
                command,
                cwd=str(resolved_path),
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'venv_path': str(venv_path),
                'venv_name': venv_name,
                'activate_command': f'source {venv_name}/bin/activate',
                'stdout': result.stdout,
                'stderr': result.stderr
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Virtual environment creation timed out'}
        except Exception as e:
            handle_exception(e, context={'function': 'create_virtual_env', 'path': path})
            return {'success': False, 'error': str(e)}

    def install_in_virtual_env(self, path: str, venv_name: str = 'venv', packages: Optional[List[str]] = None, requirements_file: Optional[str] = None) -> Dict[str, Any]:
        """Install Python packages in a virtual environment.

        Args:
            path: Working directory (mirror+vanisher)
            venv_name: Name of the virtual environment directory
            packages: Optional list of package names to install
            requirements_file: Optional requirements.txt file path

        Returns:
            Installation result
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            venv_path = resolved_path / venv_name
            if not venv_path.exists():
                return {'success': False, 'error': f'Virtual environment not found: {venv_name}. Create it first with create_virtual_env'}

            pip_executable = venv_path / 'bin' / 'pip'
            if not pip_executable.exists():
                return {'success': False, 'error': f'pip not found in virtual environment: {venv_name}'}

            installed_packages = []

            # Install from requirements file
            if requirements_file:
                req_file = resolved_path / requirements_file
                if not req_file.exists():
                    return {'success': False, 'error': f'Requirements file not found: {requirements_file}'}
                
                command = [str(pip_executable), 'install', '-r', requirements_file]
                result = subprocess.run(
                    command,
                    cwd=str(resolved_path),
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode != 0:
                    return {
                        'success': False,
                        'error': f'Failed to install from requirements file',
                        'stdout': result.stdout,
                        'stderr': result.stderr
                    }
                installed_packages.append(f'packages from {requirements_file}')

            # Install individual packages
            if packages:
                for package in packages:
                    command = [str(pip_executable), 'install', package]
                    result = subprocess.run(
                        command,
                        cwd=str(resolved_path),
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    
                    if result.returncode == 0:
                        installed_packages.append(package)
                    else:
                        logger.warning(f"Failed to install {package}: {result.stderr}")

            return {
                'success': len(installed_packages) > 0,
                'venv_name': venv_name,
                'installed_packages': installed_packages,
                'message': f'Installed {len(installed_packages)} package(s) in virtual environment {venv_name}'
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Package installation timed out'}
        except Exception as e:
            handle_exception(e, context={'function': 'install_in_virtual_env', 'path': path})
            return {'success': False, 'error': str(e)}

    def run_in_virtual_env(self, path: str, venv_name: str = 'venv', command: str = '', timeout: int = 30) -> Dict[str, Any]:
        """Run a command in a virtual environment.

        Args:
            path: Working directory (mirror+vanisher)
            venv_name: Name of the virtual environment directory
            command: Command to run in the activated virtual environment
            timeout: Execution timeout in seconds

        Returns:
            Command execution result
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            venv_path = resolved_path / venv_name
            if not venv_path.exists():
                return {'success': False, 'error': f'Virtual environment not found: {venv_name}. Create it first with create_virtual_env'}

            # Build command that activates venv and runs the command
            full_command = f'source {venv_name}/bin/activate && {command}'

            result = subprocess.run(
                ['bash', '-c', full_command],
                cwd=str(resolved_path),
                capture_output=True,
                text=True,
                timeout=timeout
            )

            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'command': full_command,
                'venv_name': venv_name,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'working_directory': str(resolved_path)
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': f'Command timed out after {timeout} seconds'}
        except Exception as e:
            handle_exception(e, context={'function': 'run_in_virtual_env', 'path': path})
            return {'success': False, 'error': str(e)}


    def run_docker_build(self, path: str, dockerfile: str = 'Dockerfile', tag: str = 'latest', build_args: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Build a Docker image.

        Args:
            path: Working directory (mirror+vanisher)
            dockerfile: Path to Dockerfile relative to working directory
            tag: Image tag
            build_args: Optional build arguments

        Returns:
            Docker build result
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            docker_file = resolved_path / dockerfile
            if not docker_file.exists():
                return {'success': False, 'error': f'Dockerfile not found: {dockerfile}'}

            command = ['docker', 'build', '-f', dockerfile, '-t', tag]

            if build_args:
                for key, value in build_args.items():
                    command.extend(['--build-arg', f'{key}={value}'])

            command.append('.')

            result = subprocess.run(
                command,
                cwd=str(resolved_path),
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes for docker builds
            )

            return {
                'success': result.returncode == 0,
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'command': ' '.join(command),
                'image_tag': tag
            }

        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Docker build timed out after 10 minutes'}
        except Exception as e:
            handle_exception(e, context={'function': 'run_docker_build', 'path': path})
            return {'success': False, 'error': str(e)}
