"""Pillar context management for coding mode persistent cross-session context.

This module provides pillar context storage that persists across sessions (only in coding mode).
Pillars behave exactly like eternals but are only enabled in coding mode.
Pillar context is:
- Loaded manually via CLI commands OR auto-loaded from pillars/ directory
- Persisted to disk (survives CLI restarts)
- Fully injected (not retrieved via similarity)
- Cross-session (permanent until explicitly deleted)
- File-based (can load documentation, specifications, etc.)
- Auto-loaded from pillars/ directory on CLI startup in coding mode
"""

import json
import requests
import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from src.utils.config_loader import ConfigLoader
from src.errors_handler import handle_exception
from src.utils.embedding_utils import EmbeddingCacheMixin, cosine_similarity


@dataclass
class PillarContext:
    """Represents a single pillar context loaded from a file."""

    label: str  # User-friendly label for this context
    file_path: str  # Original file path
    content: str  # Full text content
    timestamp: str  # ISO format timestamp when loaded
    description: str = ""  # Description/summary for semantic matching
    description_embedding: Optional[List[float]] = None  # Embedding of description (stored as list for JSON serialization)
    chunks: List[str] = field(default_factory=list)  # Chunks if content is large
    auto_loaded: bool = False  # Whether this was auto-loaded from pillars/ directory

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
    def from_dict(cls, data: Dict) -> 'PillarContext':
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
            'num_chunks': len(self.chunks),
            'auto_loaded': self.auto_loaded
        }


