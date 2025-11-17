"""
Mirror+Vanisher Manager

Manages directories that are both:
- Mirrors (synced to sandbox)
- Vanishers (loaded into LLM context)
"""

import os
import requests
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from errors_handler import handle_exception

logger = logging.getLogger(__name__)


class MirrorVanisherManager:
    """Manages operations on directories that are both mirrors and vanishers."""

    def __init__(self):
        """Initialize the manager."""
        self.sandbox_url = os.getenv('SANDBOX_URL', 'http://localhost:18001')
        self.workspace_path = Path(os.getenv('WORKSPACE_PATH', '/app/WORKSPACE'))
        self.mirrors_path = self.workspace_path / 'mirrors'

        logger.info(f"MirrorVanisherManager initialized with sandbox: {self.sandbox_url}")

    def _check_mirror_exists(self, name: str) -> Tuple[bool, Optional[Dict]]:
        """Check if a mirror exists in the sandbox.

        Args:
            name: Mirror name

        Returns:
            Tuple of (exists, mirror_info)
        """
        try:
            response = requests.get(
                f"{self.sandbox_url}/mirror-exists/{name}",
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('exists', False), result
            else:
                return False, None

        except Exception as e:
            handle_exception(e, context={'function': '_check_mirror_exists', 'name': name})
            return False, None

    def _get_all_mirrors(self) -> List[Dict]:
        """Get all registered mirrors from sandbox.

        Returns:
            List of mirror information dictionaries
        """
        try:
            response = requests.get(
                f"{self.sandbox_url}/mirror-list",
                timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('mirrors', [])
            else:
                return []

        except Exception as e:
            handle_exception(e, context={'function': '_get_all_mirrors'})
            return []

    def _check_vanisher_exists(self, label: str) -> bool:
        """Check if a vanisher is loaded (placeholder - would connect to actual vanisher manager).

        Args:
            label: Vanisher label

        Returns:
            True if vanisher exists
        """
        # In a real implementation, this would check the vanisher context manager
        # For now, we'll use a heuristic based on mirror existence
        # TODO: Integrate with actual VanisherContextManager from the main codebase
        return True  # Placeholder

    def list_mirror_vanishers(self) -> Dict[str, Any]:
        """List all directories that are both mirrors and vanishers.

        Returns:
            Dictionary with list of mirror+vanisher directories
        """
        try:
            mirrors = self._get_all_mirrors()

            mirror_vanishers = []
            for mirror in mirrors:
                name = mirror.get('name', '')
                mirror_type = mirror.get('type', '')

                # Only include directories (not individual files)
                if mirror_type == 'directory':
                    # Check if it's also a vanisher
                    is_vanisher = self._check_vanisher_exists(name)

                    if is_vanisher:
                        mirror_vanishers.append({
                            'name': name,
                            'file_count': mirror.get('file_count', 0),
                            'sync_status': mirror.get('sync_status', 'unknown'),
                            'created_at': mirror.get('created_at', ''),
                            'path': str(self.mirrors_path / name)
                        })

            return {
                'success': True,
                'count': len(mirror_vanishers),
                'mirror_vanishers': mirror_vanishers
            }

        except Exception as e:
            handle_exception(e, context={'function': 'list_mirror_vanishers'})
            return {
                'success': False,
                'error': str(e),
                'mirror_vanishers': []
            }

    def verify_mirror_vanisher(self, path: str) -> Dict[str, Any]:
        """Verify that a path is both a mirror and a vanisher.

        Args:
            path: Path to verify

        Returns:
            Dictionary with verification results
        """
        try:
            path_obj = Path(path)
            name = path_obj.name

            # Check mirror
            is_mirror, mirror_info = self._check_mirror_exists(name)

            # Check vanisher
            is_vanisher = self._check_vanisher_exists(name)

            # Check if it's a directory mirror
            # Handle both 'type' == 'directory' and 'is_file' == False
            if mirror_info:
                is_directory = (mirror_info.get('type') == 'directory' or
                              mirror_info.get('is_file') == False)
            else:
                is_directory = False

            is_valid = is_mirror and is_vanisher and is_directory

            result = {
                'success': True,
                'is_mirror': is_mirror,
                'is_vanisher': is_vanisher,
                'is_directory': is_directory,
                'is_valid_mirror_vanisher': is_valid,
                'name': name,
                'path': path
            }

            if is_mirror and mirror_info:
                result['mirror_info'] = mirror_info

            if not is_valid:
                reasons = []
                if not is_mirror:
                    reasons.append("Not mirrored (use '/mirror do @<path>' first)")
                if not is_vanisher:
                    reasons.append("Not loaded as vanisher (use '/vanisher load @<path>' first)")
                if not is_directory:
                    reasons.append("Not a directory mirror (must be a directory)")
                result['reasons'] = reasons

            return result

        except Exception as e:
            handle_exception(e, context={'function': 'verify_mirror_vanisher', 'path': path})
            return {
                'success': False,
                'error': str(e),
                'is_valid_mirror_vanisher': False
            }

    def get_mirror_path(self, name: str) -> Optional[Path]:
        """Get the sandbox path for a mirror.

        Args:
            name: Mirror name

        Returns:
            Path object or None if not found
        """
        mirror_path = self.mirrors_path / name
        if mirror_path.exists():
            return mirror_path
        return None

    def resolve_path(self, path: str) -> Optional[Path]:
        """Resolve a path to a mirror+vanisher directory in the sandbox.

        Args:
            path: Path to resolve (can be mirror name or full path)

        Returns:
            Resolved Path object or None
        """
        try:
            path_obj = Path(path)

            # If it's just a name, try to find it in mirrors
            if not path_obj.is_absolute() and '/' not in path:
                mirror_path = self.get_mirror_path(path)
                if mirror_path:
                    return mirror_path

            # Otherwise try to resolve directly
            if path_obj.exists():
                return path_obj.resolve()

            # Try as relative to mirrors directory
            mirror_path = self.mirrors_path / path
            if mirror_path.exists():
                return mirror_path

            return None

        except Exception as e:
            handle_exception(e, context={'function': 'resolve_path', 'path': path})
            return None
