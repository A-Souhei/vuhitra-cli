"""
ElasticSearch client for storing and managing heuristics data.
"""
from elasticsearch import Elasticsearch
from datetime import datetime, timezone
from typing import Dict
import logging
from src.errors_handler.error_handler import get_error_handler

logger = logging.getLogger(__name__)
error_handler = get_error_handler()


class ElasticSearchClient:
    """Manages ElasticSearch connection and data operations."""

    def __init__(self, host: str = "localhost", port: int = 9200, index_name: str = "llm_feedback"):
        """
        Initialize ElasticSearch client.
        
        Args:
            host: ElasticSearch host
            port: ElasticSearch port
            index_name: Name of the index to use
        """
        self.host = host
        self.port = port
        self.index_name = index_name
        self.es = None
        self._connect()

    def _connect(self):
        """Establish connection to ElasticSearch."""
        try:
            self.es = Elasticsearch([f"http://{self.host}:{self.port}"])
            if self.es.ping():
                logger.info(f"Connected to ElasticSearch at {self.host}:{self.port}")
                self._create_index_if_not_exists()
            else:
                error_handler.capture_message(
                    "ElasticSearch connection failed",
                    level="warning",
                    context={"host": self.host, "port": self.port}
                )
        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "elasticsearch_connect",
                    "host": self.host,
                    "port": self.port
                }
            )
            self.es = None

    def _create_index_if_not_exists(self):
        """Create the index with proper mappings if it doesn't exist."""
        if not self.es.indices.exists(index=self.index_name):
            mappings = {
                "mappings": {
                    "properties": {
                        "prompt": {"type": "text"},
                        "prompt_keywords": {"type": "keyword"},
                        "prompt_sentiment_vader": {"type": "float"},
                        "prompt_sentiment_spacy": {"type": "float"},
                        "prompt_word_count": {"type": "integer"},
                        "response": {"type": "text"},
                        "response_keywords": {"type": "keyword"},
                        "response_sentiment_vader": {"type": "float"},
                        "response_sentiment_spacy": {"type": "float"},
                        "is_code_response": {"type": "boolean"},
                        "code_purpose": {"type": "text"},
                        "response_word_count": {"type": "integer"},
                        "rating": {"type": "integer"},
                        "timestamp": {"type": "date"},
                        "processed_at": {"type": "date"},
                        "execution_time_ms": {"type": "long"},
                        "parent_heuristic_id": {"type": "keyword"},
                        "chain_depth": {"type": "integer"},
                        "chain_ids": {"type": "keyword"},
                        "contexted_heuristic_ids": {"type": "keyword"}
                    }
                }
            }
            self.es.indices.create(index=self.index_name, body=mappings)
            logger.info(f"Created index: {self.index_name}")

    def save_feedback(self, data: Dict) -> bool:
        """
        Save feedback data to ElasticSearch.
        
        Args:
            data: Dictionary containing feedback and analysis data
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.es:
            logger.warning("ElasticSearch not connected, skipping save")
            return False

        try:
            data["processed_at"] = datetime.now(timezone.utc).isoformat()
            result = self.es.index(index=self.index_name, document=data)
            logger.info(f"Saved feedback document: {result['_id']}")
            return True
        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "save_feedback",
                    "index": self.index_name,
                    "has_prompt": "prompt" in data,
                    "has_response": "response" in data
                }
            )
            return False

    def is_connected(self) -> bool:
        """Check if connected to ElasticSearch."""
        return self.es is not None and self.es.ping()

    def get_by_id(self, doc_id: str) -> Dict:
        """
        Retrieve a heuristic by its document ID.

        Args:
            doc_id: ElasticSearch document ID

        Returns:
            Dict: Document data if found
            None: If document not found or error occurs
        """
        if not self.es:
            logger.warning("ElasticSearch not connected")
            return None

        try:
            result = self.es.get(index=self.index_name, id=doc_id)
            return result["_source"] if result else None
        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "get_by_id",
                    "doc_id": doc_id,
                    "index": self.index_name
                }
            )
            return None

    def get_chain(self, doc_id: str) -> list:
        """
        Retrieve the full chain of parent heuristics for a given document.

        Args:
            doc_id: ElasticSearch document ID

        Returns:
            list: List of parent heuristics ordered from root to immediate parent
        """
        if not self.es:
            logger.warning("ElasticSearch not connected")
            return []

        try:
            chain = []
            current_doc = self.get_by_id(doc_id)

            if not current_doc:
                return []

            # Get chain_ids if available
            chain_ids = current_doc.get("chain_ids", [])

            if not chain_ids:
                return []

            # Use mget for efficient bulk retrieval (avoids N+1 queries)
            docs = [{"_id": parent_id, "_index": self.index_name} for parent_id in chain_ids]
            mget_response = self.es.mget(body={"docs": docs})

            # Build chain from mget results, maintaining order
            for doc_result in mget_response["docs"]:
                if doc_result.get("found"):
                    chain.append({
                        "_id": doc_result["_id"],
                        **doc_result["_source"]
                    })

            return chain
        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "get_chain",
                    "doc_id": doc_id,
                    "index": self.index_name
                }
            )
            return []

    def update_mapping(self):
        """
        Update the index mapping to add new fields (for existing indices).
        This is safe to call multiple times and won't affect existing data.
        """
        if not self.es:
            logger.warning("ElasticSearch not connected")
            return False

        try:
            # Add new properties to existing index
            self.es.indices.put_mapping(
                index=self.index_name,
                properties={
                    "parent_heuristic_id": {"type": "keyword"},
                    "chain_depth": {"type": "integer"},
                    "chain_ids": {"type": "keyword"},
                    "contexted_heuristic_ids": {"type": "keyword"}
                }
            )
            logger.info(f"Updated mapping for index: {self.index_name}")
            return True
        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "update_mapping",
                    "index": self.index_name
                }
            )
            return False