class PillarContextManager(EmbeddingCacheMixin):
    """Manages persistent pillar context (coding mode only)."""

    def __init__(self, enabled: bool = None, storage_dir: Optional[str] = None, pillars_dir: Optional[str] = None):
        """Initialize the pillar context manager.

        Args:
            enabled: Whether pillar context is enabled (overrides config)
            storage_dir: Custom storage directory (overrides config)
            pillars_dir: Custom pillars directory for auto-loading (default: ./pillars)
        """
        self.contexts: Dict[str, PillarContext] = {}  # label -> context
        self.config = ConfigLoader()
        self.auto_loaded_files: set = set()  # Track auto-loaded file paths to avoid re-embedding

        # Load settings from config with parameter overrides
        if enabled is None:
            pillar_config = self.config.get('pillar_context', default={})
            self.enabled = pillar_config.get('enabled', True)
        else:
            self.enabled = enabled

        # Get configuration (fallback to eternal_context config for limits)
        pillar_config = self.config.get('pillar_context', default={})
        eternal_config = self.config.get('eternal_context', default={})
        self.max_file_size_mb = pillar_config.get('max_file_size_mb', eternal_config.get('max_file_size_mb', 10))
        self.max_contexts = pillar_config.get('max_contexts', eternal_config.get('max_contexts', 20))
        chunking_config = pillar_config.get('chunking', eternal_config.get('chunking', {}))
        self.chunking_enabled = chunking_config.get('enabled', True)
        self.chunk_size = chunking_config.get('chunk_size', 1000)
        self.chunk_overlap = chunking_config.get('overlap', 200)

        # Semantic filtering configuration
        semantic_config = pillar_config.get('semantic_filtering', eternal_config.get('semantic_filtering', {}))
        self.semantic_filtering_enabled = semantic_config.get('enabled', True)
        self.similarity_threshold = semantic_config.get('similarity_threshold', 0.5)

        # Set storage directory
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            default_dir = pillar_config.get('storage_dir', '.vuhitra/pillar_contexts')
            self.storage_dir = Path(default_dir).expanduser().resolve()

        # Set pillars directory for auto-loading
        if pillars_dir:
            self.pillars_dir = Path(pillars_dir)
        else:
            default_pillars_dir = pillar_config.get('pillars_dir', 'pillars')
            self.pillars_dir = Path(default_pillars_dir).expanduser().resolve()

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

        # Load existing pillar contexts from storage
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

    def _save_to_storage(self, context: PillarContext) -> bool:
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
        """Load all pillar contexts from storage on startup.

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

                    context = PillarContext.from_dict(data)
                    self.contexts[context.label] = context
                    loaded_count += 1

                    # Track auto-loaded files
                    if context.auto_loaded:
                        self.auto_loaded_files.add(context.file_path)

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

    def auto_load_from_pillars_directory(self, verbose: bool = False) -> Tuple[int, List[str]]:
        """Auto-load files from the pillars/ directory.

        Files are only embedded if they haven't been loaded before.
        Already saved pillars are loaded but not re-embedded.

        Args:
            verbose: Whether to print debug information

        Returns:
            Tuple of (number_loaded, list_of_loaded_file_names)
        """
        loaded_count = 0
        loaded_files = []

        try:
            if not self.pillars_dir.exists():
                if verbose:
                    logging.info(f"Pillars directory does not exist: {self.pillars_dir}")
                return 0, []

            # Get all files from pillars directory (recursively)
            for file_path in self.pillars_dir.rglob('*'):
                if not file_path.is_file():
                    continue

                # Skip hidden files and common non-text files
                if file_path.name.startswith('.'):
                    continue

                # Check if file was already loaded
                file_path_str = str(file_path.resolve())
                if file_path_str in self.auto_loaded_files:
                    continue

                # Generate label from relative path
                try:
                    rel_path = file_path.relative_to(self.pillars_dir)
                    label = str(rel_path).replace('/', '_').replace('\\', '_')
                    if label.endswith(file_path.suffix):
                        label = label[:-len(file_path.suffix)]
                except ValueError:
                    label = file_path.stem

                # Load the file
                success, message = self.load_file(
                    str(file_path),
                    label=label,
                    description=None,
                    auto_loaded=True
                )

                if success:
                    loaded_count += 1
                    loaded_files.append(file_path.name)
                    self.auto_loaded_files.add(file_path_str)
                elif verbose:
                    logging.warning(f"Failed to auto-load pillar {file_path.name}: {message}")

            return loaded_count, loaded_files

        except Exception as e:
            handle_exception(e, context={
                'function': 'auto_load_from_pillars_directory',
                'pillars_dir': str(self.pillars_dir)
            })
            return loaded_count, loaded_files

    def load_file(self, file_path: str, label: Optional[str] = None, description: Optional[str] = None, auto_loaded: bool = False) -> Tuple[bool, str]:
        """Load a file into pillar context and persist it.

        Args:
            file_path: Path to file to load
            label: Optional user-friendly label (defaults to filename)
            description: Optional description/summary for semantic matching
            auto_loaded: Whether this file was auto-loaded from pillars/ directory

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.enabled:
            return False, "Pillar context is disabled"

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
                return False, f"Maximum number of pillar contexts reached ({self.max_contexts}). Clear some contexts first."

            # Generate label
            if label is None:
                label = path.stem  # Use filename without extension

            # Check if label already exists
            if label in self.contexts:
                return False, f"Pillar context with label '{label}' already exists. Use a different label or clear it first."

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

            # Create pillar context
            context = PillarContext(
                label=label,
                file_path=str(path),
                content=content,
                timestamp=datetime.now().isoformat(),
                description=description,
                description_embedding=description_embedding,
                auto_loaded=auto_loaded
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
                return False, f"Failed to persist pillar context to storage"

            # Build success message
            size_kb = context.get_size_kb()
            auto_msg = " (auto-loaded)" if auto_loaded else ""
            if context.is_chunked():
                msg = f"✓ Loaded pillar '{label}' ({size_kb:.1f} KB, {len(context.chunks)} chunks, persisted){auto_msg}"
            else:
                msg = f"✓ Loaded pillar '{label}' ({size_kb:.1f} KB, 1 chunk, persisted){auto_msg}"

            return True, msg

        except Exception as e:
            handle_exception(e, context={
                'function': 'load_file',
                'file_path': file_path,
                'label': label
            })
            return False, f"Error loading file: {str(e)}"

    def get_relevant_contexts(self, prompt: str, verbose: bool = False) -> List[Tuple[str, PillarContext, float]]:
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
                # Log warning when embedding generation fails
                logging.warning("Failed to generate embedding for prompt, returning all contexts unfiltered")
                # Fallback: return all contexts if embedding generation fails
                return [(label, ctx, 1.0) for label, ctx in self.contexts.items()]

            relevant_contexts = []

            for label, ctx in self.contexts.items():
                # Use stored description embedding or generate if not available
                if ctx.description_embedding is not None and len(ctx.description_embedding) > 0:
                    desc_embedding = np.array(ctx.description_embedding, dtype=np.float32)
                else:
                    # Fallback: generate embedding on-the-fly
                    desc_embedding = self._generate_embedding(ctx.description)
                    if desc_embedding is None:
                        continue

                # Calculate similarity using shared function
                similarity = cosine_similarity(prompt_embedding, desc_embedding)

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
            Formatted string containing relevant pillar contexts
        """
        if not self.enabled or not self.contexts:
            return ""

        try:
            # Get relevant contexts (filtered if prompt provided)
            if prompt and self.semantic_filtering_enabled:
                relevant = self.get_relevant_contexts(prompt, verbose=verbose)

                if not relevant:
                    return ""  # No relevant contexts found

                lines = ["=== Pillar Context (Coding Mode Reference Materials) ==="]

                for label, ctx, similarity in relevant:
                    lines.append(f"\n--- {label} (relevance: {similarity:.2%}) ---")
                    lines.append(ctx.content)
                    lines.append(f"--- End of {label} ---\n")

                lines.append("=== End of Pillar Context ===\n")

                return "\n".join(lines)
            else:
                # Return all contexts (no filtering)
                lines = ["=== Pillar Context (Coding Mode Reference Materials) ==="]

                for label, ctx in self.contexts.items():
                    lines.append(f"\n--- {label} ---")
                    lines.append(ctx.content)
                    lines.append(f"--- End of {label} ---\n")

                lines.append("=== End of Pillar Context ===\n")

                return "\n".join(lines)

        except Exception as e:
            handle_exception(e, context={
                'function': 'get_context_string',
                'num_contexts': len(self.contexts)
            })
            return ""

    def clear_all(self) -> int:
        """Clear all pillar contexts and delete from storage.

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
            self.auto_loaded_files.clear()

            return count

        except Exception as e:
            handle_exception(e, context={
                'function': 'clear_all'
            })
            return 0

    def remove_by_label(self, label: str) -> bool:
        """Remove specific pillar context by label and delete from storage.

        Args:
            label: Label of context to remove

        Returns:
            True if removed, False if not found
        """
        try:
            if label in self.contexts:
                ctx = self.contexts[label]

                # Delete from storage
                self._delete_from_storage(label)

                # Remove from auto-loaded tracking
                if ctx.file_path in self.auto_loaded_files:
                    self.auto_loaded_files.remove(ctx.file_path)

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
        """Get the number of loaded pillar contexts."""
        return len(self.contexts)

    def get_all_contexts(self) -> List[Dict]:
        """Get all pillar contexts as list of dictionaries.

        Returns:
            List of context dictionaries (without full content)
        """
        return [ctx.to_summary_dict() for ctx in self.contexts.values()]

    def get_context_by_label(self, label: str) -> Optional[PillarContext]:
        """Get pillar context by label.

        Args:
            label: Label to search for

        Returns:
            PillarContext if found, None otherwise
        """
        return self.contexts.get(label)

    def is_enabled(self) -> bool:
        """Check if pillar context is enabled."""
        return self.enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable pillar context.

        Args:
            enabled: Whether to enable pillar context
        """
        self.enabled = enabled
        if not enabled:
            self.clear_all()

    def get_total_size_kb(self) -> float:
        """Get total size of all pillar contexts in KB.

        Returns:
            Total size in KB
        """
        total_bytes = sum(ctx.get_size_bytes() for ctx in self.contexts.values())
        return total_bytes / 1024

    def get_summary(self) -> str:
        """Get a summary of loaded pillar contexts.

        Returns:
            Formatted summary string
        """
        if not self.contexts:
            return "No pillar contexts loaded"

        lines = ["Loaded pillar contexts:"]

        for i, (label, ctx) in enumerate(self.contexts.items(), 1):
            size_kb = ctx.get_size_kb()
            if ctx.is_chunked():
                chunks_info = f"{len(ctx.chunks)} chunks"
            else:
                chunks_info = "1 chunk"

            auto_msg = " [auto-loaded]" if ctx.auto_loaded else ""
            lines.append(f"  {i}. {label} ({size_kb:.1f} KB, {chunks_info}){auto_msg} - {ctx.file_path}")

        total_kb = self.get_total_size_kb()
        lines.append(f"\nTotal size: {total_kb:.1f} KB")
        lines.append(f"Contexts: {len(self.contexts)}/{self.max_contexts}")
        lines.append(f"Storage: {self.storage_dir}")
        lines.append(f"Auto-load directory: {self.pillars_dir}")

        return "\n".join(lines)

    def reload_from_file(self, label: str) -> Tuple[bool, str]:
        """Reload a pillar context from its original file.

        Args:
            label: Label of context to reload

        Returns:
            Tuple of (success: bool, message: str)
        """
        if label not in self.contexts:
            return False, f"Pillar context '{label}' not found"

        ctx = self.contexts[label]
        original_path = ctx.file_path
        was_auto_loaded = ctx.auto_loaded

        # Remove and reload
        self.remove_by_label(label)
        return self.load_file(original_path, label, auto_loaded=was_auto_loaded)
