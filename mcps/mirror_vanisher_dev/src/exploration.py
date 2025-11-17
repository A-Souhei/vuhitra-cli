"""
Exploration Tools - Step 1 of the Pillars Methodology

Tools for exploring codebase structure, detecting tech stack, and finding entrypoints.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List
from collections import defaultdict

from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class ExplorationTools:
    """Tools for codebase exploration."""

    def __init__(self, manager):
        """Initialize exploration tools.

        Args:
            manager: Mirror/Vanisher manager instance
        """
        self.manager = manager

        # File extension to language mapping
        self.ext_to_lang = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'React/JSX',
            '.tsx': 'React/TSX',
            '.java': 'Java',
            '.go': 'Go',
            '.rs': 'Rust',
            '.cpp': 'C++',
            '.c': 'C',
            '.h': 'C/C++ Header',
            '.cs': 'C#',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            '.r': 'R',
            '.R': 'R',
            '.sh': 'Shell',
            '.bash': 'Bash',
            '.sql': 'SQL',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.less': 'LESS',
            '.vue': 'Vue',
            '.elm': 'Elm',
            '.ex': 'Elixir',
            '.exs': 'Elixir',
            '.erl': 'Erlang',
            '.clj': 'Clojure',
            '.dart': 'Dart',
            '.lua': 'Lua',
            '.pl': 'Perl',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.json': 'JSON',
            '.toml': 'TOML',
            '.xml': 'XML',
            '.md': 'Markdown',
            '.rst': 'reStructuredText'
        }

        # Entrypoint filenames
        self.entrypoint_files = {
            'main.py', 'app.py', '__main__.py', 'run.py', 'server.py',
            'index.js', 'main.js', 'app.js', 'server.js',
            'index.ts', 'main.ts', 'app.ts', 'server.ts',
            'main.go', 'main.java', 'Main.java', 'App.java',
            'main.rs', 'main.cpp', 'main.c'
        }

    def explore_structure(self, path: str, max_depth: int = 3) -> Dict[str, Any]:
        """Explore directory structure and generate tree view.

        Args:
            path: Path to explore
            max_depth: Maximum depth for tree

        Returns:
            Dictionary with tree structure
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {
                    'success': False,
                    'error': f'Path not found or not a valid mirror+vanisher: {path}'
                }

            # Verify it's a mirror+vanisher
            verification = self.manager.verify_mirror_vanisher(str(resolved_path))
            if not verification.get('is_valid_mirror_vanisher'):
                return {
                    'success': False,
                    'error': 'Path is not a valid mirror+vanisher directory',
                    'verification': verification
                }

            tree = self._build_tree(resolved_path, max_depth)

            return {
                'success': True,
                'path': str(resolved_path),
                'max_depth': max_depth,
                'tree': tree,
                'statistics': self._calculate_stats(tree)
            }

        except Exception as e:
            handle_exception(e, context={'function': 'explore_structure', 'path': path})
            return {'success': False, 'error': str(e)}

    def _build_tree(self, root_path: Path, max_depth: int, current_depth: int = 0) -> Dict[str, Any]:
        """Recursively build directory tree.

        Args:
            root_path: Root path
            max_depth: Maximum depth
            current_depth: Current depth level

        Returns:
            Tree structure dictionary
        """
        tree = {
            'name': root_path.name,
            'type': 'directory' if root_path.is_dir() else 'file',
            'path': str(root_path),
            'children': []
        }

        if not root_path.is_dir() or current_depth >= max_depth:
            return tree

        try:
            # Sort: directories first, then files alphabetically
            items = sorted(root_path.iterdir(), key=lambda x: (not x.is_dir(), x.name))

            for item in items:
                # Skip hidden files and common ignored directories
                if item.name.startswith('.') or item.name in {'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build'}:
                    continue

                child_tree = self._build_tree(item, max_depth, current_depth + 1)
                tree['children'].append(child_tree)

        except PermissionError:
            tree['error'] = 'Permission denied'

        return tree

    def _calculate_stats(self, tree: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate statistics from tree structure.

        Args:
            tree: Tree structure

        Returns:
            Statistics dictionary
        """
        stats = {
            'total_directories': 0,
            'total_files': 0,
            'total_items': 0
        }

        def count_items(node):
            if node['type'] == 'directory':
                stats['total_directories'] += 1
            else:
                stats['total_files'] += 1
            stats['total_items'] += 1

            for child in node.get('children', []):
                count_items(child)

        count_items(tree)
        return stats

    def detect_tech_stack(self, path: str) -> Dict[str, Any]:
        """Detect technology stack and languages used.

        Args:
            path: Path to analyze

        Returns:
            Dictionary with tech stack information
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {
                    'success': False,
                    'error': f'Path not found or not a valid mirror+vanisher: {path}'
                }

            languages = defaultdict(int)
            frameworks = []
            build_tools = []
            config_files = []

            # Walk through all files
            for root, dirs, files in os.walk(resolved_path):
                # Skip ignored directories
                dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build'}]

                for file in files:
                    file_path = Path(root) / file
                    ext = file_path.suffix.lower()

                    # Count languages
                    if ext in self.ext_to_lang:
                        languages[self.ext_to_lang[ext]] += 1

                    # Detect frameworks and tools
                    if file == 'package.json':
                        frameworks.append('Node.js/npm')
                        config_files.append(str(file_path.relative_to(resolved_path)))
                    elif file == 'requirements.txt' or file == 'pyproject.toml' or file == 'setup.py':
                        frameworks.append('Python')
                        config_files.append(str(file_path.relative_to(resolved_path)))
                    elif file == 'Cargo.toml':
                        frameworks.append('Rust/Cargo')
                        config_files.append(str(file_path.relative_to(resolved_path)))
                    elif file == 'go.mod':
                        frameworks.append('Go Modules')
                        config_files.append(str(file_path.relative_to(resolved_path)))
                    elif file == 'pom.xml' or file == 'build.gradle':
                        frameworks.append('Java/Maven or Gradle')
                        config_files.append(str(file_path.relative_to(resolved_path)))
                    elif file == 'Makefile':
                        build_tools.append('Make')
                        config_files.append(str(file_path.relative_to(resolved_path)))
                    elif file == 'Dockerfile':
                        build_tools.append('Docker')
                        config_files.append(str(file_path.relative_to(resolved_path)))
                    elif file == 'docker-compose.yml':
                        build_tools.append('Docker Compose')
                        config_files.append(str(file_path.relative_to(resolved_path)))

            # Sort languages by count
            sorted_languages = sorted(languages.items(), key=lambda x: x[1], reverse=True)

            return {
                'success': True,
                'path': str(resolved_path),
                'languages': [
                    {'language': lang, 'file_count': count}
                    for lang, count in sorted_languages
                ],
                'primary_language': sorted_languages[0][0] if sorted_languages else 'Unknown',
                'frameworks': list(set(frameworks)),
                'build_tools': list(set(build_tools)),
                'config_files': config_files
            }

        except Exception as e:
            handle_exception(e, context={'function': 'detect_tech_stack', 'path': path})
            return {'success': False, 'error': str(e)}

    def find_entrypoints(self, path: str) -> Dict[str, Any]:
        """Find main entrypoints and executable files.

        Args:
            path: Path to search

        Returns:
            Dictionary with entrypoints
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {
                    'success': False,
                    'error': f'Path not found or not a valid mirror+vanisher: {path}'
                }

            entrypoints = []
            executables = []

            for root, dirs, files in os.walk(resolved_path):
                dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'dist', 'build'}]

                for file in files:
                    file_path = Path(root) / file
                    rel_path = str(file_path.relative_to(resolved_path))

                    # Check if it's an entrypoint file
                    if file in self.entrypoint_files:
                        entrypoints.append({
                            'file': rel_path,
                            'type': 'named_entrypoint',
                            'name': file
                        })

                    # Check if it's executable
                    if os.access(file_path, os.X_OK) and not file_path.is_dir():
                        executables.append({
                            'file': rel_path,
                            'type': 'executable'
                        })

                    # Check for __main__ blocks in Python files
                    if file.endswith('.py'):
                        try:
                            content = file_path.read_text()
                            if 'if __name__ == "__main__"' in content or "if __name__ == '__main__'" in content:
                                entrypoints.append({
                                    'file': rel_path,
                                    'type': 'python_main_block',
                                    'name': file
                                })
                        except:
                            pass

            return {
                'success': True,
                'path': str(resolved_path),
                'entrypoints': entrypoints,
                'executables': executables,
                'total_found': len(entrypoints) + len(executables)
            }

        except Exception as e:
            handle_exception(e, context={'function': 'find_entrypoints', 'path': path})
            return {'success': False, 'error': str(e)}

    def full_exploration(self, path: str, max_depth: int = 3) -> Dict[str, Any]:
        """Perform complete exploration (structure + tech stack + entrypoints).

        Args:
            path: Path to explore
            max_depth: Maximum depth for tree

        Returns:
            Dictionary with all exploration results
        """
        try:
            logger.info(f"Starting full exploration of: {path}")

            structure = self.explore_structure(path, max_depth)
            if not structure.get('success'):
                return structure

            tech_stack = self.detect_tech_stack(path)
            entrypoints = self.find_entrypoints(path)

            return {
                'success': True,
                'path': path,
                'structure': structure,
                'tech_stack': tech_stack,
                'entrypoints': entrypoints,
                'summary': {
                    'primary_language': tech_stack.get('primary_language', 'Unknown'),
                    'total_files': structure.get('statistics', {}).get('total_files', 0),
                    'total_directories': structure.get('statistics', {}).get('total_directories', 0),
                    'frameworks': tech_stack.get('frameworks', []),
                    'entrypoint_count': entrypoints.get('total_found', 0)
                }
            }

        except Exception as e:
            handle_exception(e, context={'function': 'full_exploration', 'path': path})
            return {'success': False, 'error': str(e)}
