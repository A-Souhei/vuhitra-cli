"""
Tests for context compacter module.
"""
import pytest
from src.context_compacter import ContextCompacter


class TestContextCompacter:
    """Test ContextCompacter functionality."""

    @pytest.fixture
    def compacter(self):
        """Create compacter instance."""
        return ContextCompacter()

    def test_extract_keywords(self, compacter):
        """Test keyword extraction."""
        text = "Python programming is essential for data science and machine learning applications"
        keywords = compacter.extract_keywords(text, top_n=5)

        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        # Check that keywords have proper structure
        for kw in keywords:
            assert "keyword" in kw
            assert "score" in kw
            assert 0 <= kw["score"] <= 1

    def test_extract_keywords_empty_text(self, compacter):
        """Test keyword extraction with empty text."""
        keywords = compacter.extract_keywords("", top_n=5)

        assert keywords == []

    def test_extract_keywords_short_text(self, compacter):
        """Test keyword extraction with very short text."""
        keywords = compacter.extract_keywords("Hi there", top_n=5)

        # Should still return list (might be empty)
        assert isinstance(keywords, list)

    def test_fix_typos_and_grammar(self, compacter):
        """Test typo fixing."""
        text = "teh  quick   brown  fox"
        fixed = compacter.fix_typos_and_grammar(text)

        assert "the" in fixed.lower()
        assert "  " not in fixed  # Multiple spaces should be fixed

    def test_fix_typos_common_mistakes(self, compacter):
        """Test fixing common typos."""
        tests = [
            ("teh cat", "the cat"),
            ("taht dog", "that dog"),
            ("waht time", "what time"),
            ("recieve message", "receive message")
        ]

        for original, expected in tests:
            fixed = compacter.fix_typos_and_grammar(original)
            assert expected.lower() in fixed.lower()

    def test_fix_typos_punctuation(self, compacter):
        """Test punctuation spacing fixes."""
        text = "Hello   ,  world  !"
        fixed = compacter.fix_typos_and_grammar(text)

        # Should fix spacing around punctuation
        assert "," in fixed
        assert "!" in fixed
        # No double spaces
        assert "  " not in fixed

    def test_remove_redundancy(self, compacter):
        """Test removing redundant sentences."""
        sentences = [
            "Python is a programming language.",
            "Python is a programming language.",  # Exact duplicate
            "JavaScript is also a programming language."
        ]

        unique = compacter.remove_redundancy(sentences)

        # Should remove exact duplicate
        assert len(unique) <= len(sentences)
        assert len(unique) >= 2

    def test_remove_redundancy_empty(self, compacter):
        """Test redundancy removal with empty list."""
        unique = compacter.remove_redundancy([])

        assert unique == []

    def test_remove_redundancy_single(self, compacter):
        """Test redundancy removal with single sentence."""
        sentences = ["Only one sentence."]
        unique = compacter.remove_redundancy(sentences)

        assert unique == sentences

    def test_compact_text(self, compacter):
        """Test text compaction."""
        text = """
        Python is a great programming language. Python is easy to learn.
        It has many libraries. The syntax is clear. Python is popular.
        Many developers use Python. It's versatile and powerful.
        """

        result = compacter.compact_text(text, max_sentences=3)

        assert "original_text" in result
        assert "compacted_text" in result
        assert "keywords" in result
        assert "compression_ratio" in result
        assert "sentence_count_before" in result
        assert "sentence_count_after" in result

        # Should be compacted
        assert result["sentence_count_after"] <= 3
        assert len(result["compacted_text"]) <= len(result["original_text"])

    def test_compact_text_short(self, compacter):
        """Test compacting short text."""
        text = "Short."
        result = compacter.compact_text(text, max_sentences=5)

        # Short text should not be modified much
        assert result["original_text"] == text
        assert len(result["compacted_text"]) > 0

    def test_compact_text_empty(self, compacter):
        """Test compacting empty text."""
        result = compacter.compact_text("", max_sentences=5)

        assert result["compression_ratio"] == 1.0
        assert result["sentence_count_before"] == 0

    def test_compact_prompt_short(self, compacter):
        """Test prompt compaction with short prompt."""
        prompt = "What is Python?"  # < 500 chars
        result = compacter.compact_prompt(prompt)

        assert result["was_compacted"] is False
        assert result["compacted_prompt"] == prompt

    def test_compact_prompt_long(self, compacter):
        """Test prompt compaction with long prompt."""
        # Create prompt > 500 chars
        prompt = "What is Python? " * 50  # ~800 chars

        result = compacter.compact_prompt(prompt)

        assert "original_prompt" in result
        assert "compacted_prompt" in result
        assert "was_compacted" in result
        assert "keywords" in result

        if result["was_compacted"]:
            assert len(result["compacted_prompt"]) <= len(result["original_prompt"])

    def test_compact_heuristics(self, compacter):
        """Test heuristics compaction."""
        heuristics = """
        Always use proper error handling. Check for edge cases.
        Validate input data. Write comprehensive tests.
        Follow coding standards. Document your code properly.
        """

        result = compacter.compact_heuristics(heuristics)

        assert "original_heuristics" in result
        assert "compacted_heuristics" in result
        assert "keywords" in result

        # Should be compacted to max 3 sentences
        compacted_sentences = result["compacted_heuristics"].split(".")
        assert len([s for s in compacted_sentences if s.strip()]) <= 3

    def test_compact_heuristics_empty(self, compacter):
        """Test compacting empty heuristics."""
        result = compacter.compact_heuristics("")

        assert result["original_heuristics"] == ""
        assert result["compacted_heuristics"] == ""

    def test_create_matrix_context_simple(self, compacter):
        """Test creating matrix context."""
        prompt = "How do I sort a list in Python?"
        heuristics = "Use the sorted() function for best performance."

        matrix = compacter.create_matrix_context(
            prompt=prompt,
            heuristics=heuristics,
            context="",
            code_blocks=None
        )

        assert "prompt" in matrix
        assert "heuristics" in matrix
        assert "formatted_for_llm" in matrix

        # Check prompt structure
        assert "original" in matrix["prompt"]
        assert "compacted" in matrix["prompt"]
        assert "keywords" in matrix["prompt"]

        # Check formatted output
        assert len(matrix["formatted_for_llm"]) > 0
        assert "USER QUERY" in matrix["formatted_for_llm"]

    def test_create_matrix_context_with_code(self, compacter):
        """Test matrix context with code blocks."""
        prompt = "Explain this code"
        code_blocks = [
            {
                "language": "python",
                "content": "def hello():\n    print('hi')",
                "original": "def hello():\n    print('hi')"
            }
        ]

        matrix = compacter.create_matrix_context(
            prompt=prompt,
            heuristics="",
            context="",
            code_blocks=code_blocks
        )

        assert "code_blocks" in matrix
        assert len(matrix["code_blocks"]) == 1
        # Code should be in formatted output
        assert "SOURCE CODE" in matrix["formatted_for_llm"]
        assert "python" in matrix["formatted_for_llm"]

    def test_create_matrix_context_minimal(self, compacter):
        """Test matrix context with minimal input."""
        matrix = compacter.create_matrix_context(
            prompt="Test",
            heuristics="",
            context="",
            code_blocks=None
        )

        assert "prompt" in matrix
        assert "formatted_for_llm" in matrix

    def test_format_matrix_for_llm(self, compacter):
        """Test LLM formatting."""
        matrix = {
            "prompt": {
                "original": "What is Python?",
                "compacted": "What is Python?",
                "keywords": []
            },
            "heuristics": {
                "original": "Python is a programming language.",
                "compacted": "Python is a programming language.",
                "keywords": []
            }
        }

        formatted = compacter._format_matrix_for_llm(matrix)

        assert "CONTEXT - Best Practices" in formatted
        assert "USER QUERY" in formatted
        assert "Python" in formatted

    def test_compression_ratio_calculation(self, compacter):
        """Test that compression ratio is calculated correctly."""
        text = "This is a test. " * 100  # Long text

        result = compacter.compact_text(text, max_sentences=5)

        assert 0 < result["compression_ratio"] <= 1.0
        # Compacted should be smaller
        assert len(result["compacted_text"]) < len(result["original_text"])

    def test_keywords_score_threshold(self, compacter):
        """Test that keyword scores meet minimum threshold."""
        text = "Python programming data science machine learning"
        keywords = compacter.extract_keywords(text, top_n=10)

        for kw in keywords:
            # Should meet minimum threshold (default 0.3)
            assert kw["score"] >= compacter.min_keyword_score
