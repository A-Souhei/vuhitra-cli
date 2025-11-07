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


class TestSandboxEndpoints:
    """Test Flask endpoints in the sandbox container."""
    
    def test_health_endpoint(self):
        """Test the health check endpoint."""
        response = requests.get(f"{SANDBOX_BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sandbox"
    
    def test_upload_single_file(self, cleanup):
        """Test uploading a single file."""
        # Create a test file
        file_content = b"This is a test file content"
        files = {'file': ('test_file.txt', io.BytesIO(file_content), 'text/plain')}
        
        # Upload the file
        response = requests.post(f"{SANDBOX_BASE_URL}/upload", files=files)
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "File uploaded successfully"
        assert data["filename"] == "test_file.txt"
        assert "/app/WORKSPACE/test_file.txt" in data["path"]
    
    def test_upload_empty_filename(self, cleanup):
        """Test uploading with empty filename."""
        files = {'file': ('', io.BytesIO(b"content"), 'text/plain')}
        
        response = requests.post(f"{SANDBOX_BASE_URL}/upload", files=files)
        assert response.status_code == 400
        assert "Empty filename" in response.json()["error"]
    
    def test_upload_no_file(self, cleanup):
        """Test upload endpoint without file."""
        response = requests.post(f"{SANDBOX_BASE_URL}/upload")
        assert response.status_code == 400
        assert "No file provided" in response.json()["error"]
    
    def test_upload_multiple_files(self, cleanup):
        """Test uploading multiple files (directory upload)."""
        files = [
            ('files', ('file1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('file2.txt', io.BytesIO(b"Content 2"), 'text/plain')),
            ('files', ('file3.txt', io.BytesIO(b"Content 3"), 'text/plain'))
        ]
        
        response = requests.post(f"{SANDBOX_BASE_URL}/upload-directory", files=files)
        assert response.status_code == 200
        
        data = response.json()
        assert "Uploaded 3 file(s)" in data["message"]
        assert len(data["uploaded"]) == 3
        assert "file1.txt" in data["uploaded"]
        assert "file2.txt" in data["uploaded"]
        assert "file3.txt" in data["uploaded"]
    
    def test_list_files(self, cleanup):
        """Test listing files in WORKSPACE."""
        # Upload some files first
        files = [
            ('files', ('list_test1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('list_test2.txt', io.BytesIO(b"Content 2"), 'text/plain'))
        ]
        requests.post(f"{SANDBOX_BASE_URL}/upload-directory", files=files)
        
        # List files
        response = requests.get(f"{SANDBOX_BASE_URL}/list")
        assert response.status_code == 200
        
        data = response.json()
        assert data["workspace"] == "/app/WORKSPACE"
        assert data["file_count"] >= 2
        
        file_names = [f["name"] for f in data["files"]]
        assert "list_test1.txt" in file_names
        assert "list_test2.txt" in file_names
    
    def test_remove_single_file(self, cleanup):
        """Test removing a single file."""
        # Upload a file first
        files = {'file': ('remove_test.txt', io.BytesIO(b"To be removed"), 'text/plain')}
        requests.post(f"{SANDBOX_BASE_URL}/upload", files=files)
        
        # Remove the file
        response = requests.delete(f"{SANDBOX_BASE_URL}/remove/remove_test.txt")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "File removed successfully"
        assert data["filename"] == "remove_test.txt"
        
        # Verify file is gone
        list_response = requests.get(f"{SANDBOX_BASE_URL}/list")
        file_names = [f["name"] for f in list_response.json()["files"]]
        assert "remove_test.txt" not in file_names
    
    def test_remove_nonexistent_file(self, cleanup):
        """Test removing a file that doesn't exist."""
        response = requests.delete(f"{SANDBOX_BASE_URL}/remove/nonexistent.txt")
        assert response.status_code == 404
        assert "File not found" in response.json()["error"]
    
    def test_remove_all_files(self, cleanup):
        """Test removing all files."""
        # Upload multiple files
        files = [
            ('files', ('all_test1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('all_test2.txt', io.BytesIO(b"Content 2"), 'text/plain')),
            ('files', ('all_test3.txt', io.BytesIO(b"Content 3"), 'text/plain'))
        ]
        requests.post(f"{SANDBOX_BASE_URL}/upload-directory", files=files)
        
        # Remove all files
        response = requests.delete(f"{SANDBOX_BASE_URL}/remove-all")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "All files removed successfully"
        assert data["removed_count"] >= 3
        
        # Verify all files are gone
        list_response = requests.get(f"{SANDBOX_BASE_URL}/list")
        assert list_response.json()["file_count"] == 0
    
    def test_upload_and_list_workflow(self, cleanup):
        """Test complete workflow: upload, list, remove."""
        # 1. Upload a file
        files = {'file': ('workflow_test.txt', io.BytesIO(b"Workflow test"), 'text/plain')}
        upload_response = requests.post(f"{SANDBOX_BASE_URL}/upload", files=files)
        assert upload_response.status_code == 200
        
        # 2. List files to verify upload
        list_response = requests.get(f"{SANDBOX_BASE_URL}/list")
        file_names = [f["name"] for f in list_response.json()["files"]]
        assert "workflow_test.txt" in file_names
        
        # 3. Remove the file
        remove_response = requests.delete(f"{SANDBOX_BASE_URL}/remove/workflow_test.txt")
        assert remove_response.status_code == 200
        
        # 4. Verify file is removed
        list_response2 = requests.get(f"{SANDBOX_BASE_URL}/list")
        file_names2 = [f["name"] for f in list_response2.json()["files"]]
        assert "workflow_test.txt" not in file_names2


class TestSandboxErrorHandler:
    """Test error handler integration in the sandbox service."""
    
    def test_error_handler_import(self):
        """Test that error handler can be imported from sandbox main module."""
        try:
            from src.errors_handler.error_handler import get_error_handler
            error_handler = get_error_handler()
            assert error_handler is not None
            assert hasattr(error_handler, 'handle_exception')
            assert hasattr(error_handler, 'capture_message')
        except ImportError as e:
            pytest.fail(f"Failed to import error handler: {str(e)}")
    
    def test_error_handler_configuration(self):
        """Test that error handler can be configured."""
        from src.errors_handler.error_handler import get_error_handler
        error_handler = get_error_handler()
        
        # Configure with DEV mode
        error_handler.configure(mode='DEV', enable_logging=True)
        assert error_handler.mode == 'DEV'
        assert error_handler.enable_logging is True
    
    def test_error_response_generic_message(self, cleanup):
        """Test that error responses don't expose internal details."""
        # Try to upload to an invalid location (this will fail internally)
        # We expect a generic error message, not the internal exception details
        files = {'file': ('test.txt', io.BytesIO(b"test"), 'text/plain')}
        
        # First upload a file normally
        response = requests.post(f"{SANDBOX_BASE_URL}/upload", files=files)
        assert response.status_code == 200
        
        # Now try to remove a non-existent file
        response = requests.delete(f"{SANDBOX_BASE_URL}/remove/nonexistent_file.txt")
        assert response.status_code == 404
        data = response.json()
        
        # Should have generic error message
        assert "error" in data
        assert data["error"] == "File not found"
        
        # Should NOT expose internal exception details
        assert "Traceback" not in str(data)
        assert "Exception" not in str(data)
    
    def test_invalid_operation_returns_generic_error(self, cleanup):
        """Test that invalid operations return generic error messages."""
        # Try to remove a directory as if it were a file
        # First create a directory by uploading with path
        files = [
            ('files', ('subdir/file.txt', io.BytesIO(b"content"), 'text/plain'))
        ]
        requests.post(f"{SANDBOX_BASE_URL}/upload-directory", files=files)
        
        # Now list to verify
        list_response = requests.get(f"{SANDBOX_BASE_URL}/list")
        assert list_response.status_code == 200
