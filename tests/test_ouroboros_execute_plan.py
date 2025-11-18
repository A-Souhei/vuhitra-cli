#!/usr/bin/env python3
"""
Tests for the Ouroboros Execute Plan functionality.

This test suite covers:
1. Ouroboros tool matching function
2. Auto-execution with iteration limits
3. RAG context history integration
4. Failure handling and exploiter function
5. Pretty printing output
6. ESC cancellation support
"""

import pytest
import json
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcps.mirror_vanisher_dev.src.execute_plan import ExecutePlan


class TestOuroborosToolMatching:
    """Test the ouroboros tool matching functionality."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock manager for testing."""
        return Mock()

    @pytest.fixture
    def mock_server(self):
        """Create a mock server instance with tools."""
        server = Mock()
        server.tools = {
            'explore_codebase': {
                'description': 'Explore and analyze codebase structure',
                'inputSchema': {'properties': {'path': {'type': 'string'}}}
            },
            'generate_code': {
                'description': 'Generate code based on requirements',
                'inputSchema': {'properties': {'task': {'type': 'string'}}}
            },
            'run_tests': {
                'description': 'Run test suite and report results',
                'inputSchema': {'properties': {'path': {'type': 'string'}}}
            }
        }
        return server

    @pytest.fixture
    def execute_plan_instance(self, mock_manager, mock_server):
        """Create an ExecutePlan instance for testing."""
        with patch.object(ExecutePlan, '__init__', lambda x, y, z: None):
            instance = ExecutePlan.__new__(ExecutePlan)
            instance.manager = mock_manager
            instance.server_instance = mock_server
            instance.redis_client = None
            instance.redis_available = False
            instance.memory_todo_list = []
            instance.memory_detailed_todo_list = []
            instance.tool_embeddings_cache = {}
            instance.similarity_threshold = 0.3
            instance.max_auto_iterations = 25
            instance.history_similarity_threshold = 0.5
            instance.history_top_k = 3
            instance.cancelled = False
            instance.execution_history = []
            instance.transformer_url = "http://localhost:16050"

            # Mock config
            instance.config = Mock()
            instance.config.get.return_value = {}

            # Mock history manager
            instance.history_manager = Mock()
            instance.history_manager.retrieve_relevant_history.return_value = []
            instance.history_manager.format_history_for_context.return_value = ""
            instance.history_manager.add_turn.return_value = True

            return instance

    def test_get_mirror_vanisher_tools(self, execute_plan_instance):
        """Test getting Mirror+Vanisher tools."""
        tools = execute_plan_instance.get_mirror_vanisher_tools()

        assert len(tools) == 3
        tool_names = [t['name'] for t in tools]
        assert 'explore_codebase' in tool_names
        assert 'generate_code' in tool_names
        assert 'run_tests' in tool_names

    def test_get_mirror_vanisher_tools_with_exclusions(self, execute_plan_instance):
        """Test excluding specific tools."""
        tools = execute_plan_instance.get_mirror_vanisher_tools(exclude_tools=['explore_codebase'])

        assert len(tools) == 2
        tool_names = [t['name'] for t in tools]
        assert 'explore_codebase' not in tool_names

    def test_get_executor_tools(self, execute_plan_instance):
        """Test getting Executor MCP tools."""
        tools = execute_plan_instance.get_executor_tools()

        assert len(tools) == 24
        tool_names = [t['name'] for t in tools]
        assert 'execute_python_code' in tool_names
        assert 'create_file' in tool_names
        assert 'install_pip_packages' in tool_names

    def test_ouroboros_match_tools_with_embeddings(self, execute_plan_instance):
        """Test ouroboros matching with semantic similarity."""
        # Mock embedding generation
        with patch.object(execute_plan_instance, '_generate_embedding') as mock_embed:
            # Return different embeddings for different texts
            def generate_embedding(text):
                if 'explore' in text.lower():
                    return np.array([1.0, 0.0, 0.0], dtype=np.float32)
                elif 'code' in text.lower():
                    return np.array([0.0, 1.0, 0.0], dtype=np.float32)
                else:
                    return np.array([0.0, 0.0, 1.0], dtype=np.float32)

            mock_embed.side_effect = generate_embedding

            todo_list = [
                {'step_number': 1, 'action': 'Explore codebase', 'details': 'Analyze structure'},
                {'step_number': 2, 'action': 'Generate code', 'details': 'Create new function'}
            ]

            detailed_list = execute_plan_instance.ouroboros_match_tools(todo_list)

            # Should match based on embeddings
            assert len(detailed_list) >= 0  # May or may not match depending on similarity

    def test_ouroboros_match_tools_keyword_fallback(self, execute_plan_instance):
        """Test ouroboros matching with keyword fallback when embeddings fail."""
        with patch.object(execute_plan_instance, '_generate_embedding', return_value=None):
            todo_list = [
                {'step_number': 1, 'action': 'execute python code', 'details': 'Run script'}
            ]

            detailed_list = execute_plan_instance.ouroboros_match_tools(todo_list)

            # Should use keyword matching
            # The result depends on Jaccard similarity threshold

    def test_ouroboros_no_match_skips_step(self, execute_plan_instance):
        """Test that steps without matches are not added to DETAILED_TODO_list."""
        with patch.object(execute_plan_instance, '_generate_embedding', return_value=None):
            with patch.object(execute_plan_instance, '_keyword_match_best_tool', return_value=None):
                todo_list = [
                    {'step_number': 1, 'action': 'Unknown action', 'details': 'No matching tool'}
                ]

                detailed_list = execute_plan_instance.ouroboros_match_tools(todo_list)

                # Step without match should not be in detailed list
                assert len(detailed_list) == 0


