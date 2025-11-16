"""Vanisher context management for coding mode session-scoped context.

This module provides vanisher context storage for session-scoped file-based context (coding mode only).
Vanishers behave exactly like ephemerals but with a key difference:
- Can only load files/directories that are mirrored (exist in Redis as mirrors)
- Only enabled in coding mode
- Session-scoped (cleared when session ends)
- Fully injected (not retrieved via similarity)
"""

import requests
import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from src.utils.config_loader import ConfigLoader
from src.errors_handler import handle_exception
from src.utils.embedding_utils import EmbeddingCacheMixin, cosine_similarity


@dataclass
class VanisherContext:
    """Represents a single vanisher context loaded from a mirrored file."""

    label: str  # User-friendly label for this context
    file_path: str  # Original file path
    content: str  # Full text content
    timestamp: str  # ISO format timestamp when loaded
    description: str = ""  # Description/summary for semantic matching
    description_embedding: Optional[np.ndarray] = None  # Embedding of description for semantic filtering
    embedding: Optional[np.ndarray] = None  # Full document embedding
    chunks: List[str] = field(default_factory=list)  # Chunks if content is large
    chunk_embeddings: List[np.ndarray] = field(default_factory=list)  # Per-chunk embeddings
    mirror_name: str = ""  # Name of the mirror in sandbox

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
        """Convert to dictionary representation (without embeddings)."""
        return {
            'label': self.label,
            'file_path': self.file_path,
            'content_size': self.get_size_bytes(),
            'timestamp': self.timestamp,
            'is_chunked': self.is_chunked(),
            'num_chunks': len(self.chunks),
            'mirror_name': self.mirror_name
        }


