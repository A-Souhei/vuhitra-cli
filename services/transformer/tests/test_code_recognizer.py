"""
Tests for code recognizer module.
"""
import pytest
from src.code_recognizer import CodeRecognizer


class TestCodeRecognizer:
    """Test CodeRecognizer functionality."""

    @pytest.fixture
    def recognizer(self):
        """Create recognizer instance."""
        return CodeRecognizer()

    def test_detect_python_code(self, recognizer):
        """Test detection of Python code."""
        code = """
def hello_world():
    print("Hello, World!")
    return True
"""
        language = recognizer.detect_code_language(code)
        assert language == "python"

    def test_detect_javascript_code(self, recognizer):
        """Test detection of JavaScript code."""
        code = """
const greeting = () => {
    console.log("Hello!");
};
"""
        language = recognizer.detect_code_language(code)
        assert language == "javascript"

    def test_detect_java_code(self, recognizer):
        """Test detection of Java code."""
        code = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello!");
    }
}
"""
        language = recognizer.detect_code_language(code)
        assert language == "java"

    def test_detect_unknown_language(self, recognizer):
        """Test detection with ambiguous code."""
        text = "This is just regular text"
        language = recognizer.detect_code_language(text)
        assert language == "unknown"

    def test_is_code_block_python(self, recognizer):
        """Test code block detection with Python."""
        code = "def test():\n    return True"
        assert recognizer.is_code_block(code) is True

    def test_is_code_block_markdown(self, recognizer):
        """Test code block detection with markdown."""
        code = "```python\nprint('hello')\n```"
        assert recognizer.is_code_block(code) is True

    def test_is_code_block_regular_text(self, recognizer):
        """Test that regular text is not detected as code."""
        text = "This is a regular sentence about programming."
        assert recognizer.is_code_block(text) is False

    def test_extract_markdown_code_blocks(self, recognizer):
        """Test extraction of markdown code blocks."""
        text = """
Here is some code:
```python
def hello():
    print("hi")
```
And more text.
"""
        blocks = recognizer.extract_code_blocks(text)

        assert len(blocks) > 0
        assert blocks[0]["language"] == "python"
        assert "def hello" in blocks[0]["content"]

    def test_extract_multiple_code_blocks(self, recognizer):
        """Test extraction of multiple code blocks."""
        text = """
```python
print("first")
```

Some text.

```javascript
console.log("second");
```
"""
        blocks = recognizer.extract_code_blocks(text)

        assert len(blocks) == 2
        assert blocks[0]["language"] == "python"
        assert blocks[1]["language"] == "javascript"

    def test_extract_code_blocks_no_language(self, recognizer):
        """Test extraction when language is not specified."""
        text = "```\nsome code\n```"
        blocks = recognizer.extract_code_blocks(text)

        assert len(blocks) > 0
        assert blocks[0]["language"] == "unknown"

    def test_separate_code_and_text_markdown(self, recognizer):
        """Test separation with markdown code blocks."""
        text = """
This is text.
```python
def test():
    pass
```
More text here.
"""
        code_blocks, text_segments = recognizer.separate_code_and_text(text)

        assert len(code_blocks) > 0
        assert len(text_segments) > 0
        # Code should be preserved
        assert "def test" in code_blocks[0]["content"]

    def test_separate_code_and_text_inline(self, recognizer):
        """Test separation with inline code."""
        text = """
Here's a function:
def hello():
    return "world"

And some explanation.
"""
        code_blocks, text_segments = recognizer.separate_code_and_text(text)

        # Should detect some code
        assert isinstance(code_blocks, list)
        assert isinstance(text_segments, list)

    def test_separate_code_and_text_no_code(self, recognizer):
        """Test separation with no code."""
        text = "This is just regular text without any code."
        code_blocks, text_segments = recognizer.separate_code_and_text(text)

        # Might have empty code blocks
        assert isinstance(code_blocks, list)
        # Should have text
        assert len(text_segments) > 0

    def test_identify_file_paths(self, recognizer):
        """Test file path identification."""
        text = "The file is located at /home/user/test.py and also ./config.yaml"
        paths = recognizer.identify_file_paths(text)

        assert isinstance(paths, list)
        # Should find at least one path
        assert len(paths) >= 1

    def test_identify_file_paths_windows(self, recognizer):
        """Test Windows file path identification."""
        text = r"The file is at C:\Users\test\file.txt"
        paths = recognizer.identify_file_paths(text)

        assert isinstance(paths, list)

    def test_identify_file_paths_no_paths(self, recognizer):
        """Test with no file paths."""
        text = "This text has no file paths."
        paths = recognizer.identify_file_paths(text)

        assert isinstance(paths, list)

    def test_code_block_preservation(self, recognizer):
        """Test that code blocks are preserved exactly."""
        original_code = """def calculate(x, y):
    # Important comment
    result = x + y
    return result"""

        text = f"```python\n{original_code}\n```"
        code_blocks, _ = recognizer.separate_code_and_text(text)

        assert len(code_blocks) > 0
        # Code should be preserved exactly
        assert original_code in code_blocks[0]["content"]

    def test_mixed_content_separation(self, recognizer):
        """Test separating mixed code and text content."""
        text = """
Introduction paragraph.

```python
def func1():
    pass
```

Middle paragraph explaining the code.

```javascript
function func2() {}
```

Conclusion paragraph.
"""
        code_blocks, text_segments = recognizer.separate_code_and_text(text)

        assert len(code_blocks) == 2
        assert len(text_segments) >= 3  # Intro, middle, conclusion
        assert code_blocks[0]["language"] == "python"
        assert code_blocks[1]["language"] == "javascript"

    def test_empty_input(self, recognizer):
        """Test with empty input."""
        code_blocks, text_segments = recognizer.separate_code_and_text("")

        assert isinstance(code_blocks, list)
        assert isinstance(text_segments, list)

    def test_code_symbols_detection(self, recognizer):
        """Test detection based on code symbols."""
        code = "const x = (a, b) => { return a + b; };"
        is_code = recognizer.is_code_block(code)

        # Should detect due to symbols and keywords
        assert is_code is True

    def test_language_indicators(self, recognizer):
        """Test that language indicators are comprehensive."""
        assert "python" in recognizer.language_indicators
        assert "javascript" in recognizer.language_indicators
        assert "java" in recognizer.language_indicators
        assert "go" in recognizer.language_indicators

        # Check Python indicators
        assert "def " in recognizer.language_indicators["python"]
        assert "import " in recognizer.language_indicators["python"]

    def test_detect_code_language_case_insensitive(self, recognizer):
        """Test that language detection is case-insensitive."""
        code = "IMPORT SOMETHING\nDEF HELLO():\n    PASS"
        language = recognizer.detect_code_language(code)

        # Should still detect as python
        assert language == "python"
