# Mirror+Vanisher Development MCP Server

A stdio MCP (Model Context Protocol) server for LLM-driven development operations on directories that are both **mirrored** (synced to sandbox) and **vanishers** (loaded into LLM context).

## Overview

This MCP server implements the complete 8-step development methodology documented in the `pillars/` directory:

1. **Exploration** - Discover project structure, tech stack, and entrypoints
2. **Architecture** - Analyze patterns, dependencies, and design
3. **Chunking** - Break large files into manageable pieces
4. **Planning** - Create atomic, file-specific implementation plans
5. **Code Generation** - Generate and apply code changes safely
6. **Testing** - Generate and run tests
7. **Quality Checks** - Run linters, formatters, and type checkers
8. **Security** - Scan for secrets and vulnerabilities

## Requirements

- Python 3.8+
- Directories must be both:
  - **Mirrored**: Synced to sandbox using `/mirror do @<path>`
  - **Vanishers**: Loaded into context using `/vanisher load @<path>`

## Installation

```bash
cd mcps/mirror_vanisher_dev
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

### As Stdio MCP Server

```bash
python server.py
```

The server communicates via JSON-RPC over stdin/stdout.

### With Claude Desktop

Add to your Claude Desktop MCP settings:

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

### With Web UI

```bash
python ui_server.py
```

Then open `http://localhost:5100` in your browser.

## Available Tools

### Mirror+Vanisher Management
- `list_mirror_vanishers` - List all valid mirror+vanisher directories
- `verify_mirror_vanisher` - Verify a directory is properly set up

### Step 1: Exploration
- `explore_structure` - Generate directory tree
- `detect_tech_stack` - Identify languages and frameworks
- `find_entrypoints` - Locate main executable files
- `full_exploration` - **Combined**: All exploration steps

### Step 2: Architecture
- `analyze_architecture` - Identify architectural patterns (MVC, microservices, etc.)
- `map_dependencies` - Map imports and dependencies
- `identify_patterns` - Find design patterns (Singleton, Factory, etc.)

### Step 3: Chunking
- `chunk_file` - Break large file into chunks
- `chunk_directory` - Create chunking strategy for directory

### Step 4: Planning
- `create_plan` - Generate implementation plan for a task
- `validate_plan` - Check plan for completeness

### Step 5: Code Generation
- `generate_diff` - Create code diff preview
- `apply_changes` - Apply changes with backups
- `rewrite_file` - Completely rewrite a file safely

### Step 6: Testing
- `generate_tests` - Create test templates
- `run_tests` - Execute tests (pytest, jest, etc.)
- `verify_changes` - Run tests for changed files

### Step 7: Quality Checks
- `run_linter` - Run linter (ruff, flake8, eslint)
- `run_formatter` - Format code (black, prettier)
- `run_type_checker` - Check types (mypy, tsc)
- `full_quality_check` - **Combined**: All quality checks

### Step 8: Security
- `scan_secrets` - Find hardcoded secrets
- `check_vulnerabilities` - Scan dependencies (safety, npm audit)
- `security_audit` - **Combined**: Complete security scan

### Multi-Step Workflows
- `complete_feature_workflow` - **Combined**: End-to-end feature implementation
- `bugfix_workflow` - **Combined**: Bug analysis and fix workflow
- `refactor_workflow` - **Combined**: Refactoring workflow

## Example Workflows

### Adding a New Feature

```python
# 1. List available mirror+vanishers
{"method": "tools/call", "params": {"name": "list_mirror_vanishers"}}

# 2. Run full exploration
{"method": "tools/call", "params": {
  "name": "full_exploration",
  "arguments": {"path": "my-project"}
}}

# 3. Create implementation plan
{"method": "tools/call", "params": {
  "name": "create_plan",
  "arguments": {
    "path": "my-project",
    "task": "Add user authentication"
  }
}}

# 4. Generate code changes (LLM-assisted)
{"method": "tools/call", "params": {
  "name": "generate_diff",
  "arguments": {
    "file_path": "my-project/auth.py",
    "changes": "Add login and logout functions"
  }
}}

# 5. Run tests
{"method": "tools/call", "params": {
  "name": "run_tests",
  "arguments": {"path": "my-project"}
}}

# 6. Quality checks
{"method": "tools/call", "params": {
  "name": "full_quality_check",
  "arguments": {"path": "my-project", "fix": true}
}}
```

Or use the combined workflow:

```python
{"method": "tools/call", "params": {
  "name": "complete_feature_workflow",
  "arguments": {
    "path": "my-project",
    "feature_description": "Add user authentication with JWT tokens"
  }
}}
```

## Resources

- `mirror-vanisher://list` - Current mirror+vanisher directories
- `workflow://status` - Status of ongoing workflows

## Environment Variables

- `SANDBOX_URL` - Sandbox API URL (default: `http://localhost:5000`)
- `WORKSPACE_PATH` - Workspace path (default: `/app/WORKSPACE`)

## Architecture

```
mcps/mirror_vanisher_dev/
├── server.py              # Main MCP server
├── ui_server.py           # Web UI server
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── src/
    ├── mirror_vanisher.py    # Mirror+Vanisher manager
    ├── exploration.py        # Step 1 tools
    ├── architecture.py       # Step 2 tools
    ├── chunking.py           # Step 3 tools
    ├── planning.py           # Step 4 tools
    ├── code_generation.py    # Step 5 tools
    ├── testing.py            # Step 6 tools
    ├── quality_checks.py     # Step 7 tools
    ├── security.py           # Step 8 tools
    └── errors_handler.py     # Error handling
```

## Testing

```bash
pytest tests/
```

## Documentation

See `docs/mcp_usage_guide.md` for detailed usage examples and `pillars/12_mcp_usage.md` for the complete pillar document.

## License

MIT License - See main project LICENSE file
