"""Eternal context management for persistent cross-session context.

This module provides eternal context storage that persists across sessions.
Unlike ephemeral context (session-scoped) and conversation history (temporary),
eternal context is:
- Loaded manually via CLI commands
- Persisted to disk (survives CLI restarts)
- Fully injected (not retrieved via similarity)
- Cross-session (permanent until explicitly deleted)
- File-based (can load documentation, specifications, etc.)
"""

import json
import requests
import numpy as np
import redis
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from src.utils.config_loader import ConfigLoader
from src.errors_handler import handle_exception


@dataclass
class EternalContext:
    """Represents a single eternal context loaded from a file."""

    label: str  # User-friendly label for this context
    file_path: str  # Original file path
    content: str  # Full text content
    timestamp: str  # ISO format timestamp when loaded
    description: str = ""  # Description/summary for semantic matching
    description_embedding: Optional[List[float]] = None  # Embedding of description (stored as list for JSON serialization)
    chunks: List[str] = field(default_factory=list)  # Chunks if content is large

    def get_size_bytes(self) -> int:
        """Get size of content in bytes."""
        return len(self.content.encode('utf-8'))

    def get_size_kb(self) -> float:
        """Get size of content in KB."""
        return self.get_size_bytes() / 1024

    def is_chunked(self) -> bool:
        """Check if content was chunked."""
        return len(self.chunks) > 0

    def to_dict(self) -> Dict:
        """Convert to dictionary representation (for JSON serialization)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'EternalContext':
        """Create instance from dictionary."""
        return cls(**data)

    def to_summary_dict(self) -> Dict:
        """Convert to summary dictionary (without full content)."""
        return {
            'label': self.label,
            'file_path': self.file_path,
            'content_size': self.get_size_bytes(),
            'timestamp': self.timestamp,
            'is_chunked': self.is_chunked(),
            'num_chunks': len(self.chunks)
        }


class EternalContextManager:
    """Manages persistent eternal context that survives across sessions."""

    def __init__(self, enabled: bool = None, storage_dir: Optional[str] = None):
        """Initialize the eternal context manager.

        Args:
            enabled: Whether eternal context is enabled (overrides config)
            storage_dir: Custom storage directory (overrides config)
        """
        self.contexts: Dict[str, EternalContext] = {}  # label -> context
        self.config = ConfigLoader()

        # Load settings from config with parameter overrides
        if enabled is None:
            eternal_config = self.config.get('eternal_context', default={})
            self.enabled = eternal_config.get('enabled', True)
        else:
            self.enabled = enabled

        # Get configuration
        eternal_config = self.config.get('eternal_context', default={})
        self.max_file_size_mb = eternal_config.get('max_file_size_mb', 10)
        self.max_contexts = eternal_config.get('max_contexts', 20)
        chunking_config = eternal_config.get('chunking', {})
        self.chunking_enabled = chunking_config.get('enabled', True)
        self.chunk_size = chunking_config.get('chunk_size', 1000)
        self.chunk_overlap = chunking_config.get('overlap', 200)

        # Semantic filtering configuration
        semantic_config = eternal_config.get('semantic_filtering', {})
        self.semantic_filtering_enabled = semantic_config.get('enabled', True)
        self.similarity_threshold = semantic_config.get('similarity_threshold', 0.5)

        # Set storage directory
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            default_dir = eternal_config.get('storage_dir', '.vuhitra/eternal_contexts')
            self.storage_dir = Path(default_dir).expanduser().resolve()

        # Create storage directory if it doesn't exist
        if self.enabled:
            try:
                self.storage_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                handle_exception(e, context={
                    'function': '__init__',
                    'storage_dir': str(self.storage_dir)
                })

        # Get transformer service URL
        self.transformer_url = self._get_transformer_url()

        # Initialize Redis for embedding caching
        self.redis_client = None
        self._init_redis()

        # Load existing eternal contexts from storage
        if self.enabled:
            self._load_from_storage()

    def _get_transformer_url(self) -> str:
        """Get transformer service URL from config with fallback to sandbox health check."""
        try:
            # Primary: Use config
            transformer_url = self.config.get_transformer_url()
            if transformer_url:
                return transformer_url

            # Fallback: Try to get from sandbox health endpoint
            sandbox_url = self.config.get_sandbox_url()
            health_endpoint = f"{sandbox_url}/health"
            response = requests.get(health_endpoint, timeout=2)

            if response.status_code == 200:
                data = response.json()
                retriever_health = data.get('retriever', {})
                transformer_url = retriever_health.get('transformer_url')

                if transformer_url:
                    return transformer_url

            # Final fallback to config default
            return self.config.get_transformer_url()

        except Exception as e:
            handle_exception(e, context={
                'function': '_get_transformer_url',
                'fallback': self.config.get_transformer_url()
            })
            return self.config.get_transformer_url()

    def _init_redis(self):
        """Initialize Redis connection for embedding caching."""
        try:
            redis_host = self.config.get('redis', 'host', default='localhost')
            redis_port = self.config.get('redis', 'port', default=6379)

            # Get password from secrets (optional)
            try:
                redis_password = self.config.get_redis_password()
            except ValueError:
                redis_password = None

            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                decode_responses=False,  # We'll store binary data (embeddings)
                socket_connect_timeout=2
            )

            # Test connection
            self.redis_client.ping()

        except Exception as e:
            # Redis is optional - continue without it
            handle_exception(e, context={
                'function': '_init_redis',
                'note': 'Embedding caching will be disabled'
            })
            self.redis_client = None

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
        if not self.redis_client:
            return None

        try:
            key = self._get_embedding_cache_key(text)
            cached_data = self.redis_client.get(key)

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
        if not self.redis_client:
            return False

        try:
            key = self._get_embedding_cache_key(text)
            # Serialize numpy array to bytes
            embedding_bytes = embedding.tobytes()

            # Cache for 30 days
            self.redis_client.setex(key, 30 * 24 * 60 * 60, embedding_bytes)
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
            # Use first 1000 characters for summary generation
            preview = content[:1000]

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
                # Limit to 200 characters
                if len(description) > 200:
                    description = description[:197] + "..."
                return description

            return None

        except Exception as e:
            handle_exception(e, context={
                'function': '_generate_description_with_llm',
                'filename': filename
            })
            return None

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Compute cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        try:
            # Normalize vectors
            vec1_norm = vec1 / (np.linalg.norm(vec1) + 1e-10)
            vec2_norm = vec2 / (np.linalg.norm(vec2) + 1e-10)

            # Compute dot product
            similarity = np.dot(vec1_norm, vec2_norm)

            # Clip to [0, 1] range
            return float(max(0.0, min(1.0, similarity)))

        except Exception as e:
            handle_exception(e, context={
                'function': '_cosine_similarity'
            })
            return 0.0

    def _chunk_text(self, text: str) -> List[str]:
        """Chunk text into overlapping segments for large files.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        try:
            # Simple word-based chunking with overlap
            words = text.split()
            chunks = []

            if len(words) <= self.chunk_size:
                return [text]  # No chunking needed

            i = 0
            while i < len(words):
                chunk_words = words[i:i + self.chunk_size]
                chunks.append(' '.join(chunk_words))

                # Move forward by (chunk_size - overlap)
                step = max(1, self.chunk_size - self.chunk_overlap)
                i += step

            return chunks

        except Exception as e:
            handle_exception(e, context={
                'function': '_chunk_text',
                'text_length': len(text)
            })
            return [text]  # Return as single chunk on error

    def _get_storage_path(self, label: str) -> Path:
        """Get storage file path for a label.

        Args:
            label: Context label

        Returns:
            Path to storage file
        """
        # Sanitize label for filename
        safe_label = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in label)
        return self.storage_dir / f"{safe_label}.json"

    def _save_to_storage(self, context: EternalContext) -> bool:
        """Save a context to persistent storage.

        Args:
            context: Context to save

        Returns:
            True if successful, False otherwise
        """
        try:
            storage_path = self._get_storage_path(context.label)
            data = context.to_dict()

            with storage_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            handle_exception(e, context={
                'function': '_save_to_storage',
                'label': context.label,
                'storage_path': str(storage_path) if 'storage_path' in locals() else 'unknown'
            })
            return False

    def _delete_from_storage(self, label: str) -> bool:
        """Delete a context from persistent storage.

        Args:
            label: Context label to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            storage_path = self._get_storage_path(label)

            if storage_path.exists():
                storage_path.unlink()
                return True

            return False

        except Exception as e:
            handle_exception(e, context={
                'function': '_delete_from_storage',
                'label': label
            })
            return False

    def _load_from_storage(self) -> int:
        """Load all eternal contexts from storage on startup.

        Returns:
            Number of contexts loaded
        """
        loaded_count = 0

        try:
            if not self.storage_dir.exists():
                return 0

            # Load all JSON files from storage directory
            for json_file in self.storage_dir.glob('*.json'):
                try:
                    with json_file.open('r', encoding='utf-8') as f:
                        data = json.load(f)

                    context = EternalContext.from_dict(data)
                    self.contexts[context.label] = context
                    loaded_count += 1

                except Exception as e:
                    handle_exception(e, context={
                        'function': '_load_from_storage',
                        'file': str(json_file)
                    })
                    # Continue loading other files

            return loaded_count

        except Exception as e:
            handle_exception(e, context={
                'function': '_load_from_storage',
                'storage_dir': str(self.storage_dir)
            })
            return loaded_count

    def load_file(self, file_path: str, label: Optional[str] = None, description: Optional[str] = None) -> Tuple[bool, str]:
        """Load a file into eternal context and persist it.

        Args:
            file_path: Path to file to load
            label: Optional user-friendly label (defaults to filename)
            description: Optional description/summary for semantic matching

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.enabled:
            return False, "Eternal context is disabled"

        try:
            # Resolve path
            path = Path(file_path).resolve()

            if not path.exists():
                return False, f"File not found: {file_path}"

            if not path.is_file():
                return False, f"Not a file: {file_path}"

            # Check file size
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                return False, f"File too large: {file_size_mb:.2f} MB (max: {self.max_file_size_mb} MB)"

            # Check max contexts limit
            if len(self.contexts) >= self.max_contexts:
                return False, f"Maximum number of eternal contexts reached ({self.max_contexts}). Clear some contexts first."

            # Generate label
            if label is None:
                label = path.stem  # Use filename without extension

            # Check if label already exists
            if label in self.contexts:
                return False, f"Eternal context with label '{label}' already exists. Use a different label or clear it first."

            # Read file content
            try:
                content = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try with latin-1 as fallback
                content = path.read_text(encoding='latin-1')

            if not content.strip():
                return False, f"File is empty: {file_path}"

            # Use provided description or auto-generate with LLM
            if description is None:
                # Try to auto-generate description using LLM
                description = self._generate_description_with_llm(content, path.name)

                # Fallback to filename if auto-generation fails
                if description is None:
                    description = f"Content from {path.name}"

            # Generate embedding for description (for semantic filtering)
            description_embedding = None
            if self.semantic_filtering_enabled and description:
                desc_emb = self._generate_embedding(description)
                if desc_emb is not None:
                    # Convert to list for JSON serialization
                    description_embedding = desc_emb.tolist()

            # Create eternal context
            context = EternalContext(
                label=label,
                file_path=str(path),
                content=content,
                timestamp=datetime.now().isoformat(),
                description=description,
                description_embedding=description_embedding
            )

            # Chunk if needed
            if self.chunking_enabled:
                chunks = self._chunk_text(content)

                if len(chunks) > 1:
                    context.chunks = chunks

            # Add to contexts
            self.contexts[label] = context

            # Persist to storage
            if not self._save_to_storage(context):
                # Rollback if save failed
                del self.contexts[label]
                return False, f"Failed to persist eternal context to storage"

            # Build success message
            size_kb = context.get_size_kb()
            if context.is_chunked():
                msg = f"✓ Loaded eternal context '{label}' ({size_kb:.1f} KB, {len(context.chunks)} chunks, persisted)"
            else:
                msg = f"✓ Loaded eternal context '{label}' ({size_kb:.1f} KB, 1 chunk, persisted)"

            return True, msg

        except Exception as e:
            handle_exception(e, context={
                'function': 'load_file',
                'file_path': file_path,
                'label': label
            })
            return False, f"Error loading file: {str(e)}"

    def get_relevant_contexts(self, prompt: str, verbose: bool = False) -> List[Tuple[str, EternalContext, float]]:
        """Get contexts relevant to the prompt based on semantic similarity.

        Args:
            prompt: User's prompt
            verbose: Whether to print debug information

        Returns:
            List of tuples (label, context, similarity_score) sorted by relevance
        """
        if not self.enabled or not self.contexts:
            return []

        # If semantic filtering is disabled, return all contexts
        if not self.semantic_filtering_enabled:
            return [(label, ctx, 1.0) for label, ctx in self.contexts.items()]

        try:
            # Generate embedding for prompt
            prompt_embedding = self._generate_embedding(prompt)
            if prompt_embedding is None:
                # Fallback: return all contexts if embedding generation fails
                return [(label, ctx, 1.0) for label, ctx in self.contexts.items()]

            relevant_contexts = []

            for label, ctx in self.contexts.items():
                # Use stored description embedding or generate if not available
                if ctx.description_embedding is not None:
                    desc_embedding = np.array(ctx.description_embedding, dtype=np.float32)
                else:
                    # Fallback: generate embedding on-the-fly
                    desc_embedding = self._generate_embedding(ctx.description)
                    if desc_embedding is None:
                        continue

                # Calculate similarity
                similarity = self._cosine_similarity(prompt_embedding, desc_embedding)

                # Filter by threshold
                if similarity >= self.similarity_threshold:
                    relevant_contexts.append((label, ctx, similarity))

            # Sort by similarity (descending)
            relevant_contexts.sort(key=lambda x: x[2], reverse=True)

            return relevant_contexts

        except Exception as e:
            handle_exception(e, context={
                'function': 'get_relevant_contexts',
                'num_contexts': len(self.contexts)
            })
            # Fallback: return all contexts on error
            return [(label, ctx, 1.0) for label, ctx in self.contexts.items()]

    def get_context_string(self, prompt: Optional[str] = None, verbose: bool = False) -> str:
        """Return formatted context string for prompt injection.

        Args:
            prompt: Optional prompt to filter contexts by semantic relevance
            verbose: Whether to print debug information

        Returns:
            Formatted string containing relevant eternal contexts
        """
        if not self.enabled or not self.contexts:
            return ""

        try:
            # Get relevant contexts (filtered if prompt provided)
            if prompt and self.semantic_filtering_enabled:
                relevant = self.get_relevant_contexts(prompt, verbose=verbose)

                if not relevant:
                    return ""  # No relevant contexts found

                lines = ["=== Eternal Context (Permanent Reference Materials) ==="]

                for label, ctx, similarity in relevant:
                    lines.append(f"\n--- {label} (relevance: {similarity:.2%}) ---")
                    lines.append(ctx.content)
                    lines.append(f"--- End of {label} ---\n")

                lines.append("=== End of Eternal Context ===\n")

                return "\n".join(lines)
            else:
                # Return all contexts (no filtering)
                lines = ["=== Eternal Context (Permanent Reference Materials) ==="]

                for label, ctx in self.contexts.items():
                    lines.append(f"\n--- {label} ---")
                    lines.append(ctx.content)
                    lines.append(f"--- End of {label} ---\n")

                lines.append("=== End of Eternal Context ===\n")

                return "\n".join(lines)

        except Exception as e:
            handle_exception(e, context={
                'function': 'get_context_string',
                'num_contexts': len(self.contexts)
            })
            return ""

    def clear_all(self) -> int:
        """Clear all eternal contexts and delete from storage.

        Returns:
            Number of contexts cleared
        """
        count = len(self.contexts)

        try:
            # Delete from storage
            for label in list(self.contexts.keys()):
                self._delete_from_storage(label)

            # Clear from memory
            self.contexts.clear()

            return count

        except Exception as e:
            handle_exception(e, context={
                'function': 'clear_all'
            })
            return 0

    def remove_by_label(self, label: str) -> bool:
        """Remove specific eternal context by label and delete from storage.

        Args:
            label: Label of context to remove

        Returns:
            True if removed, False if not found
        """
        try:
            if label in self.contexts:
                # Delete from storage
                self._delete_from_storage(label)

                # Remove from memory
                del self.contexts[label]

                return True

            return False

        except Exception as e:
            handle_exception(e, context={
                'function': 'remove_by_label',
                'label': label
            })
            return False

    def get_context_count(self) -> int:
        """Get the number of loaded eternal contexts."""
        return len(self.contexts)

    def get_all_contexts(self) -> List[Dict]:
        """Get all eternal contexts as list of dictionaries.

        Returns:
            List of context dictionaries (without full content)
        """
        return [ctx.to_summary_dict() for ctx in self.contexts.values()]

    def get_context_by_label(self, label: str) -> Optional[EternalContext]:
        """Get eternal context by label.

        Args:
            label: Label to search for

        Returns:
            EternalContext if found, None otherwise
        """
        return self.contexts.get(label)

    def is_enabled(self) -> bool:
        """Check if eternal context is enabled."""
        return self.enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable eternal context.

        Args:
            enabled: Whether to enable eternal context
        """
        self.enabled = enabled
        if not enabled:
            self.clear_all()

    def get_total_size_kb(self) -> float:
        """Get total size of all eternal contexts in KB.

        Returns:
            Total size in KB
        """
        total_bytes = sum(ctx.get_size_bytes() for ctx in self.contexts.values())
        return total_bytes / 1024

    def get_summary(self) -> str:
        """Get a summary of loaded eternal contexts.

        Returns:
            Formatted summary string
        """
        if not self.contexts:
            return "No eternal contexts loaded"

        lines = ["Loaded eternal contexts:"]

        for i, (label, ctx) in enumerate(self.contexts.items(), 1):
            size_kb = ctx.get_size_kb()
            if ctx.is_chunked():
                chunks_info = f"{len(ctx.chunks)} chunks"
            else:
                chunks_info = "1 chunk"

            lines.append(f"  {i}. {label} ({size_kb:.1f} KB, {chunks_info}) - {ctx.file_path}")

        total_kb = self.get_total_size_kb()
        lines.append(f"\nTotal size: {total_kb:.1f} KB")
        lines.append(f"Contexts: {len(self.contexts)}/{self.max_contexts}")
        lines.append(f"Storage: {self.storage_dir}")

        return "\n".join(lines)

    def reload_from_file(self, label: str) -> Tuple[bool, str]:
        """Reload an eternal context from its original file.

        Args:
            label: Label of context to reload

        Returns:
            Tuple of (success: bool, message: str)
        """
        if label not in self.contexts:
            return False, f"Eternal context '{label}' not found"

        ctx = self.contexts[label]
        original_path = ctx.file_path

        # Remove and reload
        self.remove_by_label(label)
        return self.load_file(original_path, label)
