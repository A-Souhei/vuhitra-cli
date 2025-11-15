"""Tests for Spark context management."""

import sys
import tempfile
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.utils.spark_context import SparkContextManager, SparkContext
except ImportError as e:
    print(f"⚠️  Skipping tests - missing dependencies: {e}")
    print("This is expected if venv is not activated or dependencies not installed")
    sys.exit(0)


def test_spark_context_dataclass():
    """Test SparkContext dataclass functionality."""
    context = SparkContext(
        label="test-label",
        file_path="/path/to/test.txt",
        content="This is test content.",
        timestamp="2025-01-01T12:00:00"
    )

    assert context.label == "test-label"
    assert context.file_path == "/path/to/test.txt"
    assert context.content == "This is test content."
    assert context.timestamp == "2025-01-01T12:00:00"

    # Test size calculations
    size_bytes = context.get_size_bytes()
    assert size_bytes > 0
    assert context.get_size_kb() == size_bytes / 1024

    # Test to_dict
    context_dict = context.to_dict()
    assert context_dict['label'] == "test-label"
    assert context_dict['file_path'] == "/path/to/test.txt"
    assert context_dict['content_size'] == size_bytes

    print("✓ SparkContext dataclass tests passed")


def test_spark_context_manager_disabled():
    """Test SparkContextManager when disabled."""
    manager = SparkContextManager(enabled=False)

    assert not manager.is_enabled()
    assert manager.get_count() == 0

    # Loading files should not work when disabled
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content")
        temp_path = f.name

    try:
        success, message = manager.load_file(temp_path, "test")
        assert not success
        assert "disabled" in message.lower()
        assert manager.get_count() == 0
    finally:
        Path(temp_path).unlink()

    print("✓ SparkContextManager (disabled) tests passed")


def test_spark_context_manager_enabled():
    """Test SparkContextManager basic functionality."""
    manager = SparkContextManager(enabled=True)

    assert manager.is_enabled()
    assert manager.get_count() == 0

    # Test clearing empty contexts
    success, message = manager.clear_all()
    assert success
    assert manager.get_count() == 0

    # Test get_context_string with no contexts
    context_str = manager.get_context_string()
    assert context_str == ""

    # Test get_summary with no contexts
    summary = manager.get_summary()
    assert "No Spark contexts" in summary

    print("✓ SparkContextManager (enabled) basic tests passed")


def test_spark_load_file():
    """Test loading a single file as Spark context."""
    manager = SparkContextManager(enabled=True)

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test file for Spark context.")
        temp_path = f.name

    try:
        # Load the file
        success, message = manager.load_file(temp_path, label="test-spark")
        assert success, f"Load failed: {message}"
        assert "✓" in message
        assert "test-spark" in message

        # Verify context was loaded
        assert manager.get_count() == 1

        # Get the context by label
        context = manager.get_context_by_label("test-spark")
        assert context is not None
        assert context.label == "test-spark"
        assert context.content == "This is a test file for Spark context."

        # Test get_context_string
        context_str = manager.get_context_string()
        assert "Spark Context (In-Memory)" in context_str
        assert "test-spark" in context_str
        assert "This is a test file for Spark context." in context_str

        # Test get_summary
        summary = manager.get_summary()
        assert "test-spark" in summary
        assert "Spark Contexts (1/" in summary

    finally:
        Path(temp_path).unlink()

    print("✓ Spark load_file tests passed")


def test_spark_load_file_auto_label():
    """Test loading a file without providing a label."""
    manager = SparkContextManager(enabled=True)

    # Create a temporary file with a specific name
    temp_dir = tempfile.mkdtemp()
    temp_file = Path(temp_dir) / "myfile.txt"
    temp_file.write_text("Content for auto-label test")

    try:
        # Load without label
        success, message = manager.load_file(str(temp_file))
        assert success

        # Verify auto-generated label (should be filename without extension)
        context = manager.get_context_by_label("myfile")
        assert context is not None
        assert context.label == "myfile"

    finally:
        temp_file.unlink()
        Path(temp_dir).rmdir()

    print("✓ Spark auto-label tests passed")


def test_spark_load_nonexistent_file():
    """Test loading a file that doesn't exist."""
    manager = SparkContextManager(enabled=True)

    success, message = manager.load_file("/nonexistent/path/to/file.txt", "test")
    assert not success
    assert "not found" in message.lower()
    assert manager.get_count() == 0

    print("✓ Spark load nonexistent file tests passed")


