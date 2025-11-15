"""Tests for path resolver with @ prefix."""

import sys
import tempfile
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.utils.path_resolver import PathResolver, get_path_resolver
except ImportError as e:
    print(f"⚠️  Skipping tests - missing dependencies: {e}")
    print("This is expected if venv is not activated or dependencies not installed")
    sys.exit(0)


def test_is_at_prefix_path():
    """Test detection of @ prefix paths."""
    # Create temp directory for testing
    temp_dir = tempfile.mkdtemp()
    resolver = PathResolver(working_dir=temp_dir)

    # Test @ prefix detection
    assert resolver.is_at_prefix_path("@file.txt")
    assert resolver.is_at_prefix_path("@path/to/file.txt")
    assert resolver.is_at_prefix_path("  @file.txt  ")  # with whitespace

    # Test non-@ paths
    assert not resolver.is_at_prefix_path("file.txt")
    assert not resolver.is_at_prefix_path("/path/to/file.txt")
    assert not resolver.is_at_prefix_path("./file.txt")

    # Cleanup
    Path(temp_dir).rmdir()

    print("✓ is_at_prefix_path tests passed")


def test_resolve_at_path():
    """Test resolving @ prefix paths to actual paths."""
    # Create temp directory with a test file
    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "test.txt"
    test_file.write_text("test content")

    resolver = PathResolver(working_dir=temp_dir)

    try:
        # Test resolving existing file
        success, resolved_path, error = resolver.resolve_at_path("@test.txt")
        assert success, f"Failed to resolve: {error}"
        assert resolved_path == str(test_file)
        assert error == ""

        # Test resolving non-existent file
        success, resolved_path, error = resolver.resolve_at_path("@nonexistent.txt")
        assert not success
        assert "not found" in error.lower()
        assert resolved_path == ""

        # Test path without @ prefix (should fail)
        success, resolved_path, error = resolver.resolve_at_path("test.txt")
        assert not success
        assert "does not start with @" in error

        # Test empty path after @
        success, resolved_path, error = resolver.resolve_at_path("@")
        assert not success
        assert "No path specified" in error

    finally:
        test_file.unlink()
        Path(temp_dir).rmdir()

    print("✓ resolve_at_path tests passed")


def test_resolve_path():
    """Test resolving paths with or without @ prefix."""
    # Create temp directory with a test file
    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "test.txt"
    test_file.write_text("test content")

    resolver = PathResolver(working_dir=temp_dir)

    try:
        # Test @ prefix path
        success, resolved_path, error = resolver.resolve_path("@test.txt")
        assert success
        assert resolved_path == str(test_file)

        # Test regular path (should just return it)
        success, resolved_path, error = resolver.resolve_path("/some/path/file.txt")
        assert success
        assert resolved_path == "/some/path/file.txt"
        assert error == ""

    finally:
        test_file.unlink()
        Path(temp_dir).rmdir()

    print("✓ resolve_path tests passed")


def test_is_directory():
    """Test checking if a path is a directory."""
    # Create temp directory and file
    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "test.txt"
    test_file.write_text("test content")
    test_subdir = Path(temp_dir) / "subdir"
    test_subdir.mkdir()

    resolver = PathResolver(working_dir=temp_dir)

    try:
        # Test directory
        assert resolver.is_directory("@subdir")

        # Test file (not a directory)
        assert not resolver.is_directory("@test.txt")

        # Test non-existent path
        assert not resolver.is_directory("@nonexistent")

    finally:
        test_file.unlink()
        test_subdir.rmdir()
        Path(temp_dir).rmdir()

    print("✓ is_directory tests passed")


def test_is_file():
    """Test checking if a path is a file."""
    # Create temp directory and file
    temp_dir = tempfile.mkdtemp()
    test_file = Path(temp_dir) / "test.txt"
    test_file.write_text("test content")
    test_subdir = Path(temp_dir) / "subdir"
    test_subdir.mkdir()

    resolver = PathResolver(working_dir=temp_dir)

    try:
        # Test file
        assert resolver.is_file("@test.txt")

        # Test directory (not a file)
        assert not resolver.is_file("@subdir")

        # Test non-existent path
        assert not resolver.is_file("@nonexistent")

    finally:
        test_file.unlink()
        test_subdir.rmdir()
        Path(temp_dir).rmdir()

    print("✓ is_file tests passed")


