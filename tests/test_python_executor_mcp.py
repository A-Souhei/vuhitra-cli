"""
Tests for Python Executor MCP Server

Verifies tool registration and basic functionality.
"""

import sys
import os
from pathlib import Path

# Add MCP src to path
mcp_path = Path(__file__).parent.parent / 'mcps' / 'python_executor'
sys.path.insert(0, str(mcp_path / 'src'))
sys.path.insert(0, str(mcp_path))


def test_python_executor_tool_count():
    """Test that Python Executor MCP registers exactly 7 tools."""
    from server import PythonExecutorMCPServer
    
    server = PythonExecutorMCPServer()
    
    # Should have exactly 7 tools
    assert len(server.tools) == 7, f"Expected 7 tools, got {len(server.tools)}"
    
    # Verify code operation tools (4)
    code_tools = ['write_code', 'update_code', 'run_code', 'pip_install']
    for tool in code_tools:
        assert tool in server.tools, f"Missing code tool: {tool}"
    
    # Verify vanisher management tools (3)
    vanisher_tools = ['list_vanishers', 'list_files', 'delete_vanisher']
    for tool in vanisher_tools:
        assert tool in server.tools, f"Missing vanisher management tool: {tool}"
    
    print(f"✅ Python Executor MCP has all 7 tools:")
    for i, tool_name in enumerate(sorted(server.tools.keys()), 1):
        print(f"   {i}. {tool_name}")


def test_tool_schemas():
    """Test that all tools have proper schemas."""
    from server import PythonExecutorMCPServer
    
    server = PythonExecutorMCPServer()
    
    for tool_name, tool_def in server.tools.items():
        # Each tool should have description, inputSchema, and handler
        assert 'description' in tool_def, f"{tool_name} missing description"
        assert 'inputSchema' in tool_def, f"{tool_name} missing inputSchema"
        assert 'handler' in tool_def, f"{tool_name} missing handler"
        
        # Handler should be callable
        assert callable(tool_def['handler']), f"{tool_name} handler not callable"
        
        # inputSchema should have proper structure
        schema = tool_def['inputSchema']
        assert 'type' in schema, f"{tool_name} inputSchema missing type"
        assert schema['type'] == 'object', f"{tool_name} inputSchema not object type"
        assert 'properties' in schema, f"{tool_name} inputSchema missing properties"
        assert 'required' in schema, f"{tool_name} inputSchema missing required"
    
    print(f"✅ All tools have proper schemas")


def test_vanisher_manager_methods():
    """Test that VanisherManager has all required methods."""
    from vanisher_manager import VanisherManager
    
    manager = VanisherManager()
    
    # Should have these methods
    required_methods = ['list_vanishers', 'list_files', 'delete_vanisher']
    for method_name in required_methods:
        assert hasattr(manager, method_name), f"VanisherManager missing {method_name}"
        assert callable(getattr(manager, method_name)), f"{method_name} not callable"
    
    print(f"✅ VanisherManager has all required methods")


def test_imports_clean():
    """Test that there are no unused imports."""
    import server
    import vanisher_manager
    
    # Check server.py doesn't import 'Any' unnecessarily
    server_file = Path(__file__).parent.parent / 'mcps' / 'python_executor' / 'server.py'
    with open(server_file) as f:
        content = f.read()
        # Should import Dict but not Any (since it's not used)
        assert 'from typing import Dict' in content
        assert 'from typing import Dict, Any' not in content
    
    # Check vanisher_manager.py doesn't import Optional
    vm_file = Path(__file__).parent.parent / 'mcps' / 'python_executor' / 'src' / 'vanisher_manager.py'
    with open(vm_file) as f:
        content = f.read()
        # Should have shutil at module level
        assert 'import shutil' in content
        # Should not import Optional
        assert 'Optional' not in content
    
    print(f"✅ Imports are clean (no unused imports)")


if __name__ == '__main__':
    print("Testing Python Executor MCP Server...")
    print()
    
    test_python_executor_tool_count()
    print()
    
    test_tool_schemas()
    print()
    
    test_vanisher_manager_methods()
    print()
    
    test_imports_clean()
    print()
    
    print("✅ All tests passed!")
