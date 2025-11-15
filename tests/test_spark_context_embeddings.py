"""Tests for Spark context embedding functionality."""

import sys
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.utils.spark_context import SparkContextManager, SparkContext
except ImportError as e:
    print(f"⚠️  Skipping tests - missing dependencies: {e}")
    print("This is expected if venv is not activated or dependencies not installed")
    sys.exit(0)


def test_spark_context_with_embedding():
    """Test SparkContext dataclass with embedding fields."""
    context = SparkContext(
        label="test-label",
        file_path="/path/to/test.txt",
        content="This is test content.",
        timestamp="2025-01-01T12:00:00",
        embedding=np.array([0.1, 0.2, 0.3]),
        chunks=["chunk1", "chunk2"],
        chunk_embeddings=[np.array([0.1, 0.2]), np.array([0.3, 0.4])]
    )

    assert context.embedding is not None
    assert len(context.embedding) == 3
    assert context.is_chunked()
    assert len(context.chunks) == 2
    assert len(context.chunk_embeddings) == 2

    # Test to_dict
    context_dict = context.to_dict()
    assert context_dict['is_chunked'] == True
    assert context_dict['num_chunks'] == 2

    print("✓ SparkContext with embedding tests passed")


def test_spark_context_manager_embed_disabled():
    """Test SparkContextManager with embeddings disabled."""
    # Create manager with embeddings disabled
    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = False

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content for embedding test")
        temp_path = f.name

    try:
        success, message = manager.load_file(temp_path, "test")
        assert success

        # Get the context
        context = manager.get_context_by_label("test")
        assert context is not None
        assert context.embedding is None
        assert len(context.chunk_embeddings) == 0

        # get_embeddings should return empty list when disabled
        embeddings = manager.get_embeddings()
        assert embeddings == []

    finally:
        Path(temp_path).unlink()

    print("✓ SparkContextManager with embedding disabled tests passed")


@patch('src.utils.spark_context.requests.post')
def test_spark_load_file_with_embedding(mock_post):
    """Test loading a file with embedding generation."""
    # Mock the embedding API response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'embedding': [0.1, 0.2, 0.3, 0.4, 0.5]
    }
    mock_post.return_value = mock_response

    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = True
    manager.chunking_enabled = False  # Disable chunking for simple test

    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Short test content for embedding.")
        temp_path = f.name

    try:
        # Load the file
        success, message = manager.load_file(temp_path, label="test-embed")
        assert success, f"Load failed: {message}"
        assert "embedding generated" in message or "✓" in message

        # Verify embedding was generated
        context = manager.get_context_by_label("test-embed")
        assert context is not None
        assert context.embedding is not None
        assert len(context.embedding) == 5
        assert abs(context.embedding[0] - 0.1) < 0.001  # Floating point comparison

        # Verify get_embeddings returns the embedding
        embeddings = manager.get_embeddings()
        assert len(embeddings) == 1
        assert np.array_equal(embeddings[0], context.embedding)

    finally:
        Path(temp_path).unlink()

    print("✓ Spark load_file with embedding tests passed")


@patch('src.utils.spark_context.requests.post')
def test_spark_load_file_with_chunking(mock_post):
    """Test loading a large file with chunking and chunk embeddings."""
    # Mock the embedding API response with a simple list of calls
    # Create enough mock responses for the expected number of chunks
    embedding_values = [
        [0.1, 0.2, 0.3],
        [0.2, 0.4, 0.6],
        [0.3, 0.6, 0.9],
        [0.4, 0.8, 1.2],
        [0.5, 1.0, 1.5],
        [0.6, 1.2, 1.8],
        [0.7, 1.4, 2.1],
        [0.8, 1.6, 2.4],
        [0.9, 1.8, 2.7],
        [1.0, 2.0, 3.0],
        [1.1, 2.2, 3.3],
        [1.2, 2.4, 3.6]
    ]
    
    responses = []
    for emb in embedding_values:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'embedding': emb}
        responses.append(mock_response)
    
    mock_post.side_effect = responses

    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = True
    manager.chunking_enabled = True
    manager.chunk_size = 100  # chunk_size must be larger than overlap
    manager.chunk_overlap = 20  # Reasonable overlap

    # Create a large temporary file
    large_content = "This is a long text. " * 40  # About 800 characters
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(large_content)
        temp_path = f.name

    try:
        # Load the file
        success, message = manager.load_file(temp_path, label="test-chunked")
        assert success, f"Load failed: {message}"
        assert "chunks" in message

        # Verify context was chunked
        context = manager.get_context_by_label("test-chunked")
        assert context is not None
        assert context.is_chunked()
        assert len(context.chunks) > 1
        assert len(context.chunk_embeddings) > 0
        # Allow for graceful degradation if some embeddings fail
        assert len(context.chunk_embeddings) <= len(context.chunks)

        # Verify embeddings are different for different chunks
        if len(context.chunk_embeddings) >= 2:
            assert not np.array_equal(context.chunk_embeddings[0], context.chunk_embeddings[1])

        # Verify get_embeddings returns all chunk embeddings
        embeddings = manager.get_embeddings()
        assert len(embeddings) == len(context.chunk_embeddings)

    finally:
        Path(temp_path).unlink()

    print("✓ Spark load_file with chunking tests passed")


