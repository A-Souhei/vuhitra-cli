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
                        "is_code_response": {"type": "boolean"},
                        "code_purpose": {"type": "text"},
                        "response_word_count": {"type": "integer"},
                        "rating": {"type": "integer"},
                        "timestamp": {"type": "date"},
                        "processed_at": {"type": "date"},
                        "execution_time_ms": {"type": "long"}
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
