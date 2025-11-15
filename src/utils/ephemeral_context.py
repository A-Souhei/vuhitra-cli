"""Ephemeral context management for session-scoped file-based context.

This module provides ephemeral context storage that can be loaded from files
and injected into every prompt without retrieval. Unlike conversation history
(incremental) and heuristics (retrieved), ephemeral context is:
- Loaded manually via CLI commands
- Fully injected (not retrieved via similarity)
- Session-scoped (persists until cleared)
- File-based (can load documentation, specifications, etc.)
"""

import requests
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from src.utils.config_loader import ConfigLoader
from src.errors_handler import handle_exception


@dataclass
class EphemeralContext:
    """Represents a single ephemeral context loaded from a file."""

    label: str  # User-friendly label for this context
    file_path: str  # Original file path
    content: str  # Full text content
    timestamp: str  # ISO format timestamp when loaded
    embedding: Optional[np.ndarray] = None  # Full document embedding
    chunks: List[str] = field(default_factory=list)  # Chunks if content is large
    chunk_embeddings: List[np.ndarray] = field(default_factory=list)  # Per-chunk embeddings

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
            'num_chunks': len(self.chunks)
        }


class EphemeralContextManager:
    """Manages session-scoped ephemeral context loaded from files."""

    def __init__(self, enabled: bool = None):
        """Initialize the ephemeral context manager.

        Args:
            enabled: Whether ephemeral context is enabled (overrides config)
        """
        self.contexts: List[EphemeralContext] = []
        self.config = ConfigLoader()

        # Load settings from config with parameter overrides
        if enabled is None:
            ephemeral_config = self.config.get('ephemeral_context', default={})
            self.enabled = ephemeral_config.get('enabled', True)
        else:
            self.enabled = enabled

        # Get configuration
        ephemeral_config = self.config.get('ephemeral_context', default={})
        self.max_file_size_mb = ephemeral_config.get('max_file_size_mb', 10)
        self.max_contexts = ephemeral_config.get('max_contexts', 10)
        chunking_config = ephemeral_config.get('chunking', {})
        self.chunking_enabled = chunking_config.get('enabled', True)
        self.chunk_size = chunking_config.get('chunk_size', 1000)
        self.chunk_overlap = chunking_config.get('overlap', 200)

        # Get transformer service URL
        self.transformer_url = self._get_transformer_url()

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

    def _generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text using transformer service.

        Args:
            text: Text to embed

        Returns:
            Numpy array of embedding vector, or None if failed
        """
        try:
            endpoint = f"{self.transformer_url}/api/generate-embedding"
            response = requests.post(
                endpoint,
                json={"text": text},
                timeout=30  # Longer timeout for potentially large texts
            )
            response.raise_for_status()
            data = response.json()

            embedding = data.get('embedding')
            if embedding:
                return np.array(embedding, dtype=np.float32)

            return None

        except Exception as e:
            handle_exception(e, context={
                'function': '_generate_embedding',
                'endpoint': endpoint if 'endpoint' in locals() else 'unknown',
                'text_length': len(text)
            })
            return None

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

    def load_file(self, file_path: str, label: Optional[str] = None) -> Tuple[bool, str]:
        """Load a file into ephemeral context with full embedding.

        Args:
            file_path: Path to file to load
            label: Optional user-friendly label (defaults to filename)

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.enabled:
            return False, "Ephemeral context is disabled"

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

            # Create ephemeral context
            context = EphemeralContext(
                label=label,
                file_path=str(path),
                content=content,
                timestamp=datetime.now().isoformat()
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
                msg = f"✓ Loaded '{label}' ({size_kb:.1f} KB, {len(context.chunks)} chunks, {len(context.chunk_embeddings)} embeddings)"
            else:
                embedding_status = "embedding generated" if context.embedding is not None else "no embedding"
                msg = f"✓ Loaded '{label}' ({size_kb:.1f} KB, 1 chunk, {embedding_status})"

            return True, msg

        except Exception as e:
            handle_exception(e, context={
                'function': 'load_file',
                'file_path': file_path,
                'label': label
            })
            return False, f"Error loading file: {str(e)}"

    def get_context_string(self) -> str:
        """Return formatted context string for prompt injection.

        Returns:
            Formatted string containing all ephemeral contexts
        """
        if not self.enabled or not self.contexts:
            return ""

        try:
            lines = ["=== Ephemeral Context (Session Reference Materials) ==="]

            for ctx in self.contexts:
                lines.append(f"\n--- {ctx.label} ---")
                lines.append(ctx.content)
                lines.append(f"--- End of {ctx.label} ---\n")

            lines.append("=== End of Ephemeral Context ===\n")

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
        """Clear all ephemeral contexts.

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

    def get_context_by_label(self, label: str) -> Optional[EphemeralContext]:
        """Get context by label.

        Args:
            label: Label to search for

        Returns:
            EphemeralContext if found, None otherwise
        """
        for ctx in self.contexts:
            if ctx.label == label:
                return ctx
        return None

    def is_enabled(self) -> bool:
        """Check if ephemeral context is enabled."""
        return self.enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable ephemeral context.

        Args:
            enabled: Whether to enable ephemeral context
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
        """Get a summary of loaded ephemeral contexts.

        Returns:
            Formatted summary string
        """
        if not self.contexts:
            return "No ephemeral contexts loaded"

        lines = ["Loaded ephemeral contexts:"]

        for i, ctx in enumerate(self.contexts, 1):
            size_kb = ctx.get_size_kb()
            if ctx.is_chunked():
                chunks_info = f"{len(ctx.chunks)} chunks"
            else:
                chunks_info = "1 chunk"

            lines.append(f"  {i}. {ctx.label} ({size_kb:.1f} KB, {chunks_info}) - {ctx.file_path}")

        total_kb = self.get_total_size_kb()
        lines.append(f"\nTotal size: {total_kb:.1f} KB")
        lines.append(f"Contexts: {len(self.contexts)}/{self.max_contexts}")

        return "\n".join(lines)