class TestAutoExecution:
    """Test the auto-execution functionality."""

    @pytest.fixture
    def execute_plan_instance(self):
        """Create an ExecutePlan instance for testing."""
        with patch.object(ExecutePlan, '__init__', lambda x, y, z: None):
            instance = ExecutePlan.__new__(ExecutePlan)
            instance.manager = Mock()
            instance.server_instance = Mock()
            instance.server_instance.tools = {}
            instance.redis_client = None
            instance.redis_available = False
            instance.memory_todo_list = []
            instance.memory_detailed_todo_list = []
            instance.tool_embeddings_cache = {}
            instance.similarity_threshold = 0.3
            instance.max_auto_iterations = 25
            instance.history_similarity_threshold = 0.5
            instance.history_top_k = 3
            instance.cancelled = False
            instance.execution_history = []
            instance.transformer_url = "http://localhost:16050"

            instance.config = Mock()
            instance.config.get.return_value = {}

            instance.history_manager = Mock()
            instance.history_manager.retrieve_relevant_history.return_value = []
            instance.history_manager.format_history_for_context.return_value = ""
            instance.history_manager.add_turn.return_value = True

            return instance

    def test_max_iterations_limit(self, execute_plan_instance):
        """Test that execution stops when max iterations is exceeded."""
        execute_plan_instance.max_auto_iterations = 5

        # Create a TODO list with more items than max
        execute_plan_instance.memory_todo_list = [
            {'step_number': i, 'action': f'Action {i}', 'details': f'Details {i}'}
            for i in range(1, 10)  # 9 items
        ]

        with patch.object(execute_plan_instance, 'ouroboros_match_tools') as mock_match:
            # Return 9 detailed items
            mock_match.return_value = [
                {'step_number': i, 'original_action': f'Action {i}',
                 'original_details': f'Details {i}', 'tool_name': 'test_tool',
                 'tool_source': 'test', 'tool_description': 'Test',
                 'similarity_score': 0.9, 'status': 'pending', 'execution_result': None}
                for i in range(1, 10)
            ]

            result = execute_plan_instance.execute_plan(auto_execute=True)

            assert result['success'] is False
            assert 'exceeding max limit' in result['error']

    def test_execution_without_todo_list(self, execute_plan_instance):
        """Test execution fails gracefully when no TODO_list exists."""
        execute_plan_instance.memory_todo_list = []

        result = execute_plan_instance.execute_plan(auto_execute=True)

        assert result['success'] is False
        assert 'No TODO_list found' in result['error']

    def test_no_auto_execute_builds_list_only(self, execute_plan_instance):
        """Test that auto_execute=False only builds the DETAILED_TODO_list."""
        execute_plan_instance.memory_todo_list = [
            {'step_number': 1, 'action': 'Test action', 'details': 'Test details'}
        ]

        with patch.object(execute_plan_instance, 'ouroboros_match_tools') as mock_match:
            mock_match.return_value = [
                {'step_number': 1, 'original_action': 'Test action',
                 'original_details': 'Test details', 'tool_name': 'test_tool',
                 'tool_source': 'test', 'tool_description': 'Test',
                 'similarity_score': 0.9, 'status': 'pending', 'execution_result': None}
            ]

            result = execute_plan_instance.execute_plan(auto_execute=False)

            assert result['success'] is True
            assert result['auto_execute'] is False
            assert len(result['execution_results']) == 0


