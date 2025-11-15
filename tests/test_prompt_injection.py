"""Tests for prompt injection feature."""

import pytest
import os
import re
from src.utils.prompt_injection_completer import PromptInjectionCompleter


class TestPromptInjectionCompleter:
    """Test the PromptInjectionCompleter class."""

    def test_load_injections(self):
        """Test that injections are loaded from YAML."""
        completer = PromptInjectionCompleter()
        assert len(completer.categories) > 0
        assert 'reasoning' in completer.categories
        assert 'clarity' in completer.categories
        assert 'code' in completer.categories

    def test_get_random_phrase(self):
        """Test getting a random phrase from a category."""
        completer = PromptInjectionCompleter()
        phrase = completer.get_random_phrase('reasoning')
        assert phrase is not None
        assert isinstance(phrase, str)
        assert len(phrase) > 0

    def test_get_random_phrase_invalid_category(self):
        """Test getting a phrase from invalid category returns None."""
        completer = PromptInjectionCompleter()
        phrase = completer.get_random_phrase('nonexistent_category')
        assert phrase is None

    def test_get_category_emoji(self):
        """Test getting emoji for a category."""
        completer = PromptInjectionCompleter()
        emoji = completer.get_category_emoji('reasoning')
        assert emoji == '🧠'

        emoji = completer.get_category_emoji('clarity')
        assert emoji == '✨'

        emoji = completer.get_category_emoji('code')
        assert emoji == '💻'

    def test_get_category_description(self):
        """Test getting description for a category."""
        completer = PromptInjectionCompleter()
        desc = completer.get_category_description('reasoning')
        assert desc is not None
        assert len(desc) > 0

    def test_replace_category_with_phrase(self):
        """Test replacing :category with phrase."""
        completer = PromptInjectionCompleter()
        text = "Please help me :reasoning and then :clarity"
        new_text, new_cursor = completer.replace_category_with_phrase(text, len(text))

        # Should not contain :reasoning or :clarity anymore
        assert ':reasoning' not in new_text
        assert ':clarity' not in new_text

        # Should contain emojis
        assert '🧠' in new_text
        assert '✨' in new_text

    def test_multiple_same_category_randomization(self):
        """Test that multiple instances of same category get different phrases."""
        completer = PromptInjectionCompleter()

        # Get many phrases to increase likelihood of different results
        phrases = set()
        for _ in range(20):
            phrase = completer.get_random_phrase('reasoning')
            phrases.add(phrase)

        # Should have gotten at least a few different phrases (probabilistic test)
        # With 10 phrases in the category and 20 draws, we should get multiple unique ones
        assert len(phrases) > 1

    def test_process_prompt_with_injections(self):
        """Test the full flow of processing a prompt with injections."""
        from src.cli import interactive_mode

        # Import the processing function (it's defined inside interactive_mode)
        # For testing, we'll use the completer directly
        completer = PromptInjectionCompleter()

        test_prompt = "Help me with this code :code"

        # Simulate the replacement
        pattern = r':(\w+)'
        def replace_with_phrase(match):
            category = match.group(1)
            phrase = completer.get_random_phrase(category)
            emoji = completer.get_category_emoji(category)
            if phrase:
                return f"{emoji} {phrase}"
            else:
                return match.group(0)

        result = re.sub(pattern, replace_with_phrase, test_prompt)

        assert ':code' not in result
        assert '💻' in result
        assert len(result) > len(test_prompt)
