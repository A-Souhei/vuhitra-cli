"""
Heuristics orchestration module.
Coordinates NLP analysis and ElasticSearch storage.
"""
from typing import Dict
import logging
import threading

# Support both relative imports (for local tests) and absolute imports (for Docker)
try:
    from .nlp_analyzer import NLPAnalyzer
    from .elasticsearch_client import ElasticSearchClient
except ImportError:
    from nlp_analyzer import NLPAnalyzer
    from elasticsearch_client import ElasticSearchClient

logger = logging.getLogger(__name__)


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
        try:
            prompt = feedback_data.get("prompt", "")
            response = feedback_data.get("response", "")
            
            # Analyze prompt
            prompt_sentiment = self.nlp_analyzer.analyze_sentiment(prompt)
            prompt_keywords = self.nlp_analyzer.extract_keywords(prompt)
            prompt_word_count = self.nlp_analyzer.count_words(prompt)
            
            # Analyze response
            response_keywords = self.nlp_analyzer.extract_keywords(response)
            is_code, code_purpose = self.nlp_analyzer.detect_code(response)
            response_word_count = self.nlp_analyzer.count_words(response)
            
            # Build complete data structure
            complete_data = {
                "prompt": prompt,
                "prompt_keywords": prompt_keywords,
                "prompt_sentiment_vader": prompt_sentiment["vader_score"],
                "prompt_sentiment_spacy": prompt_sentiment["spacy_score"],
                "prompt_word_count": prompt_word_count,
                "response": response,
                "response_keywords": response_keywords,
                "is_code_response": is_code,
                "code_purpose": code_purpose,
                "response_word_count": response_word_count,
                "rating": feedback_data.get("rating"),
                "timestamp": feedback_data.get("timestamp"),
                "execution_time_ms": feedback_data.get("execution_time_ms", 0)
            }
            
            # Store in ElasticSearch
            success = self.es_client.save_feedback(complete_data)
            
            if success:
                logger.info("Feedback processed and stored successfully")
            else:
                logger.warning("Feedback processed but storage failed")
                
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")

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
