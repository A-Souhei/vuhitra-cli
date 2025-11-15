"""
Mock transformer service for testing without Docker containers.

This mock provides fake embeddings for testing the heuristics retriever
without needing the actual transformer service running.
"""
import numpy as np
from typing import List


class MockTransformerService:
    """Mock transformer service for testing."""
    
    EMBEDDING_DIM = 384  # Same as all-MiniLM-L6-v2
    
    @staticmethod
    def generate_embedding(text: str) -> List[float]:
        """
        Generate a deterministic fake embedding based on text hash.
        
        This ensures:
        - Same text always gets same embedding
        - Different texts get different embeddings
        - Embeddings are normalized (unit length)
        
        Args:
            text: Input text
            
        Returns:
            List of 384 floats representing the embedding
        """
        # Use hash for deterministic randomness
        np.random.seed(hash(text) % (2**32))
        
        # Generate random vector
        embedding = np.random.randn(MockTransformerService.EMBEDDING_DIM)
        
        # Normalize to unit length (as sentence-transformers does)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding.tolist()
    
    @staticmethod
    def cosine_similarity(emb1: List[float], emb2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            emb1: First embedding
            emb2: Second embedding
            
        Returns:
            Similarity score between 0 and 1
        """
        vec1 = np.array(emb1)
        vec2 = np.array(emb2)
        
        # Cosine similarity for normalized vectors
        similarity = np.dot(vec1, vec2)
        
        # Ensure in [0, 1] range
        return float((similarity + 1) / 2)


def mock_generate_embedding_request(text: str, timeout: int = 10) -> dict:
    """
    Mock the requests.post call to transformer service.
    
    Returns a fake response that matches the actual API.
    """
    return {
        'embedding': MockTransformerService.generate_embedding(text),
        'dimension': MockTransformerService.EMBEDDING_DIM,
        'model': 'all-MiniLM-L6-v2'
    }


class MockResponse:
    """Mock requests.Response object."""
    
    def __init__(self, json_data: dict, status_code: int = 200):
        self._json_data = json_data
        self.status_code = status_code
    
    def json(self):
        return self._json_data
