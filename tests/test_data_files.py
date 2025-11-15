"""Tests using sample data files from data/ directory."""

import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.utils.spark_context import SparkContextManager
    from src.utils.path_resolver import PathResolver
except ImportError as e:
    print(f"⚠️  Skipping tests - missing dependencies: {e}")
    print("This is expected if venv is not activated or dependencies not installed")
    sys.exit(0)


# Get the repository root directory
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"


def test_data_directory_exists():
    """Test that data directory and sample files exist."""
    assert DATA_DIR.exists(), f"Data directory not found at {DATA_DIR}"
    assert DATA_DIR.is_dir(), f"Data path is not a directory: {DATA_DIR}"
    
    # Check README exists
    readme = DATA_DIR / "README.md"
    assert readme.exists(), f"README.md not found in data directory"
    
    # Check subdirectories
    docs_dir = DATA_DIR / "docs"
    examples_dir = DATA_DIR / "examples"
    assert docs_dir.exists(), "docs subdirectory not found"
    assert examples_dir.exists(), "examples subdirectory not found"
    
    print("✓ Data directory structure tests passed")


def test_load_sample_readme():
    """Test loading the sample README.md file."""
    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = False  # Disable for simple test
    
    readme_path = DATA_DIR / "README.md"
    assert readme_path.exists(), f"README.md not found at {readme_path}"
    
    # Load the file
    success, message = manager.load_file(str(readme_path), label="sample_readme")
    assert success, f"Failed to load README.md: {message}"
    
    # Verify it was loaded
    context = manager.get_context_by_label("sample_readme")
    assert context is not None
    assert "Spark Context" in context.content
    assert "Ephemeral Context" in context.content
    assert context.file_path == str(readme_path.absolute())
    
    print("✓ Load sample README tests passed")


def test_load_api_documentation():
    """Test loading API documentation file."""
    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = False
    
    api_doc = DATA_DIR / "docs" / "api.md"
    assert api_doc.exists(), f"api.md not found at {api_doc}"
    
    # Load the file
    success, message = manager.load_file(str(api_doc), label="api_docs")
    assert success, f"Failed to load api.md: {message}"
    
    # Verify content
    context = manager.get_context_by_label("api_docs")
    assert context is not None
    assert "API Documentation" in context.content
    assert "GET /api/v1/users" in context.content
    assert "POST /api/v1/users" in context.content
    
    print("✓ Load API documentation tests passed")


def test_load_coding_standards():
    """Test loading coding standards file."""
    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = False
    
    standards_doc = DATA_DIR / "docs" / "coding_standards.md"
    assert standards_doc.exists(), f"coding_standards.md not found"
    
    # Load the file
    success, message = manager.load_file(str(standards_doc), label="standards")
    assert success, f"Failed to load coding_standards.md: {message}"
    
    # Verify content
    context = manager.get_context_by_label("standards")
    assert context is not None
    assert "Coding Standards" in context.content
    assert "PEP 8" in context.content
    assert "snake_case" in context.content
    
    print("✓ Load coding standards tests passed")


@patch('src.utils.spark_context.requests.post')
def test_load_with_embeddings(mock_post):
    """Test loading sample files with embedding generation."""
    # Mock embedding response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'embedding': [0.1, 0.2, 0.3, 0.4, 0.5]
    }
    mock_post.return_value = mock_response
    
    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = True
    manager.chunking_enabled = False
    
    # Load simple file
    simple_file = DATA_DIR / "examples" / "simple.txt"
    assert simple_file.exists(), "simple.txt not found"
    
    success, message = manager.load_file(str(simple_file), label="simple")
    assert success, f"Failed to load simple.txt: {message}"
    
    # Verify embedding was generated
    context = manager.get_context_by_label("simple")
    assert context is not None
    assert context.embedding is not None
    assert len(context.embedding) == 5
    
    print("✓ Load with embeddings tests passed")