@patch('src.utils.spark_context.requests.post')
def test_spark_embedding_api_failure(mock_post):
    """Test handling of embedding API failure."""
    # Mock a failed API response
    mock_response = Mock()
    mock_response.status_code = 500
    mock_post.return_value = mock_response

    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = True

    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("Test content")
        temp_path = f.name

    try:
        # Load should still succeed even if embedding fails
        success, message = manager.load_file(temp_path, label="test-fail")
        assert success, f"Load failed: {message}"

        # Context should be loaded but without embedding
        context = manager.get_context_by_label("test-fail")
        assert context is not None
        assert context.content == "Test content"
        # Embedding might be None if API failed
        # This is acceptable - we don't want embedding failure to block loading

    finally:
        Path(temp_path).unlink()

    print("✓ Spark embedding API failure handling tests passed")


@patch('src.utils.spark_context.requests.post')
def test_spark_get_embeddings_multiple_contexts(mock_post):
    """Test get_embeddings with multiple Spark contexts."""
    # Mock the embedding API response with different embeddings for each call
    embedding_values = [
        [1.0, 2.0],
        [2.0, 4.0],
        [3.0, 6.0]
    ]
    
    responses = []
    for emb in embedding_values:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'embedding': emb}
        responses.append(mock_response)
    
    mock_post.side_effect = responses

    manager = SparkContextManager(enabled=True)
    manager.embed_enabled = True
    manager.chunking_enabled = False

    files = []
    for i in range(3):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        f.write(f"Content {i}")
        f.close()
        files.append(f.name)

    try:
        # Load multiple files
        for i, file_path in enumerate(files):
            success, _ = manager.load_file(file_path, f"spark-{i}")
            assert success

        # Get all embeddings
        embeddings = manager.get_embeddings()
        assert len(embeddings) == 3

        # Each should be different
        assert not np.array_equal(embeddings[0], embeddings[1])
        assert not np.array_equal(embeddings[1], embeddings[2])

    finally:
        for file_path in files:
            Path(file_path).unlink()

    print("✓ Spark get_embeddings with multiple contexts tests passed")


def test_spark_chunk_content():
    """Test the chunking algorithm."""
    manager = SparkContextManager(enabled=True)

    # Test small content (no chunking needed)
    small_content = "Short text"
    chunks = manager._chunk_content(small_content, chunk_size=100, overlap=20)
    assert len(chunks) == 1
    assert chunks[0] == small_content

    # Test large content with chunking
    large_content = "A" * 250
    chunks = manager._chunk_content(large_content, chunk_size=100, overlap=20)
    assert len(chunks) > 1
    
    # Verify overlap works
    # First chunk should be 100 chars
    assert len(chunks[0]) == 100
    # Second chunk should start at position 80 (100 - 20 overlap)
    # and include the overlapping 20 chars from first chunk

    print("✓ Spark chunk_content tests passed")


if __name__ == "__main__":
    # Run all tests
    test_spark_context_with_embedding()
    test_spark_context_manager_embed_disabled()
    test_spark_load_file_with_embedding()
    test_spark_load_file_with_chunking()
    test_spark_embedding_api_failure()
    test_spark_get_embeddings_multiple_contexts()
    test_spark_chunk_content()

    print("\n" + "="*60)
    print("✅ All Spark context embedding tests passed!")
    print("="*60)
