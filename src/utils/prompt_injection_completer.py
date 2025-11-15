"""
Prompt Injection Completer
Provides : + TAB autocomplete for quick prompt injection phrases
"""

import os
import re
import random
import yaml
from typing import Dict, List, Optional
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from src.errors_handler import handle_exception


class PromptInjectionCompleter(Completer):
    """
    Completer for : prefix that suggests prompt injection categories.
    When a category is selected, it injects a random phrase from that category.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the prompt injection completer.

        Args:
            config_path: Path to the prompt_injections.yaml file
        """
        self.injections: Dict = {}
        self.categories: List[str] = []

        if config_path is None:
            # Default path relative to project root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(project_root, 'data', 'prompt_injections.yaml')

        self.config_path = config_path
        self._load_injections()

    def _load_injections(self) -> None:
        """Load prompt injections from YAML config file."""
        try:
            if not os.path.exists(self.config_path):
                # Create default config if it doesn't exist
                self.injections = {}
                self.categories = []
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if data and 'prompt_injections' in data:
                self.injections = data['prompt_injections']
                self.categories = sorted(self.injections.keys())
            else:
                self.injections = {}
                self.categories = []

        except Exception as e:
            handle_exception(e, context={
                'function': 'PromptInjectionCompleter._load_injections',
                'operation': 'loading prompt injections config',
                'config_path': self.config_path
            })
            self.injections = {}
            self.categories = []

    def get_random_phrase(self, category: str) -> Optional[str]:
        """
        Get a random phrase from the specified category.

        Args:
            category: The category name

        Returns:
            A random phrase from the category, or None if category doesn't exist
        """
        try:
            if category not in self.injections:
                return None

            category_data = self.injections[category]
            phrases = category_data.get('phrases', [])

            if not phrases:
                return None

            # Randomly select one phrase
            return random.choice(phrases)

        except Exception as e:
            handle_exception(e, context={
                'function': 'PromptInjectionCompleter.get_random_phrase',
                'operation': 'selecting random phrase',
                'category': category
            })
            return None

    def get_category_emoji(self, category: str) -> str:
        """
        Get the emoji for a category.

        Args:
            category: The category name

        Returns:
            The emoji for the category, or empty string if not found
        """
        try:
            if category in self.injections:
                return self.injections[category].get('emoji', '')
            return ''
        except Exception as e:
            handle_exception(e, context={
                'function': 'PromptInjectionCompleter.get_category_emoji',
                'operation': 'getting category emoji',
                'category': category
            })
            return ''

    def get_category_description(self, category: str) -> str:
        """
        Get the description for a category.

        Args:
            category: The category name

        Returns:
            The description for the category, or empty string if not found
        """
        try:
            if category in self.injections:
                return self.injections[category].get('description', '')
            return ''
        except Exception as e:
            handle_exception(e, context={
                'function': 'PromptInjectionCompleter.get_category_description',
                'operation': 'getting category description',
                'category': category
            })
            return ''

    def get_completions(self, document: Document, complete_event):
        """
        Generate completions for : prefix.

        Args:
            document: The current document
            complete_event: The completion event

        Yields:
            Completion objects for matching categories
        """
        try:
            text_before_cursor = document.text_before_cursor

            # Match pattern :word (where word is partial or complete category name)
            match = re.search(r':([^\s]*)$', text_before_cursor)

            if not match:
                return

            prefix = match.group(1).lower()

            # Filter categories that match the prefix
            for category in self.categories:
                if category.lower().startswith(prefix):
                    emoji = self.get_category_emoji(category)
                    description = self.get_category_description(category)

                    # Create display text with emoji and description
                    display = f"{emoji} {category}"
                    if description:
                        display += f" - {description}"

                    # The completion text is just the category name
                    # We'll handle the phrase injection separately
                    yield Completion(
                        text=category,
                        start_position=-len(prefix),
                        display=display,
                        display_meta=f"{len(self.injections[category].get('phrases', []))} phrases"
                    )

        except Exception as e:
            handle_exception(e, context={
                'function': 'PromptInjectionCompleter.get_completions',
                'operation': 'generating completions',
                'text_before_cursor': text_before_cursor if 'text_before_cursor' in locals() else 'N/A'
            })

    def replace_category_with_phrase(self, text: str, cursor_position: int) -> tuple[str, int]:
        """
        Replace :category with a random phrase from that category.

        Args:
            text: The full text
            cursor_position: Current cursor position

        Returns:
            Tuple of (new_text, new_cursor_position)
        """
        try:
            # Find all :category patterns
            pattern = r':(\w+)'

            def replace_with_phrase(match):
                category = match.group(1)
                phrase = self.get_random_phrase(category)
                emoji = self.get_category_emoji(category)

                if phrase:
                    # Add emoji before the phrase
                    return f"{emoji} {phrase}"
                else:
                    # Keep original if category not found
                    return match.group(0)

            # Replace all :category with phrases
            new_text = re.sub(pattern, replace_with_phrase, text)

            # Adjust cursor position (simplified - keeps cursor at end)
            new_cursor_position = len(new_text)

            return new_text, new_cursor_position

        except Exception as e:
            handle_exception(e, context={
                'function': 'PromptInjectionCompleter.replace_category_with_phrase',
                'operation': 'replacing category with phrase',
                'text': text
            })
            return text, cursor_position
