"""String utilities module - Example for testing Mirror+Vanisher MCP."""


def reverse_string(text):
    """Reverse a string.

    Args:
        text: String to reverse

    Returns:
        Reversed string
    """
    return text[::-1]


def capitalize_words(text):
    """Capitalize first letter of each word.

    Args:
        text: String to capitalize

    Returns:
        String with capitalized words
    """
    return ' '.join(word.capitalize() for word in text.split())


def count_vowels(text):
    """Count vowels in a string.

    Args:
        text: String to count vowels in

    Returns:
        Number of vowels
    """
    vowels = 'aeiouAEIOU'
    return sum(1 for char in text if char in vowels)


def is_palindrome(text):
    """Check if string is a palindrome.

    Args:
        text: String to check

    Returns:
        True if palindrome, False otherwise
    """
    # Remove spaces and convert to lowercase
    cleaned = ''.join(text.split()).lower()
    return cleaned == cleaned[::-1]
