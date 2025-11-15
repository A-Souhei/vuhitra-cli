"""Tests for eternal context management."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.utils.eternal_context import EternalContextManager, EternalContext
except ImportError as e:
    print(f"⚠️  Skipping tests - missing dependencies: {e}")
    print("This is expected if venv is not activated or dependencies not installed")
    sys.exit(0)


def test_eternal_context_dataclass():
    """Test EternalContext dataclass functionality."""
    context = EternalContext(
        label="test-label",
        file_path="/path/to/test.txt",
        content="This is test content.",
        timestamp="2025-01-01T12:00:00"
    )

    assert context.label == "test-label"
    assert context.file_path == "/path/to/test.txt"
    assert context.content == "This is test content."
    assert context.timestamp == "2025-01-01T12:00:00"
    assert len(context.chunks) == 0

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
    assert context_dict['content'] == "This is test content."
    assert context_dict['timestamp'] == "2025-01-01T12:00:00"

    # Test from_dict
    context2 = EternalContext.from_dict(context_dict)
    assert context2.label == context.label
    assert context2.file_path == context.file_path
    assert context2.content == context.content

    # Test to_summary_dict
    summary = context.to_summary_dict()
    assert summary['label'] == "test-label"
    assert summary['content_size'] == size_bytes
    assert summary['is_chunked'] == True
    assert summary['num_chunks'] == 2

    print("✓ EternalContext dataclass tests passed")


def test_eternal_context_manager_disabled():
    """Test EternalContextManager when disabled."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = EternalContextManager(enabled=False, storage_dir=temp_dir)

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

    print("✓ EternalContextManager (disabled) tests passed")


def test_eternal_context_manager_enabled():
    """Test EternalContextManager basic functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = EternalContextManager(enabled=True, storage_dir=temp_dir)

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
        assert "No eternal contexts loaded" in summary

    print("✓ EternalContextManager (enabled) tests passed")


def test_load_file_and_persistence():
    """Test loading files into eternal context and persistence."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = EternalContextManager(enabled=True, storage_dir=temp_dir)

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is test content for eternal context.")
            temp_path = f.name

        try:
            # Test loading file without label (should use filename)
            success, message = manager.load_file(temp_path)
            assert success, f"Failed to load file: {message}"
            assert "✓ Loaded eternal context" in message
            assert "persisted" in message
            assert manager.get_context_count() == 1

            # Verify storage file was created
            storage_files = list(Path(temp_dir).glob('*.json'))
            assert len(storage_files) == 1

            # Test loading same file with different label
            success, message = manager.load_file(temp_path, "custom-label")
            assert success
            assert manager.get_context_count() == 2

            # Verify second storage file was created
            storage_files = list(Path(temp_dir).glob('*.json'))
            assert len(storage_files) == 2

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
            assert "=== Eternal Context" in context_str
            assert "test content" in context_str

            # Test get_summary
            summary = manager.get_summary()
            assert "Loaded eternal contexts:" in summary
            assert "custom-label" in summary
            assert str(temp_dir) in summary  # Storage dir in summary

            # Test persistence: create new manager with same storage dir
            manager2 = EternalContextManager(enabled=True, storage_dir=temp_dir)
            assert manager2.get_context_count() == 2, "Contexts should persist across manager instances"
            ctx2 = manager2.get_context_by_label("custom-label")
            assert ctx2 is not None
            assert ctx2.content == "This is test content for eternal context."

            # Test clear specific context
            removed = manager2.remove_by_label("custom-label")
            assert removed
            assert manager2.get_context_count() == 1

            # Verify storage file was deleted
            storage_files = list(Path(temp_dir).glob('*.json'))
            assert len(storage_files) == 1

            # Test remove non-existent context
            removed = manager2.remove_by_label("non-existent")
            assert not removed

            # Test clear all
            count = manager2.clear_all()
            assert count == 1
            assert manager2.get_context_count() == 0

            # Verify all storage files were deleted
            storage_files = list(Path(temp_dir).glob('*.json'))
            assert len(storage_files) == 0

        finally:
            Path(temp_path).unlink()

    print("✓ Load file and persistence tests passed")


