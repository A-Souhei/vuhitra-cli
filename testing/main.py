"""Main module - Example application for testing Mirror+Vanisher MCP."""

from calculator import add, subtract, multiply, divide
from string_utils import reverse_string, capitalize_words, count_vowels, is_palindrome


def main():
    """Main function demonstrating the calculator and string utilities."""
    print("=== Calculator Demo ===")
    print(f"10 + 5 = {add(10, 5)}")
    print(f"10 - 5 = {subtract(10, 5)}")
    print(f"10 * 5 = {multiply(10, 5)}")
    print(f"10 / 5 = {divide(10, 5)}")

    print("\n=== String Utilities Demo ===")
    test_string = "hello world"
    print(f"Original: {test_string}")
    print(f"Reversed: {reverse_string(test_string)}")
    print(f"Capitalized: {capitalize_words(test_string)}")
    print(f"Vowel count: {count_vowels(test_string)}")

    palindrome = "A man a plan a canal Panama"
    print(f"\n'{palindrome}' is palindrome: {is_palindrome(palindrome)}")


if __name__ == "__main__":
    main()
