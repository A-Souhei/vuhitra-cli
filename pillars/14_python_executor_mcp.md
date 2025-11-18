# Pillar 14: Using the Python Executor MCP

## Overview

The **Python Executor MCP** is a Model Context Protocol server that provides streamlined code execution capabilities in vanisher directories. It offers a focused set of tools for writing code, updating code, running tests, and managing dependencies.

This pillar document explains how to use the Python Executor MCP for code generation, testing and verification, and implementation plan execution.

## What is the Python Executor MCP?

The Python Executor MCP is a **stdio-based server** that exposes code execution tools through the Model Context Protocol. It provides a simplified interface compared to the full Executor MCP, focusing on the core development workflow:

**Key Capabilities**:
- **Code Generation** - Write new code files (full file overwrite)
- **Code Updates** - Apply targeted changes (search-and-replace)
- **Testing and Verification** - Run tests and validate implementations
- **Dependency Management** - Install packages with pip
- **Workspace Management** - List and manage vanisher directories

## Why Use the Python Executor MCP?

The Python Executor MCP implements key steps of the pillars methodology:

| Pillar Step | Python Executor Tool | Use Case |
|-------------|---------------------|----------|
| Step 1: Exploration | `list_vanishers`, `list_files` | Explore workspaces and codebase structure |
| Step 5: Code Generation | `write_code`, `update_code` | Generate code and apply changes |
| Step 6: Testing | `run_code` | Execute tests and verify implementations |

## Prerequisites

### 1. Set Up a Vanisher Directory

```bash
# Vanisher directories are automatically created when writing code
# The Python Executor will create the directory if it doesn't exist
```

### 2. Install MCP Dependencies

```bash
cd mcps/python_executor
pip install -r requirements.txt
```

## Using the Python Executor MCP

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

### Option 2: Direct Testing

```bash
python mcps/python_executor/server.py
```

Then send JSON-RPC requests via stdin.

## Tool Categories

The Python Executor MCP provides 7 tools in 2 categories:

### 1. Code Operations (4 tools)
- `write_code` - Full file overwrite for code generation
- `update_code` - Search-and-replace for targeted changes
- `run_code` - Execute code for testing and verification
- `pip_install` - Install Python packages

### 2. Vanisher Management (3 tools)
- `list_vanishers` - List available workspaces
- `list_files` - List files in a vanisher
- `delete_vanisher` - Remove vanisher directories

## Common Workflows

### Workflow 1: Code Generation - Create New File

**Goal**: Generate a new Python file as part of an implementation plan.

**Steps**:

```json
// Step 1: Write the new code file
{
  "tool": "write_code",
  "arguments": {
    "vanisher_name": "my-project",
    "filename": "src/calculator.py",
    "code": "def add(a: int, b: int) -> int:\n    \"\"\"Add two numbers.\"\"\"\n    return a + b\n\ndef subtract(a: int, b: int) -> int:\n    \"\"\"Subtract b from a.\"\"\"\n    return a - b"
  }
}
```

**Output**:
```json
{
  "success": true,
  "file_path": "/app/vanishers/my-project/src/calculator.py",
  "language": "python",
  "lines": 8,
  "size": 167
}
```

### Workflow 2: Code Update - Apply Targeted Changes

**Goal**: Fix a bug using search-and-replace pattern.

**Steps**:

```json
// Step 1: Update specific code section
{
  "tool": "update_code",
  "arguments": {
    "vanisher_name": "my-project",
    "filename": "src/calculator.py",
    "old_code": "def add(a: int, b: int) -> int:\n    \"\"\"Add two numbers.\"\"\"\n    return a + b",
    "new_code": "def add(a: int, b: int) -> int:\n    \"\"\"Add two numbers with validation.\"\"\"\n    if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):\n        raise TypeError(\"Arguments must be numbers\")\n    return a + b"
  }
}
```

### Workflow 3: Testing and Verification

**Goal**: Write tests and verify implementation.

**Steps**:

```json
// Step 1: Write test file
{
  "tool": "write_code",
  "arguments": {
    "vanisher_name": "my-project",
    "filename": "tests/test_calculator.py",
    "code": "import pytest\nfrom src.calculator import add, subtract\n\ndef test_add():\n    assert add(2, 3) == 5\n\ndef test_subtract():\n    assert subtract(5, 3) == 2\n\ndef test_add_type_error():\n    with pytest.raises(TypeError):\n        add('a', 'b')"
  }
}

// Step 2: Install test framework
{
  "tool": "pip_install",
  "arguments": {
    "vanisher_name": "my-project",
    "packages": ["pytest"]
  }
}

// Step 3: Run tests for verification
{
  "tool": "run_code",
  "arguments": {
    "vanisher_name": "my-project",
    "filename": "tests/test_calculator.py",
    "args": ["-v"]
  }
}
```

### Workflow 4: Complete Implementation Plan Execution

