# Pillar 12: Using the Mirror+Vanisher Development MCP

## Overview

The **Mirror+Vanisher Development MCP** is a Model Context Protocol server that provides LLM-driven development operations on directories that are both **mirrored** (synced to sandbox) and **vanishers** (loaded into LLM context).

This pillar document explains how to use the MCP to implement all 8 steps of the development methodology documented in Pillars 00-11.

## What is the Mirror+Vanisher MCP?

The MCP is a **stdio-based server** that exposes development tools through the Model Context Protocol. It allows LLMs (like Claude) to:

- Explore codebases systematically
- Analyze architecture and patterns
- Create implementation plans
- Generate and apply code changes
- Run tests and quality checks
- Perform security audits
- Execute complete development workflows

## Why Use Mirror+Vanisher Directories?

**Mirror+Vanisher directories** combine two powerful features:

1. **Mirrors** - Bidirectional file sync between host and sandbox
   - Files are copied to sandbox at `/app/WORKSPACE/mirrors`
   - Changes can be synced in both directions
   - Provides isolated workspace for safe operations

2. **Vanishers** - Session-scoped context for LLMs
   - File contents are loaded into LLM context
   - Enables semantic context injection
   - Only works in coding mode (`--coding`)

By combining both, the MCP can:
- **Read** the codebase (via vanisher context)
- **Analyze** the structure (via mirror access)
- **Modify** files safely (via mirror sync)
- **Execute** tools (via sandbox isolation)

## Prerequisites

### 1. Set Up a Mirror+Vanisher Directory

```bash
# Step 1: Mirror your project
/mirror do @my-project

# Step 2: Load it as a vanisher
/vanisher load @my-project my-project "My project for development"

# Step 3: Verify it's properly set up (use MCP tool)
```

### 2. Install MCP Dependencies

```bash
cd mcps/mirror_vanisher_dev
pip install -r requirements.txt
```

## Using the MCP

