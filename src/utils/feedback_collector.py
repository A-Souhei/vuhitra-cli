"""
Feedback Collector Module

This module handles user satisfaction feedback collection in interactive mode.
Feedback data is prepared for ElasticSearch storage along with prompt metadata.
"""

from datetime import datetime, timezone
from typing import Optional, Dict
from .config_loader import ConfigLoader


class FeedbackCollector:
    """Collects user satisfaction ratings after LLM responses."""

    SENTIMENT_LABELS = {
        0: "Irrelevant",
        1: "Very dissatisfied",
        2: "Dissatisfied",
        3: "Neutral",
        4: "Satisfied",
        5: "Very satisfied"
    }

    def __init__(self):
        """Initialize the feedback collector and load configuration."""
        self.config_loader = ConfigLoader()

    def is_enabled(self) -> bool:
        """
        Check if feedback collection is enabled in configuration.

        Returns:
            bool: True if feedback collection is enabled, False otherwise
        """
        return self.config_loader.get_feedback_enabled()

    def collect_feedback(self, prompt: str, response: str) -> Optional[Dict]:
        """
        Collect user satisfaction rating for the LLM response.

        Args:
            prompt: The user's original prompt
            response: The LLM's response

        Returns:
            Optional[Dict]: Feedback data dictionary if valid rating provided, None otherwise.
                           Dictionary contains: prompt, response, rating, timestamp
        """
        if not self.is_enabled():
            return None

        # Display the rating prompt with labels
        labels_str = ", ".join([f"{k}={v}" for k, v in self.SENTIMENT_LABELS.items()])
        print(f"\nRate satisfaction ({labels_str}, or Enter to skip): ", end="", flush=True)

        try:
            user_input = input().strip()

            # Handle empty input (user pressed Enter)
            if not user_input:
                return None

            # Validate and get rating
            rating = self._validate_rating(user_input)

            if rating is None:
                print("Skipping feedback.")
                return None

            # Create feedback data structure for ElasticSearch
            feedback_data = {
                "prompt": prompt,
                "response": response,
                "rating": rating,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                # Future fields for ElasticSearch integration:
                # "prompt_keywords": [],  # Will be added by keyword extraction service
                # "prompt_sentiment": "",  # Will be added by sentiment analysis service
            }

            print("Thank you for your feedback!")
            return feedback_data

        except (EOFError, KeyboardInterrupt):
            # Handle Ctrl+C or EOF gracefully
            print("\nSkipping feedback.")
            return None

    def _validate_rating(self, user_input: str) -> Optional[int]:
        """
        Validate user input for rating.

        Args:
            user_input: The raw user input string

        Returns:
            Optional[int]: Valid rating (0-5) if input is valid, None otherwise
        """
        try:
            rating = int(user_input)
            if 0 <= rating <= 5:
                return rating
            else:
                return None
        except ValueError:
            # Input is not a valid integer
            return None
