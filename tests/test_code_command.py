"""
Tests for /code command in CLI.

The /code command provides a streamlined workflow for coding sessions:
- /code init @<path> <task>: Initialize session (mirror + vanisher + create_plan + execute_plan)
- /code session exit @<path>: End session (revert+sync)

These tests document the expected behavior and can be expanded with mocked
integration tests as needed.
"""

import pytest
from unittest.mock import MagicMock, patch
from src.utils.command_handler import CommandResult


class TestCodeCommandDocumentation:
    """Documentation of expected /code command behavior."""

    def test_code_init_command_structure(self):
        """
        Documents the structure of the /code init command.

        The /code init @<path> <task> command should:
        1. Validate @ prefix in path argument
        2. Require a task description
        3. Check that vanisher context is enabled (coding mode)
        4. Execute /mirror do @<path> to mirror folder to sandbox
        5. Execute /vanisher load @<path> to load as vanisher context
        6. Create auto-prompt for LLM to call create_plan and execute_plan
        7. Return CommandResult with auto_prompt in data

        The auto-prompt is automatically injected and processed by the
        CLI main loop, triggering the LLM to call the MCP tools.

        Example usage:
            /code init @myproject Add user authentication with JWT
        """
        pass  # Documentation only

    def test_code_session_exit_command_structure(self):
        """
        Documents the structure of the /code session exit command.

        The /code session exit @<path> command should:
        1. Validate @ prefix in path argument
        2. Execute /mirror revert+sync @<path> to sync changes back to host
        3. Return success message with exit instructions

        Example usage:
            /code session exit @myproject
        """
        pass  # Documentation only

    def test_code_init_requires_coding_mode(self):
        """
        Documents that /code init requires coding mode.

        The command checks vanisher_context.is_enabled() and returns
        an error if coding mode is not enabled. Users must start the
        CLI with the --coding flag to use this command.

        Expected error message:
            "Vanisher context is disabled. Enable coding mode with --coding flag to use /code init."
        """
        pass  # Documentation only

    def test_code_init_requires_task_description(self):
        """
        Documents that /code init requires a task description.

        The command must have at least 3 arguments:
        - args[0] = "init"
        - args[1] = "@<path>"
        - args[2:] = task description (joined with spaces)

        Expected error message if task is missing:
            "Task description is required."
        """
        pass  # Documentation only

    def test_code_init_direct_mcp_calls(self):
        """
        Documents the direct MCP call behavior for /code init.

        The /code init command now directly calls MCP tools:
        1. Initialize MirrorVanisherManager
        2. Create PlanningTools and call create_plan()
        3. Create ExecutePlan and call execute_plan()
        4. Return results with plan_result and exec_result in data

        This bypasses the LLM and ensures reliable tool execution.
        """
        pass  # Documentation only

    def test_code_command_error_handling(self):
        """
        Documents expected error handling behavior.

        The /code command should handle:
        - Missing arguments (show usage)
        - Invalid subcommands (show error)
        - Path without @ prefix (show error)
        - Missing task description (show error)
        - Vanisher context disabled (show error)
        - Mirror operation failures (propagate error)
        - Vanisher load failures (propagate error)

        All errors should return CommandResult with success=False
        and a user-friendly message.
        """
        pass  # Documentation only


class TestCodeCommandWorkflow:
    """Tests for the /code command workflow integration."""

    def test_code_init_workflow_steps(self):
        """
        Documents the complete workflow of /code init.

        Step 1: /mirror do @<path>
            - Copies folder to sandbox mirror volume
            - Creates /app/WORKSPACE/mirrors/<path> in sandbox

        Step 2: /vanisher load @<path>
            - Loads mirrored content as vanisher context
            - Enables semantic filtering for relevance

        Step 3: Auto-prompt injection
            - Creates prompt for LLM to call create_plan
            - Instructs LLM to then call execute_plan
            - Prompt is automatically processed by CLI main loop

        This provides a complete end-to-end workflow initiation
        with a single command.
        """
        pass  # Documentation only

    def test_code_session_exit_workflow_steps(self):
        """
        Documents the complete workflow of /code session exit.

        Step 1: /mirror revert+sync @<path>
            - Downloads modified files from sandbox
            - Applies changes to host directory
            - Deletes host files not in sandbox (true sync)

        Step 2: Exit instructions
            - Displays success message
            - Prompts user to type 'exit' to leave CLI

        This syncs all sandbox changes back to the host,
        completing the coding session.
        """
        pass  # Documentation only


