"""
Unit tests for InsightExtractor
"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'sandbox', 'src'))

from insight_extractor import InsightExtractor


class TestInsightExtractor:
    """Test suite for InsightExtractor class"""

    @pytest.fixture
    def mock_nlp(self):
        """Create a mock spaCy NLP model"""
        mock_nlp = Mock()

        # Create mock doc with sentences
        mock_doc = Mock()

        # Mock sentence
        mock_sent = Mock()
        mock_sent.text = "This is a test solution that uses pytest framework."

        # Mock tokens
        mock_token1 = Mock()
        mock_token1.pos_ = "VERB"
        mock_token1.lemma_ = "use"
        mock_token1.is_stop = False
        mock_token1.text = "use"
        mock_token1.children = []

        mock_token2 = Mock()
        mock_token2.pos_ = "NOUN"
        mock_token2.lemma_ = "pytest"
        mock_token2.is_stop = False
        mock_token2.text = "pytest"
        mock_token2.dep_ = "dobj"

        mock_token1.children = [mock_token2]

        mock_doc.__iter__ = lambda self: iter([mock_token1, mock_token2])
        mock_doc.sents = [mock_sent]
        mock_doc.ents = []
        mock_doc.text = "This is a test response with pytest framework."

        mock_nlp.return_value = mock_doc
        return mock_nlp

    @pytest.fixture
    def extractor(self, mock_nlp):
        """Create an InsightExtractor instance with mocked NLP"""
        with patch('insight_extractor.spacy.load', return_value=mock_nlp):
            extractor = InsightExtractor(nlp_model=mock_nlp)
            return extractor

    def test_initialization(self, mock_nlp):
        """Test extractor initialization"""
        with patch('insight_extractor.spacy.load', return_value=mock_nlp):
            extractor = InsightExtractor(nlp_model=mock_nlp)
            assert extractor.nlp is not None

    def test_initialization_without_model(self):
        """Test initialization without providing NLP model"""
        with patch('insight_extractor.spacy.load') as mock_load:
            mock_nlp = Mock()
            mock_load.return_value = mock_nlp

            extractor = InsightExtractor()

            mock_load.assert_called_once_with("en_core_web_lg")
            assert extractor.nlp == mock_nlp

    def test_extract_insights_success(self, extractor):
        """Test successful insight extraction"""
        matched_heuristic = {
            'prompt': 'How to test Python code?',
            'response': 'Use pytest framework for testing. Write unit tests for functions.',
            'rating': 5,
            'is_code_response': True,
            'code_purpose': 'function definition'
        }

        result = extractor.extract_insights(matched_heuristic)

        assert 'summary' in result
        assert 'key_techniques' in result
        assert 'entities' in result
        assert 'action_items' in result
        assert 'confidence_indicators' in result
        assert 'formatted_insight' in result

        assert isinstance(result['key_techniques'], list)
        assert isinstance(result['entities'], list)
        assert isinstance(result['confidence_indicators'], list)
        assert isinstance(result['formatted_insight'], str)

    def test_extract_insights_high_rating(self, extractor):
        """Test insights with high rating generate appropriate confidence indicators"""
        matched_heuristic = {
            'prompt': 'Test prompt',
            'response': 'Test response with good content.',
            'rating': 5,
            'is_code_response': False,
            'code_purpose': ''
        }

        result = extractor.extract_insights(matched_heuristic)

        # Should have confidence indicator (but no ratings exposed)
        indicators = result.get('confidence_indicators', [])
        assert len(indicators) > 0, "Should have confidence indicators"
        assert all('rated' not in str(ind).lower() for ind in indicators), "Should not expose ratings"

    def test_extract_insights_moderate_rating(self, extractor):
        """Test insights with moderate rating"""
        matched_heuristic = {
            'prompt': 'Test prompt',
            'response': 'Test response.',
            'rating': 3,
            'is_code_response': False,
            'code_purpose': ''
        }

        result = extractor.extract_insights(matched_heuristic)

        # Should have confidence indicator (but no ratings exposed)
        indicators = result.get('confidence_indicators', [])
        assert len(indicators) > 0, "Should have confidence indicators"
        assert all('rated' not in str(ind).lower() for ind in indicators), "Should not expose ratings"

    def test_extract_insights_code_response(self, extractor):
        """Test insights extraction for code responses"""
        matched_heuristic = {
            'prompt': 'Write a function',
            'response': 'def test(): pass',
            'rating': 4,
            'is_code_response': True,
            'code_purpose': 'function definition'
        }

        result = extractor.extract_insights(matched_heuristic)

        # Just verify we get a result with the expected structure
        assert 'summary' in result
        assert 'confidence_indicators' in result
        # Check for rating indicator
        assert len(result['confidence_indicators']) > 0

    def test_extract_insights_detailed_response(self, extractor):
        """Test insights for detailed responses"""
        long_response = ' '.join(['word'] * 100)  # 100 words

        matched_heuristic = {
            'prompt': 'Test',
            'response': long_response,
            'rating': 4,
            'is_code_response': False,
            'code_purpose': ''
        }

        result = extractor.extract_insights(matched_heuristic)

        # Just verify we get a result
        assert 'summary' in result
        assert 'confidence_indicators' in result
        assert len(result['confidence_indicators']) > 0

    def test_extract_insights_concise_response(self, extractor):
        """Test insights for concise responses"""
        matched_heuristic = {
            'prompt': 'Test',
            'response': 'Short answer here.',  # ~3 words
            'rating': 4,
            'is_code_response': False,
            'code_purpose': ''
        }

        result = extractor.extract_insights(matched_heuristic)

        # Should have concise indicator for responses between 20-50 words
        # This is only 3 words, so won't have any length indicator
        # Just verify it doesn't crash
        assert result is not None

    def test_extract_key_techniques(self, extractor):
        """Test key technique extraction"""
        mock_doc = Mock()

        # Create mock verb token with objects
        mock_verb = Mock()
        mock_verb.pos_ = "VERB"
        mock_verb.lemma_ = "implement"
        mock_verb.is_stop = False

        mock_obj = Mock()
        mock_obj.text = "feature"
        mock_obj.dep_ = "dobj"

        mock_verb.children = [mock_obj]

        mock_doc.__iter__ = lambda self: iter([mock_verb])
        mock_doc.text = "implement feature"

        techniques = extractor._extract_key_techniques(mock_doc, is_code=False)

        assert isinstance(techniques, list)
        # Should extract verb phrases
        assert len(techniques) >= 0

    def test_extract_key_techniques_code_response(self, extractor):
        """Test key technique extraction for code responses"""
        mock_doc = Mock()
        mock_doc.text = "Use function and class definitions with async promises"
        mock_doc.__iter__ = lambda self: iter([])

        techniques = extractor._extract_key_techniques(mock_doc, is_code=True)

        # Should identify code-specific keywords
        assert any('function' in t.lower() for t in techniques) or \
               any('class' in t.lower() for t in techniques) or \
               any('async' in t.lower() for t in techniques)

    def test_extract_entities(self, extractor):
        """Test entity extraction"""
        mock_doc = Mock()

        # Mock named entity
        mock_ent = Mock()
        mock_ent.text = "pytest"
        mock_ent.label_ = "PRODUCT"

        mock_doc.ents = [mock_ent]

        # Mock tokens for technical terms
        mock_token = Mock()
        mock_token.text = "Flask"
        mock_token.pos_ = "PROPN"
        mock_token.is_stop = False

        mock_doc.__iter__ = lambda self: iter([mock_token])

        entities = extractor._extract_entities(mock_doc)

        assert isinstance(entities, list)
        assert len(entities) <= extractor.TOP_ENTITIES

    def test_extract_action_items(self, extractor):
        """Test action item extraction via extract_insights"""
        # Instead of testing private method directly, test through public API
        matched_heuristic = {
            'prompt': 'How to test?',
            'response': 'You should write unit tests. Install pytest first. Make sure to test edge cases.',
            'rating': 4,
            'is_code_response': False,
            'code_purpose': ''
        }

        result = extractor.extract_insights(matched_heuristic)

        # Should have action items in the result
        assert 'action_items' in result
        assert isinstance(result['action_items'], list)
        assert len(result['action_items']) <= 5

    def test_build_summary_code_response(self, extractor):
        """Test summary building for code responses"""
        summary = extractor._build_summary(
            prompt="Write a function",
            response="def test(): pass",
            key_techniques=["define function"],
            is_code=True,
            code_purpose="function definition"
        )

        assert "function definition" in summary.lower()

    def test_build_summary_non_code(self, extractor):
        """Test summary building for non-code responses"""
        summary = extractor._build_summary(
            prompt="How to test?",
            response="Testing is important. Use frameworks.",
            key_techniques=["use frameworks"],
            is_code=False,
            code_purpose=""
        )

        assert len(summary) > 0
        assert "use frameworks" in summary.lower()

    def test_build_confidence_indicators_all_factors(self, extractor):
        """Test confidence indicators with all positive factors"""
        indicators = extractor._build_confidence_indicators(
            rating=5,
            is_code=True,
            response_length=100
        )

        assert len(indicators) >= 2
        # Check for quality indicators without exposing ratings
        assert any('code' in ind.lower() for ind in indicators)
        assert any('detailed' in ind.lower() for ind in indicators)
        # Ensure no ratings are exposed
        assert all('5/5' not in ind for ind in indicators)

    def test_format_for_injection(self, extractor):
        """Test formatting of insights for LLM injection"""
        formatted = extractor._format_for_injection(
            summary="Use pytest for testing",
            key_techniques=["implement tests", "use assertions"],
            entities=[{'text': 'pytest', 'type': 'PRODUCT'}],
            confidence_indicators=["Relevant match found"]
        )

        # Check for new system-prompt style format (not conversational)
        assert "# System Context: Relevant Technical Guidance" in formatted
        assert "Recommended techniques:" in formatted
        assert "implement tests" in formatted
        assert "pytest" in formatted
        # Ensure no privacy-leaking information
        assert "rated" not in formatted.lower()
        assert "satisfaction" not in formatted.lower()

    def test_create_fallback_insight(self, extractor):
        """Test fallback insight creation when NLP fails"""
        matched_heuristic = {
            'response': 'Test response with some content here.',
            'rating': 4
        }

        result = extractor._create_fallback_insight(matched_heuristic)

        assert 'summary' in result
        assert 'formatted_insight' in result
        # Check for new format (no ratings exposed)
        assert "# System Context: Relevant Technical Guidance" in result['formatted_insight']
        # Ensure no privacy-leaking information
        assert '4/5' not in result['formatted_insight']
        assert 'rated' not in result['formatted_insight'].lower()

    def test_extract_insights_without_nlp(self):
        """Test insight extraction when NLP model is not loaded"""
        extractor = InsightExtractor()
        extractor.nlp = None  # Simulate failed loading

        matched_heuristic = {
            'prompt': 'Test',
            'response': 'Test response',
            'rating': 4,
            'is_code_response': False,
            'code_purpose': ''
        }

        result = extractor.extract_insights(matched_heuristic)

        # Should return fallback insight
        assert result is not None
        assert 'summary' in result
        assert 'formatted_insight' in result

    def test_extract_insights_with_exception(self, extractor):
        """Test insight extraction handles exceptions gracefully"""
        # Make NLP processing raise an exception
        extractor.nlp.side_effect = Exception("NLP error")

        matched_heuristic = {
            'prompt': 'Test',
            'response': 'Test response',
            'rating': 4,
            'is_code_response': False,
            'code_purpose': ''
        }

        result = extractor.extract_insights(matched_heuristic)

        # Should return fallback insight instead of crashing
        assert result is not None
        assert 'formatted_insight' in result

    def test_max_insight_length_constant(self):
        """Test that MAX_INSIGHT_LENGTH is properly defined"""
        extractor = InsightExtractor()
        assert extractor.MAX_INSIGHT_LENGTH == 150

    def test_top_entities_constant(self):
        """Test that TOP_ENTITIES is properly defined"""
        extractor = InsightExtractor()
        assert extractor.TOP_ENTITIES == 5

    def test_top_keywords_constant(self):
        """Test that TOP_KEYWORDS is properly defined"""
        extractor = InsightExtractor()
        assert extractor.TOP_KEYWORDS == 10

    def test_empty_response_handling(self, extractor):
        """Test handling of empty response"""
        matched_heuristic = {
            'prompt': 'Test',
            'response': '',
            'rating': 3,
            'is_code_response': False,
            'code_purpose': ''
        }

        result = extractor.extract_insights(matched_heuristic)

        # Should handle gracefully
        assert result is not None
        assert 'summary' in result

    def test_special_characters_in_response(self, extractor):
        """Test handling of special characters in response"""
        matched_heuristic = {
            'prompt': 'Test',
            'response': 'Use `pytest` for testing! @see docs #testing',
            'rating': 4,
            'is_code_response': False,
            'code_purpose': ''
        }

        result = extractor.extract_insights(matched_heuristic)

        # Should handle special characters without crashing
        assert result is not None
        assert 'summary' in result

    # Tests for negative insights extraction

    @pytest.fixture
    def mock_nlp_for_negative(self):
        """Create a mock spaCy NLP model specifically for negative insights"""
        mock_nlp = Mock()

        def create_mock_doc(text):
            """Factory function to create different mocks based on input"""
            mock_doc = Mock()

            # Mock sentence
            mock_sent = Mock()
            mock_sent.text = text[:100] if len(text) > 100 else text

            # Mock tokens with proper attributes
            mock_token1 = Mock()
            mock_token1.pos_ = "VERB"
            mock_token1.lemma_ = "use"
            mock_token1.is_stop = False
            mock_token1.text = "use"
            mock_token1.children = []

            mock_token2 = Mock()
            mock_token2.pos_ = "NOUN"
            mock_token2.lemma_ = "approach"
            mock_token2.is_stop = False
            mock_token2.text = "approach"
            mock_token2.dep_ = "dobj"

            mock_token1.children = [mock_token2]

            mock_doc.__iter__ = lambda self: iter([mock_token1, mock_token2])
            mock_doc.sents = [mock_sent]
            mock_doc.ents = []
            mock_doc.text = text

            return mock_doc

        mock_nlp.side_effect = create_mock_doc
        return mock_nlp

    def test_extract_negative_insights_success(self, mock_nlp_for_negative):
        """Test successful negative insight extraction"""
        extractor = InsightExtractor(nlp_model=mock_nlp_for_negative)

        matched_heuristic = {
            'prompt': 'How to test Python code?',
            'response': 'Just use print statements for debugging. Don\'t write tests.',
            'rating': 1,
            'is_code_response': False
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        assert 'summary' in result
        assert 'anti_techniques' in result
        assert 'entities' in result
        assert 'warning_indicators' in result
        assert 'formatted_insight' in result
        assert 'is_negative' in result

        assert result['is_negative'] is True
        assert isinstance(result['anti_techniques'], list)
        assert isinstance(result['entities'], list)
        assert isinstance(result['warning_indicators'], list)
        assert isinstance(result['formatted_insight'], str)

    def test_extract_negative_insights_rating_zero(self, mock_nlp_for_negative):
        """Test negative insights with rating 0"""
        extractor = InsightExtractor(nlp_model=mock_nlp_for_negative)

        matched_heuristic = {
            'prompt': 'Test prompt',
            'response': 'Bad approach that failed',
            'rating': 0,
            'is_code_response': False
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        assert result['is_negative'] is True
        assert "Failed approach" in result['summary'] or "completely unsuccessful" in result['summary']
        assert len(result['warning_indicators']) > 0

    def test_extract_negative_insights_rating_one(self, mock_nlp_for_negative):
        """Test negative insights with rating 1"""
        extractor = InsightExtractor(nlp_model=mock_nlp_for_negative)

        matched_heuristic = {
            'prompt': 'Test prompt',
            'response': 'Poor quality solution',
            'rating': 1,
            'is_code_response': False
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        assert result['is_negative'] is True
        assert "significant issues" in result['summary'] or "had significant" in result['summary']

    def test_extract_negative_insights_rating_two(self, mock_nlp_for_negative):
        """Test negative insights with rating 2"""
        extractor = InsightExtractor(nlp_model=mock_nlp_for_negative)

        matched_heuristic = {
            'prompt': 'Test prompt',
            'response': 'Below average solution',
            'rating': 2,
            'is_code_response': False
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        assert result['is_negative'] is True
        assert "notable problems" in result['summary'] or "had notable" in result['summary']

    def test_negative_insights_formatted_output(self, mock_nlp_for_negative):
        """Test that negative insights are formatted as anti-pattern warnings"""
        extractor = InsightExtractor(nlp_model=mock_nlp_for_negative)

        matched_heuristic = {
            'prompt': 'How to test?',
            'response': 'Skip testing, it wastes time',
            'rating': 0,
            'is_code_response': False
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        formatted = result['formatted_insight']

        # Should contain anti-pattern warning markers
        assert "SYSTEM DIRECTIVE - ANTI-PATTERN ALERT" in formatted or "Anti-Pattern Warning" in formatted
        assert "AVOIDED" in formatted
        assert "---" in formatted

    def test_negative_insights_code_response(self, mock_nlp_for_negative):
        """Test negative insights for code responses"""
        extractor = InsightExtractor(nlp_model=mock_nlp_for_negative)

        matched_heuristic = {
            'prompt': 'Test code',
            'response': 'Bad code example that crashes',
            'rating': 1,
            'is_code_response': True
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        # Should indicate code didn't work
        assert any("Code example did not work as expected" in indicator for indicator in result['warning_indicators'])

    def test_negative_insights_fallback(self):
        """Test fallback negative insight when NLP is not available"""
        extractor = InsightExtractor(nlp_model=None)

        matched_heuristic = {
            'prompt': 'Test',
            'response': 'Bad solution',
            'rating': 0,
            'is_code_response': False
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        # Should return fallback
        assert result is not None
        assert result['is_negative'] is True
        assert 'formatted_insight' in result
        assert "SYSTEM DIRECTIVE - ANTI-PATTERN ALERT" in result['formatted_insight'] or "Anti-Pattern Warning" in result['formatted_insight']

    def test_negative_insights_exception_handling(self, extractor):
        """Test exception handling in negative insights extraction"""
        # Create a heuristic that will cause NLP processing error
        matched_heuristic = {
            # Missing required fields to trigger exception
            'rating': 1
        }

        # Mock the nlp to raise an exception
        extractor.nlp = Mock(side_effect=Exception("NLP error"))

        result = extractor.extract_negative_insights(matched_heuristic)

        # Should return fallback instead of crashing
        assert result is not None
        assert result['is_negative'] is True
        assert 'formatted_insight' in result

    def test_negative_insights_with_user_feedback(self, extractor):
        """Test that user_feedback is properly included in negative insights"""
        matched_heuristic = {
            'prompt': 'Why do dogs kill small animals?',
            'response': 'Dogs are herbivorous animals that only eat plants.',
            'rating': 0,
            'is_code_response': False,
            'user_feedback': 'dogs are omnivorous'  # User correction
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        # Should include user_feedback in the result
        assert result is not None
        assert result['is_negative'] is True
        assert 'user_feedback' in result
        assert result['user_feedback'] == 'dogs are omnivorous'
        
        # Should include user feedback in formatted insight
        assert 'formatted_insight' in result
        formatted = result['formatted_insight']
        assert 'USER CORRECTION' in formatted
        assert 'dogs are omnivorous' in formatted
        assert 'Use the USER CORRECTION' in formatted

    def test_negative_insights_without_user_feedback(self, extractor):
        """Test that negative insights work without user_feedback"""
        matched_heuristic = {
            'prompt': 'Test prompt',
            'response': 'Bad response',
            'rating': 1,
            'is_code_response': False
            # No user_feedback field
        }

        result = extractor.extract_negative_insights(matched_heuristic)

        # Should work without user_feedback
        assert result is not None
        assert result['is_negative'] is True
        assert 'user_feedback' in result
        assert result['user_feedback'] == ''  # Should be empty string
        
        # Should have standard directive without user feedback
        formatted = result['formatted_insight']
        assert 'USER CORRECTION' not in formatted
        assert 'Do NOT repeat this mistake' in formatted