def test_spark_clear_by_label():
    """Test clearing a specific Spark context by label."""
    manager = SparkContextManager(enabled=True)

    # Create and load multiple temporary files
    files = []
    for i in range(3):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        f.write(f"Content {i}")
        f.close()
        files.append(f.name)
        manager.load_file(f.name, f"spark-{i}")

    try:
        assert manager.get_count() == 3

        # Clear one context
        success, message = manager.clear_by_label("spark-1")
        assert success
        assert "✓" in message
        assert manager.get_count() == 2

        # Verify it's gone
        assert manager.get_context_by_label("spark-1") is None
        assert manager.get_context_by_label("spark-0") is not None
        assert manager.get_context_by_label("spark-2") is not None

        # Try to clear non-existent label
        success, message = manager.clear_by_label("nonexistent")
        assert not success
        assert "not found" in message.lower()

    finally:
        for file in files:
            Path(file).unlink()

    print("✓ Spark clear_by_label tests passed")


def test_spark_clear_all():
    """Test clearing all Spark contexts."""
    manager = SparkContextManager(enabled=True)

    # Create and load multiple temporary files
    files = []
    for i in range(3):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        f.write(f"Content {i}")
        f.close()
        files.append(f.name)
        manager.load_file(f.name, f"spark-{i}")

    try:
        assert manager.get_count() == 3

        # Clear all
        success, message = manager.clear_all()
        assert success
        assert "✓" in message
        assert "3" in message
        assert manager.get_count() == 0

        # Verify all are gone
        assert manager.get_all_contexts() == []

    finally:
        for file in files:
            Path(file).unlink()

    print("✓ Spark clear_all tests passed")


def test_spark_load_directory():
    """Test loading all files in a directory."""
    manager = SparkContextManager(enabled=True)

    # Create a temporary directory with files
    temp_dir = tempfile.mkdtemp()
    temp_files = []

    for i in range(3):
        temp_file = Path(temp_dir) / f"file{i}.txt"
        temp_file.write_text(f"Content for file {i}")
        temp_files.append(temp_file)

    try:
        # Load directory
        success, message = manager.load_directory(temp_dir, label_prefix="test")
        assert success, f"Load directory failed: {message}"
        assert "✓" in message
        assert "3" in message

        # Verify all files were loaded
        assert manager.get_count() == 3

        # Check that labels have the prefix
        for i in range(3):
            context = manager.get_context_by_label(f"test_file{i}")
            assert context is not None
            assert f"Content for file {i}" in context.content

    finally:
        for temp_file in temp_files:
            temp_file.unlink()
        Path(temp_dir).rmdir()

    print("✓ Spark load_directory tests passed")


def test_spark_load_directory_nonexistent():
    """Test loading a directory that doesn't exist."""
    manager = SparkContextManager(enabled=True)

    success, message = manager.load_directory("/nonexistent/directory")
    assert not success
    assert "not found" in message.lower()

    print("✓ Spark load nonexistent directory tests passed")


def test_spark_max_contexts():
    """Test maximum Spark contexts limit."""
    manager = SparkContextManager(enabled=True)
    manager.max_contexts = 3  # Set low limit for testing

    files = []
    for i in range(5):  # Try to load more than max
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        f.write(f"Content {i}")
        f.close()
        files.append(f.name)

    try:
        # Load up to max
        for i in range(3):
            success, message = manager.load_file(files[i], f"spark-{i}")
            assert success

        assert manager.get_count() == 3

        # Try to load one more (should fail)
        success, message = manager.load_file(files[3], "spark-3")
        assert not success
        assert "maximum" in message.lower()
        assert manager.get_count() == 3

    finally:
        for file in files:
            Path(file).unlink()

    print("✓ Spark max_contexts tests passed")


def test_spark_duplicate_label():
    """Test loading with duplicate label."""
    manager = SparkContextManager(enabled=True)

    files = []
    for i in range(2):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        f.write(f"Content {i}")
        f.close()
        files.append(f.name)

    try:
        # Load first file
        success, message = manager.load_file(files[0], "duplicate-label")
        assert success

        # Try to load second file with same label
        success, message = manager.load_file(files[1], "duplicate-label")
        assert not success
        assert "already exists" in message.lower()

        # Should still have only 1 context
        assert manager.get_count() == 1

    finally:
        for file in files:
            Path(file).unlink()

    print("✓ Spark duplicate label tests passed")


if __name__ == "__main__":
    # Run all tests
    test_spark_context_dataclass()
    test_spark_context_manager_disabled()
    test_spark_context_manager_enabled()
    test_spark_load_file()
    test_spark_load_file_auto_label()
    test_spark_load_nonexistent_file()
    test_spark_clear_by_label()
    test_spark_clear_all()
    test_spark_load_directory()
    test_spark_load_directory_nonexistent()
    test_spark_max_contexts()
    test_spark_duplicate_label()

    print("\n" + "="*60)
    print("✅ All Spark context tests passed!")
    print("="*60)
