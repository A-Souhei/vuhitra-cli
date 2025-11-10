"""
NLP analysis module for sentiment analysis, keyword extraction, and code detection.
"""
import spacy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import Dict, List, Tuple
import logging
from src.errors_handler.error_handler import get_error_handler

logger = logging.getLogger(__name__)
error_handler = get_error_handler()


class NLPAnalyzer:
    """Handles NLP tasks: sentiment analysis, keyword extraction, code detection."""

    def __init__(self):
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
        
        # Code detection patterns
        self.code_keywords = {
            'def', 'class', 'import', 'function', 'const', 'let', 'var', 
            'return', 'if', 'else', 'for', 'while', 'try', 'catch', 'public', 
            'private', 'void', 'int', 'string', 'async', 'await'
        }
        self.code_symbols = {'(', ')', '{', '}', '[', ']', ';', ':', '=', '=>', '->'}

    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment using VADER.
        Note: spaCy core models don't include sentiment analysis.
        Both scores use VADER for consistency.

        Args:
            text: Input text

        Returns:
            Dict with vader_score and spacy_score (both using VADER)
        """
        # VADER sentiment (compound score: -1 to 1)
        vader_score = self.vader.polarity_scores(text)['compound']

        # Note: spaCy's core models don't include sentiment analysis
        # For true dual sentiment, would need spacytextblob or similar
        # Using VADER for both to maintain data structure consistency
        spacy_score = vader_score

        return {
            "vader_score": round(vader_score, 3),
            "spacy_score": round(spacy_score, 3)
        }

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
