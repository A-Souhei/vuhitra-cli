# Executor MCP

**Executor MCP** is a Model Context Protocol (MCP) server that provides code execution and file operation capabilities for directories that are both **mirrors** (synced to sandbox) and **vanishers** (loaded into LLM context).

## Overview

While the [Mirror+Vanisher Development MCP](../mirror_vanisher_dev) focuses on **planning** (exploration, architecture analysis, planning, testing frameworks), the **Executor MCP** focuses on **execution**:

- **Execute code** (Python, JavaScript, shell commands)
- **Create and update files** with code
- **Build and compile** projects
- **Install packages** (pip, npm)
- **Manage directories** (create, copy, move, delete)
- **Perform file operations** (create, update, append, copy, move, delete)

## Key Features

### Code Execution
- Execute Python scripts with arguments
- Run JavaScript/Node.js programs
- Execute shell commands and bash scripts
- Run code snippets dynamically

### File Operations
- Create new files with content
- Update existing files with backups
- Append content to files
- Delete files with backup safety
- Copy and move files

### Build & Compile
- Install Python packages (pip)
- Install Node.js packages (npm)
- Run build commands (make, gradle, maven, etc.)
- Compile Python code to bytecode
- Create Python virtual environments
- Build Docker images

### Directory Management
- Create directories and directory structures
- Delete directories with backups
- Copy and move directory trees
- List directory contents

## Installation

```bash
cd mcps/executor
pip install -r requirements.txt
```

## Usage

### Option 1: Stdio Mode (with Claude Desktop)

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "executor": {
      "command": "python",
      "args": ["/path/to/vuhitra-cli/mcps/executor/server.py"]
    }
  }
}
```

### Option 2: Command Line Testing

```bash
# Test the MCP server
python server.py
```

Then send JSON-RPC requests via stdin:

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
```

## Available Tools

### Mirror+Vanisher Management (2 tools)
- `list_mirror_vanishers` - List all mirror+vanisher directories
- `verify_mirror_vanisher` - Verify directory setup

### Code Execution (4 tools)
- `execute_python_code` - Run Python scripts
- `execute_javascript_code` - Run JavaScript/Node.js scripts
- `execute_shell_command` - Execute shell commands
- `execute_code_snippet` - Run code snippets dynamically

### File Operations (6 tools)
- `create_file` - Create new files
- `update_file` - Update existing files
- `append_to_file` - Append to files
- `delete_file` - Delete files with backup
- `copy_file` - Copy files
- `move_file` - Move/rename files

### Build Operations (6 tools)
- `install_pip_packages` - Install Python packages
- `install_npm_packages` - Install Node.js packages
- `run_build_command` - Run build tools
- `compile_python` - Compile Python to bytecode
- `create_virtual_env` - Create Python venv
- `run_docker_build` - Build Docker images

### Directory Operations (6 tools)
- `create_directory` - Create directories
- `create_directory_structure` - Create directory trees
- `delete_directory` - Delete directories with backup
- `copy_directory` - Copy directory trees
- `move_directory` - Move/rename directories
- `list_directory_contents` - List directory contents

**Total: 24 tools**

## Example Workflows

### Execute Python Script

```json
{
  "tool": "execute_python_code",
  "arguments": {
    "path": "my-project",
    "script_path": "main.py",
    "args": ["--verbose"],
    "timeout": 30
  }
}
```

### Create and Run a New File

```json
// Step 1: Create file
{
  "tool": "create_file",
  "arguments": {
    "path": "my-project",
    "file_path": "src/hello.py",
    "content": "print('Hello from Executor MCP!')",
    "overwrite": false
  }
}

// Step 2: Execute it
{
  "tool": "execute_python_code",
  "arguments": {
    "path": "my-project",
    "script_path": "src/hello.py"
  }
}
```

### Install Dependencies and Build

```json
// Step 1: Install Python packages
{
  "tool": "install_pip_packages",
  "arguments": {
    "path": "my-project",
    "requirements_file": "requirements.txt"
  }
}

// Step 2: Run build
{
  "tool": "run_build_command",
  "arguments": {
    "path": "my-project",
    "build_command": "python setup.py build"
  }
}
```

### Create Project Structure

```json
{
  "tool": "create_directory_structure",
  "arguments": {
    "path": "my-project",
    "structure": {
      "src": {
        "components": {},
        "utils": {}
      },
      "tests": {},
      "docs": {}
    }
  }
}
```

## Coding Mode Integration

Like the Mirror+Vanisher Development MCP, the Executor MCP is designed to work in **coding mode only**:

- **Enabled** when coding mode is ON
- **Disabled** when coding mode is OFF
- Cannot be manually toggled

This ensures execution capabilities are only available when working on code projects, maintaining a clean separation between planning and execution phases.

## Workflow with Mirror+Vanisher Development MCP

For best results, use both MCPs together:

1. **Mirror+Vanisher Development MCP**: Plan
   - Explore codebase structure
   - Analyze architecture
   - Create implementation plans
   - Generate test strategies

2. **Executor MCP**: Execute
   - Create new files with code
   - Update existing code files
   - Execute scripts and tests
   - Build and compile
   - Install dependencies

## Safety Features

- **Automatic backups** before file/directory deletions
- **Overwrite protection** for files and directories
- **Timeout limits** for code execution
- **Error handling** with detailed logging
- **Validation** of paths and operations

## Requirements

- Python 3.8+
- requests>=2.32.0
- pyyaml>=6.0
- pathlib>=1.0.1
- flask>=3.0.0 (for web UI, optional)

## Architecture

```
mcps/executor/
├── server.py                   # Main MCP server
├── src/
│   ├── __init__.py
│   ├── errors_handler.py       # Error handling
│   ├── mirror_vanisher.py      # Mirror+Vanisher management
│   ├── code_execution.py       # Code execution tools
│   ├── file_operations.py      # File operation tools
│   ├── build_operations.py     # Build and compile tools
│   └── directory_operations.py # Directory management tools
├── requirements.txt
└── README.md
```

## Contributing

See the main project [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

See [LICENSE](../../LICENSE) for details.

## Related Documentation

- [Pillar 13: Using the Executor MCP](../../pillars/13_executor_mcp.md)
- [Executor MCP Usage Guide](../../docs/executor_mcp_usage_guide.md)
- [Mirror+Vanisher Development MCP](../mirror_vanisher_dev/README.md)
- [Pillar 12: Using the Mirror+Vanisher Development MCP](../../pillars/12_mcp_usage.md)
