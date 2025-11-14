"""
Transformer Client Utility

Provides functions to interact with the Transformer NLP service
for context compaction and text processing.
"""

import requests
import time
import logging
from typing import Dict, Optional, Any
from src.utils.config_loader import ConfigLoader
from src.errors_handler import handle_exception

logger = logging.getLogger(__name__)


class TransformerClient:
    """Client for interacting with the Transformer NLP service."""

    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        """
        Initialize the transformer client.

        Args:
            config_loader: Optional ConfigLoader instance (creates new one if not provided)
        """
        self.config = config_loader or ConfigLoader()
        self._base_url = None
        self._is_enabled = None

    @property
    def base_url(self) -> str:
        """Get the base URL for the transformer service."""
        if self._base_url is None:
            host = self.config.get('transformer', 'host', default='localhost')
            port = self.config.get('transformer', 'port', default=15050)
            protocol = self.config.get('transformer', 'protocol', default='http')
            self._base_url = f"{protocol}://{host}:{port}"
        return self._base_url

    @property
    def is_enabled(self) -> bool:
        """Check if context compacter is enabled."""
        if self._is_enabled is None:
            self._is_enabled = self.config.get('context_compacter', 'enabled', default=True)
        return self._is_enabled

    def _make_request(
        self,
        endpoint: str,
        data: Dict[str, Any],
        timeout: int = 10,
        verbose: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Make a request to the transformer service.

        Args:
            endpoint: The API endpoint path
            data: Request payload
            timeout: Request timeout in seconds
            verbose: Whether to print verbose output

        Returns:
            Response data or None if request fails
        """
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()

        try:
            if verbose:
                logger.debug(f"Transformer request to {endpoint}: {data.keys()}")

            response = requests.post(url, json=data, timeout=timeout)
            response.raise_for_status()

            duration_ms = (time.time() - start_time) * 1000

            if verbose:
                logger.debug(f"Transformer response from {endpoint} in {duration_ms:.2f}ms")

            return response.json()

        except requests.exceptions.ConnectionError as e:
            # Service might not be running - this is not critical
            if verbose:
                logger.warning(f"Transformer service not available at {url}: {str(e)}")
            return None

        except requests.exceptions.Timeout as e:
            logger.warning(f"Transformer request timeout: {str(e)}")
            handle_exception(e, context={
                'function': '_make_request',
                'endpoint': endpoint,
                'timeout': timeout
            })
            return None

        except Exception as e:
            logger.error(f"Transformer request failed: {str(e)}")
            handle_exception(e, context={
                'function': '_make_request',
                'endpoint': endpoint
            })
            return None

    def create_matrix_context(
        self,
        prompt: str,
        heuristics: str = "",
        context: str = "",
        raw_text: str = "",
        verbose: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Create a matrix-style context for LLM consumption.

        This is the main method that:
        - Separates code from text
        - Compacts text components
        - Preserves code blocks
        - Generates structured matrix output

        Args:
            prompt: User's prompt
            heuristics: Heuristics from sandbox (optional)
            context: Additional context (optional)
            raw_text: Text that may contain code (optional)
            verbose: Whether to print verbose output

        Returns:
            Matrix context dictionary or None if service unavailable
        """
        if not self.is_enabled:
            if verbose:
                logger.info("Context compacter is disabled")
            return None

        endpoint = self.config.get(
            'transformer', 'endpoints', 'create_matrix',
            default='/api/create-matrix-context'
        )

        data = {
            'prompt': prompt,
            'heuristics': heuristics,
            'context': context,
            'raw_text': raw_text
        }

        return self._make_request(endpoint, data, timeout=15, verbose=verbose)

    def compact_prompt(
        self,
        prompt: str,
        verbose: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Compact a user prompt if it's too verbose.

        Args:
            prompt: The user's prompt
            verbose: Whether to print verbose output

        Returns:
            Compaction result or None if service unavailable
        """
        if not self.is_enabled:
            return None

        # Check if prompt exceeds threshold
        threshold = self.config.get(
            'context_compacter', 'prompt_compact_threshold',
            default=500
        )

        if len(prompt) < threshold:
            if verbose:
                logger.debug(f"Prompt ({len(prompt)} chars) below compaction threshold ({threshold})")
            return None

        endpoint = self.config.get(
            'transformer', 'endpoints', 'compact_prompt',
            default='/api/compact-prompt'
        )

        data = {'prompt': prompt}
        return self._make_request(endpoint, data, verbose=verbose)

    def recognize_code(
        self,
        text: str,
        verbose: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Recognize and separate code from text.

        Args:
            text: The text to analyze
            verbose: Whether to print verbose output

        Returns:
            Code recognition result or None if service unavailable
        """
        if not self.is_enabled:
            return None

        endpoint = self.config.get(
            'transformer', 'endpoints', 'recognize_code',
            default='/api/recognize-code'
        )

        data = {'text': text}
        return self._make_request(endpoint, data, verbose=verbose)

    def extract_keywords(
        self,
        text: str,
        top_n: Optional[int] = None,
        verbose: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Extract keywords from text.

        Args:
            text: The text to analyze
            top_n: Number of keywords to extract (uses config default if not provided)
            verbose: Whether to print verbose output

        Returns:
            Keywords extraction result or None if service unavailable
        """
        if not self.is_enabled:
            return None

        if top_n is None:
            top_n = self.config.get('context_compacter', 'max_keywords', default=10)

        endpoint = self.config.get(
            'transformer', 'endpoints', 'extract_keywords',
            default='/api/extract-keywords'
        )

        data = {
            'text': text,
            'top_n': top_n
        }
        return self._make_request(endpoint, data, verbose=verbose)


# Singleton instance
_transformer_client = None


def get_transformer_client(config_loader: Optional[ConfigLoader] = None) -> TransformerClient:
    """
    Get the singleton transformer client instance.

    Args:
        config_loader: Optional ConfigLoader instance

    Returns:
        TransformerClient instance
    """
    global _transformer_client
    if _transformer_client is None:
        _transformer_client = TransformerClient(config_loader)
    return _transformer_client
