# Python Executor MCP

A Model Context Protocol server for code execution in vanisher directories.

## Overview

This MCP provides tools for writing, updating, and running code in isolated vanisher directories. It's designed to work in coding mode only.

## Tools

### Code Operations

- **write_code**: Write code to a file in a vanisher directory
- **update_code**: Update code by replacing a specific section
- **run_code**: Execute code and capture output

### Vanisher Management

- **list_vanishers**: List all vanisher directories
- **list_files**: List files in a vanisher directory
- **delete_vanisher**: Delete a vanisher directory

## Usage

```bash
python server.py
```

The server communicates via JSON-RPC over stdio.

## Example

```json
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
```
