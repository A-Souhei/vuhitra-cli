"""
Heuristics orchestration module.
Coordinates NLP analysis and ElasticSearch storage.
"""
from typing import Dict
import logging
import threading
from src.errors_handler.error_handler import get_error_handler

# Support both relative imports (for Docker) and absolute imports (for tests)
try:
    from .nlp_analyzer import NLPAnalyzer
    from .elasticsearch_client import ElasticSearchClient
    from .heuristics_config_loader import HeuristicsConfigLoader
except ImportError:
    try:
        # For Docker container without package structure
        from nlp_analyzer import NLPAnalyzer
        from elasticsearch_client import ElasticSearchClient
        from heuristics_config_loader import HeuristicsConfigLoader
    except ImportError:
        # For tests running from project root
        from services.sandbox.src.nlp_analyzer import NLPAnalyzer
        from services.sandbox.src.elasticsearch_client import ElasticSearchClient
        from services.sandbox.src.heuristics_config_loader import HeuristicsConfigLoader

logger = logging.getLogger(__name__)
error_handler = get_error_handler()


class Heuristics:
    """Main heuristics orchestration class."""

    def __init__(self, es_host: str = "localhost", es_port: int = 9200,
                 es_index: str = "llm_feedback"):
        """
        Initialize heuristics service.

        Args:
            es_host: ElasticSearch host
            es_port: ElasticSearch port
            es_index: ElasticSearch index name
        """
        self.nlp_analyzer = NLPAnalyzer()
        self.es_client = ElasticSearchClient(es_host, es_port, es_index)
        self.config = HeuristicsConfigLoader()

        # Load chaining configuration
        self.chaining_enabled = self.config.get_chaining_enabled()
        self.min_rating_for_chaining = self.config.get_min_rating_for_chaining()
        self.max_chain_depth = self.config.get_max_chain_depth()

    def process_feedback(self, feedback_data: Dict) -> Dict[str, str]:
        """
        Process feedback data: analyze and store in ElasticSearch.
        Background thread handles the actual processing.
        
        Args:
            feedback_data: Dict containing prompt, response, rating, timestamp, execution_time_ms
            
        Returns:
            Dict with status and message
        """
        # Start background processing
        thread = threading.Thread(target=self._analyze_and_store, args=(feedback_data,))
        thread.daemon = True
        thread.start()
        
        return {"status": "acknowledged", "message": "Feedback received and processing"}

    def _analyze_and_store(self, feedback_data: Dict):
        """
        Perform NLP analysis and store in ElasticSearch.
        Runs in background thread.

        Args:
            feedback_data: Feedback data to process
        """
        current_step = "initialization"
        try:
            prompt = feedback_data.get("prompt", "")
            response = feedback_data.get("response", "")

            # Analyze prompt
            current_step = "prompt_sentiment_analysis"
            prompt_sentiment = self.nlp_analyzer.analyze_sentiment(prompt)

            current_step = "prompt_keyword_extraction"
            prompt_keywords = self.nlp_analyzer.extract_keywords(prompt)

            current_step = "prompt_word_count"
            prompt_word_count = self.nlp_analyzer.count_words(prompt)

            # Analyze response
            current_step = "response_sentiment_analysis"
            response_sentiment = self.nlp_analyzer.analyze_sentiment(response)

            current_step = "response_keyword_extraction"
            response_keywords = self.nlp_analyzer.extract_keywords(response)

            current_step = "code_detection"
            is_code, code_purpose = self.nlp_analyzer.detect_code(response)

            current_step = "response_word_count"
            response_word_count = self.nlp_analyzer.count_words(response)

            # Build complete data structure
            current_step = "building_data_structure"
            complete_data = {
                "prompt": prompt,
                "prompt_keywords": prompt_keywords,
                "prompt_sentiment_vader": prompt_sentiment["vader_score"],
                "prompt_sentiment_spacy": prompt_sentiment["spacy_score"],
                "prompt_word_count": prompt_word_count,
                "response": response,
                "response_keywords": response_keywords,
                "response_sentiment_vader": response_sentiment["vader_score"],
                "response_sentiment_spacy": response_sentiment["spacy_score"],
                "is_code_response": is_code,
                "code_purpose": code_purpose,
                "response_word_count": response_word_count,
                "rating": feedback_data.get("rating"),
                "timestamp": feedback_data.get("timestamp"),
                "execution_time_ms": feedback_data.get("execution_time_ms", 0)
            }

            # Add chain metadata if chaining is enabled
            current_step = "building_chain_metadata"
            chain_metadata = self._build_chain_metadata(feedback_data)
            complete_data.update(chain_metadata)

            # Store in ElasticSearch
            current_step = "storing_to_elasticsearch"
            success = self.es_client.save_feedback(complete_data)

            if success:
                logger.info("Feedback processed and stored successfully")
            else:
                logger.warning("Feedback processed but storage failed")

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "process_feedback",
                    "step": current_step,
                    "has_prompt": bool(feedback_data.get("prompt")),
                    "has_response": bool(feedback_data.get("response")),
                    "rating": feedback_data.get("rating")
                }
            )

    def _build_chain_metadata(self, feedback_data: Dict) -> Dict:
        """
        Build chain metadata for the feedback.

        Creates parent-child relationships when:
        - Chaining is enabled
        - Rating meets minimum threshold
        - Contexted heuristics were used
        - Chain depth limit not exceeded

        Args:
            feedback_data: Feedback data containing rating and contexted_heuristic_ids

        Returns:
            Dict with chain metadata fields
        """
        metadata = {
            "parent_heuristic_id": None,
            "chain_depth": 0,
            "chain_ids": [],
            "contexted_heuristic_ids": []
        }

        try:
            if not self.chaining_enabled:
                return metadata

            rating = feedback_data.get("rating", 0)
            contexted_heuristic_ids = feedback_data.get("contexted_heuristic_ids", [])

            # Store which heuristics were in context
            metadata["contexted_heuristic_ids"] = contexted_heuristic_ids

            # Only create chain link if rating is high enough
            if rating < self.min_rating_for_chaining:
                logger.debug(f"Rating {rating} below threshold {self.min_rating_for_chaining}, not creating chain")
                return metadata

            # If no contexted heuristics, this is a root heuristic
            if not contexted_heuristic_ids:
                logger.debug("No contexted heuristics, creating root heuristic")
                return metadata

            # Use the first (primary) contexted heuristic as parent
            parent_id = contexted_heuristic_ids[0]

            # Retrieve parent to get its chain information
            parent_doc = self.es_client.get_by_id(parent_id)

            if not parent_doc:
                logger.warning(
                    f"Failed to retrieve parent heuristic {parent_id}. "
                    "This may be due to a retrieval error or the parent not existing. "
                    "Creating as root heuristic instead."
                )
                return metadata

            parent_chain_depth = parent_doc.get("chain_depth", 0)
            parent_chain_ids = parent_doc.get("chain_ids", [])

            # Check chain depth limit
            new_depth = parent_chain_depth + 1
            if new_depth > self.max_chain_depth:
                logger.warning(
                    f"Chain depth limit reached ({self.max_chain_depth}), "
                    f"not creating chain link"
                )
                return metadata

            # Build chain metadata
            metadata["parent_heuristic_id"] = parent_id
            metadata["chain_depth"] = new_depth

            # Detect and handle circular references
            if parent_id in parent_chain_ids:
                logger.warning(
                    f"Circular reference detected: parent {parent_id} already exists in chain. "
                    f"Skipping duplicate to prevent infinite loop. Chain: {parent_chain_ids}"
                )
                metadata["chain_ids"] = parent_chain_ids
            else:
                metadata["chain_ids"] = parent_chain_ids + [parent_id]

            logger.info(
                f"Created chain link: parent={parent_id}, depth={new_depth}, "
                f"chain_length={len(metadata['chain_ids'])}"
            )

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "build_chain_metadata",
                    "rating": feedback_data.get("rating"),
                    "has_contexted_ids": bool(feedback_data.get("contexted_heuristic_ids"))
                }
            )
            # Return default metadata on error
            return {
                "parent_heuristic_id": None,
                "chain_depth": 0,
                "chain_ids": [],
                "contexted_heuristic_ids": feedback_data.get("contexted_heuristic_ids", [])
            }

        return metadata

    def health_check(self) -> Dict[str, bool]:
        """
        Check health of heuristics components.

        Returns:
            Dict with component health status
        """
        return {
            "nlp_ready": self.nlp_analyzer.nlp is not None,
            "elasticsearch_connected": self.es_client.is_connected()
        }
