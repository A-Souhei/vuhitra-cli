"""Spark context management for in-memory ephemeral context.

This module provides Spark context storage - a lightweight, in-memory-only
variant of ephemeral context. Sparks are:
- Created automatically when using @ prefix without /load or /load-eternal
- In-memory only (no persistence, no Redis storage)
- Dies with /clear context command
- Ideal for quick, temporary context injection
"""

import os
import requests
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from src.utils.config_loader import ConfigLoader
from src.errors_handler import handle_exception


@dataclass
class SparkContext:
    """Represents a single Spark context loaded from a file."""

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


class SparkContextManager:
    """Manages in-memory-only Spark contexts loaded from files."""

    def __init__(self, enabled: bool = None):
        """Initialize the Spark context manager.

        Args:
            enabled: Whether Spark context is enabled (overrides config)
        """
        self.contexts: List[SparkContext] = []
        self.config = ConfigLoader()

        # Load settings from config with parameter overrides
        if enabled is None:
            spark_config = self.config.get('spark_context', default={})
            self.enabled = spark_config.get('enabled', True)
        else:
            self.enabled = enabled

        # Get configuration
        spark_config = self.config.get('spark_context', default={})
        self.max_file_size_mb = spark_config.get('max_file_size_mb', 10)
        self.max_contexts = spark_config.get('max_contexts', 20)
        
        # Embedding configuration
        embed_config = spark_config.get('embed', {})
        self.embed_enabled = embed_config.get('enabled', True)
        
        # Chunking configuration (for large files)
        chunking_config = spark_config.get('chunking', {})
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
                retriever = data.get('retriever', {})
                transformer_health = retriever.get('transformer', {})
                transformer_url = transformer_health.get('url')
                if transformer_url:
                    return transformer_url
            
            # Default fallback
            return "http://localhost:16050"
        except Exception as e:
            handle_exception(e, context={
                'function': '_get_transformer_url',
                'error_type': 'TransformerURLResolution'
            })
            return "http://localhost:16050"

    def _generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """Generate embedding for text using transformer service.

        Args:
            text: Text to embed

        Returns:
            Numpy array of embedding vector, or None if failed
        """
        if not self.embed_enabled:
            return None

        try:
            endpoint = f"{self.transformer_url}/api/generate-embedding"
            response = requests.post(
                endpoint,
                json={'text': text},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                embedding = data.get('embedding')
                if embedding:
                    return np.array(embedding, dtype=np.float32)
            return None
        except Exception as e:
            handle_exception(e, context={
                'function': '_generate_embedding',
                'error_type': 'EmbeddingGeneration'
            })
            return None

    def is_enabled(self) -> bool:
        """Check if Spark context is enabled."""
        return self.enabled

    def _generate_label(self, file_path: str) -> str:
        """Generate a label from file path if none provided.

        Args:
            file_path: Path to the file

        Returns:
            Generated label (filename without extension)
        """
        return Path(file_path).stem

    def _chunk_content(self, content: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split content into overlapping chunks.

        Args:
            content: Text content to chunk
            chunk_size: Size of each chunk in characters
            overlap: Number of characters to overlap between chunks

        Returns:
            List of text chunks
        """
        if len(content) <= chunk_size:
            return [content]

        chunks = []
        start = 0
        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]
            chunks.append(chunk)
            start += (chunk_size - overlap)

        return chunks

    def load_file(self, file_path: str, label: Optional[str] = None) -> Tuple[bool, str]:
        """Load a file as Spark context with embedding generation.

        Args:
            file_path: Path to file to load
            label: Optional label for this context

        Returns:
            Tuple of (success, message)
        """
        if not self.enabled:
            return False, "Spark context is disabled in config"

        # Check if at max capacity
        if len(self.contexts) >= self.max_contexts:
            return False, f"Maximum Spark contexts reached ({self.max_contexts}). Clear some first."

        # Resolve path
        path = Path(file_path)
        if not path.exists():
            return False, f"File not found: {file_path}"

        if not path.is_file():
            return False, f"Path is not a file: {file_path}"

        # Check file size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            return False, f"File too large ({file_size_mb:.2f}MB > {self.max_file_size_mb}MB limit)"

        # Read file content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            return False, f"File is not UTF-8 text: {file_path}"
        except Exception as e:
            return False, f"Error reading file: {str(e)}"

        # Generate label if not provided
        if label is None:
            label = self._generate_label(str(path))

        # Check for duplicate label
        if self.get_context_by_label(label) is not None:
            return False, f"Spark context with label '{label}' already exists"

        # Create Spark context
        spark = SparkContext(
            label=label,
            file_path=str(path.absolute()),
            content=content,
            timestamp=datetime.now().isoformat()
        )

        # Generate embeddings if enabled
        if self.embed_enabled:
            try:
                # Check if chunking is needed
                if self.chunking_enabled and len(content) > self.chunk_size:
                    # Chunk the content
                    spark.chunks = self._chunk_content(content, self.chunk_size, self.chunk_overlap)
                    
                    # Generate embeddings for each chunk
                    for chunk in spark.chunks:
                        embedding = self._generate_embedding(chunk)
                        if embedding is not None:
                            spark.chunk_embeddings.append(embedding)
                else:
                    # Single chunk - generate full embedding
                    embedding = self._generate_embedding(content)
                    if embedding is not None:
                        spark.embedding = embedding
            except Exception as e:
                handle_exception(e, context={
                    'function': 'load_file',
                    'file_path': file_path,
                    'label': label,
                    'error_type': 'EmbeddingGeneration'
                })

        # Add to contexts
        self.contexts.append(spark)

        size_kb = spark.get_size_kb()
        
        # Build success message with embedding info
        if self.embed_enabled:
            if spark.is_chunked():
                msg = f"✓ Loaded Spark '{label}' ({size_kb:.1f}KB, {len(spark.chunks)} chunks, {len(spark.chunk_embeddings)} embeddings) from {file_path}"
            else:
                embedding_status = "embedding generated" if spark.embedding is not None else "no embedding"
                msg = f"✓ Loaded Spark '{label}' ({size_kb:.1f}KB, 1 chunk, {embedding_status}) from {file_path}"
        else:
            msg = f"✓ Loaded Spark '{label}' ({size_kb:.1f}KB) from {file_path}"
        
        return True, msg

    def load_directory(self, dir_path: str, label_prefix: Optional[str] = None) -> Tuple[bool, str]:
        """Load all files in a directory as Spark contexts.

        Args:
            dir_path: Path to directory
            label_prefix: Optional prefix for labels

        Returns:
            Tuple of (success, message)
        """
        if not self.enabled:
            return False, "Spark context is disabled in config"

        path = Path(dir_path)
        if not path.exists():
            return False, f"Directory not found: {dir_path}"

        if not path.is_dir():
            return False, f"Path is not a directory: {dir_path}"

        # Get all files in directory (non-recursive for now)
        files = [f for f in path.iterdir() if f.is_file()]

        if not files:
            return False, f"No files found in directory: {dir_path}"

        # Load each file
        loaded = []
        failed = []

        for file in files:
            # Generate label with prefix if provided
            if label_prefix:
                label = f"{label_prefix}_{file.stem}"
            else:
                label = f"{path.name}_{file.stem}"

            success, message = self.load_file(str(file), label)
            if success:
                loaded.append(str(file.name))
            else:
                failed.append((str(file.name), message))

        # Build result message
        messages = []
        if loaded:
            messages.append(f"✓ Loaded {len(loaded)} Spark(s) from {dir_path}")
            messages.append(f"  Files: {', '.join(loaded)}")

        if failed:
            messages.append(f"✗ Failed to load {len(failed)} file(s):")
            for filename, error in failed:
                messages.append(f"  - {filename}: {error}")

        if not loaded and failed:
            return False, "\n".join(messages)

        return True, "\n".join(messages)

    def clear_all(self) -> Tuple[bool, str]:
        """Clear all Spark contexts.

        Returns:
            Tuple of (success, message)
        """
        count = len(self.contexts)
        self.contexts = []
        return True, f"✓ Cleared {count} Spark context(s)"

    def clear_by_label(self, label: str) -> Tuple[bool, str]:
        """Clear a Spark context by label.

        Args:
            label: Label of the context to clear

        Returns:
            Tuple of (success, message)
        """
        for i, context in enumerate(self.contexts):
            if context.label == label:
                self.contexts.pop(i)
                return True, f"✓ Cleared Spark context '{label}'"

        return False, f"Spark context '{label}' not found"

    def get_context_by_label(self, label: str) -> Optional[SparkContext]:
        """Get a Spark context by label.

        Args:
            label: Label to search for

        Returns:
            SparkContext if found, None otherwise
        """
        for context in self.contexts:
            if context.label == label:
                return context
        return None

    def get_all_contexts(self) -> List[SparkContext]:
        """Get all Spark contexts.

        Returns:
            List of all Spark contexts
        """
        return self.contexts.copy()

    def get_context_string(self) -> str:
        """Get all Spark contexts formatted as a string for LLM context injection.

        Returns:
            Formatted string of all Spark contexts
        """
        if not self.contexts:
            return ""

        parts = ["=== Spark Context (In-Memory) ==="]

        for context in self.contexts:
            parts.append(f"\n--- Spark: {context.label} ---")
            parts.append(f"Source: {context.file_path}")
            parts.append(f"Loaded: {context.timestamp}")
            parts.append(f"\nContent:\n{context.content}")

        return "\n".join(parts)

    def get_summary(self) -> str:
        """Get a summary of all loaded Spark contexts.

        Returns:
            Formatted summary string
        """
        if not self.contexts:
            return "No Spark contexts loaded"

        lines = [f"Spark Contexts ({len(self.contexts)}/{self.max_contexts}):"]

        total_size = 0
        for context in self.contexts:
            size_kb = context.get_size_kb()
            total_size += size_kb
            lines.append(
                f"  • {context.label:20} - {size_kb:6.1f}KB - {context.file_path}"
            )

        lines.append(f"\nTotal: {total_size:.1f}KB")
        return "\n".join(lines)

    def get_count(self) -> int:
        """Get the number of loaded Spark contexts.

        Returns:
            Number of contexts
        """
        return len(self.contexts)

    def get_embeddings(self) -> List[np.ndarray]:
        """Return all embeddings (for advanced semantic operations).

        Returns:
            List of embedding arrays
        """
        if not self.embed_enabled:
            return []

        try:
            embeddings = []
            for ctx in self.contexts:
                # Add full document embedding if it exists
                if ctx.embedding is not None:
                    embeddings.append(ctx.embedding)
                # Add chunk embeddings if they exist
                elif ctx.chunk_embeddings:
                    embeddings.extend(ctx.chunk_embeddings)

            return embeddings
        except Exception as e:
            handle_exception(e, context={
                'function': 'get_embeddings',
                'error_type': 'EmbeddingRetrieval'
            })
            return []
