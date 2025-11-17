"""Tests for the Mirror+Vanisher Development MCP Server."""

import pytest
import sys
from pathlib import Path

# Add MCP server to path
mcp_path = Path(__file__).parent.parent / 'mcps' / 'mirror_vanisher_dev'
sys.path.insert(0, str(mcp_path))
sys.path.insert(0, str(mcp_path / 'src'))

from server import MCPServer
from mirror_vanisher import MirrorVanisherManager
from exploration import ExplorationTools
from architecture import ArchitectureTools
from planning import PlanningTools


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

        # Check that key tools are registered
        assert 'list_mirror_vanishers' in server.tools
        assert 'verify_mirror_vanisher' in server.tools
        assert 'explore_structure' in server.tools
        assert 'full_exploration' in server.tools
        assert 'analyze_architecture' in server.tools
        assert 'create_plan' in server.tools
        assert 'run_tests' in server.tools
        assert 'full_quality_check' in server.tools
        assert 'security_audit' in server.tools
        assert 'complete_feature_workflow' in server.tools

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
        assert response["result"]["serverInfo"]["name"] == "mirror-vanisher-dev-mcp"

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
        assert len(response["result"]["tools"]) > 0


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


class TestExplorationTools:
    """Test Exploration Tools."""

    def test_exploration_tools_initialization(self):
        """Test exploration tools initialize correctly."""
        manager = MirrorVanisherManager()
        exploration = ExplorationTools(manager)

        assert exploration.manager is not None
        assert exploration.ext_to_lang is not None
        assert len(exploration.ext_to_lang) > 0

    def test_language_detection_mapping(self):
        """Test that language detection has common extensions."""
        manager = MirrorVanisherManager()
        exploration = ExplorationTools(manager)

        assert '.py' in exploration.ext_to_lang
        assert '.js' in exploration.ext_to_lang
        assert '.java' in exploration.ext_to_lang
        assert exploration.ext_to_lang['.py'] == 'Python'

    def test_entrypoint_files_defined(self):
        """Test that entrypoint files are properly defined."""
        manager = MirrorVanisherManager()
        exploration = ExplorationTools(manager)

        assert 'main.py' in exploration.entrypoint_files
        assert 'app.py' in exploration.entrypoint_files
        assert 'index.js' in exploration.entrypoint_files


class TestArchitectureTools:
    """Test Architecture Tools."""

    def test_architecture_tools_initialization(self):
        """Test architecture tools initialize correctly."""
        manager = MirrorVanisherManager()
        architecture = ArchitectureTools(manager)

        assert architecture.manager is not None


class TestPlanningTools:
    """Test Planning Tools."""

    def test_planning_tools_initialization(self):
        """Test planning tools initialize correctly."""
        manager = MirrorVanisherManager()
        planning = PlanningTools(manager)

        assert planning.manager is not None

    def test_plan_validation_missing_steps(self):
        """Test plan validation detects missing steps."""
        manager = MirrorVanisherManager()
        planning = PlanningTools(manager)

        invalid_plan = {'task': 'test task'}  # Missing steps
        result = planning.validate_plan(invalid_plan)

        assert result['success'] == True
        assert result['is_valid'] == False
        assert len(result['issues']) > 0

    def test_plan_validation_valid_plan(self):
        """Test plan validation accepts valid plan."""
        manager = MirrorVanisherManager()
        planning = PlanningTools(manager)

        valid_plan = {
            'task': 'test task',
            'steps': [
                {'step': 1, 'action': 'test action', 'details': 'test details'}
            ],
            'testing_requirements': ['unit tests']
        }
        result = planning.validate_plan(valid_plan)

        assert result['success'] == True
        assert result['is_valid'] == True


class TestWorkflows:
    """Test Multi-Step Workflows."""

    def test_feature_workflow_structure(self):
        """Test feature workflow returns proper structure."""
        server = MCPServer()

        # Use a fake path for testing structure only
        result = server.complete_feature_workflow('test_path', 'test feature')

        assert 'workflow' in result or 'error' in result

        # If workflow was created (path doesn't need to exist for structure test)
        if 'workflow' in result:
            assert 'workflow_id' in result['workflow']
            assert 'type' in result['workflow']
            assert 'steps' in result['workflow']

    def test_bugfix_workflow_structure(self):
        """Test bugfix workflow returns proper structure."""
        server = MCPServer()

        result = server.bugfix_workflow('test_path', 'test bug')

        assert 'workflow' in result or 'error' in result


# Run tests
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
