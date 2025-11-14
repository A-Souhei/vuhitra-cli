"""
NLP analysis module for sentiment analysis, keyword extraction, and code detection.
"""
import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import Dict, List, Tuple
import logging
import requests
import yaml
from src.errors_handler.error_handler import get_error_handler

logger = logging.getLogger(__name__)
error_handler = get_error_handler()


class NLPAnalyzer:
    """Handles NLP tasks: sentiment analysis, keyword extraction, code detection."""

    def __init__(self, config_path='heuristics_config.yaml'):
        """Initialize NLP tools."""
        try:
            self.nlp = spacy.load("en_core_web_lg")
        except OSError as e:
            error_handler.capture_message(
                "spaCy model not found - NLP features will be limited",
                level="warning",
                context={
                    "operation": "nlp_init",
                    "model": "en_core_web_lg",
                    "install_command": "pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_lg-3.8.0/en_core_web_lg-3.8.0-py3-none-any.whl"
                }
            )
            self.nlp = None

        self.vader = SentimentIntensityAnalyzer()

        # Load sentiment analysis configuration
        self.sentiment_config = self._load_sentiment_config(config_path)

    def _load_sentiment_config(self, config_path: str) -> Dict:
        """Load sentiment analysis configuration from yaml file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config.get('sentiment_analysis', {
                    'use_transformer': True,
                    'transformer_url': 'http://transformer:5050',
                    'timeout_seconds': 5,
                    'fallback_to_vader': True
                })
        except Exception as e:
            logger.warning(f"Failed to load sentiment config: {e}, using defaults")
            return {
                'use_transformer': True,
                'transformer_url': 'http://transformer:5050',
                'timeout_seconds': 5,
                'fallback_to_vader': True
            }
        
        # Code detection patterns
        self.code_keywords = {
            'def', 'class', 'import', 'function', 'const', 'let', 'var', 
            'return', 'if', 'else', 'for', 'while', 'try', 'catch', 'public', 
            'private', 'void', 'int', 'string', 'async', 'await'
        }
        self.code_symbols = {'(', ')', '{', '}', '[', ']', ';', ':', '=', '=>', '->'}

    def _analyze_sentiment_transformer(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment using transformer service.

        Args:
            text: Input text

        Returns:
            Dict with vader_score and spacy_score, or None if failed
        """
        try:
            url = f"{self.sentiment_config['transformer_url']}/api/analyze-sentiment"
            timeout = self.sentiment_config.get('timeout_seconds', 5)

            response = requests.post(
                url,
                json={'text': text},
                timeout=timeout
            )
            response.raise_for_status()

            result = response.json()

            # Extract compound score (VADER-compatible: -1 to 1)
            compound_score = result.get('compound', 0.0)

            # Return in expected format
            return {
                "vader_score": round(compound_score, 3),
                "spacy_score": round(compound_score, 3)
            }

        except Exception as e:
            logger.debug(f"Transformer sentiment analysis failed: {e}")
            return None

    def _analyze_sentiment_vader(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment using VADER (fallback).

        Args:
            text: Input text

        Returns:
            Dict with vader_score and spacy_score
        """
        vader_score = self.vader.polarity_scores(text)['compound']

        return {
            "vader_score": round(vader_score, 3),
            "spacy_score": round(vader_score, 3)
        }

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment using transformer model or VADER.

        Tries transformer service first (if enabled), falls back to VADER.

        Args:
            text: Input text

        Returns:
            Dict with vader_score and spacy_score
        """
        # Try transformer if enabled
        if self.sentiment_config.get('use_transformer', True):
            result = self._analyze_sentiment_transformer(text)

            if result is not None:
                return result

            # If transformer failed and fallback is disabled, still use VADER
            if not self.sentiment_config.get('fallback_to_vader', True):
                logger.warning("Transformer sentiment failed and fallback disabled, using VADER anyway")

        # Fallback to VADER
        return self._analyze_sentiment_vader(text)

    def extract_keywords(self, text: str, top_n: int = 15) -> List[str]:
        """
        Extract top keywords from text using spaCy.
        
        Args:
            text: Input text
            top_n: Number of top keywords to return
            
        Returns:
            List of keywords
        """
        if not self.nlp:
            return []
        
        doc = self.nlp(text.lower())
        
        # Extract nouns, proper nouns, and meaningful verbs
        keywords = []
        for token in doc:
            if (token.pos_ in ('NOUN', 'PROPN', 'VERB') and 
                not token.is_stop and 
                not token.is_punct and 
                len(token.text) > 2):
                keywords.append(token.lemma_)
        
        # Get unique keywords, preserve order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:top_n]

    def detect_code(self, text: str) -> Tuple[bool, str]:
        """
        Detect if text contains code and infer purpose.
        
        Args:
            text: Input text
            
        Returns:
            Tuple of (is_code, purpose)
        """
        # Count code symbols and keywords
        words = text.split()
        total_tokens = len(words)
        
        if total_tokens == 0:
            return False, ""
        
        # Count code indicators
        symbol_count = sum(1 for char in text if char in self.code_symbols)
        keyword_count = sum(1 for word in words if word.lower() in self.code_keywords)
        
        # Calculate ratio
        code_ratio = (symbol_count + keyword_count) / max(total_tokens, 1)
        
        is_code = code_ratio >= 0.5
        
        # Infer purpose if code detected
        purpose = ""
        if is_code:
            text_lower = text.lower()
            # Check class first since classes often contain methods with 'def'
            if 'class ' in text_lower:
                purpose = "class definition"
            elif 'def ' in text_lower or 'function' in text_lower:
                purpose = "function definition"
            elif 'import ' in text_lower or 'require' in text_lower:
                purpose = "module import"
            elif 'if ' in text_lower and ('else' in text_lower or 'elif' in text_lower):
                purpose = "conditional logic"
            elif 'for ' in text_lower or 'while ' in text_lower:
                purpose = "loop implementation"
            else:
                purpose = "code snippet"
        
        return is_code, purpose

    def count_words(self, text: str) -> int:
        """
        Count words in text.

        Args:
            text: Input text

        Returns:
            Word count
        """
        if not text.strip():
            return 0
        return len(text.split())