def test_get_directory_files():
    """Test getting all files in a directory."""
    # Create temp directory with files and subdirectories
    temp_dir = tempfile.mkdtemp()

    # Create files
    file1 = Path(temp_dir) / "file1.txt"
    file2 = Path(temp_dir) / "file2.txt"
    file1.write_text("content 1")
    file2.write_text("content 2")

    # Create subdirectory (should not be included in files list)
    subdir = Path(temp_dir) / "subdir"
    subdir.mkdir()

    resolver = PathResolver(working_dir=temp_dir)

    try:
        # Get files in directory
        success, files, error = resolver.get_directory_files("@.")
        assert success, f"Failed: {error}"
        assert len(files) == 2
        assert str(file1) in files
        assert str(file2) in files
        assert str(subdir) not in files  # Directories should not be included

        # Test non-existent directory
        success, files, error = resolver.get_directory_files("@nonexistent")
        assert not success
        assert "not found" in error.lower()

        # Test file path (not a directory)
        success, files, error = resolver.get_directory_files("@file1.txt")
        assert not success
        assert "not a directory" in error.lower()

    finally:
        file1.unlink()
        file2.unlink()
        subdir.rmdir()
        Path(temp_dir).rmdir()

    print("✓ get_directory_files tests passed")


def test_resolve_at_path_with_subdirectory():
    """Test resolving @ paths with subdirectories."""
    # Create temp directory with subdirectory and file
    temp_dir = tempfile.mkdtemp()
    subdir = Path(temp_dir) / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.txt"
    test_file.write_text("test content")

    resolver = PathResolver(working_dir=temp_dir)

    try:
        # Test resolving file in subdirectory
        success, resolved_path, error = resolver.resolve_at_path("@subdir/test.txt")
        assert success, f"Failed to resolve: {error}"
        assert resolved_path == str(test_file)

        # Test resolving subdirectory itself
        success, resolved_path, error = resolver.resolve_at_path("@subdir")
        assert success
        assert resolved_path == str(subdir)

    finally:
        test_file.unlink()
        subdir.rmdir()
        Path(temp_dir).rmdir()

    print("✓ resolve_at_path with subdirectory tests passed")


def test_resolve_hidden_files():
    """Test resolving paths to hidden files (starting with .)."""
    # Create temp directory with hidden file
    temp_dir = tempfile.mkdtemp()
    hidden_file = Path(temp_dir) / ".hidden"
    hidden_file.write_text("hidden content")

    resolver = PathResolver(working_dir=temp_dir)

    try:
        # Test resolving hidden file
        success, resolved_path, error = resolver.resolve_at_path("@.hidden")
        assert success, f"Failed to resolve hidden file: {error}"
        assert resolved_path == str(hidden_file)

    finally:
        hidden_file.unlink()
        Path(temp_dir).rmdir()

    print("✓ resolve hidden files tests passed")


def test_get_path_resolver_singleton():
    """Test the global path resolver instance."""
    # Get resolver with specific working dir
    temp_dir = tempfile.mkdtemp()

    try:
        resolver1 = get_path_resolver(working_dir=temp_dir)
        assert resolver1.working_dir == Path(temp_dir)

        # Get again without specifying working_dir (should return same instance)
        resolver2 = get_path_resolver()
        assert resolver2 is resolver1

        # Get with different working_dir (should create new instance)
        temp_dir2 = tempfile.mkdtemp()
        try:
            resolver3 = get_path_resolver(working_dir=temp_dir2)
            assert resolver3.working_dir == Path(temp_dir2)
        finally:
            Path(temp_dir2).rmdir()

    finally:
        Path(temp_dir).rmdir()

    print("✓ get_path_resolver singleton tests passed")


if __name__ == "__main__":
    # Run all tests
    test_is_at_prefix_path()
    test_resolve_at_path()
    test_resolve_path()
    test_is_directory()
    test_is_file()
    test_get_directory_files()
    test_resolve_at_path_with_subdirectory()
    test_resolve_hidden_files()
    test_get_path_resolver_singleton()

    print("\n" + "="*60)
    print("✅ All path resolver tests passed!")
    print("="*60)
