"""
Code Recognition Module

Uses transformers and heuristics to detect and extract code blocks from text.
Ensures source code is preserved without compaction.
"""

import re
from typing import List, Dict, Tuple


class CodeRecognizer:
    """Recognizes and separates code from natural language text."""

    def __init__(self):
        """Initialize the code recognizer with language patterns."""
        # Common code patterns
        self.code_patterns = [
            # Code blocks (markdown, triple backticks)
            r'```[\s\S]*?```',
            # Indented code blocks (8+ spaces or tab+4 spaces to avoid false positives)
            r'^([ ]{8,}|\t[ ]{4,}).*$',
            # Common programming keywords
            r'\b(def|class|import|from|function|const|let|var|public|private|protected|static|void|int|string|bool|return|if|else|for|while|switch|case)\b',
            # Common operators and syntax
            r'[=!<>]+|&&|\|\||->|=>|::|\.\.\.|\+\+|--',
            # Function calls with parentheses
            r'\w+\([^)]*\)',
            # Variable assignments
            r'\w+\s*=\s*[^=]',
            # Semicolons at end of line
            r';$',
            # Curly braces
            r'[{}]',
            # Array/list syntax
            r'\[[^\]]*\]',
        ]

        # Programming language indicators
        self.language_indicators = {
            'python': ['def ', 'import ', 'from ', 'class ', '__init__', 'self.', 'elif ', 'lambda '],
            'javascript': ['function ', 'const ', 'let ', 'var ', '=>', 'console.log', 'require(', 'module.exports'],
            'java': ['public class', 'private ', 'protected ', 'static void', 'System.out'],
            'c++': ['#include', 'std::', 'cout <<', 'cin >>', 'namespace '],
            'go': ['func ', 'package ', 'import (', 'defer ', 'go '],
            'rust': ['fn ', 'let mut', 'impl ', 'trait ', 'pub '],
            'sql': ['SELECT ', 'FROM ', 'WHERE ', 'INSERT INTO', 'UPDATE ', 'DELETE FROM'],
            'yaml': ['---', 'apiVersion:', 'kind:', 'metadata:'],
            'json': ['":', '{', '[', '}', ']'],
        }

        # File path patterns
        self.file_path_pattern = r'(?:\/|\\)?(?:[\w-]+(?:\/|\\))*[\w-]+\.[\w]+(?:\:[\d]+)?'

    def detect_code_language(self, text: str) -> str:
        """
        Detect the programming language of a code snippet.

        Args:
            text: The text to analyze

        Returns:
            Language name or 'unknown'
        """
        text_lower = text.lower()
        scores = {}

        for lang, indicators in self.language_indicators.items():
            score = sum(1 for indicator in indicators if indicator.lower() in text_lower)
            if score > 0:
                scores[lang] = score

        if scores:
            return max(scores, key=scores.get)
        return 'unknown'

    def is_code_block(self, text: str) -> bool:
        """
        Determine if a text block is likely source code.

        Args:
            text: The text to analyze

        Returns:
            True if text appears to be code
        """
        # Check for markdown code blocks
        if re.search(r'```[\s\S]*?```', text):
            return True

        # Check for multiple code indicators
        matches = 0
        for pattern in self.code_patterns:
            if re.search(pattern, text, re.MULTILINE):
                matches += 1
                if matches >= 4:  # Threshold for confidence (increased to reduce false positives)
                    return True

        # Check for language-specific indicators
        for lang, indicators in self.language_indicators.items():
            if sum(1 for indicator in indicators if indicator in text) >= 2:
                return True

        return False

    def extract_code_blocks(self, text: str) -> List[Dict[str, str]]:
        """
        Extract code blocks from text and return them with metadata.

        Args:
            text: The text containing mixed code and natural language

        Returns:
            List of dictionaries with 'content', 'language', 'start', 'end' keys
        """
        code_blocks = []

        # Extract markdown code blocks
        markdown_pattern = r'```(\w*)\n([\s\S]*?)```'
        for match in re.finditer(markdown_pattern, text):
            lang = match.group(1) or 'unknown'
            content = match.group(2)
            code_blocks.append({
                'content': content,
                'language': lang,
                'start': match.start(),
                'end': match.end(),
                'original': match.group(0)
            })

        return code_blocks

    def separate_code_and_text(self, text: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Separate text into code blocks and natural language segments.

        Args:
            text: The mixed content

        Returns:
            Tuple of (code_blocks, text_segments) with position information
        """
        code_blocks = self.extract_code_blocks(text)
        text_segments = []

        # If no markdown code blocks, analyze by lines
        if not code_blocks:
            lines = text.split('\n')
            current_segment = []
            current_type = None  # 'code' or 'text'
            start_line = 0

            for i, line in enumerate(lines):
                is_code = self.is_code_block(line)
                line_type = 'code' if is_code else 'text'

                # Start new segment if type changes
                if current_type is None:
                    current_type = line_type
                    start_line = i

                if line_type != current_type:
                    # Save previous segment
                    content = '\n'.join(current_segment)
                    if current_type == 'code':
                        code_blocks.append({
                            'content': content,
                            'language': self.detect_code_language(content),
                            'start_line': start_line,
                            'end_line': i - 1,
                            'original': content
                        })
                    else:
                        text_segments.append({
                            'content': content,
                            'start_line': start_line,
                            'end_line': i - 1
                        })

                    # Start new segment
                    current_segment = [line]
                    current_type = line_type
                    start_line = i
                else:
                    current_segment.append(line)

            # Add final segment
            if current_segment:
                content = '\n'.join(current_segment)
                if current_type == 'code':
                    code_blocks.append({
                        'content': content,
                        'language': self.detect_code_language(content),
                        'start_line': start_line,
                        'end_line': len(lines) - 1,
                        'original': content
                    })
                else:
                    text_segments.append({
                        'content': content,
                        'start_line': start_line,
                        'end_line': len(lines) - 1
                    })
        else:
            # Extract text between code blocks
            last_end = 0
            for block in sorted(code_blocks, key=lambda x: x['start']):
                if block['start'] > last_end:
                    text_content = text[last_end:block['start']].strip()
                    if text_content:
                        text_segments.append({
                            'content': text_content,
                            'start': last_end,
                            'end': block['start']
                        })
                last_end = block['end']

            # Add remaining text after last code block
            if last_end < len(text):
                text_content = text[last_end:].strip()
                if text_content:
                    text_segments.append({
                        'content': text_content,
                        'start': last_end,
                        'end': len(text)
                    })

        return code_blocks, text_segments

    def identify_file_paths(self, text: str) -> List[str]:
        """
        Extract file paths from text.

        Args:
            text: The text to search

        Returns:
            List of file paths found
        """
        return re.findall(self.file_path_pattern, text)
