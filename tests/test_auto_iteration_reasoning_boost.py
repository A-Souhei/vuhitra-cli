"""Tests for auto-iteration reasoning boost feature."""

import pytest
from unittest.mock import patch, MagicMock
from src.utils.prompt_injection_completer import PromptInjectionCompleter


class TestAutoIterationReasoningBoost:
    """Test that reasoning prompts are injected during auto-iteration retries."""

    def test_reasoning_injection_on_retry(self):
        """Test that reasoning phrase is injected when iteration_number > 0."""
        completer = PromptInjectionCompleter()

        # Get a reasoning phrase
        phrase = completer.get_random_phrase('reasoning')
        emoji = completer.get_category_emoji('reasoning')

        assert phrase is not None
        assert emoji == '🧠'

        # Simulate what happens during auto-iteration
        iteration_number = 1  # This is a retry (not first attempt)
        enhanced_prompt = "User query: What is the answer?"

        if iteration_number > 0:
            reasoning_injection = f"{emoji} {phrase}"
            enhanced_prompt = f"{enhanced_prompt}\n\n{reasoning_injection}"

        # Verify the reasoning phrase was added
        assert emoji in enhanced_prompt
        assert phrase in enhanced_prompt
        assert "User query: What is the answer?" in enhanced_prompt

    def test_no_reasoning_injection_on_first_attempt(self):
        """Test that reasoning phrase is NOT injected on first attempt."""
        completer = PromptInjectionCompleter()

        # Get a reasoning phrase
        emoji = completer.get_category_emoji('reasoning')

        # Simulate first attempt
        iteration_number = 0  # This is the first attempt
        enhanced_prompt = "User query: What is the answer?"

        if iteration_number > 0:
            phrase = completer.get_random_phrase('reasoning')
            reasoning_injection = f"{emoji} {phrase}"
            enhanced_prompt = f"{enhanced_prompt}\n\n{reasoning_injection}"

        # Verify the reasoning phrase was NOT added
        assert emoji not in enhanced_prompt
        assert enhanced_prompt == "User query: What is the answer?"

    def test_reasoning_phrases_variety(self):
        """Test that different reasoning phrases are available."""
        completer = PromptInjectionCompleter()

        # Get multiple phrases to verify variety
        phrases = set()
        for _ in range(20):
            phrase = completer.get_random_phrase('reasoning')
            phrases.add(phrase)

        # Should have multiple different phrases (probabilistic)
        assert len(phrases) > 1

    def test_reasoning_category_exists(self):
        """Test that the reasoning category exists in the config."""
        completer = PromptInjectionCompleter()

        assert 'reasoning' in completer.categories
        assert len(completer.injections['reasoning']['phrases']) > 0
        assert completer.injections['reasoning']['emoji'] == '🧠'
        assert 'description' in completer.injections['reasoning']