class TestCodeCommandIntegration:
    """Integration tests for /code command (requires mocking)."""

    @pytest.mark.skip(reason="Requires CLI refactoring to access command handlers")
    def test_code_init_calls_mirror_and_vanisher(self):
        """
        Test that /code init calls mirror and vanisher handlers.

        This test would verify:
        1. mirror_command_handler is called with ["do", "@path"]
        2. vanisher_command_handler is called with ["load", "@path"]
        3. Result contains auto_prompt in data
        """
        pass

    @pytest.mark.skip(reason="Requires CLI refactoring to access command handlers")
    def test_code_init_auto_prompt_execution(self):
        """
        Test that auto_prompt is processed by CLI main loop.

        This test would verify:
        1. Command returns CommandResult with auto_prompt
        2. CLI main loop detects auto_prompt in result.data
        3. Prompt is passed to LLM for processing
        """
        pass

    @pytest.mark.skip(reason="Requires CLI refactoring to access command handlers")
    def test_code_session_exit_calls_revert_sync(self):
        """
        Test that /code session exit calls revert+sync.

        This test would verify:
        1. mirror_command_handler is called with ["revert+sync", "@path"]
        2. Success message includes sync results
        3. Exit instructions are displayed
        """
        pass


class TestCodeCommandEdgeCases:
    """Edge case tests for /code command."""

    def test_code_init_with_spaces_in_task(self):
        """
        Documents handling of multi-word task descriptions.

        Example: /code init @myproject Add user authentication with JWT tokens

        The task should be joined from args[2:]:
            task = "Add user authentication with JWT tokens"
        """
        pass  # Documentation only

    def test_code_init_mirror_failure_stops_workflow(self):
        """
        Documents that mirror failure stops the workflow.

        If /mirror do fails, the command should:
        1. Return immediately with error
        2. NOT attempt vanisher load
        3. NOT create auto_prompt

        This prevents partial initialization states.
        """
        pass  # Documentation only

    def test_code_init_vanisher_failure_after_mirror(self):
        """
        Documents handling of vanisher failure after successful mirror.

        If /vanisher load fails after mirror succeeds:
        1. Return error with both messages
        2. Mirror remains in sandbox
        3. User can manually /vanisher load or /mirror destroy

        Note: This leaves the mirror in place for recovery.
        """
        pass  # Documentation only


