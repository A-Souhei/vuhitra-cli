"""Token limit management with Redis-based storage.

This module provides automatic discovery and storage of model token limits.
When a model hits its token limit, we store that limit in Redis for future use.
"""

import logging
import redis
from typing import Optional
from src.utils.config_loader import ConfigLoader
from src.errors_handler import handle_exception

logger = logging.getLogger(__name__)

# Default infinite limit (will be discovered through usage)
DEFAULT_TOKEN_LIMIT = float('inf')

# Estimate: ~4 characters per token for English text
CHARS_PER_TOKEN_ESTIMATE = 4


class TokenLimitManager:
    """Manages model token limits with Redis-based discovery and storage."""

    def __init__(self):
        """Initialize the token limit manager."""
        self.config = ConfigLoader()
        self.redis_client = None
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            redis_host = self.config.get('redis', 'host', default='localhost')
            redis_port = self.config.get('redis', 'port', default=6379)

            # Get password from secrets
            try:
                redis_password = self.config.get_redis_password()
            except ValueError:
                # Password not required in some setups
                redis_password = None

            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=2
            )

            # Test connection
            self.redis_client.ping()
            logger.debug("TokenLimitManager: Redis connection established")

        except Exception as e:
            # Redis is optional - continue without it
            handle_exception(e, context={
                'function': '_init_redis',
                'note': 'Token limit discovery will not persist across sessions'
            })
            logger.warning("TokenLimitManager: Running without Redis (limits won't persist)")
            self.redis_client = None

    def _get_redis_key(self, model: str) -> str:
        """Get Redis key for storing model token limit.

        Args:
            model: Model name

        Returns:
            Redis key string
        """
        return f"model_token_limit:{model}"

    def get_limit(self, model: str) -> float:
        """Get the discovered token limit for a model.

        Args:
            model: Model name

        Returns:
            Token limit (float('inf') if not yet discovered)
        """
        if not self.redis_client:
            return DEFAULT_TOKEN_LIMIT

        try:
            key = self._get_redis_key(model)
            limit = self.redis_client.get(key)

            if limit:
                discovered_limit = int(limit)
                logger.debug(f"TokenLimitManager: Retrieved limit for {model}: {discovered_limit}")
                return float(discovered_limit)

            return DEFAULT_TOKEN_LIMIT

        except Exception as e:
            handle_exception(e, context={
                'function': 'get_limit',
                'model': model
            })
            return DEFAULT_TOKEN_LIMIT

    def store_limit(self, model: str, token_limit: int) -> bool:
        """Store the discovered token limit for a model.

        Args:
            model: Model name
            token_limit: Discovered token limit

        Returns:
            True if stored successfully, False otherwise
        """
        if not self.redis_client:
            logger.warning(f"TokenLimitManager: Cannot store limit for {model} (no Redis)")
            return False

        try:
            key = self._get_redis_key(model)

            # Only update if new limit is smaller (more accurate)
            existing_limit = self.get_limit(model)
            if existing_limit != DEFAULT_TOKEN_LIMIT and token_limit >= existing_limit:
                logger.debug(f"TokenLimitManager: Existing limit {existing_limit} is smaller, not updating")
                return False

            self.redis_client.set(key, token_limit)
            logger.info(f"TokenLimitManager: Stored limit for {model}: {token_limit} tokens")
            return True

        except Exception as e:
            handle_exception(e, context={
                'function': 'store_limit',
                'model': model,
                'token_limit': token_limit
            })
            return False

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text length.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // CHARS_PER_TOKEN_ESTIMATE

    def extract_limit_from_error(self, error_message: str) -> Optional[int]:
        """Extract token limit from Ollama error message.

        Args:
            error_message: Error message from Ollama

        Returns:
            Extracted token limit or None if not found

        Examples:
            "context length exceeded: 2048 > 2047" -> 2047
            "prompt is too long: 5000 tokens > 4096 maximum" -> 4096
        """
        try:
            error_lower = error_message.lower()

            # Pattern 1: "X > Y" where Y is the limit
            if '>' in error_message:
                parts = error_message.split('>')
                if len(parts) >= 2:
                    # Extract number from right side
                    right_part = parts[1].strip()
                    # Get first number found
                    import re
                    numbers = re.findall(r'\d+', right_part)
                    if numbers:
                        limit = int(numbers[0])
                        logger.debug(f"TokenLimitManager: Extracted limit from error: {limit}")
                        return limit

            # Pattern 2: "maximum" keyword
            if 'maximum' in error_lower:
                import re
                # Find number before "maximum"
                match = re.search(r'(\d+)\s*maximum', error_lower)
                if match:
                    limit = int(match.group(1))
                    logger.debug(f"TokenLimitManager: Extracted limit from error: {limit}")
                    return limit

            return None

        except Exception as e:
            handle_exception(e, context={
                'function': 'extract_limit_from_error',
                'error_message': error_message[:100]  # Truncate for logging
            })
            return None

    def check_limit(self, model: str, text: str) -> tuple[bool, Optional[str]]:
        """Check if text is within the model's token limit.

        Args:
            model: Model name
            text: Text to check

        Returns:
            Tuple of (is_within_limit, warning_message)
        """
        limit = self.get_limit(model)

        # If limit is infinite, always pass
        if limit == DEFAULT_TOKEN_LIMIT:
            return True, None

        estimated_tokens = self.estimate_tokens(text)

        # Use 95% threshold to be safe
        safe_limit = int(limit * 0.95)

        if estimated_tokens > safe_limit:
            warning = (
                f"Prompt may exceed token limit for {model}\n"
                f"Estimated: ~{estimated_tokens} tokens, Limit: {limit} tokens\n"
                f"Consider using /clear context or shortening your prompt"
            )
            return False, warning

        return True, None

    def clear_limit(self, model: str) -> bool:
        """Clear the stored limit for a model (for testing/reset).

        Args:
            model: Model name

        Returns:
            True if cleared successfully
        """
        if not self.redis_client:
            return False

        try:
            key = self._get_redis_key(model)
            self.redis_client.delete(key)
            logger.info(f"TokenLimitManager: Cleared limit for {model}")
            return True
        except Exception as e:
            handle_exception(e, context={
                'function': 'clear_limit',
                'model': model
            })
            return False


# Global singleton instance
_token_limit_manager = None


def get_token_limit_manager() -> TokenLimitManager:
    """Get the global TokenLimitManager instance.

    Returns:
        TokenLimitManager singleton
    """
    global _token_limit_manager
    if _token_limit_manager is None:
        _token_limit_manager = TokenLimitManager()
    return _token_limit_manager
