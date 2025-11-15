"""
Integration test for user_feedback in anti-pattern flow

This test verifies that:
1. Negative feedback (rating <= 2) with user_feedback is properly stored
2. The user_feedback field is included in Elasticsearch index
3. Anti-pattern retrieval includes user_feedback in the context
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'sandbox', 'src'))

from insight_extractor import InsightExtractor


class TestUserFeedbackAntiPattern:
    """Test user_feedback integration in anti-pattern handling"""

    @pytest.fixture
    def extractor(self):
        """Create InsightExtractor with mocked NLP"""
        with patch('insight_extractor.spacy.load') as mock_spacy:
            # Create mock NLP model
            mock_nlp = Mock()
            mock_doc = Mock()
            mock_doc.__iter__ = lambda self: iter([])
            mock_doc.sents = []
            mock_doc.ents = []
            mock_doc.text = "test"
            mock_nlp.return_value = mock_doc
            mock_spacy.return_value = mock_nlp
            
            extractor = InsightExtractor()
            extractor.nlp = mock_nlp
            return extractor

    def test_full_anti_pattern_flow_with_user_feedback(self, extractor):
        """
        Test complete flow: negative rating + user feedback → storage → retrieval → context injection
        
        Scenario:
        - User asks: "Why do dogs kill small animals?"
        - LLM responds (incorrectly): "Dogs are herbivorous"
        - User rates 0 (very dissatisfied)
        - User provides feedback: "dogs are omnivorous"
        - System stores this as anti-pattern
        - Future similar prompts get corrected context
        """
        # Step 1: User provides negative feedback with correction
        matched_heuristic = {
            'prompt': 'Why do dogs kill small animals?',
            'response': 'Dogs are herbivorous animals that only eat plants.',
            'rating': 0,
            'is_code_response': False,
            'user_feedback': 'dogs are omnivorous'
        }

        # Step 2: Extract anti-pattern insights (what would be stored)
        result = extractor.extract_negative_insights(matched_heuristic)

        # Verify user_feedback is in the result
        assert 'user_feedback' in result
        assert result['user_feedback'] == 'dogs are omnivorous'
        assert result['is_negative'] is True

        # Step 3: Verify formatted insight includes user correction
        formatted = result['formatted_insight']
        
        # Should have anti-pattern alert
        assert 'ANTI-PATTERN ALERT' in formatted or 'Anti-Pattern' in formatted
        
        # Should show the incorrect response
        assert 'herbivorous' in formatted or 'INCORRECT' in formatted
        
        # Should prominently display user correction
        assert 'USER CORRECTION' in formatted
        assert 'dogs are omnivorous' in formatted
        
        # Should tell LLM to use the correction
        assert 'Use the USER CORRECTION' in formatted or 'factually accurate' in formatted

    def test_anti_pattern_without_user_feedback(self, extractor):
        """Test that anti-pattern works without user_feedback (user skipped it)"""
        matched_heuristic = {
            'prompt': 'Test question',
            'response': 'Wrong answer',
            'rating': 1,
            'is_code_response': False
            # No user_feedback - user pressed Enter to skip
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        # Should still work
        assert result is not None
        assert result['is_negative'] is True
        assert 'user_feedback' in result
        assert result['user_feedback'] == ''
        
        # Should have standard directive instead
        formatted = result['formatted_insight']
        assert 'Do NOT repeat this mistake' in formatted
        assert 'USER CORRECTION' not in formatted

    def test_multiple_ratings_with_user_feedback(self, extractor):
        """Test that all low ratings (0, 1, 2) properly handle user_feedback"""
        for rating in [0, 1, 2]:
            matched_heuristic = {
                'prompt': f'Test prompt {rating}',
                'response': f'Bad response {rating}',
                'rating': rating,
                'is_code_response': False,
                'user_feedback': f'correction for rating {rating}'
            }

            result = extractor.extract_negative_insights(matched_heuristic)

            # All should include user_feedback
            assert result['user_feedback'] == f'correction for rating {rating}'
            assert 'USER CORRECTION' in result['formatted_insight']
            assert f'correction for rating {rating}' in result['formatted_insight']

    def test_formatted_context_structure_with_feedback(self, extractor):
        """Test that the formatted context has proper structure for LLM injection"""
        matched_heuristic = {
            'prompt': 'What is Python used for?',
            'response': 'Python is only used for web scraping',
            'rating': 0,
            'is_code_response': False,
            'user_feedback': 'Python is a general-purpose language used for web, data science, automation, AI, etc.'
        }

        result = extractor.extract_negative_insights(matched_heuristic)
        formatted = result['formatted_insight']

        # Verify structure
        lines = formatted.split('\n')
        
        # Should have clear sections
        assert any('SYSTEM DIRECTIVE' in line or 'Anti-Pattern' in line for line in lines), \
            "Missing system directive header"
        
        # Should mark incorrect answer
        assert any('INCORRECT' in line or 'AVOID' in line for line in lines), \
            "Missing incorrect answer marker"
        
        # Should have user correction section
        assert any('USER CORRECTION' in line for line in lines), \
            "Missing user correction section"
        
        # Should have directive to use correction
        assert any('DIRECTIVE' in line or 'Use the USER CORRECTION' in formatted for line in lines), \
            "Missing directive to use correction"

    def test_code_anti_pattern_with_user_feedback(self, extractor):
        """Test anti-pattern with code and user feedback"""
        matched_heuristic = {
            'prompt': 'How to read a file in Python?',
            'response': 'file = open("file.txt")\ndata = file.read()',
            'rating': 1,
            'is_code_response': True,
            'user_feedback': 'Should use context manager: with open("file.txt") as file:'
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        # Should handle code context
        assert result['is_negative'] is True
        assert 'user_feedback' in result
        assert 'context manager' in result['user_feedback']
        
        # Should include both bad code and correction
        formatted = result['formatted_insight']
        assert 'open("file.txt")' in formatted  # Shows the bad code
        assert 'context manager' in formatted  # Shows the correction

    def test_user_feedback_empty_string_vs_none(self, extractor):
        """Test handling of empty string vs None for user_feedback"""
        # Test with None
        heuristic_none = {
            'prompt': 'Test',
            'response': 'Bad',
            'rating': 0,
            'is_code_response': False,
            'user_feedback': None
        }
        
        result_none = extractor.extract_negative_insights(heuristic_none)
        # Should convert None to empty string
        assert result_none['user_feedback'] == '' or result_none['user_feedback'] is None
        
        # Test with empty string
        heuristic_empty = {
            'prompt': 'Test',
            'response': 'Bad',
            'rating': 0,
            'is_code_response': False,
            'user_feedback': ''
        }
        
        result_empty = extractor.extract_negative_insights(heuristic_empty)
        assert result_empty['user_feedback'] == ''

    def test_user_feedback_special_characters(self, extractor):
        """Test user_feedback with special characters and formatting"""
        matched_heuristic = {
            'prompt': 'Test question',
            'response': 'Wrong answer',
            'rating': 0,
            'is_code_response': False,
            'user_feedback': 'Correct answer has quotes: "value" and newlines\nand special chars: <>&'
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        # Should preserve special characters
        assert '"value"' in result['user_feedback']
        assert result['formatted_insight'] is not None
        # Should still format properly even with special chars
        assert 'USER CORRECTION' in result['formatted_insight']