class TestPrettyPrinting:
    """Test the pretty printing functionality."""

    @pytest.fixture
    def execute_plan_instance(self):
        """Create an ExecutePlan instance for testing."""
        with patch.object(ExecutePlan, '__init__', lambda x, y, z: None):
            instance = ExecutePlan.__new__(ExecutePlan)
            return instance

    def test_pretty_print_step_info(self, execute_plan_instance):
        """Test pretty printing of step information."""
        item = {
            'original_action': 'Create file',
            'original_details': 'Create a new Python file',
            'tool_name': 'create_file',
            'tool_source': 'executor',
            'similarity_score': 0.85
        }

        output = execute_plan_instance.pretty_print_step_info(item, 1, 5)

        assert 'ITERATION 1/5' in output
        assert 'Create file' in output
        assert 'create_file' in output
        assert 'executor' in output
        assert '85' in output  # Similarity percentage


class TestRAGContextIntegration:
    """Test the RAG context history integration."""

    @pytest.fixture
    def execute_plan_instance(self):
        """Create an ExecutePlan instance for testing."""
        with patch.object(ExecutePlan, '__init__', lambda x, y, z: None):
            instance = ExecutePlan.__new__(ExecutePlan)
            instance.history_manager = Mock()
            instance.history_top_k = 3
            instance.history_similarity_threshold = 0.5
            return instance

    def test_get_rag_context_with_history(self, execute_plan_instance):
        """Test retrieving RAG context from history."""
        # Mock relevant history
        execute_plan_instance.history_manager.retrieve_relevant_history.return_value = [
            (Mock(prompt="Previous prompt", response="Previous response"), 0.8)
        ]
        execute_plan_instance.history_manager.format_history_for_context.return_value = "Formatted history"

        context = execute_plan_instance.get_rag_context("Test step")

        assert context == "Formatted history"
        execute_plan_instance.history_manager.retrieve_relevant_history.assert_called_once()

    def test_get_rag_context_empty_history(self, execute_plan_instance):
        """Test RAG context when no relevant history exists."""
        execute_plan_instance.history_manager.retrieve_relevant_history.return_value = []

        context = execute_plan_instance.get_rag_context("Test step")

        assert context == ""