class VanisherContextManager(EmbeddingCacheMixin):
    """Manages session-scoped vanisher context (coding mode only, requires mirrors)."""

    def __init__(self, enabled: bool = None):
        """Initialize the vanisher context manager.

        Args:
            enabled: Whether vanisher context is enabled (overrides config)
        """
        self.contexts: List[VanisherContext] = []
        self.config = ConfigLoader()

        # Load settings from config with parameter overrides
        if enabled is None:
            vanisher_config = self.config.get('vanisher_context', default={})
            self.enabled = vanisher_config.get('enabled', True)
        else:
            self.enabled = enabled

        # Get configuration (fallback to ephemeral_context config for limits)
        vanisher_config = self.config.get('vanisher_context', default={})
        ephemeral_config = self.config.get('ephemeral_context', default={})
        self.max_file_size_mb = vanisher_config.get('max_file_size_mb', ephemeral_config.get('max_file_size_mb', 10))
        self.max_contexts = vanisher_config.get('max_contexts', ephemeral_config.get('max_contexts', 10))
        chunking_config = vanisher_config.get('chunking', ephemeral_config.get('chunking', {}))
        self.chunking_enabled = chunking_config.get('enabled', True)
        self.chunk_size = chunking_config.get('chunk_size', 1000)
        self.chunk_overlap = chunking_config.get('overlap', 200)

        # Semantic filtering configuration
        semantic_config = vanisher_config.get('semantic_filtering', ephemeral_config.get('semantic_filtering', {}))
        self.semantic_filtering_enabled = semantic_config.get('enabled', True)
        self.similarity_threshold = semantic_config.get('similarity_threshold', 0.5)

        # Get transformer service URL
        self.transformer_url = self._get_transformer_url()

        # Initialize Redis for embedding caching
        self.redis_client = None
        self._init_redis()

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

    def _check_mirror_exists(self, mirror_name: str) -> Tuple[bool, Optional[Dict]]:
        """Check if a mirror exists in the sandbox.

        Args:
            mirror_name: Name of the mirror to check

        Returns:
            Tuple of (exists: bool, mirror_info: Optional[Dict])
        """
        try:
            sandbox_url = self.config.get_sandbox_url()
            response = requests.get(
                f"{sandbox_url}/mirror-exists/{mirror_name}",
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('exists'):
                    return True, result
                else:
                    return False, None
            else:
                return False, None

        except Exception as e:
            handle_exception(e, context={
                'function': '_check_mirror_exists',
                'mirror_name': mirror_name
            })
            return False, None

    def load_file(self, file_path: str, label: Optional[str] = None, description: Optional[str] = None) -> Tuple[bool, str]:
        """Load a file into vanisher context if it's mirrored.

        IMPORTANT: The file/directory must be mirrored to sandbox first using /mirror do @path.

        Args:
            file_path: Path to file to load
            label: Optional user-friendly label (defaults to filename)
            description: Optional description/summary for semantic matching

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.enabled:
            return False, "Vanisher context is disabled"

        try:
            # Resolve path
            path = Path(file_path).resolve()

            if not path.exists():
                return False, f"File not found: {file_path}"

            if not path.is_file():
                return False, f"Not a file: {file_path}"

            # Generate mirror name from path
            mirror_name = path.stem if path.is_file() else path.name

            # Check if file is mirrored
            is_mirrored, mirror_info = self._check_mirror_exists(mirror_name)
            if not is_mirrored:
                return False, f"Cannot load vanisher: '{mirror_name}' is not mirrored. Use '/mirror do @{path.name}' first to mirror it."

            # Check file size
            file_size_mb = path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_file_size_mb:
                return False, f"File too large: {file_size_mb:.2f} MB (max: {self.max_file_size_mb} MB)"

            # Check max contexts limit
            if len(self.contexts) >= self.max_contexts:
                return False, f"Maximum number of contexts reached ({self.max_contexts}). Clear some contexts first."

            # Generate label
            if label is None:
                label = path.stem  # Use filename without extension

            # Check if label already exists
            if any(ctx.label == label for ctx in self.contexts):
                return False, f"Context with label '{label}' already exists. Use a different label or clear it first."

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
                description_embedding = self._generate_embedding(description)

            # Create vanisher context
            context = VanisherContext(
                label=label,
                file_path=str(path),
                content=content,
                timestamp=datetime.now().isoformat(),
                description=description,
                description_embedding=description_embedding,
                mirror_name=mirror_name
            )

            # Chunk if needed
            if self.chunking_enabled:
                chunks = self._chunk_text(content)

                if len(chunks) > 1:
                    context.chunks = chunks

                    # Generate embeddings for each chunk
                    for i, chunk in enumerate(chunks):
                        embedding = self._generate_embedding(chunk)
                        if embedding is not None:
                            context.chunk_embeddings.append(embedding)
                else:
                    # Single chunk - generate full embedding
                    embedding = self._generate_embedding(content)
                    if embedding is not None:
                        context.embedding = embedding
            else:
                # No chunking - generate full embedding
                embedding = self._generate_embedding(content)
                if embedding is not None:
                    context.embedding = embedding

            # Add to contexts
            self.contexts.append(context)

            # Build success message
            size_kb = context.get_size_kb()
            if context.is_chunked():
                msg = f"✓ Loaded vanisher '{label}' ({size_kb:.1f} KB, {len(context.chunks)} chunks, {len(context.chunk_embeddings)} embeddings) [mirrored as '{mirror_name}']"
            else:
                embedding_status = "embedding generated" if context.embedding is not None else "no embedding"
                msg = f"✓ Loaded vanisher '{label}' ({size_kb:.1f} KB, 1 chunk, {embedding_status}) [mirrored as '{mirror_name}']"

            return True, msg

        except Exception as e:
            handle_exception(e, context={
                'function': 'load_file',
                'file_path': file_path,
                'label': label
            })
            return False, f"Error loading file: {str(e)}"

    def get_relevant_contexts(self, prompt: str, verbose: bool = False) -> List[Tuple[VanisherContext, float]]:
        """Get contexts relevant to the prompt based on semantic similarity.

        Args:
            prompt: User's prompt
            verbose: Whether to print debug information

        Returns:
            List of tuples (context, similarity_score) sorted by relevance
        """
        if not self.enabled or not self.contexts:
            return []

        # If semantic filtering is disabled, return all contexts
        if not self.semantic_filtering_enabled:
            return [(ctx, 1.0) for ctx in self.contexts]

        try:
            # Generate embedding for prompt
            prompt_embedding = self._generate_embedding(prompt)
            if prompt_embedding is None:
                # Log warning when embedding generation fails
                logging.warning("Failed to generate embedding for prompt, returning all contexts unfiltered")
                # Fallback: return all contexts if embedding generation fails
                return [(ctx, 1.0) for ctx in self.contexts]

            relevant_contexts = []

            for ctx in self.contexts:
                # Use stored description embedding or generate if not available
                if ctx.description_embedding is not None:
                    desc_embedding = ctx.description_embedding
                    # Ensure desc_embedding is a numpy array (handle JSON deserialization)
                    if isinstance(desc_embedding, list):
                        desc_embedding = np.array(desc_embedding, dtype=np.float32)
                else:
                    # Fallback: generate embedding on-the-fly
                    desc_embedding = self._generate_embedding(ctx.description)
                    if desc_embedding is None:
                        continue

                # Calculate similarity using shared function
                similarity = cosine_similarity(prompt_embedding, desc_embedding)

                # Filter by threshold
                if similarity >= self.similarity_threshold:
                    relevant_contexts.append((ctx, similarity))

            # Sort by similarity (descending)
            relevant_contexts.sort(key=lambda x: x[1], reverse=True)

            return relevant_contexts

        except Exception as e:
            handle_exception(e, context={
                'function': 'get_relevant_contexts',
                'num_contexts': len(self.contexts)
            })
            # Fallback: return all contexts on error
            return [(ctx, 1.0) for ctx in self.contexts]

    def get_context_string(self, prompt: Optional[str] = None, verbose: bool = False) -> str:
        """Return formatted context string for prompt injection.

        Args:
            prompt: Optional prompt to filter contexts by semantic relevance
            verbose: Whether to print debug information

        Returns:
            Formatted string containing relevant vanisher contexts
        """
        if not self.enabled or not self.contexts:
            return ""

        try:
            # Get relevant contexts (filtered if prompt provided)
            if prompt and self.semantic_filtering_enabled:
                relevant = self.get_relevant_contexts(prompt, verbose=verbose)

                if not relevant:
                    return ""  # No relevant contexts found

                lines = ["=== Vanisher Context (Coding Mode Session Materials) ==="]

                for ctx, similarity in relevant:
                    lines.append(f"\n--- {ctx.label} (relevance: {similarity:.2%}) ---")
                    lines.append(ctx.content)
                    lines.append(f"--- End of {ctx.label} ---\n")

                lines.append("=== End of Vanisher Context ===\n")

                return "\n".join(lines)
            else:
                # Return all contexts (no filtering)
                lines = ["=== Vanisher Context (Coding Mode Session Materials) ==="]

                for ctx in self.contexts:
                    lines.append(f"\n--- {ctx.label} ---")
                    lines.append(ctx.content)
                    lines.append(f"--- End of {ctx.label} ---\n")

                lines.append("=== End of Vanisher Context ===\n")

                return "\n".join(lines)

        except Exception as e:
            handle_exception(e, context={
                'function': 'get_context_string',
                'num_contexts': len(self.contexts)
            })
            return ""

    def get_embeddings(self) -> List[np.ndarray]:
        """Return all embeddings (for advanced semantic operations).

        Returns:
            List of embedding arrays
        """
        embeddings = []

        try:
            for ctx in self.contexts:
                if ctx.embedding is not None:
                    embeddings.append(ctx.embedding)
                elif ctx.chunk_embeddings:
                    embeddings.extend(ctx.chunk_embeddings)

            return embeddings

        except Exception as e:
            handle_exception(e, context={
                'function': 'get_embeddings',
                'num_contexts': len(self.contexts)
            })
            return []

    def clear_all(self) -> int:
        """Clear all vanisher contexts.

        Returns:
            Number of contexts cleared
        """
        count = len(self.contexts)
        self.contexts.clear()
        return count

    def remove_by_label(self, label: str) -> bool:
        """Remove specific context by label.

        Args:
            label: Label of context to remove

        Returns:
            True if removed, False if not found
        """
        try:
            for i, ctx in enumerate(self.contexts):
                if ctx.label == label:
                    self.contexts.pop(i)
                    return True
            return False

        except Exception as e:
            handle_exception(e, context={
                'function': 'remove_by_label',
                'label': label
            })
            return False

    def get_context_count(self) -> int:
        """Get the number of loaded contexts."""
        return len(self.contexts)

    def get_all_contexts(self) -> List[Dict]:
        """Get all contexts as list of dictionaries.

        Returns:
            List of context dictionaries (without full content)
        """
        return [ctx.to_dict() for ctx in self.contexts]

    def get_context_by_label(self, label: str) -> Optional[VanisherContext]:
        """Get context by label.

        Args:
            label: Label to search for

        Returns:
            VanisherContext if found, None otherwise
        """
        for ctx in self.contexts:
            if ctx.label == label:
                return ctx
        return None

    def is_enabled(self) -> bool:
        """Check if vanisher context is enabled."""
        return self.enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable vanisher context.

        Args:
            enabled: Whether to enable vanisher context
        """
        self.enabled = enabled
        if not enabled:
            self.clear_all()

    def get_total_size_kb(self) -> float:
        """Get total size of all contexts in KB.

        Returns:
            Total size in KB
        """
        total_bytes = sum(ctx.get_size_bytes() for ctx in self.contexts)
        return total_bytes / 1024

    def get_summary(self) -> str:
        """Get a summary of loaded vanisher contexts.

        Returns:
            Formatted summary string
        """
        if not self.contexts:
            return "No vanisher contexts loaded"

        lines = ["Loaded vanisher contexts:"]

        for i, ctx in enumerate(self.contexts, 1):
            size_kb = ctx.get_size_kb()
            if ctx.is_chunked():
                chunks_info = f"{len(ctx.chunks)} chunks"
            else:
                chunks_info = "1 chunk"

            lines.append(f"  {i}. {ctx.label} ({size_kb:.1f} KB, {chunks_info}) [mirror: {ctx.mirror_name}] - {ctx.file_path}")

        total_kb = self.get_total_size_kb()
        lines.append(f"\nTotal size: {total_kb:.1f} KB")
        lines.append(f"Contexts: {len(self.contexts)}/{self.max_contexts}")

        return "\n".join(lines)
