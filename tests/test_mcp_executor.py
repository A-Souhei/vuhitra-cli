"""Tests for the Executor MCP Server."""

import pytest
import sys
from pathlib import Path

# Add MCP server to path
mcp_path = Path(__file__).parent.parent / 'mcps' / 'executor'
sys.path.insert(0, str(mcp_path))
sys.path.insert(0, str(mcp_path / 'src'))

from server import MCPServer
from mirror_vanisher import MirrorVanisherManager
from code_execution import CodeExecutionTools
from file_operations import FileOperationsTools
from build_operations import BuildOperationsTools
from directory_operations import DirectoryOperationsTools


class TestMCPServer:
    """Test MCP Server initialization and basic functionality."""

    def test_server_initialization(self):
        """Test that MCP server initializes correctly."""
        server = MCPServer()
        assert server.manager is not None
        assert server.tools is not None
        assert len(server.tools) > 0

    def test_tools_registration(self):
        """Test that all tools are properly registered."""
        server = MCPServer()

        # Check mirror+vanisher management tools
        assert 'list_mirror_vanishers' in server.tools
        assert 'verify_mirror_vanisher' in server.tools

        # Check code execution tools
        assert 'execute_python_code' in server.tools
        assert 'execute_javascript_code' in server.tools
        assert 'execute_shell_command' in server.tools
        assert 'execute_code_snippet' in server.tools

        # Check file operations tools
        assert 'create_file' in server.tools
        assert 'update_file' in server.tools
        assert 'append_to_file' in server.tools
        assert 'delete_file' in server.tools
        assert 'copy_file' in server.tools
        assert 'move_file' in server.tools

        # Check build operations tools
        assert 'install_pip_packages' in server.tools
        assert 'install_npm_packages' in server.tools
        assert 'run_build_command' in server.tools
        assert 'compile_python' in server.tools
        assert 'create_virtual_env' in server.tools
        assert 'install_in_virtual_env' in server.tools
        assert 'run_in_virtual_env' in server.tools
        assert 'run_docker_build' in server.tools

        # Check directory operations tools
        assert 'create_directory' in server.tools
        assert 'create_directory_structure' in server.tools
        assert 'delete_directory' in server.tools
        assert 'copy_directory' in server.tools
        assert 'move_directory' in server.tools
        assert 'list_directory_contents' in server.tools

    def test_tool_count(self):
        """Test that we have the expected number of tools."""
        server = MCPServer()
        # 2 (mirror+vanisher) + 4 (execution) + 6 (file ops) + 8 (build & venv) + 6 (directory) = 26
        assert len(server.tools) == 26

    def test_initialize_request(self):
        """Test initialize request handling."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }

        response = server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert response["result"]["serverInfo"]["name"] == "executor-mcp"

    def test_tools_list_request(self):
        """Test tools/list request handling."""
        server = MCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }

        response = server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 2
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 26


class TestMirrorVanisherManager:
    """Test Mirror+Vanisher Manager."""

    def test_manager_initialization(self):
        """Test manager initializes correctly."""
        manager = MirrorVanisherManager()
        assert manager.sandbox_url is not None
        assert manager.workspace_path is not None

    def test_list_mirror_vanishers_structure(self):
        """Test that list_mirror_vanishers returns proper structure."""
        manager = MirrorVanisherManager()
        result = manager.list_mirror_vanishers()

        assert 'success' in result
        assert 'mirror_vanishers' in result
        assert isinstance(result['mirror_vanishers'], list)


class TestCodeExecutionTools:
    """Test Code Execution Tools."""

    def test_code_execution_initialization(self):
        """Test code execution tools initialize correctly."""
        manager = MirrorVanisherManager()
        tools = CodeExecutionTools(manager)
        assert tools.manager is not None


class TestFileOperationsTools:
    """Test File Operations Tools."""

    def test_file_operations_initialization(self):
        """Test file operations tools initialize correctly."""
        manager = MirrorVanisherManager()
        tools = FileOperationsTools(manager)
        assert tools.manager is not None


class TestBuildOperationsTools:
    """Test Build Operations Tools."""

    def test_build_operations_initialization(self):
        """Test build operations tools initialize correctly."""
        manager = MirrorVanisherManager()
        tools = BuildOperationsTools(manager)
        assert tools.manager is not None


class TestDirectoryOperationsTools:
    """Test Directory Operations Tools."""

    def test_directory_operations_initialization(self):
        """Test directory operations tools initialize correctly."""
        manager = MirrorVanisherManager()
        tools = DirectoryOperationsTools(manager)
        assert tools.manager is not None


class TestToolSchemas:
    """Test that all tools have proper schemas."""

    def test_all_tools_have_descriptions(self):
        """Test that all tools have descriptions."""
        server = MCPServer()
        for tool_name, tool in server.tools.items():
            assert 'description' in tool, f"Tool {tool_name} missing description"
            assert len(tool['description']) > 0, f"Tool {tool_name} has empty description"

    def test_all_tools_have_input_schemas(self):
        """Test that all tools have input schemas."""
        server = MCPServer()
        for tool_name, tool in server.tools.items():
            assert 'inputSchema' in tool, f"Tool {tool_name} missing inputSchema"
            assert 'type' in tool['inputSchema'], f"Tool {tool_name} inputSchema missing type"
            assert 'properties' in tool['inputSchema'], f"Tool {tool_name} inputSchema missing properties"

    def test_all_tools_have_handlers(self):
        """Test that all tools have handlers."""
        server = MCPServer()
        for tool_name, tool in server.tools.items():
            assert 'handler' in tool, f"Tool {tool_name} missing handler"
            assert callable(tool['handler']), f"Tool {tool_name} handler is not callable"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