### Option 1: Stdio Mode (with Claude Desktop)

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "mirror-vanisher-dev": {
      "command": "python",
      "args": ["/path/to/vuhitra-cli/mcps/mirror_vanisher_dev/server.py"]
    }
  }
}
```

Then in Claude Desktop, the MCP tools will be available automatically.

### Option 2: Web UI Mode

```bash
python mcps/mirror_vanisher_dev/ui_server.py
# Open http://localhost:5100
```

The web UI provides a user-friendly interface for all MCP operations.

## The 8-Step Development Process with MCP

This section shows how to use the MCP to implement each pillar's methodology.

### Step 1: Exploration (Pillar 01)

**Goal**: Understand the codebase structure, tech stack, and entrypoints.

**MCP Tools**:
- `explore_structure` - Generate directory tree
- `detect_tech_stack` - Identify languages and frameworks
- `find_entrypoints` - Locate main executable files
- `full_exploration` ⭐ - **Combined tool** for all exploration

**Example**:

```json
{
  "tool": "full_exploration",
  "arguments": {
    "path": "my-project",
    "max_depth": 3
  }
}
```

**Output**:
```json
{
  "success": true,
  "structure": {
    "tree": {...},
    "statistics": {
      "total_files": 42,
      "total_directories": 8
    }
  },
  "tech_stack": {
    "primary_language": "Python",
    "frameworks": ["Flask", "Python"],
    "build_tools": ["Docker", "Make"]
  },
  "entrypoints": [
    {"file": "main.py", "type": "python_main_block"},
    {"file": "app.py", "type": "named_entrypoint"}
  ]
}
```

**When to Use**: At the start of any task to understand the codebase.

### Step 2: Architecture Analysis (Pillar 02)

**Goal**: Understand architectural patterns and system design.

**MCP Tools**:
- `analyze_architecture` - Identify patterns (MVC, microservices, etc.)
- `map_dependencies` - Map imports and dependencies
- `identify_patterns` - Find design patterns (Singleton, Factory, etc.)

**Example**:

```json
{
  "tool": "analyze_architecture",
  "arguments": {
    "path": "my-project"
  }
}
```

**Output**:
```json
{
  "success": true,
  "structure_type": "MVC",
  "patterns": ["MVC (Model-View-Controller)", "Layered Architecture"],
  "directories": ["models", "views", "controllers", "services"],
  "analysis": {
    "has_tests": true,
    "has_docs": true,
    "has_config": true
  }
}
```

**When to Use**: When planning refactoring, adding features, or understanding system design.

### Step 3: Chunking (Pillar 03)

**Goal**: Break large files into manageable pieces.

**MCP Tools**:
- `chunk_file` - Break a single file into chunks
- `chunk_directory` - Create chunking strategy for entire directory

**Example**:

```json
{
  "tool": "chunk_file",
  "arguments": {
    "file_path": "my-project/large_file.py",
    "chunk_size": 100,
    "overlap": 10
  }
}
```

**Output**:
```json
{
  "success": true,
  "total_lines": 450,
  "chunk_count": 5,
  "chunks": [
    {
      "chunk_number": 1,
      "start_line": 1,
      "end_line": 100,
      "content": "..."
    },
    ...
  ]
}
```

**When to Use**: When dealing with files > 500 lines that exceed context windows.

### Step 4: Planning (Pillar 04)

**Goal**: Create atomic, file-specific implementation plans.

**MCP Tools**:
- `create_plan` - Generate implementation plan
- `validate_plan` - Check plan completeness

**Example**:

```json
{
  "tool": "create_plan",
  "arguments": {
    "path": "my-project",
    "task": "Add user authentication with JWT tokens",
    "context": {
      "exploration": {...},
      "architecture": {...}
    }
  }
}
```

**Output**:
```json
{
  "success": true,
  "plan": {
    "type": "feature_implementation",
    "task": "Add user authentication with JWT tokens",
    "steps": [
      {"step": 1, "action": "Design API/interface", "details": "..."},
      {"step": 2, "action": "Implement core logic", "details": "..."},
      {"step": 3, "action": "Add error handling", "details": "..."},
      {"step": 4, "action": "Write tests", "details": "..."},
      {"step": 5, "action": "Update documentation", "details": "..."}
    ],
    "testing_requirements": ["Unit tests", "Integration tests", "Edge case tests"]
  }
}
```

**Plan Types**:
- `bugfix` - Bug fixes
- `refactoring` - Code refactoring
- `feature_implementation` - New features
- `general` - Other tasks

**When to Use**: Before implementing any non-trivial change.

### Step 5: Code Generation (Pillar 05)

**Goal**: Generate and apply code changes safely.

**MCP Tools**:
- `generate_diff` - Create code diff preview
- `apply_changes` - Apply changes with backup
- `rewrite_file` - Completely rewrite a file

**Example**:

```json
{
  "tool": "generate_diff",
  "arguments": {
    "file_path": "my-project/auth.py",
    "changes": "Add login and logout functions with JWT support"
  }
}
```

Then apply:

```json
{
  "tool": "apply_changes",
  "arguments": {
    "file_path": "my-project/auth.py",
    "diff": "...",
    "dry_run": false
  }
}
```

**Safety Features**:
- Automatic backup creation
- Dry-run mode for preview
- File validation before modification

**When to Use**: When implementing planned changes.

### Step 6: Testing (Pillar 06)

**Goal**: Generate and run tests to verify functionality.

**MCP Tools**:
- `generate_tests` - Create test templates
- `run_tests` - Execute tests
- `verify_changes` - Run tests for changed files

**Example**:

```json
{
  "tool": "generate_tests",
  "arguments": {
    "file_path": "my-project/auth.py",
    "test_type": "unit"
  }
}
```

Then run:

```json
{
  "tool": "run_tests",
  "arguments": {
    "path": "my-project"
  }
}
```

**Supported Frameworks**:
- Python: `pytest`, `unittest`
- JavaScript: `jest`, `mocha`

**Test Types**:
- `unit` - Unit tests
- `integration` - Integration tests
- `edge` - Edge case tests

**When to Use**: After any code changes, before committing.

### Step 7: Quality Checks (Pillar 07)

**Goal**: Ensure code quality through linting, formatting, and type checking.

**MCP Tools**:
- `run_linter` - Run linter
- `run_formatter` - Format code
- `run_type_checker` - Check types
- `full_quality_check` ⭐ - **Combined tool** for all checks

**Example**:

```json
{
  "tool": "full_quality_check",
  "arguments": {
    "path": "my-project",
    "fix": true
  }
}
```

**Output**:
```json
{
  "success": true,
  "all_checks_passed": true,
  "results": {
    "linter": {"success": true, "linter": "ruff"},
    "formatter": {"success": true, "formatter": "black"},
    "type_checker": {"success": true, "type_checker": "mypy"}
  }
}
```

**Supported Tools**:
- Python: `ruff`, `flake8`, `black`, `mypy`
- JavaScript: `eslint`, `prettier`, `tsc`

**When to Use**: Before committing, during code review, as part of CI/CD.

### Step 8: Security Scanning (Pillar 08)

**Goal**: Identify security issues and vulnerabilities.

**MCP Tools**:
- `scan_secrets` - Find hardcoded secrets
- `check_vulnerabilities` - Scan dependencies
- `security_audit` ⭐ - **Combined tool** for complete audit

**Example**:

```json
{
  "tool": "security_audit",
  "arguments": {
    "path": "my-project"
  }
}
```

**Output**:
```json
{
  "success": true,
  "has_security_issues": true,
  "secrets_scan": {
    "total_findings": 2,
    "findings": [
      {
        "file": "config.py",
        "line": 15,
        "type": "API Key",
        "severity": "high"
      }
    ]
  },
  "vulnerabilities_check": {
    "vulnerabilities_found": true,
    "results": [...]
  }
}
```

**Detects**:
- API keys, passwords, tokens
- AWS credentials
- Database passwords
- Vulnerable dependencies

**When to Use**: Before committing, especially before production deployment.

## Multi-Step Workflows

The MCP provides **end-to-end workflows** that combine multiple steps:

### 1. Complete Feature Workflow

Implements a new feature from start to finish.

```json
{
  "tool": "complete_feature_workflow",
  "arguments": {
    "path": "my-project",
    "feature_description": "Add user authentication with JWT tokens"
  }
}
```

**Steps**:
1. ✅ Full exploration
2. ✅ Create implementation plan
3. 🔄 Ready for implementation (use `generate_diff`/`apply_changes`)
4. ⏳ Ready for testing (use `generate_tests`/`run_tests`)
5. ⏳ Ready for quality checks (use `full_quality_check`)

### 2. Bugfix Workflow

Fixes a bug systematically.

```json
{
  "tool": "bugfix_workflow",
  "arguments": {
    "path": "my-project",
    "bug_description": "Login function throws error on empty password"
  }
}
```

**Steps**:
1. ✅ Exploration
2. ✅ Architecture analysis
3. ✅ Create fix plan
4. 🔄 Ready for implementation
5. ⏳ Ready for verification

### 3. Refactor Workflow

Refactors code while maintaining functionality.

```json
{
  "tool": "refactor_workflow",
  "arguments": {
    "path": "my-project",
    "refactor_goal": "Extract authentication logic into separate service class"
  }
}
```

**Steps**:
1. ✅ Architecture analysis
2. ✅ Create refactoring plan
3. 🔄 Ready for refactoring
4. ⏳ Ready for testing (ensure no behavior changes)
5. ⏳ Ready for quality checks

## Best Practices

### 1. Always Verify First

```json
{"tool": "verify_mirror_vanisher", "arguments": {"path": "my-project"}}
```

Ensure the directory is properly set up before starting work.

### 2. Start with Exploration

```json
{"tool": "full_exploration", "arguments": {"path": "my-project"}}
```

Understand the codebase before making changes.

### 3. Create Plans

```json
{"tool": "create_plan", "arguments": {"path": "my-project", "task": "..."}}
```

Think through changes before implementing.

### 4. Use Workflows for Complex Tasks

```json
{"tool": "complete_feature_workflow", "arguments": {...}}
```

Workflows guide you through all necessary steps.

### 5. Test Everything

```json
{"tool": "run_tests", "arguments": {"path": "my-project"}}
```

Always run tests after modifications.

### 6. Check Quality Regularly

```json
{"tool": "full_quality_check", "arguments": {"path": "my-project", "fix": true}}
```

Maintain code quality throughout development.

### 7. Audit Security

```json
{"tool": "security_audit", "arguments": {"path": "my-project"}}
```

Scan for security issues before committing.

## Example: Complete Development Session

Here's a complete example of using the MCP to add a new feature:

```
1. List available projects
   → list_mirror_vanishers

