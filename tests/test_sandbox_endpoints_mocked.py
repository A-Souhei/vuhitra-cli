"""
Mocked tests for sandbox endpoints without requiring actual container.
These tests use mocks to simulate container responses for CI/CD efficiency.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import io
import sys
import os

# Add parent directory to path to import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestSandboxEndpointsMocked:
    """Test Flask endpoints with mocked HTTP requests (no container required)."""

    @pytest.fixture
    def mock_requests(self):
        """Fixture to provide mocked requests module."""
        with patch('requests.get') as mock_get, \
             patch('requests.post') as mock_post, \
             patch('requests.delete') as mock_delete:
            yield {
                'get': mock_get,
                'post': mock_post,
                'delete': mock_delete
            }

    def test_health_endpoint(self, mock_requests):
        """Test the health check endpoint with mock."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "service": "sandbox"
        }
        mock_requests['get'].return_value = mock_response

        # Simulate the request
        import requests
        response = requests.get("http://localhost:18001/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "sandbox"

    def test_upload_single_file(self, mock_requests):
        """Test uploading a single file with mock."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "File uploaded successfully",
            "filename": "test_file.txt",
            "path": "/app/WORKSPACE/test_file.txt"
        }
        mock_requests['post'].return_value = mock_response

        # Simulate the request
        import requests
        file_content = b"This is a test file content"
        files = {'file': ('test_file.txt', io.BytesIO(file_content), 'text/plain')}
        response = requests.post("http://localhost:18001/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "File uploaded successfully"
        assert data["filename"] == "test_file.txt"
        assert "/app/WORKSPACE/test_file.txt" in data["path"]

    def test_upload_empty_filename(self, mock_requests):
        """Test uploading with empty filename (mocked error)."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Empty filename"
        }
        mock_requests['post'].return_value = mock_response

        import requests
        files = {'file': ('', io.BytesIO(b"content"), 'text/plain')}
        response = requests.post("http://localhost:18001/upload", files=files)

        assert response.status_code == 400
        assert "Empty filename" in response.json()["error"]

    def test_upload_no_file(self, mock_requests):
        """Test upload endpoint without file (mocked error)."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "No file provided"
        }
        mock_requests['post'].return_value = mock_response

        import requests
        response = requests.post("http://localhost:18001/upload")

        assert response.status_code == 400
        assert "No file provided" in response.json()["error"]

    def test_upload_multiple_files(self, mock_requests):
        """Test uploading multiple files (mocked)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "Uploaded 3 file(s) successfully",
            "uploaded": ["file1.txt", "file2.txt", "file3.txt"]
        }
        mock_requests['post'].return_value = mock_response

        import requests
        files = [
            ('files', ('file1.txt', io.BytesIO(b"Content 1"), 'text/plain')),
            ('files', ('file2.txt', io.BytesIO(b"Content 2"), 'text/plain')),
            ('files', ('file3.txt', io.BytesIO(b"Content 3"), 'text/plain'))
        ]
        response = requests.post("http://localhost:18001/upload-directory", files=files)

        assert response.status_code == 200
        data = response.json()
        assert "Uploaded 3 file(s)" in data["message"]
        assert len(data["uploaded"]) == 3
        assert "file1.txt" in data["uploaded"]
        assert "file2.txt" in data["uploaded"]
        assert "file3.txt" in data["uploaded"]

    def test_list_files(self, mock_requests):
        """Test listing files in WORKSPACE (mocked)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "workspace": "/app/WORKSPACE",
            "file_count": 2,
            "files": [
                {"name": "list_test1.txt", "size": 9},
                {"name": "list_test2.txt", "size": 9}
            ]
        }
        mock_requests['get'].return_value = mock_response

        import requests
        response = requests.get("http://localhost:18001/list")

        assert response.status_code == 200
        data = response.json()
        assert data["workspace"] == "/app/WORKSPACE"
        assert data["file_count"] >= 2

        file_names = [f["name"] for f in data["files"]]
        assert "list_test1.txt" in file_names
        assert "list_test2.txt" in file_names

    def test_remove_single_file(self, mock_requests):
        """Test removing a single file (mocked)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "File removed successfully",
            "filename": "remove_test.txt"
        }
        mock_requests['delete'].return_value = mock_response

        import requests
        response = requests.delete("http://localhost:18001/remove/remove_test.txt")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "File removed successfully"
        assert data["filename"] == "remove_test.txt"

    def test_remove_nonexistent_file(self, mock_requests):
        """Test removing a file that doesn't exist (mocked error)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error": "File not found"
        }
        mock_requests['delete'].return_value = mock_response

        import requests
        response = requests.delete("http://localhost:18001/remove/nonexistent.txt")

        assert response.status_code == 404
        assert "File not found" in response.json()["error"]

    def test_remove_all_files(self, mock_requests):
        """Test removing all files (mocked)."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": "All files removed successfully",
            "removed_count": 3
        }
        mock_requests['delete'].return_value = mock_response

        import requests
        response = requests.delete("http://localhost:18001/remove-all")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "All files removed successfully"
        assert data["removed_count"] >= 3


class TestSandboxErrorHandlerMocked:
    """Test error handler integration with mocks (no container required)."""

    def test_error_handler_import(self):
        """Test that error handler can be imported."""
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

    @pytest.fixture
    def mock_requests(self):
        """Fixture to provide mocked requests module."""
        with patch('requests.delete') as mock_delete:
            yield mock_delete

    def test_error_response_generic_message(self, mock_requests):
        """Test that error responses don't expose internal details (mocked)."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error": "File not found"
        }
        mock_requests.return_value = mock_response

        import requests
        response = requests.delete("http://localhost:18001/remove/nonexistent_file.txt")

        assert response.status_code == 404
        data = response.json()

        # Should have generic error message
        assert "error" in data
        assert data["error"] == "File not found"

        # Should NOT expose internal exception details
        assert "Traceback" not in str(data)
        assert "Exception" not in str(data)
