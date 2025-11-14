"""
Context Compacter Module

Uses transformer models to compact and improve context quality while preserving code.
Provides predictable, deterministic compaction to minimize hallucinations.
"""

import re
from typing import Dict, List, Optional
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer


class ContextCompacter:
    """
    Compacts context using transformer models while preserving code blocks.

    Features:
    - Extracts keywords from text
    - Reformulates sentences to fix typos and improve clarity
    - Summarizes verbose text
    - Preserves source code blocks
    - Generates structured matrix context
    """

    def __init__(self):
        """Initialize the context compacter with transformer models."""
        # Use a lightweight sentence transformer for embeddings
        self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

        # KeyBERT for keyword extraction
        self.kw_model = KeyBERT(model=self.sentence_model)

        # Deterministic settings to reduce hallucinations
        self.max_keywords = 10
        self.min_keyword_score = 0.3
        self.redundancy_threshold = 0.7  # For removing similar sentences

    def extract_keywords(self, text: str, top_n: int = None) -> List[Dict[str, float]]:
        """
        Extract keywords from text using KeyBERT.

        Args:
            text: The text to extract keywords from
            top_n: Number of keywords to extract (default: self.max_keywords)

        Returns:
            List of dictionaries with 'keyword' and 'score' keys
        """
        if not text or len(text.strip()) < 10:
            return []

        top_n = top_n or self.max_keywords

        try:
            # Use KeyBERT to extract keywords
            keywords = self.kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),  # Unigrams and bigrams
                stop_words='english',
                top_n=top_n,
                use_maxsum=True,  # Use Max Sum Similarity for diversity
                nr_candidates=20
            )

            # Filter by minimum score
            filtered_keywords = [
                {'keyword': kw, 'score': float(score)}
                for kw, score in keywords
                if score >= self.min_keyword_score
            ]

            return filtered_keywords
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return []

    def fix_typos_and_grammar(self, text: str) -> str:
        """
        Fix common typos and grammar issues.
        Uses rule-based approach for predictability.

        Args:
            text: The text to fix

        Returns:
            Fixed text
        """
        # Common typo corrections
        typo_map = {
            r'\bteh\b': 'the',
            r'\btaht\b': 'that',
            r'\bwaht\b': 'what',
            r'\bwihch\b': 'which',
            r'\brecieve\b': 'receive',
            r'\boccured\b': 'occurred',
            r'\bseperate\b': 'separate',
            r'\bdefinately\b': 'definitely',
        }

        fixed_text = text
        for pattern, replacement in typo_map.items():
            fixed_text = re.sub(pattern, replacement, fixed_text, flags=re.IGNORECASE)

        # Fix multiple spaces
        fixed_text = re.sub(r'\s+', ' ', fixed_text)

        # Fix spacing around punctuation
        fixed_text = re.sub(r'\s+([.,!?;:])', r'\1', fixed_text)
        fixed_text = re.sub(r'([.,!?;:])\s*', r'\1 ', fixed_text)

        # Ensure sentences start with capital letters
        sentences = re.split(r'([.!?]\s+)', fixed_text)
        fixed_sentences = []
        for i, sent in enumerate(sentences):
            if i % 2 == 0 and sent:  # Actual sentence, not separator
                sent = sent.strip()
                if sent:
                    sent = sent[0].upper() + sent[1:]
                fixed_sentences.append(sent)
            else:
                fixed_sentences.append(sent)

        fixed_text = ''.join(fixed_sentences)

        return fixed_text.strip()

    def remove_redundancy(self, sentences: List[str]) -> List[str]:
        """
        Remove redundant sentences using semantic similarity.

        Args:
            sentences: List of sentences

        Returns:
            List of unique sentences
        """
        if len(sentences) <= 1:
            return sentences

        try:
            # Get embeddings for all sentences
            embeddings = self.sentence_model.encode(sentences)

            # Keep track of which sentences to keep
            keep_indices = [0]  # Always keep first sentence

            for i in range(1, len(sentences)):
                # Compare with all kept sentences
                is_unique = True
                for j in keep_indices:
                    # Calculate cosine similarity
                    similarity = embeddings[i] @ embeddings[j] / (
                        (embeddings[i] @ embeddings[i]) ** 0.5 *
                        (embeddings[j] @ embeddings[j]) ** 0.5
                    )

                    if similarity >= self.redundancy_threshold:
                        is_unique = False
                        break

                if is_unique:
                    keep_indices.append(i)

            return [sentences[i] for i in keep_indices]
        except Exception as e:
            print(f"Error removing redundancy: {e}")
            return sentences

    def compact_text(self, text: str, max_sentences: Optional[int] = None) -> Dict[str, any]:
        """
        Compact text by extracting key information.

        Args:
            text: The text to compact
            max_sentences: Maximum number of sentences to keep (optional)

        Returns:
            Dictionary with compacted text and metadata
        """
        if not text or len(text.strip()) < 20:
            return {
                'original_text': text,
                'compacted_text': text,
                'keywords': [],
                'compression_ratio': 1.0,
                'sentence_count_before': 0,
                'sentence_count_after': 0
            }

        # Fix typos and grammar first
        cleaned_text = self.fix_typos_and_grammar(text)

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', cleaned_text)
        original_sentence_count = len(sentences)

        # Remove redundant sentences
        unique_sentences = self.remove_redundancy(sentences)

        # Limit to max sentences if specified
        if max_sentences and len(unique_sentences) > max_sentences:
            # Keep the most important sentences based on keyword density
            sentence_scores = []
            keywords = self.extract_keywords(cleaned_text)
            keyword_set = {kw['keyword'].lower() for kw in keywords}

            for sent in unique_sentences:
                # Score based on keyword matches
                sent_lower = sent.lower()
                score = sum(1 for kw in keyword_set if kw in sent_lower)
                sentence_scores.append((sent, score))

            # Sort by score and keep top sentences
            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            compacted_sentences = [sent for sent, _ in sentence_scores[:max_sentences]]

            # Restore original order
            compacted_sentences = [
                sent for sent in unique_sentences if sent in compacted_sentences
            ]
        else:
            compacted_sentences = unique_sentences

        compacted_text = ' '.join(compacted_sentences)

        # Extract keywords
        keywords = self.extract_keywords(compacted_text)

        return {
            'original_text': text,
            'compacted_text': compacted_text,
            'keywords': keywords,
            'compression_ratio': len(compacted_text) / max(len(text), 1),
            'sentence_count_before': original_sentence_count,
            'sentence_count_after': len(compacted_sentences)
        }

    def compact_prompt(self, prompt: str) -> Dict[str, any]:
        """
        Compact a user prompt if it's too verbose.

        Args:
            prompt: The user's prompt

        Returns:
            Dictionary with compaction results
        """
        # Only compact if prompt is very long (> 500 chars)
        if len(prompt) < 500:
            return {
                'original_prompt': prompt,
                'compacted_prompt': prompt,
                'was_compacted': False,
                'keywords': []
            }

        result = self.compact_text(prompt, max_sentences=5)

        return {
            'original_prompt': prompt,
            'compacted_prompt': result['compacted_text'],
            'was_compacted': True,
            'keywords': result['keywords'],
            'compression_ratio': result['compression_ratio']
        }

    def compact_heuristics(self, heuristics_text: str) -> Dict[str, any]:
        """
        Compact heuristics/context from the sandbox service.

        Args:
            heuristics_text: The heuristics text

        Returns:
            Dictionary with compacted heuristics
        """
        if not heuristics_text or len(heuristics_text.strip()) < 50:
            return {
                'original_heuristics': heuristics_text,
                'compacted_heuristics': heuristics_text,
                'keywords': []
            }

        result = self.compact_text(heuristics_text, max_sentences=3)

        return {
            'original_heuristics': heuristics_text,
            'compacted_heuristics': result['compacted_text'],
            'keywords': result['keywords'],
            'compression_ratio': result['compression_ratio']
        }

    def create_matrix_context(
        self,
        prompt: str,
        heuristics: str = "",
        context: str = "",
        code_blocks: List[Dict] = None
    ) -> Dict[str, any]:
        """
        Create a matrix-style context with all components.

        Args:
            prompt: User's prompt
            heuristics: Heuristics from sandbox
            context: Additional context
            code_blocks: List of code blocks to preserve

        Returns:
            Dictionary with structured matrix context
        """
        # Compact each component
        compacted_prompt = self.compact_prompt(prompt)
        compacted_heuristics = self.compact_heuristics(heuristics) if heuristics else None
        compacted_context = self.compact_text(context) if context else None

        # Build matrix structure
        matrix = {
            'prompt': {
                'original': compacted_prompt['original_prompt'],
                'compacted': compacted_prompt['compacted_prompt'],
                'keywords': compacted_prompt.get('keywords', [])
            }
        }

        if compacted_heuristics:
            matrix['heuristics'] = {
                'original': compacted_heuristics['original_heuristics'],
                'compacted': compacted_heuristics['compacted_heuristics'],
                'keywords': compacted_heuristics.get('keywords', [])
            }

        if compacted_context:
            matrix['context'] = {
                'original': compacted_context['original_text'],
                'compacted': compacted_context['compacted_text'],
                'keywords': compacted_context.get('keywords', [])
            }

        if code_blocks:
            matrix['code_blocks'] = code_blocks

        # Create formatted output for LLM
        formatted_context = self._format_matrix_for_llm(matrix)
        matrix['formatted_for_llm'] = formatted_context

        return matrix

    def _format_matrix_for_llm(self, matrix: Dict) -> str:
        """
        Format the matrix context for LLM consumption.

        Args:
            matrix: The matrix dictionary

        Returns:
            Formatted string for LLM
        """
        parts = []

        # Add heuristics if present
        if 'heuristics' in matrix:
            parts.append(f"[CONTEXT - Best Practices]\n{matrix['heuristics']['compacted']}\n")

        # Add context if present
        if 'context' in matrix:
            parts.append(f"[CONTEXT - Additional Information]\n{matrix['context']['compacted']}\n")

        # Add code blocks if present
        if 'code_blocks' in matrix and matrix['code_blocks']:
            parts.append("[SOURCE CODE - DO NOT MODIFY]")
            for i, block in enumerate(matrix['code_blocks'], 1):
                lang = block.get('language', 'unknown')
                content = block.get('content', block.get('original', ''))
                parts.append(f"Code Block {i} ({lang}):\n```{lang}\n{content}\n```\n")

        # Add the user's query
        parts.append(f"[USER QUERY]\n{matrix['prompt']['compacted']}")

        return '\n'.join(parts)