def test_at_prefix_with_data_directory():
    """Test @ prefix resolution for data directory files."""
    # Set working directory to repo root
    path_resolver = PathResolver(working_dir=str(REPO_ROOT))
    
    # Test resolving @ prefix paths
    test_cases = [
        ("@data/README.md", DATA_DIR / "README.md"),
        ("@data/docs/api.md", DATA_DIR / "docs" / "api.md"),
        ("@data/docs/coding_standards.md", DATA_DIR / "docs" / "coding_standards.md"),
    ]
    
    for at_path, expected_path in test_cases:
        success, resolved_path, error = path_resolver.resolve_path(at_path)
        assert success, f"Failed to resolve {at_path}: {error}"
        assert resolved_path == str(expected_path.absolute()), \
            f"Path mismatch for {at_path}: {resolved_path} != {expected_path}"
    
    print("✓ @ prefix with data directory tests passed")


def test_load_multiple_data_files():
    """Test loading multiple sample files."""
    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = False
    
    # Load multiple files
    files_to_load = [
        (DATA_DIR / "README.md", "readme"),
        (DATA_DIR / "docs" / "api.md", "api"),
        (DATA_DIR / "docs" / "configuration.md", "config"),
    ]
    
    for file_path, label in files_to_load:
        if file_path.exists():
            success, message = manager.load_file(str(file_path), label=label)
            assert success, f"Failed to load {file_path.name}: {message}"
    
    # Verify all are loaded
    assert manager.get_count() >= 3
    assert manager.get_context_by_label("readme") is not None
    assert manager.get_context_by_label("api") is not None
    assert manager.get_context_by_label("config") is not None
    
    # Get summary
    summary = manager.get_summary()
    assert "Spark Contexts" in summary
    assert "readme" in summary
    assert "api" in summary
    
    print("✓ Load multiple data files tests passed")


def test_directory_loading_docs():
    """Test loading entire docs directory."""
    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = False
    
    docs_dir = DATA_DIR / "docs"
    assert docs_dir.exists() and docs_dir.is_dir()
    
    # Load directory
    success, message = manager.load_directory(str(docs_dir), label_prefix="doc")
    assert success, f"Failed to load docs directory: {message}"
    
    # Check that files were loaded
    count = manager.get_count()
    assert count > 0, "No files were loaded from docs directory"
    
    # Verify at least one context was created
    all_contexts = manager.get_all_contexts()
    assert len(all_contexts) > 0
    
    # Check that labels have the prefix
    labels = [ctx.label for ctx in all_contexts]
    assert any("doc_" in label for label in labels), \
        f"No labels with 'doc_' prefix found: {labels}"
    
    print("✓ Directory loading tests passed")


def test_context_string_with_data_files():
    """Test context string generation with sample data."""
    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = False
    
    # Load a sample file
    readme_path = DATA_DIR / "README.md"
    if readme_path.exists():
        success, _ = manager.load_file(str(readme_path), label="test_readme")
        assert success
        
        # Get context string
        context_str = manager.get_context_string()
        
        assert "=== Spark Context (In-Memory) ===" in context_str
        assert "--- Spark: test_readme ---" in context_str
        assert "Source:" in context_str
        assert str(readme_path) in context_str
        assert "Content:" in context_str
    
    print("✓ Context string with data files tests passed")


def test_file_sizes():
    """Test that sample files are reasonable sizes."""
    files_to_check = [
        DATA_DIR / "README.md",
        DATA_DIR / "docs" / "api.md",
        DATA_DIR / "docs" / "coding_standards.md",
        DATA_DIR / "docs" / "configuration.md",
    ]
    
    for file_path in files_to_check:
        if file_path.exists():
            size_bytes = file_path.stat().st_size
            size_kb = size_bytes / 1024
            
            # Files should be between 0.1 KB and 10 KB
            assert size_kb > 0.1, f"{file_path.name} is too small ({size_kb:.2f} KB)"
            assert size_kb < 10, f"{file_path.name} is too large ({size_kb:.2f} KB)"
    
    print("✓ File size tests passed")


if __name__ == "__main__":
    # Run all tests
    test_data_directory_exists()
    test_load_sample_readme()
    test_load_api_documentation()
    test_load_coding_standards()
    test_load_with_embeddings()
    test_at_prefix_with_data_directory()
    test_load_multiple_data_files()
    test_directory_loading_docs()
    test_context_string_with_data_files()
    test_file_sizes()
    
    print("\n" + "="*60)
    print("✅ All data file tests passed!")
    print("="*60)
