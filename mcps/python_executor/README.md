# Python Executor MCP

A Model Context Protocol server for code execution in vanisher directories.

## Overview

This MCP provides tools for writing, updating, and running code in isolated vanisher directories. It's designed to work in coding mode only.

## Features

- Auto-detects and uses venv for Python (venv, .venv, env, .env)
- Supports Python (.py), JavaScript (.js), R (.r, .R), Shell (.sh, .bash)
- 300 second timeout for package installation

## Tools

### Code Operations (4 tools)

- **write_code**: Write code to a file in a vanisher directory
- **update_code**: Update code by replacing a specific section
- **run_code**: Execute code and capture output
- **pip_install**: Install Python packages using pip

### Vanisher Management (3 tools)

- **list_vanishers**: List all vanisher directories
- **list_files**: List files in a vanisher directory
- **delete_vanisher**: Delete a vanisher directory

**Total: 7 tools**

## Installation

```bash
cd mcps/python_executor
pip install -r requirements.txt
```

## Usage

### Option 1: Stdio Mode (with Claude Desktop)

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "python-executor": {
      "command": "python",
      "args": ["/path/to/vuhitra-cli/mcps/python_executor/server.py"]
    }
  }
}
```

### Option 2: Command Line Testing

```bash
python server.py
```

The server communicates via JSON-RPC over stdio.

## Example Workflows

### Write and Run Code

```json
// Step 1: Write code
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "write_code",
    "arguments": {
      "vanisher_name": "my-project",
      "filename": "main.py",
      "code": "print('Hello, World!')"
    }
  }
}

// Step 2: Run code
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "run_code",
    "arguments": {
      "vanisher_name": "my-project",
      "filename": "main.py"
    }
  }
}
```

### Install Packages and Run

```json
// Step 1: Install packages
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "pip_install",
    "arguments": {
      "vanisher_name": "my-project",
      "packages": ["requests", "numpy>=1.20"]
    }
  }
}

// Step 2: Write code using packages
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "write_code",
    "arguments": {
      "vanisher_name": "my-project",
      "filename": "fetch.py",
      "code": "import requests\nresponse = requests.get('https://api.github.com')\nprint(response.status_code)"
    }
  }
}

// Step 3: Run code
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "run_code",
    "arguments": {
      "vanisher_name": "my-project",
      "filename": "fetch.py"
    }
  }
}
```

## Architecture

```
mcps/python_executor/
├── server.py              # Main MCP server
├── requirements.txt       # Dependencies
├── README.md             # This file
└── src/
    ├── __init__.py
    ├── errors_handler.py  # Error handling
    ├── vanisher_manager.py # Vanisher directory management
    └── code_tools.py      # Code operations tools
```

## Related Documentation

- [Executor MCP](../executor/README.md)
- [Mirror+Vanisher Development MCP](../mirror_vanisher_dev/README.md)
