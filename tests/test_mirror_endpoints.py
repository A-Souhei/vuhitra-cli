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


class TestMirrorDownloadEndpoint:
    """Test download-mirror endpoint for bidirectional sync."""

    def test_download_single_file_mirror(self, cleanup):
        """Test downloading a single file from mirror."""
        # Create a mirror with single file
        file_content = b"Download test content"
        files = [('files', ('single.txt', io.BytesIO(file_content), 'text/plain'))]
        data = {'target_name': 'single_file'}

        sync_response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )
        assert sync_response.status_code == 200

        # Download the file
        download_response = requests.get(
            f"{SANDBOX_BASE_URL}/download-mirror/single_file"
        )

        assert download_response.status_code == 200
        assert download_response.content == file_content

    def test_download_directory_as_zip(self, cleanup):
        """Test downloading a directory mirror as zip archive."""
        # Create mirror with multiple files
        files = [
            ('files', ('file1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('file2.txt', io.BytesIO(b"Content 2"), 'text/plain')),
            ('files', ('subdir/file3.txt', io.BytesIO(b"Content 3"), 'text/plain'))
        ]
        data = {'target_name': 'test_dir'}

        sync_response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )
        assert sync_response.status_code == 200

        # Download as zip
        download_response = requests.get(
            f"{SANDBOX_BASE_URL}/download-mirror/test_dir"
        )

        assert download_response.status_code == 200
        assert 'application/zip' in download_response.headers.get('content-type', '')

        # Verify it's a valid zip file
        import zipfile
        import io as io_module
        zip_data = io_module.BytesIO(download_response.content)
        with zipfile.ZipFile(zip_data, 'r') as zf:
            file_list = zf.namelist()
            assert 'file1.txt' in file_list
            assert 'file2.txt' in file_list
            # Path separator might be different
            assert any('file3.txt' in name for name in file_list)

    def test_download_nonexistent_mirror(self, cleanup):
        """Test downloading a mirror that doesn't exist."""
        response = requests.get(
            f"{SANDBOX_BASE_URL}/download-mirror/nonexistent"
        )

        assert response.status_code == 404
        assert "Mirror not found" in response.json()["error"]

    def test_download_specific_file_from_mirror(self, cleanup):
        """Test downloading a specific file from a directory mirror."""
        # Create mirror with multiple files
        files = [
            ('files', ('file1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('file2.txt', io.BytesIO(b"Content 2"), 'text/plain'))
        ]
        data = {'target_name': 'multi_dir'}

        sync_response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )
        assert sync_response.status_code == 200

        # Download specific file
        download_response = requests.get(
            f"{SANDBOX_BASE_URL}/download-mirror/multi_dir?file_path=file1.txt"
        )

        assert download_response.status_code == 200
        assert download_response.content == b"Content 1"

    def test_download_invalid_file_path(self, cleanup):
        """Test downloading with invalid file_path parameter."""
        # Create a mirror first
        files = [('files', ('test.txt', io.BytesIO(b"Test"), 'text/plain'))]
        data = {'target_name': 'test_mirror'}

        sync_response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )
        assert sync_response.status_code == 200

        # Try to download non-existent file
        download_response = requests.get(
            f"{SANDBOX_BASE_URL}/download-mirror/test_mirror?file_path=nonexistent.txt"
        )

        assert download_response.status_code == 404


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

    def test_download_mirror_uses_error_handler(self, cleanup):
        """Test that download-mirror endpoint integrates with error handler."""
        response = requests.get(
            f"{SANDBOX_BASE_URL}/download-mirror/nonexistent"
        )

        assert response.status_code == 404
        result = response.json()
        assert "error" in result
        # Should NOT expose internal exception details
        assert "Traceback" not in str(result)


class TestMirrorExistsEndpoint:
    """Test mirror-exists endpoint for checking mirror existence."""

    def test_mirror_exists_true_for_directory(self, cleanup):
        """Test that mirror-exists returns true for existing directory mirror."""
        # Create a mirror first
        files = [
            ('files', ('file1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('file2.txt', io.BytesIO(b"Content 2"), 'text/plain'))
        ]
        data = {'target_name': 'exists_dir'}

        sync_response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )
        assert sync_response.status_code == 200

        # Check if it exists
        response = requests.get(
            f"{SANDBOX_BASE_URL}/mirror-exists/exists_dir"
        )

        assert response.status_code == 200
        result = response.json()
        assert result["exists"] is True
        assert result["target_name"] == "exists_dir"
        assert result["is_file"] is False
        assert result["file_count"] == 2

    def test_mirror_exists_true_for_file(self, cleanup):
        """Test that mirror-exists returns true for existing file mirror."""
        # Create a single file mirror
        files = [('files', ('single.txt', io.BytesIO(b"Content"), 'text/plain'))]
        data = {'target_name': 'exists_file'}

        sync_response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )
        assert sync_response.status_code == 200

        # Check if it exists
        response = requests.get(
            f"{SANDBOX_BASE_URL}/mirror-exists/exists_file"
        )

        assert response.status_code == 200
        result = response.json()
        assert result["exists"] is True
        assert result["is_file"] is True
        assert result["file_count"] == 1

    def test_mirror_exists_false(self, cleanup):
        """Test that mirror-exists returns false for non-existent mirror."""
        response = requests.get(
            f"{SANDBOX_BASE_URL}/mirror-exists/nonexistent"
        )

        assert response.status_code == 200
        result = response.json()
        assert result["exists"] is False
        assert result["target_name"] == "nonexistent"


class TestMirrorSyncedEndpoint:
    """Test mirror-synced endpoint for checking sync status."""

    def test_mirror_synced_true(self, cleanup):
        """Test that mirror-synced returns true when files match."""
        # Create a mirror
        files = [
            ('files', ('sync1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('sync2.txt', io.BytesIO(b"Content 2"), 'text/plain'))
        ]
        data = {'target_name': 'synced_test'}

        sync_response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )
        assert sync_response.status_code == 200

        # Get mirror info to build file list
        mirror_response = requests.post(
            f"{SANDBOX_BASE_URL}/revert-sync",
            json={'target_name': 'synced_test'}
        )
        assert mirror_response.status_code == 200
        mirror_files = mirror_response.json()['files']

        # Check sync status with same files
        check_response = requests.post(
            f"{SANDBOX_BASE_URL}/mirror-synced",
            json={
                'target_name': 'synced_test',
                'files': mirror_files
            }
        )

        assert check_response.status_code == 200
        result = check_response.json()
        assert result["synced"] is True

    def test_mirror_synced_false_different_files(self, cleanup):
        """Test that mirror-synced returns false when files differ."""
        # Create a mirror
        files = [
            ('files', ('sync1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('sync2.txt', io.BytesIO(b"Content 2"), 'text/plain'))
        ]
        data = {'target_name': 'not_synced'}

        sync_response = requests.post(
            f"{SANDBOX_BASE_URL}/sync",
            files=files,
            data=data
        )
        assert sync_response.status_code == 200

        # Check with different file list
        check_response = requests.post(
            f"{SANDBOX_BASE_URL}/mirror-synced",
            json={
                'target_name': 'not_synced',
                'files': [
                    {'name': 'sync1.txt', 'size': 9, 'modified': 1234567890},
                    {'name': 'different.txt', 'size': 10, 'modified': 1234567891}
                ]
            }
        )

        assert check_response.status_code == 200
        result = check_response.json()
        assert result["synced"] is False
        assert "differences" in result

    def test_mirror_synced_mirror_not_found(self, cleanup):
        """Test mirror-synced returns 404 when mirror doesn't exist."""
        response = requests.post(
            f"{SANDBOX_BASE_URL}/mirror-synced",
            json={
                'target_name': 'nonexistent',
                'files': [{'name': 'test.txt', 'size': 10, 'modified': 1234567890}]
            }
        )

        assert response.status_code == 404
        assert "Mirror not found" in response.json()["error"]

    def test_mirror_synced_no_files_provided(self, cleanup):
        """Test mirror-synced returns error when files list not provided."""
        response = requests.post(
            f"{SANDBOX_BASE_URL}/mirror-synced",
            json={'target_name': 'test'}
        )

        assert response.status_code == 400
        assert "No files list provided" in response.json()["error"]
