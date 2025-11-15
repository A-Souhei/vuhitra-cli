"""
HeuristicsRetriever - Embedding-based heuristics lookup system.

This module implements a sophisticated retrieval system using:
1. Sentence-transformer embeddings for semantic similarity
2. Elasticsearch kNN (k-nearest neighbors) search
3. Rating-based filtering
4. Configurable weights and thresholds

Replaces the old spaCy + Levenshtein approach with pure embedding-based similarity.
"""
import logging
from typing import Dict, List, Optional, Any
from elasticsearch import Elasticsearch
import requests

# Support both relative imports (for Docker) and absolute imports (for tests)
try:
    from heuristics_config_loader import HeuristicsConfigLoader
except ImportError:
    # For tests running from project root
    from services.sandbox.src.heuristics_config_loader import HeuristicsConfigLoader

try:
    from src.errors_handler.error_handler import get_error_handler
except ImportError:
    # For tests running from project root
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from src.errors_handler.error_handler import get_error_handler

logger = logging.getLogger(__name__)
error_handler = get_error_handler()


class HeuristicsRetriever:
    """
    Embedding-based heuristics retrieval system.

    Retrieves the best matching historical interaction from Elasticsearch
    using sentence-transformer embeddings and cosine similarity.
    """

    def __init__(
        self,
        es_client: Elasticsearch,
        index_name: str = "llm_feedback",
        es_client_wrapper=None,
        transformer_host: str = "transformer",
        transformer_port: int = 5050
    ):
        """
        Initialize the retriever.

        Args:
            es_client: Elasticsearch client instance
            index_name: Name of the index to query
            es_client_wrapper: Optional ElasticSearchClient wrapper for advanced operations
            transformer_host: Transformer service host
            transformer_port: Transformer service port
        """
        self.es = es_client
        self.index_name = index_name
        self.es_client_wrapper = es_client_wrapper
        self.transformer_host = transformer_host
        self.transformer_port = transformer_port
        self.transformer_url = f"http://{transformer_host}:{transformer_port}"

        # Load configuration
        self.config = HeuristicsConfigLoader()

        # Load weights and thresholds from config
        self.SEMANTIC_WEIGHT = self.config.get_semantic_weight()
        self.RATING_WEIGHT = self.config.get_rating_weight()

        self.MIN_RATING = self.config.get_min_rating()
        self.MAX_RATING_NEGATIVE = self.config.get_max_rating_negative()
        self.MAX_CANDIDATES = self.config.get_max_stage1_candidates()
        
        # Minimum similarity threshold (0-1)
        self.MIN_SIMILARITY = 0.5  # Can be made configurable

        # Chain configuration
        self.CHAINING_ENABLED = self.config.get_chaining_enabled()
        self.INCLUDE_CHAIN_IN_CONTEXT = self.config.get_include_chain_in_context()
        self.MIN_PARENT_RATING = self.config.get_min_parent_rating()

    def health_check(self) -> Dict[str, Any]:
        """
        Check health of retriever components.
        
        Returns:
            Dict with health status of ES and transformer service
        """
        health = {
            'elasticsearch': False,
            'transformer_service': False,
            'overall': False
        }
        
        # Check Elasticsearch
        if self.es:
            try:
                health['elasticsearch'] = self.es.ping()
            except:
                pass
        
        # Check transformer service
        try:
            response = requests.get(
                f"{self.transformer_url}/health",
                timeout=2
            )
            health['transformer_service'] = response.status_code == 200
        except:
            pass
        
        health['overall'] = health['elasticsearch'] and health['transformer_service']
        return health

    def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using transformer service.

        Args:
            text: Text to generate embedding for

        Returns:
            List of floats representing the embedding, or None if failed
        """
        try:
            response = requests.post(
                f"{self.transformer_url}/api/generate-embedding",
                json={"text": text},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('embedding')
            else:
                logger.warning(f"Failed to generate embedding: {response.status_code}")
                return None

        except Exception as e:
            logger.warning(f"Error calling transformer service for embedding: {e}")
            return None

    def retrieve_best_match(
        self,
        prompt: str,
        min_rating: int = None,
        negative_weight_boost: float = 0.0
    ) -> Optional[Dict]:
        """
        Retrieve the best matching heuristic for the given prompt using embeddings.

        Args:
            prompt: User's input prompt
            min_rating: Minimum rating threshold (default: MIN_RATING)
            negative_weight_boost: Boost factor for negative heuristics influence (0.0-1.0)
                                  Higher values reduce positive heuristic confidence

        Returns:
            Dictionary containing:
                - matched_heuristic: The best matching document
                - confidence_score: Overall confidence (0-1, adjusted by boost)
                - scoring_breakdown: Individual scores for each method
            Returns None if no suitable match found
        """
        if not self.es:
            logger.warning("Retriever not properly initialized")
            return None

        if min_rating is None:
            min_rating = self.MIN_RATING

        try:
            # Generate embedding for the prompt
            prompt_embedding = self._generate_embedding(prompt)
            if not prompt_embedding:
                logger.error("Failed to generate embedding for prompt")
                return None

            # Search using kNN with rating filter
            query = {
                "knn": {
                    "field": "prompt_embedding",
                    "query_vector": prompt_embedding,
                    "k": self.MAX_CANDIDATES,
                    "num_candidates": self.MAX_CANDIDATES * 2,
                    "filter": {
                        "range": {
                            "rating": {"gte": min_rating}
                        }
                    }
                }
            }

            response = self.es.search(
                index=self.index_name,
                knn=query["knn"],
                size=self.MAX_CANDIDATES,
                _source=True
            )

            hits = response['hits']['hits']
            
            if not hits:
                logger.info("No candidates found with embedding search")
                return None

            logger.info(f"Found {len(hits)} candidates with embedding search")

            # Process results and calculate final scores
            scored_candidates = []
            for hit in hits:
                doc = hit['_source']
                doc['_id'] = hit['_id']
                
                # The _score from kNN search is the similarity score (cosine similarity, 0-1)
                similarity_score = hit['_score']
                
                # Skip if below minimum similarity threshold
                if similarity_score < self.MIN_SIMILARITY:
                    continue
                
                # Use ONLY embedding similarity as the confidence score
                # Rating is kept in the document for filtering but doesn't affect scoring
                scored_candidates.append({
                    'document': doc,
                    'similarity_score': similarity_score,
                    'final_score': similarity_score  # Pure embedding similarity
                })

            if not scored_candidates:
                logger.info("No matches passed similarity threshold")
                return None

            # Sort by similarity score (already the final score)
            scored_candidates.sort(key=lambda x: x['final_score'], reverse=True)
            best_match = scored_candidates[0]

            # Apply negative weight boost if specified
            adjusted_confidence = best_match['final_score'] * (1.0 - negative_weight_boost)

            result = {
                'matched_heuristic': best_match['document'],
                'confidence_score': adjusted_confidence,
                'scoring_breakdown': {
                    'embedding_similarity': best_match['similarity_score'],
                    'negative_weight_boost_applied': negative_weight_boost
                },
                'chain': []
            }

            # Retrieve chain if enabled
            if self.CHAINING_ENABLED and self.INCLUDE_CHAIN_IN_CONTEXT and self.es_client_wrapper:
                doc_id = best_match['document'].get('_id')
                if doc_id:
                    chain = self.es_client_wrapper.get_chain(doc_id)
                    # Filter chain by minimum parent rating if configured
                    if self.MIN_PARENT_RATING > 0:
                        chain = [
                            c for c in chain
                            if c.get('rating', 0) >= self.MIN_PARENT_RATING
                        ]
                    result['chain'] = chain
                    logger.info(f"Retrieved chain with {len(chain)} parent heuristics")

            logger.info(
                f"Best match found with confidence {result['confidence_score']:.3f} "
                f"(rating: {best_match['document']['rating']}, similarity: {best_match['similarity_score']:.3f})"
            )

            return result

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "retrieve_best_match",
                    "prompt_length": len(prompt),
                    "min_rating": min_rating
                }
            )
            return None

    def retrieve_negative_heuristics(
        self,
        prompt: str,
        max_rating: int = None,
        negative_weight_boost: float = 0.0,
        verbose: bool = False
    ) -> Optional[Dict]:
        """
        Retrieve the best matching negative heuristic (anti-pattern) using embeddings.

        Args:
            prompt: User's input prompt
            max_rating: Maximum rating threshold (default: MAX_RATING_NEGATIVE)
            negative_weight_boost: Boost factor for negative heuristics influence (0.0-1.0)
                                  Higher values increase negative heuristic confidence

        Returns:
            Dictionary containing matched negative heuristic and confidence score
        """
        if not self.es:
            logger.warning("Retriever not properly initialized")
            return None

        if max_rating is None:
            max_rating = self.MAX_RATING_NEGATIVE

        try:
            # Generate embedding for the prompt
            prompt_embedding = self._generate_embedding(prompt)
            if not prompt_embedding:
                logger.error("Failed to generate embedding for prompt")
                return None

            # Search using kNN with rating filter (low ratings)
            query = {
                "knn": {
                    "field": "prompt_embedding",
                    "query_vector": prompt_embedding,
                    "k": self.MAX_CANDIDATES,
                    "num_candidates": self.MAX_CANDIDATES * 2,
                    "filter": {
                        "range": {
                            "rating": {"lte": max_rating}
                        }
                    }
                }
            }

            response = self.es.search(
                index=self.index_name,
                knn=query["knn"],
                size=self.MAX_CANDIDATES,
                _source=True
            )

            hits = response['hits']['hits']

            if not hits:
                logger.info("No negative heuristic candidates found with embedding search")
                return None

            logger.info(f"Found {len(hits)} negative candidates with embedding search")

            # Process results
            scored_candidates = []
            for hit in hits:
                doc = hit['_source']
                doc['_id'] = hit['_id']
                
                similarity_score = hit['_score']
                
                if similarity_score < self.MIN_SIMILARITY:
                    continue
                
                rating = doc.get('rating', 2)
                # Use ONLY embedding similarity (no rating weighting)
                # For negative heuristics, rating is kept for filtering only
                
                scored_candidates.append({
                    'document': doc,
                    'similarity_score': similarity_score,
                    'final_score': similarity_score  # Pure embedding similarity
                })

            if not scored_candidates:
                logger.info("No negative matches passed similarity threshold")
                return None

            scored_candidates.sort(key=lambda x: x['final_score'], reverse=True)
            best_match = scored_candidates[0]

            # Apply negative weight boost (increase confidence)
            adjusted_confidence = min(1.0, best_match['final_score'] * (1.0 + negative_weight_boost))

            result = {
                'matched_heuristic': best_match['document'],
                'confidence_score': adjusted_confidence,
                'scoring_breakdown': {
                    'embedding_similarity': best_match['similarity_score'],
                    'negative_weight_boost_applied': negative_weight_boost
                },
                'is_negative': True,
                'chain': []
            }

            # Retrieve chain for negative heuristics if enabled
            if self.CHAINING_ENABLED and self.INCLUDE_CHAIN_IN_CONTEXT and self.es_client_wrapper:
                doc_id = best_match['document'].get('_id')
                if doc_id:
                    chain = self.es_client_wrapper.get_chain(doc_id)
                    result['chain'] = chain
                    if verbose:
                        logger.info(f"Retrieved negative chain with {len(chain)} parent anti-patterns")

            logger.info(
                f"Best negative match found with confidence {result['confidence_score']:.3f} "
                f"(rating: {best_match['document']['rating']}, similarity: {best_match['similarity_score']:.3f})"
            )

            return result

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "retrieve_negative_heuristics",
                    "prompt_length": len(prompt),
                    "max_rating": max_rating
                }
            )
            return None