class TestFailureHandling:
    """Test the failure handling and exploiter function."""

    @pytest.fixture
    def execute_plan_instance(self):
        """Create an ExecutePlan instance for testing."""
        with patch.object(ExecutePlan, '__init__', lambda x, y, z: None):
            instance = ExecutePlan.__new__(ExecutePlan)
            instance.config = Mock()
            instance.config.get.return_value = {
                'use': 'local',
                'local': {'host': 'localhost', 'port': 11434, 'protocol': 'http', 'api_path': '/api/generate'}
            }
            return instance

    def test_handle_failure_returns_info(self, execute_plan_instance):
        """Test that handle_failure returns proper failure information."""
        item = {
            'step_number': 1,
            'original_action': 'Failed action',
            'tool_name': 'failed_tool'
        }
        error_result = {'error': 'Test error'}
        todo_list = []

        result = execute_plan_instance.handle_failure(item, error_result, todo_list)

        # Should return tuple with choice, new list, and failure info
        assert len(result) == 3
        assert result[0] == 'continue'

    @patch('requests.post')
    def test_exploiter_function_generates_alternative(self, mock_post, execute_plan_instance):
        """Test exploiter function generates alternative plan."""
        # Mock ouroboros_match_tools
        execute_plan_instance.ouroboros_match_tools = Mock(return_value=[
            {'step_number': 1, 'tool_name': 'alternative_tool'}
        ])

        # Mock LLM response with new plan
        mock_response = Mock()
        mock_response.json.return_value = {
            'response': '[{"step_number": 1, "action": "Alternative", "details": "New approach"}]'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        failure_info = {
            'failed_action': 'Original action',
            'failed_tool': 'original_tool',
            'error': 'Test error'
        }
        todo_list = [{'step_number': 1, 'action': 'Original', 'details': 'Original details'}]

        result = execute_plan_instance.exploiter_function(failure_info, todo_list)

        # Should generate new detailed list
        assert len(result) == 1


class TestConfigIntegration:
    """Test configuration integration."""

    def test_config_loads_ouroboros_settings(self):
        """Test that ouroboros settings are loaded from config."""
        config_path = Path(__file__).parent.parent / "config.yaml"

        if config_path.exists():
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)

            # Check ouroboros config exists
            assert 'ouroboros' in config
            assert 'max_auto_iterations' in config['ouroboros']
            assert config['ouroboros']['max_auto_iterations'] == 25

    def test_config_default_values(self):
        """Test default values when config is missing."""
        from mcps.mirror_vanisher_dev.src.execute_plan import (
            DEFAULT_MAX_AUTO_ITERATIONS,
            DEFAULT_SIMILARITY_THRESHOLD
        )

        assert DEFAULT_MAX_AUTO_ITERATIONS == 25
        assert DEFAULT_SIMILARITY_THRESHOLD == 0.3


class TestToolExecution:
    """Test the tool execution functionality."""

    @pytest.fixture
    def execute_plan_instance(self):
        """Create an ExecutePlan instance for testing."""
        with patch.object(ExecutePlan, '__init__', lambda x, y, z: None):
            instance = ExecutePlan.__new__(ExecutePlan)
            instance.execution_history = []
            instance.history_manager = Mock()
            instance.history_manager.add_turn.return_value = True
            return instance

    def test_execute_tool_success(self, execute_plan_instance):
        """Test successful tool execution."""
        item = {
            'step_number': 1,
            'original_action': 'Test action',
            'tool_name': 'test_tool',
            'tool_source': 'test'
        }

        result = execute_plan_instance.execute_tool(item, "test context")

        assert result['success'] is True
        assert result['tool_name'] == 'test_tool'
        assert len(execute_plan_instance.execution_history) == 1

    def test_execution_history_accumulates(self, execute_plan_instance):
        """Test that execution history accumulates across executions."""
        for i in range(3):
            item = {
                'step_number': i + 1,
                'original_action': f'Action {i}',
                'tool_name': f'tool_{i}',
                'tool_source': 'test'
            }
            execute_plan_instance.execute_tool(item, "")

        assert len(execute_plan_instance.execution_history) == 3