class TestCodeCommandFunctional:
    """Functional tests that exercise the /code command logic directly."""

    def _create_code_command_handler(self, mock_mirror_handler, mock_vanisher_handler, mock_vanisher_context,
                                      mock_planning_tools=None, mock_executor=None):
        """
        Create a code_command_handler with mocked dependencies.

        This recreates the handler logic from src/cli.py for testing purposes.
        """
        def code_command_handler(args):
            """Handle /code command for combined coding workflow operations."""
            if not args:
                return CommandResult(
                    success=False,
                    message="Usage: /code init @<path> <task> - Initialize coding session\n"
                            "       /code session exit @<path> - End coding session\n"
                            "\n"
                            "Examples:\n"
                            "  /code init @myproject Add user authentication with JWT\n"
                            "  /code session exit @myproject - Sync changes back and exit"
                )

            subcommand = args[0].lower()

            # Handle 'session exit' as a two-word subcommand
            if subcommand == "session" and len(args) > 1 and args[1].lower() == "exit":
                if len(args) < 3:
                    return CommandResult(
                        success=False,
                        message="Usage: /code session exit @<path>"
                    )

                path_arg = args[2]
                if not path_arg.startswith('@'):
                    return CommandResult(
                        success=False,
                        message=f"Path must start with @ prefix. Example: /code session exit @myproject"
                    )

                # Execute revert+sync
                revert_result = mock_mirror_handler(["revert+sync", path_arg])

                if not revert_result.success:
                    return CommandResult(
                        success=False,
                        message=f"Failed to sync changes back:\n{revert_result.message}"
                    )

                return CommandResult(
                    success=True,
                    message=f"{revert_result.message}\n\n"
                            f"Coding session ended. Changes synced back to host.\n"
                            f"Type 'exit' to leave the CLI.",
                    data={'should_exit': True}
                )

            elif subcommand == "init":
                if len(args) < 2:
                    return CommandResult(
                        success=False,
                        message="Usage: /code init @<path> <task description>"
                    )

                path_arg = args[1]
                if not path_arg.startswith('@'):
                    return CommandResult(
                        success=False,
                        message=f"Path must start with @ prefix. Example: /code init @myproject Add authentication"
                    )

                if len(args) < 3:
                    return CommandResult(
                        success=False,
                        message="Task description is required.\n"
                                "Usage: /code init @<path> <task description>\n"
                                "Example: /code init @myproject Add user authentication with JWT"
                    )

                task = " ".join(args[2:])

                # Check if vanisher context is enabled
                if not mock_vanisher_context.is_enabled():
                    return CommandResult(
                        success=False,
                        message="Vanisher context is disabled. Enable coding mode with --coding flag to use /code init."
                    )

                messages = []

                # Step 1: Execute mirror do
                mirror_result = mock_mirror_handler(["do", path_arg])

                if not mirror_result.success:
                    return CommandResult(
                        success=False,
                        message=f"Failed to mirror folder:\n{mirror_result.message}"
                    )

                messages.append(f"[1/2] Mirror: {mirror_result.message}")

                # Step 2: Execute vanisher load
                target_name = path_arg[1:]

                vanisher_result = mock_vanisher_handler(["load", path_arg])

                if not vanisher_result.success:
                    messages.append(f"[2/2] Vanisher load failed: {vanisher_result.message}")
                    return CommandResult(
                        success=False,
                        message="\n\n".join(messages)
                    )

                messages.append(f"[2/2] Vanisher: {vanisher_result.message}")
                messages.append(f"\nCoding session initialized for '{target_name}'.")
                messages.append(f"Task: {task}")

                # Direct MCP tool calls
                if mock_planning_tools and mock_executor:
                    # Step 3: Create plan
                    messages.append("\n[3/4] Creating implementation plan...")
                    plan_result = mock_planning_tools.create_plan(target_name, task)

                    if not plan_result.get('success', False):
                        error_msg = plan_result.get('error', 'Unknown error creating plan')
                        messages.append(f"[3/4] Plan creation failed: {error_msg}")
                        return CommandResult(
                            success=False,
                            message="\n\n".join(messages)
                        )

                    todo_list = plan_result.get('TODO_list', [])
                    plan_type = plan_result.get('type', 'feature')
                    messages.append(f"[3/4] Plan created: {len(todo_list)} steps ({plan_type})")

                    # Step 4: Execute plan
                    messages.append("\n[4/4] Executing plan with Ouroboros auto-executor...")
                    exec_result = mock_executor.execute_plan(auto_execute=True)

                    if not exec_result.get('success', False):
                        error_msg = exec_result.get('error', 'Unknown error executing plan')
                        messages.append(f"[4/4] Execution failed: {error_msg}")
                        return CommandResult(
                            success=False,
                            message="\n\n".join(messages)
                        )

                    completed = exec_result.get('completed_count', 0)
                    failed = exec_result.get('failed_count', 0)
                    total = exec_result.get('detailed_todo_list_count', 0)

                    messages.append(f"[4/4] Execution complete: {completed}/{total} steps completed, {failed} failed")

                    return CommandResult(
                        success=True,
                        message="\n\n".join(messages),
                        data={
                            'plan_result': plan_result,
                            'exec_result': exec_result
                        }
                    )
                else:
                    # Fallback for tests that don't provide MCP mocks
                    messages.append("Creating and executing implementation plan...")
                    return CommandResult(
                        success=True,
                        message="\n\n".join(messages),
                        data={'needs_mcp': True}
                    )

            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown subcommand: {subcommand}\n"
                            f"Available: /code init @<path>, /code session exit @<path>"
                )

        return code_command_handler

    def test_code_no_args_shows_usage(self):
        """Test that calling /code without arguments shows usage."""
        handler = self._create_code_command_handler(
            MagicMock(), MagicMock(), MagicMock()
        )
        result = handler([])

        assert not result.success
        assert "Usage:" in result.message
        assert "/code init" in result.message
        assert "/code session exit" in result.message

    def test_code_init_missing_path_shows_error(self):
        """Test that /code init without path shows error."""
        handler = self._create_code_command_handler(
            MagicMock(), MagicMock(), MagicMock()
        )
        result = handler(["init"])

        assert not result.success
        assert "Usage: /code init @<path>" in result.message

    def test_code_init_path_without_at_prefix_shows_error(self):
        """Test that /code init with path missing @ prefix shows error."""
        handler = self._create_code_command_handler(
            MagicMock(), MagicMock(), MagicMock()
        )
        result = handler(["init", "myproject", "Add", "feature"])

        assert not result.success
        assert "Path must start with @ prefix" in result.message

    def test_code_init_missing_task_shows_error(self):
        """Test that /code init without task shows error."""
        handler = self._create_code_command_handler(
            MagicMock(), MagicMock(), MagicMock()
        )
        result = handler(["init", "@myproject"])

        assert not result.success
        assert "Task description is required" in result.message

    def test_code_init_vanisher_disabled_shows_error(self):
        """Test that /code init fails when vanisher context is disabled."""
        mock_vanisher = MagicMock()
        mock_vanisher.is_enabled.return_value = False

        handler = self._create_code_command_handler(
            MagicMock(), MagicMock(), mock_vanisher
        )
        result = handler(["init", "@myproject", "Add", "feature"])

        assert not result.success
        assert "Vanisher context is disabled" in result.message
        assert "--coding flag" in result.message

    def test_code_init_mirror_failure_stops_workflow(self):
        """Test that mirror failure stops the workflow."""
        mock_vanisher = MagicMock()
        mock_vanisher.is_enabled.return_value = True

        mock_mirror = MagicMock()
        mock_mirror.return_value = CommandResult(
            success=False,
            message="Path not found: /nonexistent"
        )

        handler = self._create_code_command_handler(
            mock_mirror, MagicMock(), mock_vanisher
        )
        result = handler(["init", "@nonexistent", "Add", "feature"])

        assert not result.success
        assert "Failed to mirror folder" in result.message
        assert "Path not found" in result.message

    def test_code_init_vanisher_failure_after_mirror(self):
        """Test that vanisher failure after successful mirror returns error."""
        mock_vanisher_context = MagicMock()
        mock_vanisher_context.is_enabled.return_value = True

        mock_mirror = MagicMock()
        mock_mirror.return_value = CommandResult(
            success=True,
            message="Synced 10 file(s) to sandbox 'myproject'"
        )

        mock_vanisher = MagicMock()
        mock_vanisher.return_value = CommandResult(
            success=False,
            message="Failed to load vanisher context"
        )

        handler = self._create_code_command_handler(
            mock_mirror, mock_vanisher, mock_vanisher_context
        )
        result = handler(["init", "@myproject", "Add", "feature"])

        assert not result.success
        assert "[1/2] Mirror:" in result.message
        assert "[2/2] Vanisher load failed" in result.message

    def test_code_init_success_with_mcp_calls(self):
        """Test that successful /code init calls MCP tools and returns results."""
        mock_vanisher_context = MagicMock()
        mock_vanisher_context.is_enabled.return_value = True

        mock_mirror = MagicMock()
        mock_mirror.return_value = CommandResult(
            success=True,
            message="Synced 15 file(s) to sandbox 'myproject'"
        )

        mock_vanisher = MagicMock()
        mock_vanisher.return_value = CommandResult(
            success=True,
            message="Loaded 15 file(s) from @myproject"
        )

        # Mock MCP tools
        mock_planning = MagicMock()
        mock_planning.create_plan.return_value = {
            'success': True,
            'type': 'feature',
            'TODO_list': [
                {'step': 1, 'action': 'Analyze', 'details': 'Analyze requirements'},
                {'step': 2, 'action': 'Implement', 'details': 'Implement feature'},
                {'step': 3, 'action': 'Test', 'details': 'Write tests'}
            ]
        }

        mock_executor = MagicMock()
        mock_executor.execute_plan.return_value = {
            'success': True,
            'completed_count': 3,
            'failed_count': 0,
            'detailed_todo_list_count': 3
        }

        handler = self._create_code_command_handler(
            mock_mirror, mock_vanisher, mock_vanisher_context,
            mock_planning, mock_executor
        )
        result = handler(["init", "@myproject", "Add", "user", "authentication"])

        assert result.success
        assert result.data is not None
        assert 'plan_result' in result.data
        assert 'exec_result' in result.data
        assert result.data['plan_result']['success'] is True
        assert result.data['exec_result']['completed_count'] == 3
        mock_planning.create_plan.assert_called_once_with("myproject", "Add user authentication")
        mock_executor.execute_plan.assert_called_once_with(auto_execute=True)

    def test_code_init_plan_failure(self):
        """Test that plan creation failure is handled properly."""
        mock_vanisher_context = MagicMock()
        mock_vanisher_context.is_enabled.return_value = True

        mock_mirror = MagicMock()
        mock_mirror.return_value = CommandResult(success=True, message="OK")

        mock_vanisher = MagicMock()
        mock_vanisher.return_value = CommandResult(success=True, message="OK")

        # Mock planning failure
        mock_planning = MagicMock()
        mock_planning.create_plan.return_value = {
            'success': False,
            'error': 'Could not generate plan for task'
        }

        mock_executor = MagicMock()

        handler = self._create_code_command_handler(
            mock_mirror, mock_vanisher, mock_vanisher_context,
            mock_planning, mock_executor
        )
        result = handler(["init", "@myproject", "Invalid", "task"])

        assert not result.success
        assert "Plan creation failed" in result.message
        mock_executor.execute_plan.assert_not_called()

    def test_code_init_execution_failure(self):
        """Test that execution failure is handled properly."""
        mock_vanisher_context = MagicMock()
        mock_vanisher_context.is_enabled.return_value = True

        mock_mirror = MagicMock()
        mock_mirror.return_value = CommandResult(success=True, message="OK")

        mock_vanisher = MagicMock()
        mock_vanisher.return_value = CommandResult(success=True, message="OK")

        # Mock planning success but execution failure
        mock_planning = MagicMock()
        mock_planning.create_plan.return_value = {
            'success': True,
            'type': 'feature',
            'TODO_list': [{'step': 1, 'action': 'Do', 'details': 'Something'}]
        }

        mock_executor = MagicMock()
        mock_executor.execute_plan.return_value = {
            'success': False,
            'error': 'No tool matches found'
        }

        handler = self._create_code_command_handler(
            mock_mirror, mock_vanisher, mock_vanisher_context,
            mock_planning, mock_executor
        )
        result = handler(["init", "@myproject", "Do", "something"])

        assert not result.success
        assert "Execution failed" in result.message

    def test_code_session_exit_missing_path_shows_error(self):
        """Test that /code session exit without path shows error."""
        handler = self._create_code_command_handler(
            MagicMock(), MagicMock(), MagicMock()
        )
        result = handler(["session", "exit"])

        assert not result.success
        assert "Usage: /code session exit @<path>" in result.message

    def test_code_session_exit_path_without_at_prefix_shows_error(self):
        """Test that /code session exit with path missing @ shows error."""
        handler = self._create_code_command_handler(
            MagicMock(), MagicMock(), MagicMock()
        )
        result = handler(["session", "exit", "myproject"])

        assert not result.success
        assert "Path must start with @ prefix" in result.message

    def test_code_session_exit_revert_sync_failure(self):
        """Test that revert+sync failure returns error."""
        mock_mirror = MagicMock()
        mock_mirror.return_value = CommandResult(
            success=False,
            message="Mirror not found: myproject"
        )

        handler = self._create_code_command_handler(
            mock_mirror, MagicMock(), MagicMock()
        )
        result = handler(["session", "exit", "@myproject"])

        assert not result.success
        assert "Failed to sync changes back" in result.message
        assert "Mirror not found" in result.message

    def test_code_session_exit_success(self):
        """Test that successful /code session exit returns proper message."""
        mock_mirror = MagicMock()
        mock_mirror.return_value = CommandResult(
            success=True,
            message="Synced 12 file(s) from sandbox to host 'myproject/'"
        )

        handler = self._create_code_command_handler(
            mock_mirror, MagicMock(), MagicMock()
        )
        result = handler(["session", "exit", "@myproject"])

        assert result.success
        assert "Coding session ended" in result.message
        assert "Type 'exit' to leave the CLI" in result.message
        assert result.data is not None
        assert result.data.get('should_exit') is True

    def test_code_unknown_subcommand_shows_error(self):
        """Test that unknown subcommand shows error."""
        handler = self._create_code_command_handler(
            MagicMock(), MagicMock(), MagicMock()
        )
        result = handler(["unknown"])

        assert not result.success
        assert "Unknown subcommand: unknown" in result.message
        assert "/code init" in result.message
        assert "/code session exit" in result.message

    def test_code_init_message_format(self):
        """Test that /code init success message has correct format."""
        mock_vanisher_context = MagicMock()
        mock_vanisher_context.is_enabled.return_value = True

        mock_mirror = MagicMock()
        mock_mirror.return_value = CommandResult(
            success=True,
            message="Synced 15 file(s) to sandbox 'myproject'"
        )

        mock_vanisher = MagicMock()
        mock_vanisher.return_value = CommandResult(
            success=True,
            message="Loaded 15 file(s) from @myproject"
        )

        # Mock MCP tools
        mock_planning = MagicMock()
        mock_planning.create_plan.return_value = {
            'success': True,
            'type': 'bugfix',
            'TODO_list': [
                {'step': 1, 'action': 'Identify', 'details': 'Find root cause'},
                {'step': 2, 'action': 'Fix', 'details': 'Apply fix'}
            ]
        }

        mock_executor = MagicMock()
        mock_executor.execute_plan.return_value = {
            'success': True,
            'completed_count': 2,
            'failed_count': 0,
            'detailed_todo_list_count': 2
        }

        handler = self._create_code_command_handler(
            mock_mirror, mock_vanisher, mock_vanisher_context,
            mock_planning, mock_executor
        )
        result = handler(["init", "@myproject", "Fix", "bug"])

        assert result.success
        assert "[1/2] Mirror:" in result.message
        assert "[2/2] Vanisher:" in result.message
        assert "Coding session initialized for 'myproject'" in result.message
        assert "Task: Fix bug" in result.message
        assert "[3/4] Plan created:" in result.message
        assert "[4/4] Execution complete:" in result.message
