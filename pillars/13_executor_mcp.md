# Pillar 13: Using the Executor MCP

## Overview

The **Executor MCP** is a Model Context Protocol server that provides LLM-driven code execution and file operation capabilities on directories that are both **mirrored** (synced to sandbox) and **vanishers** (loaded into LLM context).

This pillar document explains how to use the Executor MCP to execute code, create/update files, build projects, install packages, and manage directories.

## What is the Executor MCP?

The Executor MCP is a **stdio-based server** that exposes execution tools through the Model Context Protocol. It complements the [Mirror+Vanisher Development MCP](12_mcp_usage.md) by providing execution capabilities:

**Mirror+Vanisher Development MCP** (Pillar 12):
- **PLANS** the work
- Explores codebases
- Analyzes architecture
- Creates implementation plans
- Generates test strategies

**Executor MCP** (This pillar):
- **EXECUTES** the work
- Runs code and scripts
- Creates and updates files
- Builds and compiles projects
- Installs packages
- Manages directories

## Why Use the Executor MCP?

The Executor MCP allows LLMs to:

- **Execute code** - Run Python, JavaScript, and shell scripts
- **Create files** - Generate new source files with code
- **Update files** - Modify existing code files with backups
- **Build projects** - Compile code and build applications
- **Install packages** - Add Python (pip) and Node.js (npm) dependencies
- **Manage directories** - Create, copy, move, and delete directory structures
- **Perform file operations** - Create, update, append, copy, move, and delete files

## Prerequisites

### 1. Set Up a Mirror+Vanisher Directory

```bash
# Step 1: Mirror your project
/mirror do @my-project

# Step 2: Load it as a vanisher
/vanisher load @my-project my-project "My project for execution"

# Step 3: Verify it's properly set up (use MCP tool)
```

### 2. Install MCP Dependencies

```bash
cd mcps/executor
pip install -r requirements.txt
```

## Using the Executor MCP

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

Then in Claude Desktop, the MCP tools will be available automatically.

### Option 2: Direct Testing

```bash
python mcps/executor/server.py
```

Then send JSON-RPC requests via stdin.

## Tool Categories

The Executor MCP provides 26 tools organized into 5 categories:

### 1. Mirror+Vanisher Management (2 tools)
- `list_mirror_vanishers` - List available directories
- `verify_mirror_vanisher` - Verify directory setup

### 2. Code Execution (4 tools)
- `execute_python_code` - Run Python scripts
- `execute_javascript_code` - Run JavaScript/Node.js scripts
- `execute_shell_command` - Execute shell commands
- `execute_code_snippet` - Run code snippets dynamically

### 3. File Operations (6 tools)
- `create_file` - Create new files
- `update_file` - Update existing files
- `append_to_file` - Append content
- `delete_file` - Delete with backup
- `copy_file` - Copy files
- `move_file` - Move/rename files

### 4. Build & Package Management (8 tools)
- `install_pip_packages` - Install Python packages
- `install_npm_packages` - Install Node.js packages
- `run_build_command` - Run build tools
- `compile_python` - Compile Python bytecode
- `create_virtual_env` - Create Python venv
- `install_in_virtual_env` - Install packages in venv
- `run_in_virtual_env` - Run commands in venv
- `run_docker_build` - Build Docker images

### 5. Directory Operations (6 tools)
- `create_directory` - Create directories
- `create_directory_structure` - Create directory trees
- `delete_directory` - Delete with backup
- `copy_directory` - Copy directory trees
- `move_directory` - Move/rename directories
- `list_directory_contents` - List contents

## Common Workflows

### Workflow 1: Create and Execute a New Script

**Goal**: Create a new Python script and run it.

**Steps**:

```json
// Step 1: Create the file
{
  "tool": "create_file",
  "arguments": {
    "path": "my-project",
    "file_path": "src/hello.py",
    "content": "def main():\n    print('Hello from Executor MCP!')\n\nif __name__ == '__main__':\n    main()",
    "overwrite": false
  }
}

// Step 2: Execute the script
{
  "tool": "execute_python_code",
  "arguments": {
    "path": "my-project",
    "script_path": "src/hello.py"
  }
}
```

**Output**:
```json
{
  "success": true,
  "return_code": 0,
  "stdout": "Hello from Executor MCP!\n",
  "stderr": "",
  "command": "python3 src/hello.py",
  "working_directory": "/app/WORKSPACE/mirrors/my-project"
}
```

### Workflow 2: Install Dependencies and Build

**Goal**: Install project dependencies and build the project.

**Steps**:

```json
// Step 1: Install Python packages from requirements.txt
{
  "tool": "install_pip_packages",
  "arguments": {
    "path": "my-project",
    "requirements_file": "requirements.txt"
  }
}

// Step 2: Run tests
{
  "tool": "execute_shell_command",
  "arguments": {
    "path": "my-project",
    "command": "pytest tests/"
  }
}

// Step 3: Run build command
{
  "tool": "run_build_command",
  "arguments": {
    "path": "my-project",
    "build_command": "python setup.py build"
  }
}
```