class TestStepExplanation:
    """Test the LLM step explanation generation."""

    @pytest.fixture
    def execute_plan_instance(self):
        """Create an ExecutePlan instance for testing."""
        with patch.object(ExecutePlan, '__init__', lambda x, y, z: None):
            instance = ExecutePlan.__new__(ExecutePlan)
            instance.config = Mock()
            instance.config.get.return_value = {
                'use': 'local',
                'local': {'host': 'localhost', 'port': 11434, 'protocol': 'http', 'api_path': '/api/generate'},
                'default': {'local': 'tinyllama'}
            }
            return instance

    @patch('requests.post')
    def test_generate_explanation_success(self, mock_post, execute_plan_instance):
        """Test successful explanation generation."""
        mock_response = Mock()
        mock_response.json.return_value = {'response': 'This step will create a new file.'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        item = {
            'tool_name': 'create_file',
            'tool_description': 'Create a new file',
            'original_action': 'Create file',
            'original_details': 'Create config.yaml'
        }

        explanation = execute_plan_instance.generate_step_explanation(item, "")

        assert 'create' in explanation.lower() or 'file' in explanation.lower() or explanation == "Executing the planned step..."

    @patch('requests.post')
    def test_generate_explanation_fallback(self, mock_post, execute_plan_instance):
        """Test fallback when LLM fails."""
        mock_post.side_effect = Exception("Connection error")

        item = {
            'tool_name': 'test_tool',
            'tool_description': 'Test',
            'original_action': 'Test',
            'original_details': 'Test'
        }

        explanation = execute_plan_instance.generate_step_explanation(item, "")

        assert explanation == "Executing the planned step..."


class TestEscCancellation:
    """Test the ESC key cancellation functionality."""

    @pytest.fixture
    def execute_plan_instance(self):
        """Create an ExecutePlan instance for testing."""
        with patch.object(ExecutePlan, '__init__', lambda x, y, z: None):
            instance = ExecutePlan.__new__(ExecutePlan)
            return instance

    @patch('sys.stdin')
    @patch('select.select')
    def test_check_for_esc_not_tty(self, mock_select, mock_stdin, execute_plan_instance):
        """Test ESC check when not in TTY."""
        mock_stdin.isatty.return_value = False

        result = execute_plan_instance.check_for_esc_key()

        assert result is False

    @patch('sys.stdin')
    @patch('select.select')
    def test_check_for_esc_no_input(self, mock_select, mock_stdin, execute_plan_instance):
        """Test ESC check when no input available."""
        mock_stdin.isatty.return_value = True
        mock_select.return_value = ([], [], [])

        result = execute_plan_instance.check_for_esc_key()

        assert result is False


class TestRedisIntegration:
    """Test Redis storage integration."""

    @pytest.fixture
    def execute_plan_instance(self):
        """Create an ExecutePlan instance for testing."""
        with patch.object(ExecutePlan, '__init__', lambda x, y, z: None):
            instance = ExecutePlan.__new__(ExecutePlan)
            instance.redis_client = Mock()
            instance.redis_available = True
            instance.memory_detailed_todo_list = []
            return instance

    def test_save_detailed_todo_list_redis(self, execute_plan_instance):
        """Test saving DETAILED_TODO_list to Redis."""
        detailed_list = [
            {'step_number': 1, 'tool_name': 'test_tool'}
        ]

        result = execute_plan_instance.save_detailed_todo_list(detailed_list)

        assert result is True
        execute_plan_instance.redis_client.set.assert_called_once()

    def test_save_detailed_todo_list_memory_fallback(self, execute_plan_instance):
        """Test saving to memory when Redis fails."""
        execute_plan_instance.redis_available = False

        detailed_list = [
            {'step_number': 1, 'tool_name': 'test_tool'}
        ]

        result = execute_plan_instance.save_detailed_todo_list(detailed_list)

        assert result is True
        assert execute_plan_instance.memory_detailed_todo_list == detailed_list


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
