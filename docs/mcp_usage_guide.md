# Mirror+Vanisher Development MCP Usage Guide

Complete guide for using the Mirror+Vanisher Development MCP server to perform LLM-driven development operations.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup](#setup)
3. [Core Concepts](#core-concepts)
4. [Tool Categories](#tool-categories)
5. [Workflows](#workflows)
6. [Examples](#examples)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

Before using the MCP, you need:

1. **A directory that is both**:
   - **Mirrored**: Synced to sandbox (`/mirror do @<path>`)
   - **Vanisher**: Loaded into context (`/vanisher load @<path>`)

2. **Python 3.8+** installed

3. **MCP dependencies** installed:
   ```bash
   cd mcps/mirror_vanisher_dev
   pip install -r requirements.txt
   ```

## Setup

### Creating a Mirror+Vanisher Directory

```bash
# 1. Mirror your project directory
/mirror do @my-project

# 2. Load it as a vanisher
/vanisher load @my-project my-project "My project for development"

# 3. Verify it's properly set up
# Use the MCP tool: verify_mirror_vanisher with path "my-project"
```

### Starting the MCP Server

#### Stdio Mode (for Claude Desktop)

```bash
python mcps/mirror_vanisher_dev/server.py
```

#### Web UI Mode

```bash
python mcps/mirror_vanisher_dev/ui_server.py
# Open http://localhost:5100
```

## Core Concepts

### The 8 Pillars

The MCP implements all 8 steps of the development methodology:

1. **Exploration** - Understand the codebase structure
2. **Architecture** - Analyze patterns and dependencies
3. **Chunking** - Break large files into manageable pieces
4. **Planning** - Create implementation plans
5. **Code Generation** - Generate and apply changes
6. **Testing** - Create and run tests
7. **Quality** - Run linters, formatters, type checkers
8. **Security** - Scan for secrets and vulnerabilities

### Tool Types

- **Atomic Tools**: Perform a single specific operation
- **Combined Tools**: Execute multiple related operations
- **Workflow Tools**: Complete end-to-end processes

## Tool Categories

### 1. Mirror+Vanisher Management

#### `list_mirror_vanishers`

List all directories that are both mirrors and vanishers.

```json
{
  "method": "tools/call",
  "params": {
    "name": "list_mirror_vanishers",
    "arguments": {}
  }
}
```

**Returns**:
```json
{
  "success": true,
  "count": 2,
  "mirror_vanishers": [
    {
      "name": "my-project",
      "file_count": 42,
      "sync_status": "synced",
      "path": "/app/WORKSPACE/mirrors/my-project"
    }
  ]
}
```

#### `verify_mirror_vanisher`

Verify a directory is properly set up as both mirror and vanisher.

```json
{
  "method": "tools/call",
  "params": {
    "name": "verify_mirror_vanisher",
    "arguments": {
      "path": "my-project"
    }
  }
}
```

### 2. Exploration Tools

#### `explore_structure`

Generate directory tree view.

```json
{
  "method": "tools/call",
  "params": {
    "name": "explore_structure",
    "arguments": {
      "path": "my-project",
      "max_depth": 3
    }
  }
}
```

#### `detect_tech_stack`

Identify languages, frameworks, and build tools.

```json
{
  "method": "tools/call",
  "params": {
    "name": "detect_tech_stack",
    "arguments": {
      "path": "my-project"
    }
  }
}
```

#### `find_entrypoints`

Locate main executable files.

```json
{
  "method": "tools/call",
  "params": {
    "name": "find_entrypoints",
    "arguments": {
      "path": "my-project"
    }
  }
}
```

#### `full_exploration` (Combined)

Run all exploration steps at once.

```json
{
  "method": "tools/call",
  "params": {
    "name": "full_exploration",
    "arguments": {
      "path": "my-project",
      "max_depth": 3
    }
  }
}
```

### 3. Architecture Tools

#### `analyze_architecture`

Identify architectural patterns (MVC, microservices, clean architecture, etc.).

```json
{
  "method": "tools/call",
  "params": {
    "name": "analyze_architecture",
    "arguments": {
      "path": "my-project"
    }
  }
}
```

#### `map_dependencies`

Map imports and dependencies between files.

```json
{
  "method": "tools/call",
  "params": {
    "name": "map_dependencies",
    "arguments": {
      "path": "my-project"
    }
  }
}
```

#### `identify_patterns`

Find design patterns (Singleton, Factory, Observer, etc.).

```json
{
  "method": "tools/call",
  "params": {
    "name": "identify_patterns",
    "arguments": {
      "path": "my-project"
    }
  }
}
```

### 4. Planning Tools

#### `create_plan`

Create an atomic, file-specific implementation plan.

```json
{
  "method": "tools/call",
  "params": {
    "name": "create_plan",
    "arguments": {
      "path": "my-project",
      "task": "Add user authentication with JWT tokens",
      "context": {
        "exploration": {...},
        "architecture": {...}
      }
    }
  }
}
```

**Plan Types Detected**:
- `bugfix` - Bug fixes
- `refactoring` - Code refactoring
- `feature_implementation` - New features
- `general` - Other tasks

#### `validate_plan`

Check a plan for completeness and feasibility.

```json
{
  "method": "tools/call",
  "params": {
    "name": "validate_plan",
    "arguments": {
      "plan": {...}
    }
  }
}
```

### 5. Code Generation Tools

#### `generate_diff`

Generate code diff preview.

```json
{
  "method": "tools/call",
  "params": {
    "name": "generate_diff",
    "arguments": {
      "file_path": "my-project/auth.py",
      "changes": "Add login and logout functions with JWT support"
    }
  }
}
```

#### `apply_changes`

Apply changes with automatic backup.

```json
{
  "method": "tools/call",
  "params": {
    "name": "apply_changes",
    "arguments": {
      "file_path": "my-project/auth.py",
      "diff": "...",
      "dry_run": false
    }
  }
}
```

#### `rewrite_file`

Completely rewrite a file with backup.

```json
{
  "method": "tools/call",
  "params": {
    "name": "rewrite_file",
    "arguments": {
      "file_path": "my-project/config.py",
      "new_content": "...",
      "backup": true
    }
  }
}
```

### 6. Testing Tools

#### `generate_tests`

Generate test templates.

```json
{
  "method": "tools/call",
  "params": {
    "name": "generate_tests",
    "arguments": {
      "file_path": "my-project/auth.py",
      "test_type": "unit"
    }
  }
}
```

**Test Types**:
- `unit` - Unit tests
- `integration` - Integration tests
- `edge` - Edge case tests

#### `run_tests`

Execute tests.

```json
{
  "method": "tools/call",
  "params": {
    "name": "run_tests",
    "arguments": {
      "path": "my-project",
      "test_framework": "pytest"
    }
  }
}
```

**Supported Frameworks**:
- Python: `pytest`, `unittest`
- JavaScript: `jest`, `mocha`

#### `verify_changes`

Run tests for specific changed files.

```json
{
  "method": "tools/call",
  "params": {
    "name": "verify_changes",
    "arguments": {
      "files_changed": ["auth.py", "config.py"]
    }
  }
}
```

### 7. Quality Check Tools

#### `run_linter`

Run linter.

```json
{
  "method": "tools/call",
  "params": {
    "name": "run_linter",
    "arguments": {
      "path": "my-project",
      "fix": true
    }
  }
}
```

**Supported Linters**:
- Python: `ruff`, `flake8`
- JavaScript: `eslint`

#### `run_formatter`

Run code formatter.

```json
{
  "method": "tools/call",
  "params": {
    "name": "run_formatter",
    "arguments": {
      "path": "my-project",
      "check_only": false
    }
  }
}
```

**Supported Formatters**:
- Python: `ruff format`, `black`
- JavaScript: `prettier`

#### `run_type_checker`

Run type checker.

```json
{
  "method": "tools/call",
  "params": {
    "name": "run_type_checker",
    "arguments": {
      "path": "my-project"
    }
  }
}
```

**Supported Type Checkers**:
- Python: `mypy`
- TypeScript: `tsc`

#### `full_quality_check` (Combined)

Run all quality checks.

```json
{
  "method": "tools/call",
  "params": {
    "name": "full_quality_check",
    "arguments": {
      "path": "my-project",
      "fix": true
    }
  }
}
```

### 8. Security Tools

#### `scan_secrets`

Scan for hardcoded secrets.

```json
{
  "method": "tools/call",
  "params": {
    "name": "scan_secrets",
    "arguments": {
      "path": "my-project"
    }
  }
}
```

**Detects**:
- API keys
- Passwords
- Tokens
- AWS credentials
- Private keys
- Database passwords

#### `check_vulnerabilities`

Check dependencies for vulnerabilities.

```json
{
  "method": "tools/call",
  "params": {
    "name": "check_vulnerabilities",
    "arguments": {
      "path": "my-project"
    }
  }
}
```

**Uses**:
- Python: `safety`
- JavaScript: `npm audit`

#### `security_audit` (Combined)

Run complete security audit.

```json
{
  "method": "tools/call",
  "params": {
    "name": "security_audit",
    "arguments": {
      "path": "my-project"
    }
  }
}
```

## Workflows

### Complete Feature Workflow

End-to-end feature implementation.

```json
{
  "method": "tools/call",
  "params": {
    "name": "complete_feature_workflow",
    "arguments": {
      "path": "my-project",
      "feature_description": "Add user authentication with JWT tokens"
    }
  }
}
```

**Steps**:
1. Full exploration
2. Create plan
3. Ready for implementation (use generate_diff/apply_changes)
4. Ready for testing (use generate_tests/run_tests)
5. Ready for quality checks (use full_quality_check)

### Bugfix Workflow

Complete bug fixing process.

```json
{
  "method": "tools/call",
  "params": {
    "name": "bugfix_workflow",
    "arguments": {
      "path": "my-project",
      "bug_description": "Login function throws error on empty password"
    }
  }
}
```

**Steps**:
1. Exploration
2. Architecture analysis
3. Create fix plan
4. Ready for implementation
5. Ready for verification

### Refactor Workflow

Refactoring process.

```json
{
  "method": "tools/call",
  "params": {
    "name": "refactor_workflow",
    "arguments": {
      "path": "my-project",
      "refactor_goal": "Extract authentication logic into separate service class"
    }
  }
}
```

## Examples

See `/testing/README.md` for complete examples using the example Python project.

## Best Practices

1. **Always verify first**: Use `verify_mirror_vanisher` before starting work
2. **Start with exploration**: Run `full_exploration` to understand the codebase
3. **Plan before coding**: Use `create_plan` to think through changes
4. **Use workflows for complex tasks**: They guide you through all necessary steps
5. **Test after changes**: Always run `run_tests` after modifications
6. **Check quality regularly**: Use `full_quality_check` frequently
7. **Scan for security**: Run `security_audit` before committing

## Troubleshooting

### "Path not found or not a valid mirror+vanisher"

**Solution**: Ensure the directory is both mirrored and loaded as a vanisher:
```bash
/mirror do @your-project
/vanisher load @your-project your-project "Description"
```

### "Test framework not found"

**Solution**: Install the required test framework:
```bash
pip install pytest  # For Python
npm install  # For JavaScript
```

### "No suitable linter found"

**Solution**: Install linting tools:
```bash
pip install ruff flake8  # For Python
npm install -g eslint  # For JavaScript
```

### Web UI shows "No mirror+vanisher directories found"

**Solution**: Create at least one mirror+vanisher directory first using the CLI commands above.

## Support

For issues or questions:
- See `pillars/12_mcp_usage.md` for the complete pillar document
- Check the main README at `mcps/mirror_vanisher_dev/README.md`
- Report issues at https://github.com/A-Souhei/vuhitra-cli/issues
