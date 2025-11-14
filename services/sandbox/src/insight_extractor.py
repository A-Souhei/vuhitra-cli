"""
InsightExtractor - Extracts actionable insights from matched heuristics.

This module summarizes historical interactions into concise, actionable insights
that can be injected into LLM context to improve response quality.
"""
import logging
from typing import Dict, List, Any
import spacy

# Support both relative imports (for Docker) and absolute imports (for tests)
try:
    from heuristics_config_loader import HeuristicsConfigLoader
except ImportError:
    # For tests running from project root
    from services.sandbox.src.heuristics_config_loader import HeuristicsConfigLoader

try:
    from src.errors_handler.error_handler import get_error_handler
except ImportError:
    # For tests running from project root
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    from src.errors_handler.error_handler import get_error_handler

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

            # Detect perfect match: rating=5 (perfect score)
            is_perfect_match = (rating == 5)

            # Format as injectable context
            formatted_insight = self._format_for_injection(
                summary=summary,
                key_techniques=key_techniques,
                entities=entities,
                confidence_indicators=confidence_indicators,
                matched_response=response,
                rating=rating,
                is_perfect_match=is_perfect_match
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

        Note: Does NOT include ratings to protect user privacy.

        Args:
            rating: User rating (0-5) - used for filtering but not exposed
            is_code: Whether response is code
            response_length: Number of words in response

        Returns:
            List of confidence indicator strings (no ratings exposed)
        """
        indicators = []

        # Quality indicators based on rating (but don't expose the rating itself)
        if rating >= 4:
            indicators.append("High quality match")
        elif rating >= 3:
            indicators.append("Good quality match")

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
        confidence_indicators: List[str],
        matched_response: str = "",
        rating: int = 0,
        is_perfect_match: bool = False
    ) -> str:
        """
        Format insights as injectable LLM context using system-prompt style.

        Args:
            summary: Solution summary
            key_techniques: List of techniques
            entities: List of entities
            confidence_indicators: Confidence indicators
            matched_response: The actual response from the matched heuristic
            rating: User rating of the matched heuristic (0-5)
            is_perfect_match: True if this is a 5-star match with very high confidence

        Returns:
            Formatted string ready for LLM context injection
        """
        lines = []
        lines.append("# System Context: Relevant Technical Guidance")
        lines.append("")

        # For perfect matches (5-star + high confidence), use directive approach
        if is_perfect_match and matched_response:
            lines.append("SYSTEM DIRECTIVE - VERIFIED ANSWER")
            lines.append("")
            lines.append("This exact question has a VERIFIED correct answer:")
            lines.append("")
            lines.append("```")
            lines.append(matched_response)
            lines.append("```")
            lines.append("")
            lines.append("CRITICAL INSTRUCTION:")
            lines.append("- Provide the EXACT answer shown above")
            lines.append("- Do NOT elaborate, explain, or add extra information")
            lines.append("- Do NOT rephrase or reword the answer")
            lines.append("- Copy the verified answer VERBATIM")
            lines.append("---")
            return "\n".join(lines)

        # For non-perfect matches, use the standard approach
        lines.append("Based on analysis of similar technical questions, consider the following approach:")
        lines.append("")

        # Include the actual response from the matched heuristic
        if matched_response:
            # Truncate if too long
            max_response_length = 500
            truncated_response = matched_response[:max_response_length]
            if len(matched_response) > max_response_length:
                truncated_response += "..."

            lines.append("Successful approach from similar question:")
            lines.append("```")
            lines.append(truncated_response)
            lines.append("```")
            lines.append("")

        # Add techniques as recommendations (not as direct quotes)
        if key_techniques:
            lines.append("Recommended techniques:")
            for tech in key_techniques[:3]:
                lines.append(f"  - {tech}")
            lines.append("")

        # Add entities as relevant technologies
        if entities:
            entity_names = [e['text'] for e in entities[:3]]
            lines.append(f"Relevant technologies to consider: {', '.join(entity_names)}")
            lines.append("")

        lines.append("Please provide a comprehensive response that addresses the user's specific question.")
        lines.append("---")

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

        formatted = """# System Context: Relevant Technical Guidance

Based on analysis of similar questions, relevant context has been identified.
Please provide a comprehensive response addressing the user's specific question.
---"""

        return {
            'summary': summary,
            'key_techniques': [],
            'entities': [],
            'action_items': [],
            'confidence_indicators': ["Relevant match found"],
            'formatted_insight': formatted
        }

    def extract_chain_insights(
        self,
        matched_heuristic: Dict,
        chain: List[Dict]
    ) -> Dict[str, Any]:
        """
        Extract insights from a matched heuristic and its parent chain.

        This creates a rich context showing the evolution of solutions,
        with explicit instructions to iterate and improve rather than copy.

        Args:
            matched_heuristic: The primary matched heuristic
            chain: List of parent heuristics (ordered from root to immediate parent)

        Returns:
            Dict[str, Any]: If `chain` is non-empty, returns a dictionary containing all fields from
            `extract_insights()` plus:
                - chain_insights: List of parent insight summaries
                - has_chain: Boolean indicating chain presence (True)
                - formatted_insight: Chain-aware formatting (overwrites standard format)
            If `chain` is empty or an exception occurs, returns the result of `extract_insights()`
            (without the above extra fields).
        """
        if not chain:
            # No chain, use standard insight extraction
            return self.extract_insights(matched_heuristic)

        try:
            # Extract insights from the primary match
            primary_insights = self.extract_insights(matched_heuristic)

            # Extract insights from chain parents
            chain_insights = []
            for parent in chain:
                parent_insight = self.extract_insights(parent)
                chain_insights.append({
                    'rating': parent.get('rating', 0),
                    'summary': parent_insight.get('summary', ''),
                    'key_techniques': parent_insight.get('key_techniques', []),
                    'entities': parent_insight.get('entities', [])
                })

            # Format as chain context with anti-copying instructions
            formatted_chain = self._format_chain_for_injection(
                primary_heuristic=matched_heuristic,
                primary_insights=primary_insights,
                chain_insights=chain_insights
            )

            return {
                **primary_insights,
                'chain_insights': chain_insights,
                'formatted_insight': formatted_chain,
                'has_chain': True
            }

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "extract_chain_insights",
                    "chain_length": len(chain)
                }
            )
            # Fallback to standard extraction
            return self.extract_insights(matched_heuristic)

    def extract_negative_insights(self, matched_heuristic: Dict) -> Dict[str, Any]:
        """
        Extract insights from a negative heuristic (anti-pattern).

        This method formats low-rated heuristics as warnings about approaches to avoid,
        rather than recommendations to follow.

        Args:
            matched_heuristic: The matched historical interaction with low rating

        Returns:
            Dictionary containing:
                - summary: Concise summary of why this approach failed
                - anti_techniques: List of approaches that didn't work
                - entities: Important named entities (tools, libraries that were problematic)
                - warning_indicators: Why this is a low-quality match to avoid
                - formatted_insight: Ready-to-inject context string (as anti-pattern)
                - is_negative: True to indicate this is a negative heuristic
        """
        if not self.nlp:
            logger.warning("spaCy model not loaded, cannot extract negative insights")
            return self._create_fallback_negative_insight(matched_heuristic)

        try:
            prompt = matched_heuristic.get('prompt', '')
            response = matched_heuristic.get('response', '')
            rating = matched_heuristic.get('rating', 0)
            is_code = matched_heuristic.get('is_code_response', False)

            # Limit response text for performance
            response_text = response[:self.MAX_NLP_TEXT_LENGTH] if len(response) > self.MAX_NLP_TEXT_LENGTH else response

            # Process the response with spaCy
            response_doc = self.nlp(response_text)

            # Extract problematic techniques
            anti_techniques = self._extract_key_techniques(response_doc, is_code)
            entities = self._extract_entities(response_doc)

            # Build summary focused on what went wrong
            summary = self._build_negative_summary(
                prompt=prompt,
                response=response,
                anti_techniques=anti_techniques,
                rating=rating
            )

            # Warning indicators instead of confidence indicators
            warning_indicators = self._build_warning_indicators(
                rating=rating,
                is_code=is_code,
                response_length=len(response.split())
            )

            # Format as anti-pattern context
            formatted_insight = self._format_negative_for_injection(
                summary=summary,
                anti_techniques=anti_techniques,
                entities=entities,
                warning_indicators=warning_indicators,
                failed_response=response  # Include the actual failed response
            )

            return {
                'summary': summary,
                'anti_techniques': anti_techniques,
                'entities': entities,
                'warning_indicators': warning_indicators,
                'formatted_insight': formatted_insight,
                'is_negative': True
            }

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "extract_negative_insights",
                    "has_response": 'response' in matched_heuristic
                }
            )
            return self._create_fallback_negative_insight(matched_heuristic)

    def _build_negative_summary(
        self,
        prompt: str,
        response: str,
        anti_techniques: List[str],
        rating: int
    ) -> str:
        """
        Build a concise summary of why this approach was unsuccessful.

        Args:
            prompt: Original prompt
            response: Response text
            anti_techniques: Extracted techniques that didn't work
            rating: User rating (low)

        Returns:
            Summary string focused on what to avoid
        """
        # Limit text for performance
        response_text = response[:self.MAX_NLP_TEXT_LENGTH] if len(response) > self.MAX_NLP_TEXT_LENGTH else response

        summary_parts = []

        # Indicate this was an unsuccessful approach
        if rating == 0:
            summary_parts.append("This approach was completely unsuccessful")
        elif rating == 1:
            summary_parts.append("This approach had significant issues")
        else:  # rating == 2
            summary_parts.append("This approach had notable problems")

        # Add what was tried if available
        if anti_techniques:
            summary_parts.append(f"attempting to use {anti_techniques[0]}")

        return ", ".join(summary_parts)

    def _build_warning_indicators(
        self,
        rating: int,
        is_code: bool,
        response_length: int
    ) -> List[str]:
        """
        Build warning indicators for why this approach should be avoided.

        Args:
            rating: User rating (0-2 for negative heuristics)
            is_code: Whether response is code
            response_length: Number of words in response

        Returns:
            List of warning indicator strings
        """
        indicators = []

        # Quality warnings based on rating
        if rating == 0:
            indicators.append("Failed approach - did not work")
        elif rating == 1:
            indicators.append("Poor quality solution - many issues")
        elif rating == 2:
            indicators.append("Below average solution - has problems")

        # Additional context
        if is_code:
            indicators.append("Code example did not work as expected")

        if response_length < 20:
            indicators.append("Insufficient explanation")

        return indicators

    def _format_negative_for_injection(
        self,
        summary: str,
        anti_techniques: List[str],
        entities: List[Dict],
        warning_indicators: List[str],
        failed_response: str = ""
    ) -> str:
        """
        Format negative insights as anti-pattern warnings for LLM context.

        Args:
            summary: Summary of why approach failed
            anti_techniques: List of techniques to avoid
            entities: List of entities that were problematic
            warning_indicators: Warning indicators
            failed_response: The actual failed response to show as example of what NOT to do

        Returns:
            Formatted string ready for LLM context injection as anti-pattern
        """
        lines = []
        lines.append("# SYSTEM DIRECTIVE - ANTI-PATTERN ALERT")
        lines.append("")
        lines.append("CRITICAL: A similar question was previously answered INCORRECTLY.")
        lines.append(f"Problem: {summary}")
        lines.append("")

        # Show the failed response as an example of what NOT to do
        if failed_response:
            # Truncate if too long
            max_response_length = 300
            truncated_response = failed_response[:max_response_length]
            if len(failed_response) > max_response_length:
                truncated_response += "..."

            lines.append("INCORRECT answer that must be AVOIDED:")
            lines.append("```")
            lines.append(truncated_response)
            lines.append("```")
            lines.append("")
            lines.append("DIRECTIVE: Do NOT repeat this mistake. Provide the factually correct answer.")
            lines.append("")

        # Add techniques as things to avoid
        if anti_techniques:
            lines.append("Failed approaches to avoid:")
            for tech in anti_techniques[:3]:
                lines.append(f"  ✗ {tech}")
            lines.append("")

        # Add entities as technologies to be careful with in this context
        if entities:
            entity_names = [e['text'] for e in entities[:3]]
            lines.append(f"Problematic tools/concepts in this context: {', '.join(entity_names)}")
            lines.append("")

        lines.append("---")
        lines.append("")

        return "\n".join(lines)

    def extract_negative_chain_insights(self, matched_heuristic: Dict, chain: List[Dict]) -> Dict[str, Any]:
        """
        Extract insights from a negative heuristic with its chain of parent failures.

        This shows the complete history of failed attempts for auto-iteration,
        helping the LLM avoid repeating ANY previous mistake.

        Args:
            matched_heuristic: The primary matched negative heuristic
            chain: List of parent negative heuristics (previous failed attempts)

        Returns:
            Dictionary containing:
                - summary: Combined summary of all failures
                - anti_techniques: All failed techniques
                - entities: All problematic entities
                - chain_anti_patterns: List of individual failure summaries
                - formatted_insight: Complete chain-aware anti-pattern context
                - is_negative: True
                - has_chain: True
        """
        if not chain:
            # No chain, use standard negative insight extraction
            return self.extract_negative_insights(matched_heuristic)

        try:
            # Extract insights from the primary match (most recent failure)
            primary_insights = self.extract_negative_insights(matched_heuristic)

            # Extract insights from chain parents (previous failures)
            chain_anti_patterns = []
            for parent in chain:
                parent_insight = self.extract_negative_insights(parent)
                chain_anti_patterns.append({
                    'rating': parent.get('rating', 0),
                    'summary': parent_insight.get('summary', ''),
                    'failed_response': parent.get('response', '')[:200],  # Truncated
                    'anti_techniques': parent_insight.get('anti_techniques', [])
                })

            # Format as complete anti-pattern chain
            formatted_chain = self._format_negative_chain_for_injection(
                primary_heuristic=matched_heuristic,
                primary_insights=primary_insights,
                chain_anti_patterns=chain_anti_patterns
            )

            return {
                **primary_insights,
                'chain_anti_patterns': chain_anti_patterns,
                'formatted_insight': formatted_chain,
                'has_chain': True,
                'is_negative': True
            }

        except Exception as e:
            error_handler.handle_exception(
                e,
                context={
                    "operation": "extract_negative_chain_insights",
                    "chain_length": len(chain)
                }
            )
            # Fallback to standard negative extraction
            return self.extract_negative_insights(matched_heuristic)

    def _format_negative_chain_for_injection(
        self,
        primary_heuristic: Dict,
        primary_insights: Dict,
        chain_anti_patterns: List[Dict]
    ) -> str:
        """
        Format negative chain insights showing complete failure history.

        Args:
            primary_heuristic: Most recent failed attempt
            primary_insights: Insights from primary failure
            chain_anti_patterns: List of previous failure insights

        Returns:
            Formatted string with complete anti-pattern chain
        """
        lines = []
        lines.append("# SYSTEM DIRECTIVE - MULTIPLE ANTI-PATTERN ALERTS")
        lines.append("")
        lines.append(f"CRITICAL: This question has been attempted {len(chain_anti_patterns) + 1} times with FAILURES.")
        lines.append("ALL previous incorrect answers are shown below. Do NOT repeat ANY of these mistakes.")
        lines.append("")

        # Show each failed attempt in reverse chronological order (most recent first)
        attempt_num = len(chain_anti_patterns) + 1

        # Show primary (most recent) failure
        lines.append(f"=== FAILED ATTEMPT #{attempt_num} (MOST RECENT) ===")
        lines.append(f"Problem: {primary_insights.get('summary', 'Unknown issue')}")

        primary_response = primary_heuristic.get('response', '')[:300]
        if primary_response:
            lines.append("INCORRECT answer:")
            lines.append("```")
            lines.append(primary_response)
            if len(primary_heuristic.get('response', '')) > 300:
                lines.append("...")
            lines.append("```")
        lines.append("")

        # Show chain parents (previous failures) in reverse chronological order
        for i, parent in enumerate(reversed(chain_anti_patterns)):
            attempt_num = len(chain_anti_patterns) - i
            lines.append(f"=== FAILED ATTEMPT #{attempt_num} ===")
            lines.append(f"Problem: {parent.get('summary', 'Unknown issue')}")

            if parent.get('failed_response'):
                lines.append("INCORRECT answer:")
                lines.append("```")
                lines.append(parent['failed_response'])
                lines.append("...")
                lines.append("```")
            lines.append("")

        lines.append("=" * 60)
        lines.append("")
        lines.append("DIRECTIVE: You have seen ALL failed attempts above.")
        lines.append("Provide the FACTUALLY CORRECT answer. Do NOT repeat any of these mistakes.")
        lines.append("---")
        lines.append("")

        return "\n".join(lines)

    def _create_fallback_negative_insight(self, matched_heuristic: Dict) -> Dict[str, Any]:
        """
        Create a basic negative insight when full NLP analysis is not available.

        Args:
            matched_heuristic: The matched negative heuristic document

        Returns:
            Basic negative insight dictionary
        """
        formatted = """# SYSTEM DIRECTIVE - ANTI-PATTERN ALERT

CRITICAL: A similar question was previously answered INCORRECTLY.
Provide a factually correct answer to the user's question.
---"""

        return {
            'summary': "Approach with known issues",
            'anti_techniques': [],
            'entities': [],
            'warning_indicators': ["Low quality match"],
            'formatted_insight': formatted,
            'is_negative': True
        }

    def _format_chain_for_injection(
        self,
        primary_heuristic: Dict,
        primary_insights: Dict,
        chain_insights: List[Dict]
    ) -> str:
        """
        Format chain insights as system guidance without revealing feedback system.

        Args:
            primary_heuristic: The primary matched heuristic
            primary_insights: Extracted insights from primary match
            chain_insights: List of insights from parent heuristics

        Returns:
            Formatted string with chain context as system-level guidance
        """
        lines = []

        # Check if primary is a perfect match (rating=5)
        primary_rating = primary_heuristic.get('rating', 0)
        is_perfect_match = (primary_rating == 5)
        primary_response = primary_heuristic.get('response', '')

        # For perfect matches, use simplified directive approach
        if is_perfect_match and primary_response:
            lines.append("SYSTEM DIRECTIVE - VERIFIED ANSWER")
            lines.append("")
            lines.append("This exact question has a VERIFIED correct answer:")
            lines.append("")
            lines.append("```")
            lines.append(primary_response)
            lines.append("```")
            lines.append("")
            lines.append("CRITICAL INSTRUCTION:")
            lines.append("- Provide the EXACT answer shown above")
            lines.append("- Do NOT elaborate, explain, or add extra information")
            lines.append("- Do NOT rephrase or reword the answer")
            lines.append("- Copy the verified answer VERBATIM")
            lines.append("---")
            return "\n".join(lines)

        # For non-perfect matches, show chain context
        lines.append("# System Context: Progressive Technical Solutions")
        lines.append("")
        lines.append("Multiple approaches have been analyzed for similar questions.")
        lines.append("Use these insights to inform your response:")
        lines.append("")

        # Include the actual response from the primary matched heuristic
        if primary_response:
            # Truncate if too long
            max_response_length = 500
            truncated_response = primary_response[:max_response_length]
            if len(primary_response) > max_response_length:
                truncated_response += "..."

            lines.append("Most relevant successful approach:")
            lines.append("```")
            lines.append(truncated_response)
            lines.append("```")
            lines.append("")

        # Collect all unique techniques and technologies from chain
        all_techniques = []
        all_entities = []

        # Add from chain
        for insight in chain_insights:
            all_techniques.extend(insight.get('key_techniques', []))
            all_entities.extend([e['text'] for e in insight.get('entities', [])])

        # Add from primary
        all_techniques.extend(primary_insights.get('key_techniques', []))
        all_entities.extend([e['text'] for e in primary_insights.get('entities', [])])

        # Remove duplicates while preserving order
        seen_techniques = set()
        unique_techniques = []
        for tech in all_techniques:
            if tech not in seen_techniques:
                seen_techniques.add(tech)
                unique_techniques.append(tech)

        seen_entities = set()
        unique_entities = []
        for entity in all_entities:
            if entity not in seen_entities:
                seen_entities.add(entity)
                unique_entities.append(entity)

        # Format as recommendations
        if unique_techniques:
            lines.append("Recommended approaches (ordered by relevance):")
            for i, tech in enumerate(unique_techniques[:5], 1):
                lines.append(f"  {i}. {tech}")
            lines.append("")

        if unique_entities:
            lines.append(f"Relevant technologies: {', '.join(unique_entities[:5])}")
            lines.append("")

        lines.append("Please provide a detailed, comprehensive response addressing the user's specific question.")
        lines.append("---")

        return "\n".join(lines)