**Goal**: Implement a feature following the pillars methodology.

**Steps**:

```
1. list_files("my-project") → Explore existing structure
2. write_code("my-project", "src/auth.py", "<auth code>") → Code generation
3. pip_install("my-project", ["pyjwt", "bcrypt"]) → Install dependencies
4. write_code("my-project", "tests/test_auth.py", "<tests>") → Create tests
5. run_code("my-project", "tests/test_auth.py") → Testing and verification
```

## Integration with Other MCPs

The Python Executor MCP works best with:

### Mirror+Vanisher Development MCP (Planning)

```
1. create_plan("project", "Add authentication") → Get implementation plan
2. Use Python Executor to execute the plan:
   - write_code for code generation
   - update_code for targeted changes
   - run_code for testing and verification
```

### Executor MCP (Extended Operations)

For operations not covered by Python Executor:
- Building Docker images
- Complex directory operations
- Multi-file operations
- Build automation

## Code Quality Standards

When using the Python Executor MCP, follow these standards:

### For Code Generation (write_code)

- Follow project style conventions
- Include docstrings/comments for complex logic
- Handle errors appropriately
- Use proper type hints if applicable
- Ensure code is testable and maintainable

### For Code Updates (update_code)

- Only modify necessary lines - no unrelated changes
- Preserve existing code style and formatting
- Add comments for complex logic
- Include error handling where appropriate
- Follow project conventions

### For Testing (run_code)

- Run tests after every code change
- Test one thing per test - keep tests focused
- Use descriptive test names
- Follow Arrange-Act-Assert pattern
- Mock external dependencies

## Best Practices

### 1. Explore Before Implementing

```json
{"tool": "list_files", "arguments": {"vanisher_name": "my-project"}}
```

Understand the codebase structure before making changes.

### 2. Install Dependencies First

```json
{"tool": "pip_install", "arguments": {
  "vanisher_name": "my-project",
  "packages": ["pytest", "requests"]
}}
```

Set up the environment before code generation.

### 3. Write Tests Alongside Code

```json
// After writing implementation
{"tool": "write_code", "arguments": {
  "vanisher_name": "my-project",
  "filename": "tests/test_feature.py",
  "code": "<test code>"
}}
```

### 4. Verify Every Change

```json
{"tool": "run_code", "arguments": {
  "vanisher_name": "my-project",
  "filename": "tests/test_feature.py"
}}
```

### 5. Use Search-and-Replace for Bug Fixes

```json
{"tool": "update_code", "arguments": {
  "vanisher_name": "my-project",
  "filename": "src/buggy.py",
  "old_code": "return a + b  # Bug: should multiply",
  "new_code": "return a * b  # Fixed: now multiplies"
}}
```

## Troubleshooting

### "Vanisher directory not found"

**Cause**: The vanisher doesn't exist yet.

**Solution**: The `write_code` tool automatically creates vanisher directories:
```json
{"tool": "write_code", "arguments": {
  "vanisher_name": "new-project",
  "filename": "main.py",
  "code": "print('Hello')"
}}
```

### "Old code not found in file"

**Cause**: The old_code string doesn't match exactly.

**Solution**: Ensure exact match including whitespace:
- Copy the exact text from the file
- Check indentation (spaces vs tabs)
- Include newlines if present

### "Execution timed out"

**Cause**: Code execution exceeded timeout.

**Solution**: Increase timeout parameter:
```json
{"tool": "run_code", "arguments": {
  "vanisher_name": "my-project",
  "filename": "long_running.py",
  "timeout": 120
}}
```

### "Package installation failed"

**Cause**: Network issues or invalid package names.

**Solution**:
1. Check package name spelling
2. Verify network connectivity
3. Use specific versions: `["package==1.0.0"]`

## Coding Mode Behavior

Like other MCPs, the Python Executor MCP is **automatically managed by coding mode**:

- **Enabled** when `--coding` mode is ON
- **Disabled** when `--coding` mode is OFF
- **Cannot be manually toggled**

## Summary

The Python Executor MCP provides:

- **Code Generation** - Full file overwrite with `write_code`
- **Targeted Changes** - Search-and-replace with `update_code`
- **Testing and Verification** - Execute tests with `run_code`
- **Dependency Management** - Install packages with `pip_install`
- **Workspace Exploration** - List vanishers and files

**Use it to**: Execute implementation plans by writing code, applying targeted changes, installing dependencies, and running tests for verification.

**Key Workflow**:
1. Explore workspace with `list_files`
2. Generate code with `write_code`
3. Update code with `update_code`
4. Install dependencies with `pip_install`
5. Test and verify with `run_code`

**Next Steps**:
1. Create a vanisher directory by writing a file
2. Follow the pillars methodology for implementation
3. Write tests for testing and verification
4. Integrate with Mirror+Vanisher Development MCP for planning

---

*Part of the LLM Codebase Interaction Guide - Pillar 14*