def test_file_validation():
    """Test file validation and error handling."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = EternalContextManager(enabled=True, storage_dir=temp_dir)

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
        success, message = manager.load_file(temp_dir)
        assert not success
        assert "not a file" in message.lower()

    print("✓ File validation tests passed")


def test_max_contexts_limit():
    """Test maximum contexts limit."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = EternalContextManager(enabled=True, storage_dir=temp_dir)
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

            # Verify 3 storage files
            storage_files = list(Path(temp_dir).glob('*.json'))
            assert len(storage_files) == 3

            # Try to load one more (should fail)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write("Extra content")
                temp_files.append(f.name)

            success, message = manager.load_file(temp_files[-1], "label-extra")
            assert not success
            assert "maximum" in message.lower()

            # Storage files should still be 3
            storage_files = list(Path(temp_dir).glob('*.json'))
            assert len(storage_files) == 3

        finally:
            for temp_file in temp_files:
                Path(temp_file).unlink()

    print("✓ Max contexts limit tests passed")


def test_chunking():
    """Test text chunking for large files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = EternalContextManager(enabled=True, storage_dir=temp_dir)
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

            # Test loading large file (may chunk internally)
            success, message = manager.load_file(temp_path, "large-file")
            assert success

            ctx = manager.get_context_by_label("large-file")
            assert ctx is not None

            # Test persistence with chunks
            manager2 = EternalContextManager(enabled=True, storage_dir=temp_dir)
            ctx2 = manager2.get_context_by_label("large-file")
            assert ctx2 is not None
            if ctx.is_chunked():
                assert ctx2.is_chunked(), "Chunked state should persist"
                assert len(ctx2.chunks) == len(ctx.chunks), "Chunk count should persist"

        finally:
            Path(temp_path).unlink()

    print("✓ Chunking tests passed")


def test_get_total_size():
    """Test total size calculation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = EternalContextManager(enabled=True, storage_dir=temp_dir)

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

            # Test persistence of total size
            manager2 = EternalContextManager(enabled=True, storage_dir=temp_dir)
            total_kb2 = manager2.get_total_size_kb()
            assert total_kb2 == total_kb, "Total size should be consistent after reload"

        finally:
            for temp_file in temp_files:
                Path(temp_file).unlink()

    print("✓ Total size calculation tests passed")


def test_reload_from_file():
    """Test reloading an eternal context from its original file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = EternalContextManager(enabled=True, storage_dir=temp_dir)

        # Create a file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Original content")
            temp_path = f.name

        try:
            # Load the file
            success, message = manager.load_file(temp_path, "test-reload")
            assert success

            # Modify the original file
            with open(temp_path, 'w') as f:
                f.write("Modified content")

            # Reload from file
            success, message = manager.reload_from_file("test-reload")
            assert success

            # Verify content was updated
            ctx = manager.get_context_by_label("test-reload")
            assert ctx is not None
            assert ctx.content == "Modified content"

            # Test reload non-existent context
            success, message = manager.reload_from_file("non-existent")
            assert not success

        finally:
            Path(temp_path).unlink()

    print("✓ Reload from file tests passed")


def test_storage_directory_creation():
    """Test that storage directory is created if it doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage_path = Path(temp_dir) / "nested" / "storage"
        assert not storage_path.exists()

        manager = EternalContextManager(enabled=True, storage_dir=str(storage_path))
        assert storage_path.exists(), "Storage directory should be created"
        assert storage_path.is_dir()

    print("✓ Storage directory creation tests passed")


if __name__ == '__main__':
    print("Running eternal context tests...\n")

    test_eternal_context_dataclass()
    test_eternal_context_manager_disabled()
    test_eternal_context_manager_enabled()
    test_load_file_and_persistence()
    test_file_validation()
    test_max_contexts_limit()
    test_chunking()
    test_get_total_size()
    test_reload_from_file()
    test_storage_directory_creation()

    print("\n✅ All eternal context tests passed!")
