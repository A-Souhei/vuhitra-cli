"""
InsightExtractor - Extracts actionable insights from matched heuristics.

This module summarizes historical interactions into concise, actionable insights
that can be injected into LLM context to improve response quality.
"""
import logging
from typing import Dict, List, Any
import spacy

# Support both relative imports (for local tests) and absolute imports (for Docker)
try:
    from src.errors_handler.error_handler import get_error_handler
    from heuristics_config_loader import HeuristicsConfigLoader
except ImportError:
    # For tests running from the test directory
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from src.errors_handler.error_handler import get_error_handler
    from heuristics_config_loader import HeuristicsConfigLoader

logger = logging.getLogger(__name__)
error_handler = get_error_handler()


class InsightExtractor:
    """
    Extracts and summarizes insights from matched heuristics.

    Analyzes high-quality historical responses to extract:
    - Key solution patterns
    - Technical approaches
    - Success indicators
    - Relevant techniques
    """

    def __init__(self, nlp_model=None):
        """
        Initialize the insight extractor.

        Args:
            nlp_model: Optional spaCy model (will load if not provided)
        """
        self.nlp = nlp_model

        # Load configuration
        self.config = HeuristicsConfigLoader()
        self.MAX_INSIGHT_LENGTH = self.config.get_max_insight_length()
        self.TOP_ENTITIES = self.config.get_top_entities()
        self.TOP_KEYWORDS = self.config.get_top_keywords()

        # Limit text length for NLP processing to improve performance
        self.MAX_NLP_TEXT_LENGTH = 1000

        if self.nlp is None:
            self._load_spacy_model()

    def _load_spacy_model(self):
        """Load spaCy language model."""
        try:
            self.nlp = spacy.load("en_core_web_lg")
            logger.info("Loaded spaCy model for insight extraction")
        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "load_spacy_model",
                    "component": "insight_extractor"
                }
            )
            self.nlp = None

    def extract_insights(self, matched_heuristic: Dict) -> Dict[str, Any]:
        """
        Extract insights from a matched heuristic.

        Args:
            matched_heuristic: The matched historical interaction document

        Returns:
            Dictionary containing:
                - summary: Concise summary of the solution
                - key_techniques: List of technical approaches identified
                - entities: Important named entities (tools, libraries, etc.)
                - confidence_indicators: Why this is a high-quality match
                - formatted_insight: Ready-to-inject context string
        """
        if not self.nlp:
            logger.warning("spaCy model not loaded, cannot extract insights")
            return self._create_fallback_insight(matched_heuristic)

        try:
            prompt = matched_heuristic.get('prompt', '')
            response = matched_heuristic.get('response', '')
            rating = matched_heuristic.get('rating', 0)
            is_code = matched_heuristic.get('is_code_response', False)
            code_purpose = matched_heuristic.get('code_purpose', '')

            # Limit response text for performance (process only first ~1000 chars)
            # This is sufficient for extracting key insights
            response_text = response[:self.MAX_NLP_TEXT_LENGTH] if len(response) > self.MAX_NLP_TEXT_LENGTH else response

            # Process the response with spaCy
            response_doc = self.nlp(response_text)

            # Extract key components
            key_techniques = self._extract_key_techniques(response_doc, is_code)
            entities = self._extract_entities(response_doc)
            action_items = self._extract_action_items(response_doc)

            # Build summary
            summary = self._build_summary(
                prompt=prompt,
                response=response,
                key_techniques=key_techniques,
                is_code=is_code,
                code_purpose=code_purpose
            )

            # Confidence indicators
            confidence_indicators = self._build_confidence_indicators(
                rating=rating,
                is_code=is_code,
                response_length=len(response.split())
            )

            # Format as injectable context
            formatted_insight = self._format_for_injection(
                summary=summary,
                key_techniques=key_techniques,
                entities=entities,
                confidence_indicators=confidence_indicators
            )

            return {
                'summary': summary,
                'key_techniques': key_techniques,
                'entities': entities,
                'action_items': action_items,
                'confidence_indicators': confidence_indicators,
                'formatted_insight': formatted_insight
            }

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "extract_insights",
                    "has_response": 'response' in matched_heuristic
                }
            )
            return self._create_fallback_insight(matched_heuristic)

    def _extract_key_techniques(self, doc, is_code: bool) -> List[str]:
        """
        Extract key technical approaches and techniques from response.

        Args:
            doc: spaCy Doc object
            is_code: Whether this is a code response

        Returns:
            List of key technique descriptions
        """
        techniques = []

        # Extract verb phrases (action-oriented techniques)
        for token in doc:
            if token.pos_ == 'VERB' and not token.is_stop:
                # Get verb with its direct objects
                verb_phrase = token.lemma_
                objects = [child.text for child in token.children if child.dep_ in ['dobj', 'pobj']]

                if objects:
                    technique = f"{verb_phrase} {' '.join(objects[:2])}"
                    techniques.append(technique)

        # For code responses, identify specific code patterns
        if is_code:
            code_keywords = [
                'function', 'class', 'method', 'variable', 'loop', 'conditional',
                'import', 'module', 'library', 'framework', 'API', 'database',
                'async', 'promise', 'callback', 'decorator', 'interface'
            ]

            for keyword in code_keywords:
                if keyword.lower() in doc.text.lower():
                    techniques.append(f"uses {keyword}")

        # Remove duplicates and limit
        techniques = list(dict.fromkeys(techniques))[:self.TOP_KEYWORDS]

        return techniques

    def _extract_entities(self, doc) -> List[Dict[str, str]]:
        """
        Extract named entities (tools, libraries, technologies).

        Args:
            doc: spaCy Doc object

        Returns:
            List of entity dictionaries with text and label
        """
        entities = []

        # Extract named entities
        for ent in doc.ents:
            if ent.label_ in ['PRODUCT', 'ORG', 'GPE', 'PERSON', 'WORK_OF_ART']:
                entities.append({
                    'text': ent.text,
                    'type': ent.label_
                })

        # Also look for common technical terms (capitalized words)
        for token in doc:
            if len(token.text) > 2 and token.text[0].isupper() and not token.is_stop:
                # Check if it's a potential library/framework/tool name
                if token.pos_ in ['PROPN', 'NOUN']:
                    entities.append({
                        'text': token.text,
                        'type': 'TECH'
                    })

        # Remove duplicates
        seen = set()
        unique_entities = []
        for ent in entities:
            if ent['text'] not in seen:
                seen.add(ent['text'])
                unique_entities.append(ent)

        return unique_entities[:self.TOP_ENTITIES]

    def _extract_action_items(self, doc) -> List[str]:
        """
        Extract actionable steps from the response.

        Args:
            doc: spaCy Doc object

        Returns:
            List of action items
        """
        action_items = []

        # Look for sentences with imperative verbs or instructions
        for sent in doc.sents:
            sent_text = sent.text.strip()

            # Check for imperative patterns
            if len(sent_text) > 10:
                first_token = sent[0]

                # Imperative sentences often start with verbs
                if first_token.pos_ == 'VERB':
                    action_items.append(sent_text)

                # Look for "you should", "you can", "try to", etc.
                elif any(pattern in sent_text.lower() for pattern in [
                    'you should', 'you can', 'you need to', 'try to',
                    'make sure', 'ensure that', 'consider', 'use '
                ]):
                    action_items.append(sent_text)

        return action_items[:5]  # Limit to top 5 actions

    def _build_summary(
        self,
        prompt: str,
        response: str,
        key_techniques: List[str],
        is_code: bool,
        code_purpose: str
    ) -> str:
        """
        Build a concise summary of the solution.

        Args:
            prompt: Original prompt
            response: Response text
            key_techniques: Extracted techniques
            is_code: Whether response contains code
            code_purpose: Purpose of code if applicable

        Returns:
            Summary string
        """
        # Limit text for performance - only need first sentence
        response_text = response[:self.MAX_NLP_TEXT_LENGTH] if len(response) > self.MAX_NLP_TEXT_LENGTH else response

        # Extract first meaningful sentence from response
        doc = self.nlp(response_text)
        sentences = list(doc.sents)

        first_sentence = ""
        if sentences:
            first_sentence = str(sentences[0]).strip()

        # Build summary
        if is_code and code_purpose:
            summary = f"Solution involves {code_purpose}"
        elif first_sentence:
            # Take first sentence, truncate if too long
            summary = first_sentence[:200]
        else:
            summary = "Solution provides technical guidance"

        # Add key technique if available
        if key_techniques:
            summary += f", using {key_techniques[0]}"

        return summary

    def _build_confidence_indicators(
        self,
        rating: int,
        is_code: bool,
        response_length: int
    ) -> List[str]:
        """
        Build confidence indicators for why this is a good match.

        Args:
            rating: User rating (0-5)
            is_code: Whether response is code
            response_length: Number of words in response

        Returns:
            List of confidence indicator strings
        """
        indicators = []

        # Rating-based indicator
        if rating >= 4:
            indicators.append(f"High user satisfaction (rated {rating}/5)")
        elif rating >= 3:
            indicators.append(f"Positive user feedback (rated {rating}/5)")

        # Response quality indicators
        if is_code:
            indicators.append("Contains working code example")

        if response_length > 50:
            indicators.append("Detailed explanation provided")
        elif response_length > 20:
            indicators.append("Concise solution")

        return indicators

    def _format_for_injection(
        self,
        summary: str,
        key_techniques: List[str],
        entities: List[Dict],
        confidence_indicators: List[str]
    ) -> str:
        """
        Format insights as injectable LLM context.

        Args:
            summary: Solution summary
            key_techniques: List of techniques
            entities: List of entities
            confidence_indicators: Confidence indicators

        Returns:
            Formatted string ready for LLM context injection
        """
        lines = ["[RELEVANT CONTEXT FROM SIMILAR PAST INTERACTION]"]
        lines.append(f"Summary: {summary}")

        if key_techniques:
            techniques_str = ", ".join(key_techniques[:3])
            lines.append(f"Approach: {techniques_str}")

        if entities:
            entity_names = [e['text'] for e in entities[:3]]
            lines.append(f"Related tools/technologies: {', '.join(entity_names)}")

        if confidence_indicators:
            lines.append(f"Quality: {confidence_indicators[0]}")

        lines.append("[END CONTEXT]")

        return "\n".join(lines)

    def _create_fallback_insight(self, matched_heuristic: Dict) -> Dict[str, Any]:
        """
        Create a basic insight when full NLP analysis is not available.

        Args:
            matched_heuristic: The matched heuristic document

        Returns:
            Basic insight dictionary
        """
        response = matched_heuristic.get('response', '')
        rating = matched_heuristic.get('rating', 0)

        # Simple extraction without NLP
        summary = response[:200] + "..." if len(response) > 200 else response

        formatted = f"""[RELEVANT CONTEXT FROM SIMILAR PAST INTERACTION]
Summary: High-quality response found (rated {rating}/5)
[END CONTEXT]"""

        return {
            'summary': summary,
            'key_techniques': [],
            'entities': [],
            'action_items': [],
            'confidence_indicators': [f"Rated {rating}/5"],
            'formatted_insight': formatted
        }
