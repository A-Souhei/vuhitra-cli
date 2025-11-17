"""
Architecture Tools - Step 2 of the Pillars Methodology

Tools for analyzing architectural patterns, mapping dependencies, and identifying design patterns.
"""

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Set
from collections import defaultdict

from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class ArchitectureTools:
    """Tools for architecture analysis."""

    def __init__(self, manager):
        """Initialize architecture tools."""
        self.manager = manager

    def analyze_architecture(self, path: str) -> Dict[str, Any]:
        """Analyze architectural patterns in the codebase.

        Args:
            path: Path to analyze

        Returns:
            Dictionary with architecture analysis
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            patterns = []
            structure_type = 'Unknown'

            # Detect directory structure patterns
            dirs = [d.name for d in resolved_path.iterdir() if d.is_dir() and not d.name.startswith('.')]

            # Check for MVC pattern
            if any(d in dirs for d in ['models', 'views', 'controllers']):
                patterns.append('MVC (Model-View-Controller)')
                structure_type = 'MVC'

            # Check for layered architecture
            if any(d in dirs for d in ['services', 'repositories', 'dao', 'models']):
                patterns.append('Layered Architecture')
                if structure_type == 'Unknown':
                    structure_type = 'Layered'

            # Check for microservices
            if 'services' in dirs and len([d for d in dirs if 'service' in d.lower()]) > 1:
                patterns.append('Microservices')
                structure_type = 'Microservices'

            # Check for Clean Architecture / Hexagonal
            if any(d in dirs for d in ['domain', 'application', 'infrastructure', 'interfaces']):
                patterns.append('Clean/Hexagonal Architecture')
                structure_type = 'Clean Architecture'

            # Check for feature-based structure
            if len(dirs) > 3 and all(not d in ['src', 'lib', 'app', 'tests'] for d in dirs):
                patterns.append('Feature-based Structure')

            return {
                'success': True,
                'path': str(resolved_path),
                'structure_type': structure_type,
                'patterns': patterns,
                'directories': dirs,
                'analysis': self._detailed_analysis(resolved_path)
            }

        except Exception as e:
            handle_exception(e, context={'function': 'analyze_architecture', 'path': path})
            return {'success': False, 'error': str(e)}

    def _detailed_analysis(self, path: Path) -> Dict[str, Any]:
        """Perform detailed architecture analysis."""
        analysis = {
            'has_tests': False,
            'has_docs': False,
            'has_config': False,
            'has_scripts': False
        }

        for item in path.iterdir():
            name_lower = item.name.lower()
            if 'test' in name_lower:
                analysis['has_tests'] = True
            if name_lower in ['docs', 'documentation', 'doc']:
                analysis['has_docs'] = True
            if name_lower in ['config', 'configuration', 'settings']:
                analysis['has_config'] = True
            if name_lower in ['scripts', 'bin', 'tools']:
                analysis['has_scripts'] = True

        return analysis

    def map_dependencies(self, path: str) -> Dict[str, Any]:
        """Map dependencies between modules/files.

        Args:
            path: Path to analyze

        Returns:
            Dictionary with dependency map
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            dependencies = defaultdict(list)

            # Scan Python files for imports
            for root, dirs, files in os.walk(resolved_path):
                dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', 'venv', '.venv'}]

                for file in files:
                    if file.endswith('.py'):
                        file_path = Path(root) / file
                        rel_path = str(file_path.relative_to(resolved_path))

                        try:
                            content = file_path.read_text()
                            # Find imports
                            imports = re.findall(r'^\s*(?:from|import)\s+([^\s]+)', content, re.MULTILINE)
                            dependencies[rel_path] = list(set(imports))
                        except:
                            pass

            return {
                'success': True,
                'path': str(resolved_path),
                'dependencies': dict(dependencies),
                'file_count': len(dependencies),
                'total_dependencies': sum(len(deps) for deps in dependencies.values())
            }

        except Exception as e:
            handle_exception(e, context={'function': 'map_dependencies', 'path': path})
            return {'success': False, 'error': str(e)}

    def identify_patterns(self, path: str) -> Dict[str, Any]:
        """Identify design patterns in use.

        Args:
            path: Path to analyze

        Returns:
            Dictionary with identified patterns
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            patterns_found = []

            # Scan for common design pattern indicators
            for root, dirs, files in os.walk(resolved_path):
                dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', 'venv', '.venv'}]

                for file in files:
                    if file.endswith('.py'):
                        file_path = Path(root) / file
                        file_lower = file.lower()

                        # Singleton pattern
                        if 'singleton' in file_lower:
                            patterns_found.append({'pattern': 'Singleton', 'file': str(file_path.relative_to(resolved_path))})

                        # Factory pattern
                        if 'factory' in file_lower:
                            patterns_found.append({'pattern': 'Factory', 'file': str(file_path.relative_to(resolved_path))})

                        # Strategy pattern
                        if 'strategy' in file_lower:
                            patterns_found.append({'pattern': 'Strategy', 'file': str(file_path.relative_to(resolved_path))})

                        # Observer pattern
                        if 'observer' in file_lower or 'listener' in file_lower:
                            patterns_found.append({'pattern': 'Observer', 'file': str(file_path.relative_to(resolved_path))})

                        # Decorator pattern
                        if 'decorator' in file_lower:
                            patterns_found.append({'pattern': 'Decorator', 'file': str(file_path.relative_to(resolved_path))})

            return {
                'success': True,
                'path': str(resolved_path),
                'patterns': patterns_found,
                'pattern_count': len(patterns_found)
            }

        except Exception as e:
            handle_exception(e, context={'function': 'identify_patterns', 'path': path})
            return {'success': False, 'error': str(e)}