### Workflow 3: Create Project Structure

**Goal**: Initialize a new project with proper directory structure.

**Steps**:

```json
// Step 1: Create directory structure
{
  "tool": "create_directory_structure",
  "arguments": {
    "path": "my-project",
    "structure": {
      "src": {
        "components": {},
        "utils": {},
        "models": {}
      },
      "tests": {
        "unit": {},
        "integration": {}
      },
      "docs": {},
      "scripts": {}
    }
  }
}

// Step 2: Create main entry point
{
  "tool": "create_file",
  "arguments": {
    "path": "my-project",
    "file_path": "src/main.py",
    "content": "#!/usr/bin/env python3\n\"\"\"Main entry point.\"\"\"\n\ndef main():\n    print('Application started')\n\nif __name__ == '__main__':\n    main()"
  }
}

// Step 3: Create requirements file
{
  "tool": "create_file",
  "arguments": {
    "path": "my-project",
    "file_path": "requirements.txt",
    "content": "pytest>=7.0.0\nrequests>=2.32.0"
  }
}
```

### Workflow 4: Update Existing Code

**Goal**: Update an existing file and test it.

**Steps**:

```json
// Step 1: Read the current file (use vanisher context)
// Step 2: Update the file with new code
{
  "tool": "update_file",
  "arguments": {
    "path": "my-project",
    "file_path": "src/calculator.py",
    "content": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n\ndef multiply(a, b):\n    return a * b",
    "backup": true
  }
}

// Step 3: Run tests for the updated file
{
  "tool": "execute_shell_command",
  "arguments": {
    "path": "my-project",
    "command": "pytest tests/test_calculator.py -v"
  }
}
```

### Workflow 5: Execute Code Snippet for Testing

**Goal**: Test a code snippet without creating a permanent file.

**Steps**:

```json
{
  "tool": "execute_code_snippet",
  "arguments": {
    "path": "my-project",
    "language": "python",
    "code": "import sys\nprint(f'Python version: {sys.version}')\nprint('Environment variables loaded successfully')"
  }
}
```

### Workflow 6: Build and Package Application

**Goal**: Build a Docker image for the application.

**Steps**:

```json
// Step 1: Create Dockerfile
{
  "tool": "create_file",
  "arguments": {
    "path": "my-project",
    "file_path": "Dockerfile",
    "content": "FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nCMD [\"python\", \"src/main.py\"]"
  }
}

// Step 2: Build Docker image
{
  "tool": "run_docker_build",
  "arguments": {
    "path": "my-project",
    "dockerfile": "Dockerfile",
    "tag": "my-app:latest"
  }
}
```

## Integration with Mirror+Vanisher Development MCP

For complete development workflows, use both MCPs together:

### Phase 1: Planning (Mirror+Vanisher Development MCP)

```json
// 1. Explore the codebase
{"tool": "full_exploration", "arguments": {"path": "my-project"}}

// 2. Analyze architecture
{"tool": "analyze_architecture", "arguments": {"path": "my-project"}}

// 3. Create implementation plan
{"tool": "create_plan", "arguments": {
  "path": "my-project",
  "task": "Add user authentication feature"
}}

// 4. Generate code diff (preview)
{"tool": "generate_diff", "arguments": {
  "file_path": "my-project/src/auth.py",
  "changes": "Add login and logout functions"
}}
```

### Phase 2: Execution (Executor MCP)

```json
// 5. Create new authentication file
{"tool": "create_file", "arguments": {
  "path": "my-project",
  "file_path": "src/auth.py",
  "content": "<generated code from planning phase>"
}}

// 6. Install required packages
{"tool": "install_pip_packages", "arguments": {
  "path": "my-project",
  "packages": ["pyjwt", "bcrypt"]
}}

// 7. Execute tests
{"tool": "execute_shell_command", "arguments": {
  "path": "my-project",
  "command": "pytest tests/test_auth.py"
}}

// 8. Run build
{"tool": "run_build_command", "arguments": {
  "path": "my-project",
  "build_command": "python setup.py build"
}}
```

### Phase 3: Quality Assurance (Mirror+Vanisher Development MCP)

```json
// 9. Run quality checks
{"tool": "full_quality_check", "arguments": {
  "path": "my-project",
  "fix": true
}}

// 10. Security audit
{"tool": "security_audit", "arguments": {"path": "my-project"}}
```

## Safety Features

The Executor MCP includes multiple safety mechanisms:

### Automatic Backups
- File updates create timestamped backups
- File deletions save backup copies
- Directory deletions create zip archives

