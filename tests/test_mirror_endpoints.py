"""
Tests for mirror endpoints (/sync and /revert-sync) in sandbox service.
These tests verify synchronization functionality between host and sandbox mirrors.
"""
import pytest
import requests
import io
import sys
import os

# Add parent directory to path to import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


SANDBOX_BASE_URL = "http://localhost:18001"


def is_container_running():
    """Check if the sandbox container is running and accessible."""
    try:
        response = requests.get(f"{SANDBOX_BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout):
        return False


@pytest.fixture(scope="module", autouse=True)
def check_container():
    """Check if container is running before running tests."""
    if not is_container_running():
        pytest.skip("Sandbox container is not running")


@pytest.fixture(scope="function")
def cleanup():
    """Cleanup fixture to remove all files after each test."""
    yield
    # Clean up after test
    try:
        requests.delete(f"{SANDBOX_BASE_URL}/remove-all", timeout=5)
    except (requests.ConnectionError, requests.Timeout):
        pass


class TestMirrorEndpoints:
    """Test mirror synchronization endpoints in the sandbox container."""

    def test_sync_single_file(self, cleanup):
        """Test syncing a single file to mirror."""
        file_content = b"This is a test file for mirroring"
        files = [('files', ('test.txt', io.BytesIO(file_content), 'text/plain'))]
        data = {'target_name': 'test_mirror'}

        response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )

        assert response.status_code == 200
        result = response.json()
        assert "Synced 1 file(s)" in result["message"]
        assert result["target_name"] == "test_mirror"
        assert "test.txt" in result["synced"]

    def test_sync_multiple_files(self, cleanup):
        """Test syncing multiple files to mirror."""
        files = [
            ('files', ('file1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('file2.txt', io.BytesIO(b"Content 2"), 'text/plain')),
            ('files', ('file3.txt', io.BytesIO(b"Content 3"), 'text/plain'))
        ]
        data = {'target_name': 'multi_mirror'}

        response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )

        assert response.status_code == 200
        result = response.json()
        assert "Synced 3 file(s)" in result["message"]
        assert len(result["synced"]) == 3

    def test_sync_updates_existing_files(self, cleanup):
        """Test that sync updates existing files and deletes orphaned files."""
        # First sync
        files = [
            ('files', ('file1.txt', io.BytesIO(b"Original content 1"), 'text/plain')),
            ('files', ('file2.txt', io.BytesIO(b"Original content 2"), 'text/plain')),
            ('files', ('file3.txt', io.BytesIO(b"Original content 3"), 'text/plain'))
        ]
        data = {'target_name': 'update_mirror'}

        response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )
        assert response.status_code == 200

        # Second sync - update file1, keep file2, remove file3, add file4
        files = [
            ('files', ('file1.txt', io.BytesIO(b"Updated content 1"), 'text/plain')),
            ('files', ('file2.txt', io.BytesIO(b"Original content 2"), 'text/plain')),
            ('files', ('file4.txt', io.BytesIO(b"New content 4"), 'text/plain'))
        ]

        response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result["synced"]) == 3
        assert "file3.txt" in result["deleted"]  # file3 should be deleted

    def test_sync_no_files_provided(self, cleanup):
        """Test sync with no files provided."""
        data = {'target_name': 'empty_mirror'}

        response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            data=data
        )

        assert response.status_code == 400
        assert "No files provided" in response.json()["error"]

    def test_sync_no_target_name(self, cleanup):
        """Test sync without target_name."""
        files = [('files', ('test.txt', io.BytesIO(b"content"), 'text/plain'))]

        response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files
        )

        assert response.status_code == 400
        assert "No target_name provided" in response.json()["error"]

    def test_sync_with_subdirectories(self, cleanup):
        """Test syncing files with subdirectory structure."""
        files = [
            ('files', ('dir1/file1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('dir1/file2.txt', io.BytesIO(b"Content 2"), 'text/plain')),
            ('files', ('dir2/file3.txt', io.BytesIO(b"Content 3"), 'text/plain'))
        ]
        data = {'target_name': 'nested_mirror'}

        response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )

        assert response.status_code == 200
        result = response.json()
        assert len(result["synced"]) == 3

    def test_revert_sync_retrieves_mirror_info(self, cleanup):
        """Test revert-sync endpoint retrieves mirror information."""
        # First, create a mirror with files
        files = [
            ('files', ('file1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('file2.txt', io.BytesIO(b"Content 2"), 'text/plain'))
        ]
        data = {'target_name': 'revert_test'}

        sync_response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )
        assert sync_response.status_code == 200

        # Now test revert-sync
        response = requests.post(
            f"{SANDBOX_BASE_URL}/revert-sync",
            json={'target_name': 'revert_test'}
        )

        assert response.status_code == 200
        result = response.json()
        assert result["target_name"] == "revert_test"
        assert result["file_count"] == 2
        assert len(result["files"]) == 2

        # Check file info structure
        for file_info in result["files"]:
            assert "name" in file_info
            assert "size" in file_info
            assert "modified" in file_info
            assert "is_file" in file_info

    def test_revert_sync_mirror_not_found(self, cleanup):
        """Test revert-sync with non-existent mirror."""
        response = requests.post(
            f"{SANDBOX_BASE_URL}/revert-sync",
            json={'target_name': 'nonexistent_mirror'}
        )

        assert response.status_code == 404
        assert "Mirror not found" in response.json()["error"]

    def test_revert_sync_no_target_name(self, cleanup):
        """Test revert-sync without target_name."""
        response = requests.post(
            f"{SANDBOX_BASE_URL}/revert-sync",
            json={}
        )

        assert response.status_code == 400
        assert "No target_name provided" in response.json()["error"]

    def test_sync_and_revert_sync_workflow(self, cleanup):
        """Test complete workflow: sync to mirror, then revert-sync."""
        # 1. Sync files to mirror
        files = [
            ('files', ('workflow1.txt', io.BytesIO(b"Workflow content 1"), 'text/plain')),
            ('files', ('workflow2.txt', io.BytesIO(b"Workflow content 2"), 'text/plain')),
            ('files', ('subdir/workflow3.txt', io.BytesIO(b"Workflow content 3"), 'text/plain'))
        ]
        data = {'target_name': 'workflow_mirror'}

        sync_response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )
        assert sync_response.status_code == 200

        # 2. Retrieve mirror info via revert-sync
        revert_response = requests.post(
            f"{SANDBOX_BASE_URL}/revert-sync",
            json={'target_name': 'workflow_mirror'}
        )
        assert revert_response.status_code == 200

        result = revert_response.json()
        assert result["file_count"] == 3

        file_names = [f["name"] for f in result["files"]]
        assert "workflow1.txt" in file_names
        assert "workflow2.txt" in file_names
        assert "subdir/workflow3.txt" in file_names or "subdir\\workflow3.txt" in file_names  # OS path separator


class TestMirrorErrorHandling:
    """Test error handling for mirror endpoints."""

    def test_sync_uses_error_handler(self, cleanup):
        """Test that sync endpoint integrates with error handler."""
        # This is validated by the presence of error_handler.handle_exception
        # calls in the implementation. We verify graceful error responses.

        # Invalid request should return proper error
        response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            data={'target_name': 'test'}
        )

        assert response.status_code == 400
        result = response.json()
        assert "error" in result
        # Should NOT expose internal exception details
        assert "Traceback" not in str(result)

    def test_revert_sync_uses_error_handler(self, cleanup):
        """Test that revert-sync endpoint integrates with error handler."""
        # Invalid JSON should be handled gracefully
        response = requests.post(
            f"{SANDBOX_BASE_URL}/revert-sync",
            json={'target_name': 'nonexistent'}
        )

        assert response.status_code == 404
        result = response.json()
        assert "error" in result
        # Should NOT expose internal exception details
        assert "Traceback" not in str(result)
