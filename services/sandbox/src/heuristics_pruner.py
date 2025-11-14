"""
Heuristics Pruner - Automatic cleanup of unretrievable heuristics.

This module implements an intelligent pruning system that removes heuristics
that will never be retrieved again due to the existence of better-rated similar heuristics.

The pruning logic:
1. For each heuristic in the database, simulate its retrieval
2. Check if it would appear in the top results given current retrieval logic
3. If similar heuristics with higher ratings exist, mark for deletion
4. Batch delete marked heuristics to optimize storage

This keeps the database lean and improves retrieval performance.
"""
import logging
from typing import Dict, List, Set
from elasticsearch import Elasticsearch

# Support both relative imports (for Docker) and absolute imports (for tests)
try:
    from heuristics_config_loader import HeuristicsConfigLoader
    from heuristics_retriever import HeuristicsRetriever
except ImportError:
    from services.sandbox.src.heuristics_config_loader import HeuristicsConfigLoader
    from services.sandbox.src.heuristics_retriever import HeuristicsRetriever

try:
    from src.errors_handler.error_handler import get_error_handler
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from src.errors_handler.error_handler import get_error_handler

logger = logging.getLogger(__name__)
error_handler = get_error_handler()


class HeuristicsPruner:
    """
    Auto-pruning system for heuristics database.

    Identifies and removes heuristics that are no longer retrievable due to
    the existence of higher-rated similar heuristics.
    """

    def __init__(self, es_client: Elasticsearch, index_name: str,
                 retriever: HeuristicsRetriever, config_loader: HeuristicsConfigLoader = None):
        """
        Initialize the pruner.

        Args:
            es_client: Elasticsearch client instance
            index_name: Name of the index containing heuristics
            retriever: HeuristicsRetriever instance for simulation
            config_loader: Optional config loader (creates new if None)
        """
        self.es = es_client
        self.index_name = index_name
        self.retriever = retriever
        self.config = config_loader or HeuristicsConfigLoader()

        # Load pruning configuration
        self.ENABLED = self.config.get_auto_pruning_enabled()
        self.SIMILARITY_THRESHOLD = self.config.get_pruning_similarity_threshold()
        self.MIN_RATING_DIFFERENCE = self.config.get_pruning_min_rating_difference()
        self.BATCH_SIZE = self.config.get_pruning_batch_size()

    def prune_unretrievable_heuristics(self, verbose: bool = False) -> Dict:
        """
        Main pruning method. Identifies and removes unretrievable heuristics.

        A heuristic is considered unretrievable if:
        1. It wouldn't appear in retrieval results for its own prompt
        2. Similar heuristics with higher ratings exist
        3. The rating difference exceeds MIN_RATING_DIFFERENCE

        Args:
            verbose: Enable detailed logging

        Returns:
            Dict with pruning statistics:
                - enabled: Whether pruning is enabled
                - total_checked: Total heuristics examined
                - pruned_count: Number of heuristics removed
                - errors: Number of errors encountered
        """
        if not self.ENABLED:
            logger.info("Auto-pruning is disabled in configuration")
            return {
                "enabled": False,
                "total_checked": 0,
                "pruned_count": 0,
                "errors": 0
            }

        try:
            logger.info("Starting auto-pruning of unretrievable heuristics...")

            # Fetch all heuristics in batches
            all_heuristics = self._fetch_all_heuristics()

            if not all_heuristics:
                logger.info("No heuristics found in database")
                return {
                    "enabled": True,
                    "total_checked": 0,
                    "pruned_count": 0,
                    "errors": 0
                }

            total_checked = len(all_heuristics)
            logger.info(f"Checking {total_checked} heuristics for pruning...")

            # Identify heuristics to prune
            to_prune = self._identify_unretrievable(all_heuristics, verbose)

            if not to_prune:
                logger.info("No unretrievable heuristics found")
                return {
                    "enabled": True,
                    "total_checked": total_checked,
                    "pruned_count": 0,
                    "errors": 0
                }

            # Delete identified heuristics
            pruned_count, errors = self._batch_delete(to_prune)

            logger.info(
                f"Pruning complete: {pruned_count} heuristics removed, "
                f"{errors} errors, {total_checked} total checked"
            )

            return {
                "enabled": True,
                "total_checked": total_checked,
                "pruned_count": pruned_count,
                "errors": errors
            }

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "prune_unretrievable_heuristics",
                    "index": self.index_name
                }
            )
            return {
                "enabled": True,
                "total_checked": 0,
                "pruned_count": 0,
                "errors": 1
            }

    def _fetch_all_heuristics(self) -> List[Dict]:
        """
        Fetch all heuristics from Elasticsearch in batches.

        Returns:
            List of all heuristic documents with _id and rating
        """
        try:
            all_docs = []
            scroll_size = self.BATCH_SIZE

            # Initial search with scroll
            response = self.es.search(
                index=self.index_name,
                scroll='2m',
                size=scroll_size,
                body={
                    "query": {"match_all": {}},
                    "_source": ["prompt", "rating", "prompt_keywords", "response_keywords"]
                }
            )

            scroll_id = response.get('_scroll_id')
            hits = response['hits']['hits']

            while hits:
                for hit in hits:
                    all_docs.append({
                        '_id': hit['_id'],
                        'prompt': hit['_source'].get('prompt', ''),
                        'rating': hit['_source'].get('rating', 0),
                        'prompt_keywords': hit['_source'].get('prompt_keywords', []),
                        'response_keywords': hit['_source'].get('response_keywords', [])
                    })

                # Get next batch
                if not scroll_id:
                    break

                response = self.es.scroll(scroll_id=scroll_id, scroll='2m')
                hits = response['hits']['hits']
                scroll_id = response.get('_scroll_id')

            # Clear scroll
            if scroll_id:
                self.es.clear_scroll(scroll_id=scroll_id)

            logger.info(f"Fetched {len(all_docs)} heuristics from database")
            return all_docs

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "fetch_all_heuristics",
                    "index": self.index_name
                }
            )
            return []

    def _identify_unretrievable(self, all_heuristics: List[Dict], verbose: bool) -> Set[str]:
        """
        Identify heuristics that are unretrievable.

        Strategy:
        - ONLY prune heuristics with rating=0 (completely failed responses)
        - Check if higher-rated similar heuristics exist
        - If yes and rating difference >= MIN_RATING_DIFFERENCE, mark for pruning
        - Conservative approach: preserve all ratings >= 1

        Args:
            all_heuristics: List of all heuristics
            verbose: Enable detailed logging

        Returns:
            Set of heuristic IDs to prune
        """
        to_prune = set()

        # Group heuristics by similarity (using keyword overlap as proxy)
        # This is more efficient than doing full retrieval simulation for each one
        for i, heuristic in enumerate(all_heuristics):
            try:
                h_id = heuristic['_id']
                h_rating = heuristic['rating']
                h_keywords = set(heuristic.get('prompt_keywords', []) +
                               heuristic.get('response_keywords', []))

                # ONLY prune rating=0 heuristics (completely failed responses)
                # This is a conservative approach to preserve learning data
                if h_rating != 0:
                    continue

                # Skip if no keywords (can't determine similarity)
                if not h_keywords:
                    continue

                # Check against all other heuristics for better-rated similar ones
                for j, other in enumerate(all_heuristics):
                    if i == j:
                        continue

                    other_rating = other['rating']
                    other_keywords = set(other.get('prompt_keywords', []) +
                                       other.get('response_keywords', []))

                    if not other_keywords:
                        continue

                    # Calculate keyword overlap (Jaccard similarity)
                    intersection = h_keywords & other_keywords
                    union = h_keywords | other_keywords

                    if not union:
                        continue

                    similarity = len(intersection) / len(union)

                    # If similar AND other has higher rating (any rating >= 1), mark for pruning
                    # Since we're only pruning rating=0, any better alternative means we should prune
                    if similarity >= self.SIMILARITY_THRESHOLD:
                        # For rating=0 heuristics, check if other rating is sufficiently better
                        rating_difference = other_rating - h_rating
                        if rating_difference >= self.MIN_RATING_DIFFERENCE:
                            if verbose:
                                logger.info(
                                    f"Marking {h_id} for pruning: rating={h_rating} (failed), "
                                    f"better alternative with rating={other_rating}, "
                                    f"similarity={similarity:.2f}"
                                )
                            to_prune.add(h_id)
                            break  # No need to check further once marked

            except Exception as e:
                logger.warning(f"Error processing heuristic {heuristic.get('_id', 'unknown')}: {e}")
                continue

        logger.info(f"Identified {len(to_prune)} heuristics for pruning")
        return to_prune

    def _batch_delete(self, ids_to_delete: Set[str]) -> tuple:
        """
        Delete heuristics in batches.

        Args:
            ids_to_delete: Set of document IDs to delete

        Returns:
            Tuple of (successfully_deleted_count, error_count)
        """
        if not ids_to_delete:
            return 0, 0

        deleted_count = 0
        error_count = 0

        # Convert set to list for batching
        ids_list = list(ids_to_delete)

        # Delete in batches
        for i in range(0, len(ids_list), self.BATCH_SIZE):
            batch = ids_list[i:i + self.BATCH_SIZE]

            try:
                # Use bulk delete API
                body = []
                for doc_id in batch:
                    body.append({"delete": {"_index": self.index_name, "_id": doc_id}})

                if body:
                    response = self.es.bulk(body=body, refresh=True)

                    # Count successes and failures
                    for item in response.get('items', []):
                        if 'delete' in item:
                            if item['delete'].get('status') in [200, 201, 204]:
                                deleted_count += 1
                            else:
                                error_count += 1

            except Exception as e:
                logger.error(f"Error deleting batch: {e}")
                error_count += len(batch)

        logger.info(f"Batch delete complete: {deleted_count} deleted, {error_count} errors")
        return deleted_count, error_count
