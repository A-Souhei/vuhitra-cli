#!/usr/bin/env python3
"""
Python Executor MCP Server

A Model Context Protocol server for code execution in vanisher directories.
Provides tools for writing, updating, and running code.

Available only in coding mode.
"""

import json
import sys
import logging
from typing import Dict, Any

# Add src to path
sys.path.insert(0, 'src')

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
                "description": """Write code to a file in a vanisher directory.

Creates a new file or overwrites an existing file with the provided code content.
The vanisher directory will be automatically created if it doesn't exist.

Use this tool when you need to:
- Create a new code file from scratch
- Completely replace the contents of an existing file
- Start a new coding project in a clean workspace

The tool automatically detects the programming language from the file extension
and reports useful metadata like file size and line count.

Parameters:
- vanisher_name: Name of the vanisher directory (workspace)
- filename: Name of the file to create (can include subdirectories like 'src/main.py')
- code: The complete code content to write
- language: Optional language hint (auto-detected from extension if not provided)

Returns success status, file path, detected language, and file statistics.""",
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
                "description": """Update code in an existing file by replacing a specific section.

Performs a precise find-and-replace operation on existing code. This is useful
for making targeted modifications without rewriting the entire file.

Use this tool when you need to:
- Fix a bug in existing code
- Update a specific function or class
- Modify imports or configuration
- Refactor a particular code section

The tool ensures the old_code exists exactly once in the file to prevent
accidental multiple replacements. If the old_code is not found or appears
multiple times, the operation will fail with helpful error messages.

Parameters:
- vanisher_name: Name of the vanisher directory
- filename: Name of the file to update
- old_code: The exact code section to find and replace (must match perfectly)
- new_code: The replacement code

Returns success status and details about the change (lines affected, size change).""",
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
                "description": """Run code from a file in a vanisher directory.

Executes the code file using the appropriate interpreter based on file extension.
Captures both stdout and stderr output for analysis.

Supported file types:
- .py: Python (using python interpreter)
- .js: JavaScript (using node)
- .r, .R: R scripts (using Rscript)
- .sh, .bash: Shell scripts (using bash)

Use this tool when you need to:
- Test code you've written
- Run scripts and capture output
- Execute build or test commands
- Validate code functionality

The execution runs with a configurable timeout (default 30 seconds) to prevent
hanging processes. You can pass command-line arguments and custom environment
variables as needed.

Parameters:
- vanisher_name: Name of the vanisher directory
- filename: Name of the file to execute
- args: Optional list of command-line arguments
- timeout: Execution timeout in seconds (default: 30)
- env: Optional dictionary of environment variables

Returns exit code, stdout, stderr, and the command that was executed.""",
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

            # Vanisher Management
            "list_vanishers": {
                "description": """List all vanisher directories.

Returns a list of all vanisher directories that have been created,
along with their file counts. Use this to see available workspaces
and their contents.

Returns list of vanisher names, paths, and file counts.""",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                },
                "handler": self.manager.list_vanishers
            },

            "list_files": {
                "description": """List all files in a vanisher directory.

Returns a detailed list of all files in a specific vanisher directory,
including their relative paths and sizes. Useful for exploring the
workspace contents.

Parameters:
- vanisher_name: Name of the vanisher directory to list

Returns list of files with names, paths, and sizes.""",
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
                "description": """Delete a vanisher directory and all its contents.

Permanently removes a vanisher directory and all files within it.
Use with caution as this operation cannot be undone.

Parameters:
- name: Name of the vanisher directory to delete

Returns success status and confirmation message.""",
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
