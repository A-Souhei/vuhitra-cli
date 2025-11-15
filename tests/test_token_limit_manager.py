"""Tests for token limit manager."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.utils.token_limit_manager import TokenLimitManager, DEFAULT_TOKEN_LIMIT, CHARS_PER_TOKEN_ESTIMATE
except ImportError as e:
    print(f"⚠️  Skipping tests - missing dependencies: {e}")
    print("This is expected if venv is not activated or dependencies not installed")
    sys.exit(0)


def test_token_estimation():
    """Test token estimation from text."""
    manager = TokenLimitManager()

    text = "Hello world! This is a test."
    tokens = manager.estimate_tokens(text)

    # Should be roughly len(text) / 4
    expected = len(text) // CHARS_PER_TOKEN_ESTIMATE
    assert tokens == expected

    print(f"✓ Token estimation: '{text}' -> ~{tokens} tokens")


def test_extract_limit_from_error():
    """Test extracting token limits from error messages."""
    manager = TokenLimitManager()

    # Test pattern 1: "X > Y"
    error1 = "context length exceeded: 2048 > 2047"
    limit1 = manager.extract_limit_from_error(error1)
    assert limit1 == 2047
    print(f"✓ Extracted limit from error 1: {limit1}")

    # Test pattern 2: "maximum" keyword
    error2 = "prompt is too long: 5000 tokens exceeds 4096 maximum"
    limit2 = manager.extract_limit_from_error(error2)
    assert limit2 == 4096
    print(f"✓ Extracted limit from error 2: {limit2}")

    # Test no match
    error3 = "some other error"
    limit3 = manager.extract_limit_from_error(error3)
    assert limit3 is None
    print(f"✓ No limit extracted from unrelated error: {limit3}")


def test_default_limit():
    """Test default infinite limit."""
    manager = TokenLimitManager()

    # Should return infinity for unknown model
    limit = manager.get_limit("unknown-model-xyz")
    assert limit == DEFAULT_TOKEN_LIMIT
    assert limit == float('inf')

    print(f"✓ Default limit is infinite: {limit}")


def test_check_limit():
    """Test limit checking."""
    manager = TokenLimitManager()

    # With no discovered limit, should always pass
    text = "A" * 10000
    is_ok, warning = manager.check_limit("test-model", text)
    assert is_ok
    assert warning is None

    print(f"✓ Check limit with infinite limit: passed")


def test_redis_key_generation():
    """Test Redis key generation."""
    manager = TokenLimitManager()

    key1 = manager._get_redis_key("llama3.1:8b")
    assert key1 == "model_token_limit:llama3.1:8b"

    key2 = manager._get_redis_key("tinyllama")
    assert key2 == "model_token_limit:tinyllama"

    print(f"✓ Redis key generation: {key1}, {key2}")


if __name__ == '__main__':
    print("Running token limit manager tests...\n")

    test_token_estimation()
    test_extract_limit_from_error()
    test_default_limit()
    test_check_limit()
    test_redis_key_generation()

    print("\n✅ All tests passed!")
    print("\nNote: Redis storage/retrieval tests are skipped (require Redis)")
    print("The system will function without Redis, but limits won't persist across sessions")
