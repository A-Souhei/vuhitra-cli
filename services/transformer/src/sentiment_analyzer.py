"""
Sentiment Analyzer Module

Uses transformer models for sentiment analysis.
Provides more accurate contextual sentiment analysis compared to rule-based approaches.
"""

from transformers import pipeline
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """
    Transformer-based sentiment analyzer.

    Uses distilbert-base-uncased-finetuned-sst-2-english:
    - Lightweight (~250MB)
    - Fast inference (~100-200ms)
    - Accurate contextual understanding
    - Trained on SST-2 (Stanford Sentiment Treebank)
    """

    def __init__(self):
        """Initialize the sentiment analyzer with lazy loading."""
        self._analyzer = None
        self.model_name = "distilbert-base-uncased-finetuned-sst-2-english"

    def _load_model(self):
        """Lazy load the sentiment analysis model."""
        if self._analyzer is None:
            logger.info(f"Loading sentiment analysis model: {self.model_name}")
            try:
                self._analyzer = pipeline(
                    "sentiment-analysis",
                    model=self.model_name,
                    truncation=True,
                    max_length=512  # Limit to 512 tokens
                )
                logger.info("Sentiment analysis model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load sentiment model: {e}")
                raise

    def analyze(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text.

        Args:
            text: Input text to analyze

        Returns:
            Dictionary with sentiment scores:
            {
                'label': 'POSITIVE' or 'NEGATIVE',
                'score': float (0.0-1.0),
                'compound': float (-1.0 to 1.0, VADER-compatible)
            }
        """
        if not text or not text.strip():
            return {
                'label': 'NEUTRAL',
                'score': 0.5,
                'compound': 0.0
            }

        # Lazy load model
        if self._analyzer is None:
            self._load_model()

        try:
            # Get prediction
            result = self._analyzer(text[:512])[0]  # Truncate to 512 chars

            label = result['label']
            confidence = result['score']

            # Convert to VADER-compatible compound score (-1 to 1)
            # POSITIVE: 0 to 1, NEGATIVE: -1 to 0
            if label == 'POSITIVE':
                compound = confidence
            else:  # NEGATIVE
                compound = -confidence

            return {
                'label': label,
                'score': confidence,
                'compound': round(compound, 3)
            }

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            # Return neutral on error
            return {
                'label': 'NEUTRAL',
                'score': 0.5,
                'compound': 0.0
            }

    def analyze_batch(self, texts: list) -> list:
        """
        Analyze sentiment for multiple texts.

        Args:
            texts: List of texts to analyze

        Returns:
            List of sentiment dictionaries
        """
        if not texts:
            return []

        # Lazy load model
        if self._analyzer is None:
            self._load_model()

        try:
            # Truncate all texts to 512 chars
            truncated_texts = [text[:512] for text in texts]

            # Batch prediction
            results = self._analyzer(truncated_texts)

            # Convert to standard format
            formatted_results = []
            for result in results:
                label = result['label']
                confidence = result['score']

                # Convert to compound score
                if label == 'POSITIVE':
                    compound = confidence
                else:
                    compound = -confidence

                formatted_results.append({
                    'label': label,
                    'score': confidence,
                    'compound': round(compound, 3)
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Batch sentiment analysis failed: {e}")
            # Return neutral for all on error
            return [
                {'label': 'NEUTRAL', 'score': 0.5, 'compound': 0.0}
                for _ in texts
            ]

    def get_model_info(self) -> Dict[str, str]:
        """
        Get information about the sentiment model.

        Returns:
            Dictionary with model information
        """
        return {
            'model_name': self.model_name,
            'model_type': 'DistilBERT',
            'task': 'sentiment-analysis',
            'framework': 'transformers',
            'labels': ['POSITIVE', 'NEGATIVE'],
            'max_length': '512 tokens',
            'trained_on': 'SST-2 (Stanford Sentiment Treebank)'
        }
