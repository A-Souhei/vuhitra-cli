#!/usr/bin/env python3
"""
Python Executor MCP Server

A Model Context Protocol server for code execution in vanisher directories.
Provides tools for writing, updating, and running code.

Available only in coding mode.
"""

import json
import sys
import os
import logging
from typing import Dict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from vanisher_manager import VanisherManager
from code_tools import CodeTools
from errors_handler import handle_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class PythonExecutorMCPServer:
    """MCP Server for Python code execution in vanisher directories."""

    def __init__(self):
        """Initialize the MCP server."""
        self.manager = VanisherManager()
        self.code_tools = CodeTools(self.manager)
        self.tools = self._register_tools()
        self.resources = self._register_resources()

        logger.info("PythonExecutorMCPServer initialized")

    def _register_tools(self) -> Dict[str, Dict]:
        """Register all available tools.

        Returns:
            Dictionary mapping tool names to their definitions
        """
        return {
            # Code Operations
            "write_code": {
                "description": """Write code to a file in a vanisher directory for code generation and implementation.

Creates a new file or performs a full file overwrite with the provided code content in a safe and traceable manner.
The vanisher directory will be automatically created if it doesn't exist.

This tool implements Step 5 (Code Generation) of the pillars methodology by providing full file overwrite capability for code generation tasks.

Use this tool when you need to:
- Generate new code files as part of an implementation plan
- Perform full file overwrite for small files or complete rewrites
- Create source files following project style conventions
- Implement new features by writing code to specific file paths
- Create test files for testing and verification workflows
- Write configuration files or scripts for automation
- Start a new coding project in a clean workspace

The tool automatically detects the programming language from the file extension
and reports useful metadata like file size and line count.

Code Quality Standards:
- Follow project style conventions
- Include docstrings/comments for complex logic
- Handle errors appropriately
- Use proper type hints if applicable
- Ensure code is testable and maintainable

Parameters:
- vanisher_name: Name of the vanisher directory (workspace)
- filename: Name of the file to create (can include subdirectories like 'src/main.py')
- code: The complete code content to write
- language: Optional language hint (auto-detected from extension if not provided)

Returns success status, file path, detected language, and file statistics. Essential for code generation workflows and implementation plan execution.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "vanisher_name": {
                            "type": "string",
                            "description": "Name of the vanisher directory"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Name of the file to create/write"
                        },
                        "code": {
                            "type": "string",
                            "description": "The code content to write"
                        },
                        "language": {
                            "type": "string",
                            "description": "Optional language hint (python, javascript, etc.)"
                        }
                    },
                    "required": ["vanisher_name", "filename", "code"]
                },
                "handler": self.code_tools.write_code
            },

            "update_code": {
                "description": """Update code in an existing file using search-and-replace pattern for targeted changes.

Performs a precise search-and-replace operation on existing code in a safe and traceable manner.
This implements the search-and-replace method from Step 5 (Code Generation) of the pillars methodology.

Use this tool when you need to:
- Apply targeted changes to specific code sections without full file overwrite
- Fix bugs by modifying only necessary lines
- Implement fixes from an implementation plan
- Update specific functions, classes, or code blocks
- Refactor particular code sections while preserving existing code style
- Modify imports, configuration, or specific logic
- Apply changes from unified diff or patch generation

The tool ensures the old_code exists exactly once in the file to prevent
accidental multiple replacements. If the old_code is not found or appears
multiple times, the operation will fail with helpful error messages.

Code Quality Standards:
- Only modify necessary lines - no unrelated changes
- Preserve existing code style and formatting
- Add comments for complex logic
- Include error handling where appropriate
- Follow project conventions

Parameters:
- vanisher_name: Name of the vanisher directory
- filename: Name of the file to update
- old_code: The exact code section to find and replace (must match perfectly)
- new_code: The replacement code

Returns success status and details about the change (lines affected, size change). Essential for implementing bug fixes and targeted refactoring.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "vanisher_name": {
                            "type": "string",
                            "description": "Name of the vanisher directory"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Name of the file to update"
                        },
                        "old_code": {
                            "type": "string",
                            "description": "The code section to find and replace"
                        },
                        "new_code": {
                            "type": "string",
                            "description": "The replacement code"
                        }
                    },
                    "required": ["vanisher_name", "filename", "old_code", "new_code"]
                },
                "handler": self.code_tools.update_code
            },

            "run_code": {
                "description": """Run code from a file in a vanisher directory for testing and verification.

Executes the code file using the appropriate interpreter based on file extension.
Captures both stdout and stderr output for analysis and verification.

This tool implements Step 6 (Testing and Verification) of the pillars methodology by providing code execution capability for running tests and validating implementations.

Supported file types:
- .py: Python (using python interpreter) - for unit tests, integration tests, and scripts
- .js: JavaScript (using node) - for Node.js tests and scripts
- .r, .R: R scripts (using Rscript) - for data analysis and statistical tests
- .sh, .bash: Shell scripts (using bash) - for automation and build scripts

Use this tool when you need to:
- Execute tests for testing and verification of implementations
- Run unit tests, integration tests, or edge case tests
- Validate code functionality after code generation
- Execute test commands (pytest, npm test, etc.)
- Verify changes by running test suites
- Run scripts and capture output for analysis
- Execute build or automation commands
- Validate implementations from implementation plans

The execution runs with a configurable timeout (default 30 seconds) to prevent
hanging processes. You can pass command-line arguments and custom environment
variables as needed.

Testing Best Practices:
- Run tests after every code change
- Capture output for verification
- Check exit codes for test pass/fail status
- Use timeouts to prevent hanging tests

Parameters:
- vanisher_name: Name of the vanisher directory
- filename: Name of the file to execute
- args: Optional list of command-line arguments
- timeout: Execution timeout in seconds (default: 30)
- env: Optional dictionary of environment variables

Returns exit code, stdout, stderr, and the command that was executed. Essential for testing and verification workflows and validating implementation plans.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "vanisher_name": {
                            "type": "string",
                            "description": "Name of the vanisher directory"
                        },
                        "filename": {
                            "type": "string",
                            "description": "Name of the file to run"
                        },
                        "args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional command-line arguments"
                        },
                        "timeout": {
                            "type": "integer",
                            "default": 30,
                            "description": "Execution timeout in seconds"
                        },
                        "env": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                            "description": "Optional environment variables"
                        }
                    },
                    "required": ["vanisher_name", "filename"]
                },
                "handler": self.code_tools.run_code
            },

            "pip_install": {
                "description": """Install Python packages using pip in a vanisher directory for dependency management.

Installs packages into the virtual environment if one exists in the vanisher
directory, otherwise uses the system pip. This is essential for setting up
project dependencies before code generation and testing workflows.

This tool supports the pillars methodology by enabling proper environment setup
for code execution, testing, and verification phases.

Use this tool when you need to:
- Install dependencies as part of an implementation plan
- Set up testing frameworks (pytest, unittest) for testing and verification
- Add packages required for code generation tasks
- Install libraries needed by generated code
- Set up the environment before running tests
- Add development dependencies for quality checks
- Install packages with version specifiers for reproducible builds

The tool automatically detects and uses the venv if present (checks venv,
.venv, env, .env directories). Installation has a longer default timeout
(300 seconds) to accommodate large packages.

Best Practices:
- Install dependencies early in implementation workflows
- Use version specifiers for reproducible environments
- Install test frameworks before running tests
- Use virtual environments for isolation

Parameters:
- vanisher_name: Name of the vanisher directory
- packages: List of package names to install (supports version specifiers like 'numpy>=1.20')
- timeout: Installation timeout in seconds (default: 300)

Returns exit code, stdout, stderr, and whether venv was used. Essential for setting up environments for code generation and testing workflows.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "vanisher_name": {
                            "type": "string",
                            "description": "Name of the vanisher directory"
                        },
                        "packages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of packages to install (e.g., ['requests', 'numpy>=1.20'])"
                        },
                        "timeout": {
                            "type": "integer",
                            "default": 300,
                            "description": "Installation timeout in seconds"
                        }
                    },
                    "required": ["vanisher_name", "packages"]
                },
                "handler": self.code_tools.pip_install
            },

            # Vanisher Management Tools
            "list_vanishers": {
                "description": """List all vanisher directories for exploring available workspaces.

Enumerates all vanisher workspaces available for code generation, testing, and execution.
Each vanisher is an isolated directory where you can write, update, and run code
following the pillars methodology.

This tool supports Step 1 (Exploration) by helping you discover available workspaces
for implementation plans and development workflows.

Use this tool when you need to:
- Explore available workspaces before starting an implementation plan
- See what vanisher directories exist for code generation
- Find workspaces ready for testing and verification
- Check vanisher directory contents
- Discover existing code projects
- Identify workspaces for new feature implementation

Returns a list of vanisher directories with their names, paths, and file counts. Essential for exploration and planning workflows.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "handler": self.manager.list_vanishers
            },

            "list_files": {
                "description": """List all files in a vanisher directory for exploring codebase structure.

Shows all files present in a specific vanisher workspace, including files
in subdirectories. Essential for understanding project structure before
code generation and identifying files for testing and verification.

This tool supports Step 1 (Exploration) of the pillars methodology by enabling
codebase exploration and file discovery within vanisher workspaces.

Use this tool when you need to:
- Explore codebase structure before implementing features
- See what files exist for understanding project organization
- Find specific files to modify in an implementation plan
- Check directory structure for architecture analysis
- Identify test files for testing and verification workflows
- Discover source files for code generation tasks
- Find files to read for context before making changes

Parameters:
- vanisher_name: Name of the vanisher directory to list

Returns a list of files with their names, full paths, and sizes. Essential for exploration and planning phases of development workflows.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "vanisher_name": {
                            "type": "string",
                            "description": "Name of the vanisher directory"
                        }
                    },
                    "required": ["vanisher_name"]
                },
                "handler": self.manager.list_files
            },

            "delete_vanisher": {
                "description": """Delete a vanisher directory and all its contents for workspace cleanup.

Permanently removes a vanisher workspace and all files within it. This action
cannot be undone, so use with caution.

Use this tool when you need to:
- Clean up temporary workspaces after completing implementation plans
- Remove obsolete vanisher directories
- Free up disk space after testing and verification is complete
- Reset a workspace completely for new projects
- Remove failed or abandoned code generation attempts
- Clean up after build and test cycles

Parameters:
- name: Name of the vanisher directory to delete

Returns success status and confirmation message. Use as part of cleanup phase in development workflows.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the vanisher directory to delete"
                        }
                    },
                    "required": ["name"]
                },
                "handler": self.manager.delete_vanisher
            }
        }

    def _register_resources(self) -> Dict[str, Dict]:
        """Register available resources.

        Returns:
            Dictionary mapping resource names to their definitions
        """
        return {}

    def handle_request(self, request: Dict) -> Dict:
        """Handle a JSON-RPC request.

        Args:
            request: The JSON-RPC request

        Returns:
            JSON-RPC response
        """
        method = request.get('method', '')
        params = request.get('params', {})
        request_id = request.get('id')

        try:
            if method == 'initialize':
                result = {
                    'protocolVersion': '2024-11-05',
                    'capabilities': {
                        'tools': {},
                        'resources': {}
                    },
                    'serverInfo': {
                        'name': 'python-executor',
                        'version': '1.0.0'
                    }
                }

            elif method == 'notifications/initialized':
                # Client acknowledged initialization
                return None

            elif method == 'tools/list':
                tools_list = []
                for name, tool in self.tools.items():
                    tools_list.append({
                        'name': name,
                        'description': tool['description'],
                        'inputSchema': tool['inputSchema']
                    })
                result = {'tools': tools_list}

            elif method == 'tools/call':
                tool_name = params.get('name')
                arguments = params.get('arguments', {})

                if tool_name not in self.tools:
                    return {
                        'jsonrpc': '2.0',
                        'id': request_id,
                        'error': {
                            'code': -32601,
                            'message': f'Unknown tool: {tool_name}'
                        }
                    }

                handler = self.tools[tool_name]['handler']
                tool_result = handler(**arguments)

                result = {
                    'content': [
                        {
                            'type': 'text',
                            'text': json.dumps(tool_result, indent=2)
                        }
                    ]
                }

            elif method == 'resources/list':
                result = {'resources': []}

            else:
                return {
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'error': {
                        'code': -32601,
                        'message': f'Method not found: {method}'
                    }
                }

            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'result': result
            }

        except Exception as e:
            handle_exception(e, context={
                'function': 'handle_request',
                'method': method
            })
            return {
                'jsonrpc': '2.0',
                'id': request_id,
                'error': {
                    'code': -32603,
                    'message': str(e)
                }
            }

    def run(self):
        """Run the MCP server using stdio transport."""
        logger.info("Starting Python Executor MCP server...")

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
                response = self.handle_request(request)

                if response:
                    print(json.dumps(response), flush=True)

            except json.JSONDecodeError as e:
                error_response = {
                    'jsonrpc': '2.0',
                    'id': None,
                    'error': {
                        'code': -32700,
                        'message': f'Parse error: {str(e)}'
                    }
                }
                print(json.dumps(error_response), flush=True)

            except Exception as e:
                handle_exception(e, context={'function': 'run'})
                error_response = {
                    'jsonrpc': '2.0',
                    'id': None,
                    'error': {
                        'code': -32603,
                        'message': f'Internal error: {str(e)}'
                    }
                }
                print(json.dumps(error_response), flush=True)


def main():
    """Main entry point."""
    server = PythonExecutorMCPServer()
    server.run()


if __name__ == '__main__':
    main()
