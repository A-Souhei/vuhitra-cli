"""Conversation history management with RAG-based retrieval.

This module provides conversation history storage with embedding-based
similarity search for retrieving relevant past conversations.
"""

import requests
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
from src.utils.config_loader import ConfigLoader
from src.errors_handler import handle_exception

# Import heuristics config loader from sandbox service
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "sandbox" / "src"))
from heuristics_config_loader import HeuristicsConfigLoader


class ConversationTurn:
    """Represents a single conversation turn (user prompt + assistant response)."""

    def __init__(self, prompt: str, response: str, timestamp: Optional[str] = None):
        """Initialize a conversation turn.

        Args:
            prompt: User's prompt
            response: Assistant's response
            timestamp: ISO format timestamp (auto-generated if not provided)
        """
        self.prompt = prompt
        self.response = response
        self.timestamp = timestamp or datetime.now().isoformat()
        self.embedding: Optional[np.ndarray] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            'prompt': self.prompt,
            'response': self.response,
            'timestamp': self.timestamp
        }

    def get_combined_text(self) -> str:
        """Get combined text for embedding (prompt + response)."""
        return f"User: {self.prompt}\nAssistant: {self.response}"


class ConversationHistoryManager:
    """Manages conversation history with embedding-based retrieval."""

    def __init__(self, max_history_size: int = None, enabled: bool = None):
        """Initialize the conversation history manager.

        Args:
            max_history_size: Maximum number of conversation turns to keep (overrides config)
            enabled: Whether conversation history is enabled (overrides config)
        """
        self.history: List[ConversationTurn] = []
        self.config = ConfigLoader()
        self.heuristics_config = HeuristicsConfigLoader()

        # Load settings from config, with parameter overrides
        if enabled is None:
            self.enabled = self.heuristics_config.get_conversation_history_enabled()
        else:
            self.enabled = enabled

        if max_history_size is None:
            self.max_history_size = self.heuristics_config.get_conversation_history_max_size()
        else:
            self.max_history_size = max_history_size

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
                timeout=10
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

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (-1 to 1, where 1 is identical, 0 is orthogonal, -1 is opposite)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    def add_turn(self, prompt: str, response: str) -> bool:
        """Add a conversation turn and generate its embedding.

        Args:
            prompt: User's prompt
            response: Assistant's response

        Returns:
            True if successfully added, False otherwise
        """
        if not self.enabled:
            return False

        try:
            turn = ConversationTurn(prompt, response)

            # Generate embedding for the conversation turn
            combined_text = turn.get_combined_text()
            embedding = self._generate_embedding(combined_text)

            if embedding is not None:
                turn.embedding = embedding
                self.history.append(turn)

                # Enforce max history size (FIFO)
                if len(self.history) > self.max_history_size:
                    self.history.pop(0)

                return True

            return False

        except Exception as e:
            handle_exception(e, context={
                'function': 'add_turn',
                'prompt_length': len(prompt),
                'response_length': len(response)
            })
            return False

    def retrieve_relevant_history(
        self,
        query: str,
        top_k: int = 3,
        min_similarity: float = 0.5
    ) -> List[Tuple[ConversationTurn, float]]:
        """Retrieve relevant conversation history for a query using similarity search.

        Args:
            query: Current user query
            top_k: Number of most relevant turns to return
            min_similarity: Minimum similarity threshold

        Returns:
            List of (ConversationTurn, similarity_score) tuples, sorted by relevance
        """
        if not self.enabled or len(self.history) == 0:
            return []

        try:
            # Generate embedding for query
            query_embedding = self._generate_embedding(query)

            if query_embedding is None:
                return []

            # Calculate similarity scores for all history turns
            scored_turns: List[Tuple[ConversationTurn, float]] = []

            for turn in self.history:
                if turn.embedding is not None:
                    similarity = self._cosine_similarity(query_embedding, turn.embedding)

                    if similarity >= min_similarity:
                        scored_turns.append((turn, similarity))

            # Sort by similarity (highest first) and return top_k
            scored_turns.sort(key=lambda x: x[1], reverse=True)
            return scored_turns[:top_k]

        except Exception as e:
            handle_exception(e, context={
                'function': 'retrieve_relevant_history',
                'query_length': len(query),
                'history_size': len(self.history)
            })
            return []

    def format_history_for_context(
        self,
        relevant_turns: List[Tuple[ConversationTurn, float]]
    ) -> str:
        """Format relevant conversation history for LLM context.

        Args:
            relevant_turns: List of (ConversationTurn, similarity_score) tuples

        Returns:
            Formatted string for context injection
        """
        if not relevant_turns:
            return ""

        lines = ["=== Relevant Conversation History ==="]

        for turn, similarity in relevant_turns:
            lines.append(f"\n[Relevance: {similarity:.2%}]")
            lines.append(f"User: {turn.prompt}")
            lines.append(f"Assistant: {turn.response}")

        lines.append("\n=== End of Conversation History ===\n")

        return "\n".join(lines)

    def clear_history(self):
        """Clear all conversation history."""
        self.history.clear()

    def get_history_count(self) -> int:
        """Get the number of conversation turns in history."""
        return len(self.history)

    def get_all_history(self) -> List[Dict]:
        """Get all conversation history as list of dictionaries.

        Returns:
            List of conversation turn dictionaries
        """
        return [turn.to_dict() for turn in self.history]

    def is_enabled(self) -> bool:
        """Check if conversation history is enabled."""
        return self.enabled

    def set_enabled(self, enabled: bool):
        """Enable or disable conversation history.

        Args:
            enabled: Whether to enable conversation history
        """
        self.enabled = enabled
        if not enabled:
            self.clear_history()
