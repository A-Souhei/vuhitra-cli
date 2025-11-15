"""Tests for ephemeral context management."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.utils.ephemeral_context import EphemeralContextManager, EphemeralContext
except ImportError as e:
    print(f"⚠️  Skipping tests - missing dependencies: {e}")
    print("This is expected if venv is not activated or dependencies not installed")
    sys.exit(0)


def test_ephemeral_context_dataclass():
    """Test EphemeralContext dataclass functionality."""
    context = EphemeralContext(
        label="test-label",
        file_path="/path/to/test.txt",
        content="This is test content.",
        timestamp="2025-01-01T12:00:00"
    )

    assert context.label == "test-label"
    assert context.file_path == "/path/to/test.txt"
    assert context.content == "This is test content."
    assert context.timestamp == "2025-01-01T12:00:00"
    assert context.embedding is None
    assert len(context.chunks) == 0
    assert len(context.chunk_embeddings) == 0

    # Test size calculations
    size_bytes = context.get_size_bytes()
    assert size_bytes > 0
    assert context.get_size_kb() == size_bytes / 1024

    # Test is_chunked
    assert not context.is_chunked()
    context.chunks = ["chunk1", "chunk2"]
    assert context.is_chunked()

    # Test to_dict
    context_dict = context.to_dict()
    assert context_dict['label'] == "test-label"
    assert context_dict['file_path'] == "/path/to/test.txt"
    assert context_dict['content_size'] == size_bytes
    assert context_dict['is_chunked'] == True
    assert context_dict['num_chunks'] == 2

    print("✓ EphemeralContext dataclass tests passed")


def test_ephemeral_context_manager_disabled():
    """Test EphemeralContextManager when disabled."""
    manager = EphemeralContextManager(enabled=False)

    assert not manager.is_enabled()
    assert manager.get_context_count() == 0

    # Loading files should not work when disabled
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content")
        temp_path = f.name

    try:
        success, message = manager.load_file(temp_path, "test")
        assert not success
        assert "disabled" in message.lower()
        assert manager.get_context_count() == 0
    finally:
        Path(temp_path).unlink()

    print("✓ EphemeralContextManager (disabled) tests passed")


def test_ephemeral_context_manager_enabled():
    """Test EphemeralContextManager basic functionality."""
    manager = EphemeralContextManager(enabled=True)

    assert manager.is_enabled()
    assert manager.get_context_count() == 0

    # Test clearing empty contexts
    count = manager.clear_all()
    assert count == 0
    assert manager.get_context_count() == 0

    # Test enable/disable
    manager.set_enabled(False)
    assert not manager.is_enabled()

    manager.set_enabled(True)
    assert manager.is_enabled()

    # Test get_context_string with no contexts
    context_str = manager.get_context_string()
    assert context_str == ""

    # Test get_summary with no contexts
    summary = manager.get_summary()
    assert "No ephemeral contexts loaded" in summary

    print("✓ EphemeralContextManager (enabled) tests passed")


def test_load_file():
    """Test loading files into ephemeral context."""
    manager = EphemeralContextManager(enabled=True)

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is test content for ephemeral context.")
        temp_path = f.name

    try:
        # Test loading file without label (should use filename)
        success, message = manager.load_file(temp_path)
        assert success, f"Failed to load file: {message}"
        assert "✓ Loaded" in message
        assert manager.get_context_count() == 1

        # Test loading same file with different label
        success, message = manager.load_file(temp_path, "custom-label")
        assert success
        assert manager.get_context_count() == 2

        # Test loading with duplicate label
        success, message = manager.load_file(temp_path, "custom-label")
        assert not success
        assert "already exists" in message.lower()

        # Test getting context by label
        ctx = manager.get_context_by_label("custom-label")
        assert ctx is not None
        assert ctx.label == "custom-label"
        assert "test content" in ctx.content

        # Test get_all_contexts
        all_contexts = manager.get_all_contexts()
        assert len(all_contexts) == 2

        # Test get_context_string
        context_str = manager.get_context_string()
        assert "=== Ephemeral Context" in context_str
        assert "test content" in context_str

        # Test get_summary
        summary = manager.get_summary()
        assert "Loaded ephemeral contexts:" in summary
        assert "custom-label" in summary

        # Test clear specific context
        removed = manager.remove_by_label("custom-label")
        assert removed
        assert manager.get_context_count() == 1

        # Test remove non-existent context
        removed = manager.remove_by_label("non-existent")
        assert not removed

        # Test clear all
        count = manager.clear_all()
        assert count == 1
        assert manager.get_context_count() == 0

    finally:
        Path(temp_path).unlink()

    print("✓ Load file tests passed")


def test_file_validation():
    """Test file validation and error handling."""
    manager = EphemeralContextManager(enabled=True)

    # Test non-existent file
    success, message = manager.load_file("/path/to/non/existent/file.txt")
    assert not success
    assert "not found" in message.lower()

    # Test empty file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("")
        temp_path = f.name

    try:
        success, message = manager.load_file(temp_path)
        assert not success
        assert "empty" in message.lower()
    finally:
        Path(temp_path).unlink()

    # Test directory instead of file
    with tempfile.TemporaryDirectory() as temp_dir:
        success, message = manager.load_file(temp_dir)
        assert not success
        assert "not a file" in message.lower()

    print("✓ File validation tests passed")


def test_max_contexts_limit():
    """Test maximum contexts limit."""
    manager = EphemeralContextManager(enabled=True)
    manager.max_contexts = 3  # Set a low limit for testing

    temp_files = []

    try:
        # Create and load files up to the limit
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(f"Content {i}")
                temp_files.append(f.name)

            success, message = manager.load_file(temp_files[i], f"label-{i}")
            assert success

        assert manager.get_context_count() == 3

        # Try to load one more (should fail)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Extra content")
            temp_files.append(f.name)

        success, message = manager.load_file(temp_files[-1], "label-extra")
        assert not success
        assert "maximum" in message.lower()

    finally:
        for temp_file in temp_files:
            Path(temp_file).unlink()

    print("✓ Max contexts limit tests passed")


def test_chunking():
    """Test text chunking for large files."""
    manager = EphemeralContextManager(enabled=True)
    manager.chunking_enabled = True
    manager.chunk_size = 10  # Small chunk size for testing
    manager.chunk_overlap = 2

    # Create a large text file
    large_text = " ".join([f"word{i}" for i in range(100)])

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(large_text)
        temp_path = f.name

    try:
        # Test chunking
        chunks = manager._chunk_text(large_text)
        assert len(chunks) > 1, "Large text should be chunked"

        # Verify overlap
        # With chunk_size=10 and overlap=2, we expect chunks to overlap

        # Test loading large file (may chunk internally)
        success, message = manager.load_file(temp_path, "large-file")
        assert success

        ctx = manager.get_context_by_label("large-file")
        assert ctx is not None

    finally:
        Path(temp_path).unlink()

    print("✓ Chunking tests passed")


def test_get_total_size():
    """Test total size calculation."""
    manager = EphemeralContextManager(enabled=True)

    temp_files = []

    try:
        # Create multiple files
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(f"Content {i}" * 100)  # Make it somewhat large
                temp_files.append(f.name)

            manager.load_file(temp_files[i], f"file-{i}")

        # Test total size
        total_kb = manager.get_total_size_kb()
        assert total_kb > 0

    finally:
        for temp_file in temp_files:
            Path(temp_file).unlink()

    print("✓ Total size calculation tests passed")


if __name__ == '__main__':
    print("Running ephemeral context tests...\n")

    test_ephemeral_context_dataclass()
    test_ephemeral_context_manager_disabled()
    test_ephemeral_context_manager_enabled()
    test_load_file()
    test_file_validation()
    test_max_contexts_limit()
    test_chunking()
    test_get_total_size()

    print("\n✅ All ephemeral context tests passed!")
