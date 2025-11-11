"""
HeuristicsRetriever - Complex multi-stage heuristics lookup system.

This module implements a sophisticated retrieval system that combines:
1. Elasticsearch keyword filtering (Stage 1)
2. Levenshtein distance scoring (Stage 2)
3. spaCy semantic similarity (Stage 3)
4. Weighted scoring algorithm

The goal is to find the most relevant historical interaction given a user prompt.
"""
import logging
from typing import Dict, List, Optional, Tuple
from elasticsearch import Elasticsearch
from rapidfuzz import fuzz
import spacy
import numpy as np

# Support both relative imports (for local tests) and absolute imports (for Docker)
try:
    from src.errors_handler.error_handler import get_error_handler
except ImportError:
    # For tests running from the test directory
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from src.errors_handler.error_handler import get_error_handler

logger = logging.getLogger(__name__)
error_handler = get_error_handler()


class HeuristicsRetriever:
    """
    Multi-stage heuristics retrieval system.

    Retrieves the best matching historical interaction from Elasticsearch
    using a combination of keyword matching, edit distance, and semantic similarity.
    """

    # Scoring weights (must sum to 1.0)
    SEMANTIC_WEIGHT = 0.50
    LEVENSHTEIN_WEIGHT = 0.25
    KEYWORD_WEIGHT = 0.15
    RATING_WEIGHT = 0.10

    # Filtering thresholds
    MIN_RATING = 3  # Only consider ratings >= 3
    MAX_STAGE1_CANDIDATES = 100  # Limit ES results for performance
    MAX_STAGE2_CANDIDATES = 10  # Top candidates for semantic analysis

    def __init__(self, es_client: Elasticsearch, index_name: str = "llm_feedback"):
        """
        Initialize the retriever.

        Args:
            es_client: Elasticsearch client instance
            index_name: Name of the index to query
        """
        self.es = es_client
        self.index_name = index_name
        self.nlp = None
        self._load_spacy_model()

    def _load_spacy_model(self):
        """Load spaCy language model with word vectors."""
        try:
            # Use large model which includes word vectors
            self.nlp = spacy.load("en_core_web_lg")
            logger.info("Loaded spaCy model: en_core_web_lg")
        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "load_spacy_model",
                    "model": "en_core_web_lg"
                }
            )
            self.nlp = None

    def retrieve_best_match(
        self,
        prompt: str,
        min_rating: int = None,
        max_results: int = 1
    ) -> Optional[Dict]:
        """
        Retrieve the best matching heuristic for the given prompt.

        Args:
            prompt: User's input prompt
            min_rating: Minimum rating threshold (default: MIN_RATING)
            max_results: Number of top results to return (default: 1)

        Returns:
            Dictionary containing:
                - matched_heuristic: The best matching document
                - confidence_score: Overall confidence (0-1)
                - scoring_breakdown: Individual scores for each method
            Returns None if no suitable match found
        """
        if not self.es or not self.nlp:
            logger.warning("Retriever not properly initialized")
            return None

        if min_rating is None:
            min_rating = self.MIN_RATING

        try:
            # Stage 1: Keyword filtering with Elasticsearch
            candidates = self._stage1_keyword_filter(prompt, min_rating)

            if not candidates:
                logger.info("No candidates found in Stage 1 (keyword filter)")
                return None

            logger.info(f"Stage 1: Found {len(candidates)} candidates")

            # Stage 2: Levenshtein distance scoring
            scored_candidates = self._stage2_levenshtein_scoring(prompt, candidates)

            # Take top N candidates for semantic analysis
            top_candidates = sorted(
                scored_candidates,
                key=lambda x: x['levenshtein_score'],
                reverse=True
            )[:self.MAX_STAGE2_CANDIDATES]

            logger.info(f"Stage 2: Selected {len(top_candidates)} candidates for semantic analysis")

            # Stage 3: Semantic similarity with spaCy
            final_scores = self._stage3_semantic_similarity(prompt, top_candidates)

            if not final_scores:
                logger.info("No matches passed semantic similarity threshold")
                return None

            # Sort by final weighted score
            final_scores.sort(key=lambda x: x['final_score'], reverse=True)

            # Return top result(s)
            best_match = final_scores[0]

            result = {
                'matched_heuristic': best_match['document'],
                'confidence_score': best_match['final_score'],
                'scoring_breakdown': {
                    'semantic_similarity': best_match['semantic_score'],
                    'levenshtein_similarity': best_match['levenshtein_score'],
                    'keyword_overlap': best_match['keyword_score'],
                    'rating_normalized': best_match['rating_score']
                }
            }

            logger.info(
                f"Best match found with confidence {result['confidence_score']:.3f} "
                f"(rating: {best_match['document']['rating']})"
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

    def _stage1_keyword_filter(self, prompt: str, min_rating: int) -> List[Dict]:
        """
        Stage 1: Filter candidates using Elasticsearch keyword matching.

        Uses ES's built-in text matching with keyword boosting and rating filter.

        Args:
            prompt: User's input prompt
            min_rating: Minimum rating threshold

        Returns:
            List of candidate documents
        """
        try:
            # Extract keywords from prompt using spaCy
            doc = self.nlp(prompt)
            keywords = [
                token.lemma_.lower()
                for token in doc
                if not token.is_stop and not token.is_punct and len(token.text) >= 3
                and token.pos_ in ['NOUN', 'PROPN', 'VERB']
            ]

            # Build Elasticsearch query
            # We use a bool query with:
            # - must: rating filter
            # - should: text match on prompt + keyword terms boost
            query = {
                "bool": {
                    "must": [
                        {"range": {"rating": {"gte": min_rating}}}
                    ],
                    "should": [
                        {
                            "match": {
                                "prompt": {
                                    "query": prompt,
                                    "boost": 2.0
                                }
                            }
                        }
                    ]
                }
            }

            # Add keyword boosts if we extracted any
            if keywords:
                for keyword in keywords[:10]:  # Limit to top 10 keywords
                    query["bool"]["should"].append({
                        "term": {
                            "prompt_keywords": {
                                "value": keyword,
                                "boost": 1.5
                            }
                        }
                    })

            # Execute search
            response = self.es.search(
                index=self.index_name,
                query=query,
                size=self.MAX_STAGE1_CANDIDATES,
                _source=True
            )

            # Extract documents
            candidates = []
            for hit in response['hits']['hits']:
                doc = hit['_source']
                doc['_id'] = hit['_id']
                doc['_score'] = hit['_score']
                candidates.append(doc)

            return candidates

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "stage1_keyword_filter",
                    "index": self.index_name
                }
            )
            return []

    def _stage2_levenshtein_scoring(
        self,
        prompt: str,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        Stage 2: Score candidates using Levenshtein distance.

        Calculates normalized edit distance between prompts using rapidfuzz.

        Args:
            prompt: User's input prompt
            candidates: List of candidate documents

        Returns:
            Candidates with added 'levenshtein_score' field (0-1)
        """
        prompt_lower = prompt.lower().strip()

        for candidate in candidates:
            candidate_prompt = candidate.get('prompt', '').lower().strip()

            if not candidate_prompt:
                candidate['levenshtein_score'] = 0.0
                continue

            # Calculate Levenshtein similarity ratio using rapidfuzz (0-100)
            # rapidfuzz.fuzz.ratio returns a value from 0-100
            similarity_percent = fuzz.ratio(prompt_lower, candidate_prompt)

            # Convert to 0-1 scale
            similarity = similarity_percent / 100.0

            candidate['levenshtein_score'] = max(0.0, min(1.0, similarity))

        return candidates

    def _stage3_semantic_similarity(
        self,
        prompt: str,
        candidates: List[Dict]
    ) -> List[Dict]:
        """
        Stage 3: Calculate semantic similarity using spaCy word vectors.

        Uses cosine similarity between prompt and candidate prompt vectors.

        Args:
            prompt: User's input prompt
            candidates: List of top candidates

        Returns:
            List of candidates with final weighted scores
        """
        try:
            # Get prompt vector
            prompt_doc = self.nlp(prompt)

            if not prompt_doc.has_vector:
                logger.warning("Prompt has no vector representation")
                return []

            results = []

            for candidate in candidates:
                candidate_prompt = candidate.get('prompt', '')
                candidate_doc = self.nlp(candidate_prompt)

                if not candidate_doc.has_vector:
                    continue

                # Calculate cosine similarity between vectors
                semantic_score = prompt_doc.similarity(candidate_doc)

                # Ensure score is in [0, 1] range (similarity can be negative)
                semantic_score = max(0.0, min(1.0, semantic_score))

                # Get other scores
                levenshtein_score = candidate.get('levenshtein_score', 0.0)

                # Calculate keyword overlap score
                keyword_score = self._calculate_keyword_overlap(
                    candidate.get('prompt_keywords', []),
                    prompt_doc
                )

                # Normalize rating (0-5 scale to 0-1 scale)
                rating = candidate.get('rating', 0)
                rating_score = rating / 5.0

                # Calculate weighted final score
                final_score = (
                    self.SEMANTIC_WEIGHT * semantic_score +
                    self.LEVENSHTEIN_WEIGHT * levenshtein_score +
                    self.KEYWORD_WEIGHT * keyword_score +
                    self.RATING_WEIGHT * rating_score
                )

                results.append({
                    'document': candidate,
                    'final_score': final_score,
                    'semantic_score': semantic_score,
                    'levenshtein_score': levenshtein_score,
                    'keyword_score': keyword_score,
                    'rating_score': rating_score
                })

            return results

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "stage3_semantic_similarity",
                    "num_candidates": len(candidates)
                }
            )
            return []

    def _calculate_keyword_overlap(
        self,
        candidate_keywords: List[str],
        prompt_doc
    ) -> float:
        """
        Calculate weighted keyword overlap score between candidate and prompt.

        Subject nouns (direct objects, subjects of sentences) get 5x weight.
        Proper nouns (PROPN) get 4x weight.
        Common nouns (NOUN) get 2x weight.
        Verbs get 1x weight.

        Args:
            candidate_keywords: List of keywords from candidate
            prompt_doc: spaCy Doc object of the prompt

        Returns:
            Weighted overlap score (0-1)
        """
        if not candidate_keywords:
            return 0.0

        # Identify subject tokens (nsubj, dobj, pobj) - these are the main topics
        subject_tokens = set()
        for token in prompt_doc:
            # Subject, direct object, or prepositional object
            if token.dep_ in ['nsubj', 'nsubjpass', 'dobj', 'pobj', 'attr']:
                subject_tokens.add(token.lemma_.lower())

        # Extract keywords from prompt with POS tags for weighting
        prompt_keyword_weights = {}
        for token in prompt_doc:
            if not token.is_stop and not token.is_punct and len(token.text) >= 3:
                lemma = token.lemma_.lower()

                # Subject nouns get highest weight (5x)
                if lemma in subject_tokens:
                    prompt_keyword_weights[lemma] = 5.0
                # Proper nouns get 4x weight
                elif token.pos_ == 'PROPN':
                    prompt_keyword_weights[lemma] = 4.0
                # Common nouns get 2x weight
                elif token.pos_ == 'NOUN':
                    prompt_keyword_weights[lemma] = 2.0
                # Verbs get 1x weight
                elif token.pos_ == 'VERB':
                    prompt_keyword_weights[lemma] = 1.0

        if not prompt_keyword_weights:
            return 0.0

        # Calculate weighted overlap
        candidate_set = set(candidate_keywords)
        prompt_set = set(prompt_keyword_weights.keys())

        # Weighted intersection: sum weights of matching keywords
        intersection = sum(
            prompt_keyword_weights[kw]
            for kw in candidate_set & prompt_set
        )

        # Total possible weight: sum all prompt keyword weights
        total_weight = sum(prompt_keyword_weights.values())

        if total_weight == 0:
            return 0.0

        return min(1.0, intersection / total_weight)

    def health_check(self) -> Dict[str, bool]:
        """
        Check health of retriever components.

        Returns:
            Dictionary with component health status
        """
        return {
            'elasticsearch_connected': self.es is not None and self.es.ping(),
            'spacy_loaded': self.nlp is not None,
            'index_exists': bool(self.es.indices.exists(index=self.index_name)) if self.es else False
        }
