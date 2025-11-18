"""Shared utilities for embedding generation and caching.

This module provides common functionality for:
- Redis-based embedding caching
- Embedding generation via transformer service
- LLM-based description generation
- Cosine similarity computation
"""

import hashlib
import redis
import requests
import numpy as np
from typing import Optional
from src.errors_handler import handle_exception
from src.utils.config_loader import ConfigLoader

# Constants
EMBEDDING_CACHE_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
DESCRIPTION_PREVIEW_LENGTH = 1000  # Characters to use for LLM summary
DESCRIPTION_MAX_LENGTH = 200  # Maximum description length


class EmbeddingCacheMixin:
    """Mixin providing Redis caching for embeddings."""

    def _init_redis(self):
        """Initialize Redis connection for embedding caching.

        Uses a separate Redis client with decode_responses=False for binary embeddings.
        This is separate from any other Redis client the class may have for JSON data.
        """
        try:
            redis_host = self.config.get('redis', 'host', default='localhost')
            redis_port = self.config.get('redis', 'port', default=6379)

            # Get password from secrets (optional)
            try:
                redis_password = self.config.get_redis_password()
            except ValueError:
                redis_password = None

            self._embedding_redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=False,  # Binary data for embeddings
                socket_connect_timeout=2
            )

            # Test connection
            self._embedding_redis_client.ping()

        except Exception as e:
            # Redis is optional - continue without it
            handle_exception(e, context={
                'function': '_init_redis',
                'note': 'Embedding caching will be disabled'
            })
            self._embedding_redis_client = None

    # Alias for backwards compatibility
    _init_embedding_redis = _init_redis

    def _get_embedding_cache_key(self, text: str) -> str:
        """Generate Redis cache key for an embedding.

        Args:
            text: Text to generate key for

        Returns:
            Cache key string
        """
        # Use SHA256 hash of text as key
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return f"embedding_cache:{text_hash}"

    def _get_cached_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get cached embedding from Redis.

        Args:
            text: Text to get embedding for

        Returns:
            Cached embedding or None if not found
        """
        # Check if embedding redis client is initialized
        if not hasattr(self, '_embedding_redis_client') or not self._embedding_redis_client:
            return None

        try:
            key = self._get_embedding_cache_key(text)
            cached_data = self._embedding_redis_client.get(key)

            if cached_data:
                # Deserialize numpy array
                embedding = np.frombuffer(cached_data, dtype=np.float32)
                return embedding

            return None

        except Exception as e:
            handle_exception(e, context={
                'function': '_get_cached_embedding',
                'text_length': len(text)
            })
            return None

    def _cache_embedding(self, text: str, embedding: np.ndarray) -> bool:
        """Cache embedding in Redis.

        Args:
            text: Text the embedding is for
            embedding: Embedding vector to cache

        Returns:
            True if cached successfully
        """
        # Check if embedding redis client is initialized
        if not hasattr(self, '_embedding_redis_client') or not self._embedding_redis_client:
            return False

        try:
            key = self._get_embedding_cache_key(text)
            # Serialize numpy array to bytes
            embedding_bytes = embedding.tobytes()

            # Cache with configurable TTL
            self._embedding_redis_client.setex(key, EMBEDDING_CACHE_TTL_SECONDS, embedding_bytes)
            return True

        except Exception as e:
            handle_exception(e, context={
                'function': '_cache_embedding',
                'text_length': len(text)
            })
            return False

    def _generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text using transformer service with Redis caching.

        Args:
            text: Text to embed

        Returns:
            Numpy array of embedding vector, or None if failed
        """
        try:
            # Check cache first
            cached_embedding = self._get_cached_embedding(text)
            if cached_embedding is not None:
                return cached_embedding

            # Generate new embedding
            endpoint = f"{self.transformer_url}/api/generate-embedding"
            response = requests.post(
                endpoint,
                json={"text": text},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            embedding = data.get('embedding')
            if embedding:
                embedding_array = np.array(embedding, dtype=np.float32)

                # Cache the embedding
                self._cache_embedding(text, embedding_array)

                return embedding_array

            return None

        except Exception as e:
            handle_exception(e, context={
                'function': '_generate_embedding',
                'endpoint': endpoint if 'endpoint' in locals() else 'unknown',
                'text_length': len(text)
            })
            return None

    def _generate_description_with_llm(self, content: str, filename: str) -> Optional[str]:
        """Generate a description/summary of content using LLM.

        Args:
            content: File content
            filename: Name of the file

        Returns:
            Generated description or None if failed
        """
        try:
            # Use configured preview length for summary generation
            preview = content[:DESCRIPTION_PREVIEW_LENGTH]

            # Build prompt for LLM
            prompt = f"""Generate a brief 1-2 sentence description of this file content.
Focus on what the file contains and its purpose.
Do not include formatting, just return the plain text description.

Filename: {filename}

Content preview:
{preview}

Description:"""

            # Get Ollama config
            ollama_config = self.config.get('ollama', default={})
            use_mode = ollama_config.get('use', 'local')
            ollama_server = ollama_config.get(use_mode, {})

            # Get model config
            model_config = self.config.get('model', default={})
            default_models = model_config.get('default', {})
            model = default_models.get(use_mode, 'tinyllama')

            # Build Ollama URL
            protocol = ollama_server.get('protocol', 'http')
            host = ollama_server.get('host', 'localhost')
            port = ollama_server.get('port', 11434)
            api_path = ollama_server.get('api_path', '/api/generate')

            url = f"{protocol}://{host}:{port}{api_path}"

            # Call Ollama
            response = requests.post(
                url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            description = data.get('response', '').strip()

            # Clean up and limit description length
            if description:
                # Remove quotes if present
                description = description.strip('"\'')
                # Limit to configured max length
                if len(description) > DESCRIPTION_MAX_LENGTH:
                    description = description[:DESCRIPTION_MAX_LENGTH - 3] + "..."
                return description

            return None

        except Exception as e:
            handle_exception(e, context={
                'function': '_generate_description_with_llm',
                'filename': filename
            })
            return None


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        vec1: First vector
        vec2: Second vector

    Returns:
        Cosine similarity score (0-1), or 0.0 for zero vectors
    """
    try:
        # Check for zero vectors
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        
        # Normalize vectors
        vec1_norm = vec1 / norm1
        vec2_norm = vec2 / norm2

        # Compute dot product
        similarity = np.dot(vec1_norm, vec2_norm)

        # Clip to [0, 1] range (due to floating point errors)
        return float(np.clip(similarity, 0.0, 1.0))

    except Exception as e:
        handle_exception(e, context={
            'function': 'cosine_similarity',
            'vec1_shape': vec1.shape if hasattr(vec1, 'shape') else 'unknown',
            'vec2_shape': vec2.shape if hasattr(vec2, 'shape') else 'unknown'
        })
        return 0.0
