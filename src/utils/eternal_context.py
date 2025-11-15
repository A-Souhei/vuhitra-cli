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

    def load_file(self, file_path: str, label: Optional[str] = None) -> Tuple[bool, str]:
        """Load a file into eternal context and persist it.

        Args:
            file_path: Path to file to load
            label: Optional user-friendly label (defaults to filename)

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

            # Create eternal context
            context = EternalContext(
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

    def get_context_string(self) -> str:
        """Return formatted context string for prompt injection.

        Returns:
            Formatted string containing all eternal contexts
        """
        if not self.enabled or not self.contexts:
            return ""

        try:
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