2. Verify project setup
   → verify_mirror_vanisher("my-project")

3. Explore the codebase
   → full_exploration("my-project")

4. Create implementation plan
   → create_plan("my-project", "Add password reset feature")

5. Implement changes
   → generate_diff("auth.py", "Add reset_password function")
   → apply_changes("auth.py", diff)

6. Generate tests
   → generate_tests("auth.py", "unit")

7. Run tests
   → run_tests("my-project")

8. Quality check
   → full_quality_check("my-project", fix=true)

9. Security scan
   → security_audit("my-project")

10. Commit changes (manually via git)
```

Or use the workflow tool:

```
1. complete_feature_workflow("my-project", "Add password reset feature")
2. Follow the steps provided
3. Commit when done
```

## Integration with Existing Pillars

This MCP implements all concepts from Pillars 00-11:

- **Pillar 00**: Overall framework → Multi-step workflows
- **Pillar 01**: Exploration → `full_exploration` tool
- **Pillar 02**: Architecture → `analyze_architecture` tool
- **Pillar 03**: Chunking → `chunk_file`/`chunk_directory` tools
- **Pillar 04**: Planning → `create_plan`/`validate_plan` tools
- **Pillar 05**: Code Generation → `generate_diff`/`apply_changes` tools
- **Pillar 06**: Testing → `generate_tests`/`run_tests` tools
- **Pillar 07**: Quality Checks → `full_quality_check` tool
- **Pillar 08**: Security → `security_audit` tool
- **Pillar 09**: Prompts → Tool descriptions and schemas
- **Pillar 10**: Advanced Tips → Combined tools and workflows
- **Pillar 11**: Pitfalls → Safety features (backups, dry-run, validation)

## Troubleshooting

### "Path not found or not a valid mirror+vanisher"

**Cause**: Directory is not both mirrored and vanisher.

**Solution**:
```bash
/mirror do @your-project
/vanisher load @your-project your-project "Description"
```

### "Test framework not found"

**Cause**: Required test framework not installed.

**Solution**:
```bash
pip install pytest  # For Python
npm install  # For JavaScript
```

### "No suitable linter found"

**Cause**: Linting tools not installed.

**Solution**:
```bash
pip install ruff flake8  # For Python
npm install -g eslint  # For JavaScript
```

## Additional Resources

- **README**: `mcps/mirror_vanisher_dev/README.md`
- **Usage Guide**: `docs/mcp_usage_guide.md`
- **Example Project**: `testing/README.md`
- **Tests**: `tests/test_mcp_mirror_vanisher.py`
- **Web UI**: Run `python mcps/mirror_vanisher_dev/ui_server.py`

## Summary

The Mirror+Vanisher Development MCP provides:

✅ **Atomic Tools** - Single-purpose operations
✅ **Combined Tools** - Multi-step operations
✅ **Workflow Tools** - End-to-end processes
✅ **8-Step Methodology** - Complete development process
✅ **Safety Features** - Backups, validation, dry-run
✅ **Web UI** - User-friendly interface
✅ **Stdio Protocol** - Claude Desktop integration

**Use it to**: Fix bugs, add features, refactor code, analyze architecture, ensure quality, and maintain security—all within directories that are both mirrored to sandbox and loaded into LLM context.

**Next Steps**:
1. Set up a mirror+vanisher directory
2. Try the example project in `testing/`
3. Use the web UI at http://localhost:5100
4. Integrate with Claude Desktop
5. Start building!