### Overwrite Protection
- Files cannot be overwritten without explicit flag
- Directories protected from accidental replacement

### Timeout Limits
- Code execution has configurable timeouts
- Default 30s for scripts, 300s for builds
- Prevents runaway processes

### Error Handling
- All operations return detailed error messages
- Exceptions logged with context
- Failures don't crash the MCP server

### Path Validation
- All paths resolved and validated
- Mirror+vanisher verification required
- Prevents access outside workspace

## Best Practices

### 1. Always Verify First

```json
{"tool": "verify_mirror_vanisher", "arguments": {"path": "my-project"}}
```

Ensure the directory is properly set up before executing operations.

### 2. Use Backups for Destructive Operations

```json
{"tool": "update_file", "arguments": {
  "path": "my-project",
  "file_path": "important.py",
  "content": "...",
  "backup": true  // Always true for important files
}}
```

### 3. Test Before Building

```json
// Run tests first
{"tool": "execute_shell_command", "arguments": {
  "path": "my-project",
  "command": "pytest"
}}

// Then build
{"tool": "run_build_command", "arguments": {
  "path": "my-project",
  "build_command": "make"
}}
```

### 4. Use Code Snippets for Experiments

```json
{"tool": "execute_code_snippet", "arguments": {
  "path": "my-project",
  "language": "python",
  "code": "# Quick test without creating files"
}}
```

### 5. Install Dependencies Early

```json
// Install before execution
{"tool": "install_pip_packages", "arguments": {
  "path": "my-project",
  "requirements_file": "requirements.txt"
}}
```

### 6. Create Virtual Environments

```json
// Isolate dependencies
{"tool": "create_virtual_env", "arguments": {
  "path": "my-project",
  "venv_name": "venv"
}}
```

## Complete Development Example

Here's a complete example of using both MCPs to add a feature:

### Step 1: Planning Phase

```
1. explore_structure("my-project") → Understand layout
2. detect_tech_stack("my-project") → Identify Python + Flask
3. create_plan("my-project", "Add REST API endpoint") → Get plan
```

### Step 2: Execution Phase

```
4. create_file("my-project", "src/api.py", "<code>") → Create API file
5. update_file("my-project", "src/main.py", "<updated>") → Update main
6. install_pip_packages("my-project", ["flask-restful"]) → Add dependencies
```

### Step 3: Testing Phase

```
7. create_file("my-project", "tests/test_api.py", "<tests>") → Create tests
8. execute_shell_command("my-project", "pytest tests/") → Run tests
9. execute_python_code("my-project", "src/main.py") → Test manually
```

### Step 4: Quality Phase

```
10. full_quality_check("my-project", fix=true) → Lint + format + types
11. security_audit("my-project") → Check security
12. run_tests("my-project") → Final validation
```

### Step 5: Build Phase

```
13. run_build_command("my-project", "python setup.py build") → Build
14. run_docker_build("my-project") → Create container
```

## Troubleshooting

### "Path not found or not a valid mirror+vanisher"

**Cause**: Directory is not both mirrored and vanisher.

**Solution**:
```bash
/mirror do @your-project
/vanisher load @your-project your-project "Description"
```

### "Execution timed out"

**Cause**: Code execution exceeded timeout limit.

**Solution**: Increase timeout parameter:
```json
{"tool": "execute_python_code", "arguments": {
  "timeout": 60  // Increase from default 30s
}}
```

### "Permission denied" errors

**Cause**: File or directory permissions issues.

**Solution**: Check workspace permissions and ensure files are writable.

### "Package installation failed"

**Cause**: Missing dependencies or network issues.

**Solution**:
1. Check internet connectivity
2. Verify package names
3. Check requirements.txt syntax

## Coding Mode Behavior

Like the Mirror+Vanisher Development MCP, the Executor MCP is **automatically managed by coding mode**:

- **Enabled** when `--coding` mode is ON
- **Disabled** when `--coding` mode is OFF
- **Cannot be manually toggled**

This ensures execution capabilities are only available when working on code projects.

## Summary

The Executor MCP provides:

✅ **Code Execution** - Run scripts in multiple languages
✅ **File Operations** - Create, update, delete, copy, move files
✅ **Build Tools** - Compile, build, package applications
✅ **Package Management** - Install pip and npm packages
✅ **Directory Management** - Create, organize, manage folders
✅ **Safety Features** - Backups, timeouts, validation
✅ **Integration** - Works seamlessly with Mirror+Vanisher Development MCP

**Use it to**: Execute code, create/update files, build projects, install packages, manage directories—all within directories that are both mirrored to sandbox and loaded into LLM context.

**Next Steps**:
1. Set up a mirror+vanisher directory
2. Install Executor MCP dependencies
3. Try the example workflows above
4. Integrate with Mirror+Vanisher Development MCP
5. Build complete features using both MCPs!
