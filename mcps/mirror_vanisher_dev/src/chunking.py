"""
Chunking Tools - Step 3 of the Pillars Methodology

Tools for breaking large files and codebases into manageable chunks.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class ChunkingTools:
    """Tools for code chunking."""

    def __init__(self, manager):
        """Initialize chunking tools."""
        self.manager = manager

    def chunk_file(self, file_path: str, chunk_size: int = 100, overlap: int = 10) -> Dict[str, Any]:
        """Break a large file into manageable chunks.

        Args:
            file_path: File to chunk
            chunk_size: Lines per chunk
            overlap: Overlap lines between chunks

        Returns:
            Dictionary with chunks
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return {'success': False, 'error': f'File not found: {file_path}'}

            lines = path.read_text().splitlines()
            total_lines = len(lines)

            chunks = []
            i = 0
            chunk_num = 1

            while i < total_lines:
                end = min(i + chunk_size, total_lines)
                chunk_lines = lines[i:end]

                chunks.append({
                    'chunk_number': chunk_num,
                    'start_line': i + 1,
                    'end_line': end,
                    'line_count': len(chunk_lines),
                    'content': '\n'.join(chunk_lines)
                })

                i += (chunk_size - overlap)
                chunk_num += 1

            return {
                'success': True,
                'file_path': file_path,
                'total_lines': total_lines,
                'chunk_size': chunk_size,
                'overlap': overlap,
                'chunk_count': len(chunks),
                'chunks': chunks
            }

        except Exception as e:
            handle_exception(e, context={'function': 'chunk_file', 'file_path': file_path})
            return {'success': False, 'error': str(e)}

    def chunk_directory(self, path: str, max_file_size: int = 500) -> Dict[str, Any]:
        """Create chunking strategy for entire directory.

        Args:
            path: Directory to analyze
            max_file_size: Max file size in lines before chunking

        Returns:
            Dictionary with chunking strategy
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            files_to_chunk = []
            small_files = []

            for root, dirs, files in Path(resolved_path).rglob('*'):
                if root.is_file():
                    file_path = root
                    try:
                        lines = len(file_path.read_text().splitlines())

                        if lines > max_file_size:
                            files_to_chunk.append({
                                'file': str(file_path.relative_to(resolved_path)),
                                'lines': lines,
                                'estimated_chunks': (lines // max_file_size) + 1
                            })
                        else:
                            small_files.append({
                                'file': str(file_path.relative_to(resolved_path)),
                                'lines': lines
                            })
                    except:
                        pass

            return {
                'success': True,
                'path': str(resolved_path),
                'max_file_size': max_file_size,
                'files_needing_chunks': files_to_chunk,
                'small_files': small_files,
                'total_large_files': len(files_to_chunk),
                'total_small_files': len(small_files)
            }

        except Exception as e:
            handle_exception(e, context={'function': 'chunk_directory', 'path': path})
            return {'success': False, 'error': str(e)}
