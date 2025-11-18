# Code Command

The `/code` command provides a streamlined workflow for coding sessions, combining multiple operations into single commands for efficient project initialization and cleanup.

## Overview

The code command automates the typical coding workflow:

1. **Initialize**: Mirror project → Load as vanisher → Create plan → Execute plan
2. **Exit**: Sync changes back to host → End session

This eliminates the need to manually run multiple commands and ensures a consistent workflow.

## Prerequisites

- **Coding mode enabled**: Start CLI with `--coding` flag
- **Sandbox services running**: Docker containers must be up
- **MCP server available**: Mirror+Vanisher MCP for create_plan/execute_plan

```bash
# Start CLI in coding mode
vuhitra --coding
```

## Commands

### `/code init @<path> <task>`

Initialize a coding session with automatic plan creation and execution.

**Usage:**
```bash
/code init @<path> <task description>
```

**Examples:**
```bash
# Initialize session for adding authentication
/code init @myproject Add user authentication with JWT tokens

# Initialize session for bug fix
/code init @webapp Fix the login timeout issue in session handler

# Initialize session for refactoring
/code init @api-service Refactor database connection pooling
```

**Workflow:**

1. **Mirror the folder** (`/mirror do @<path>`)
   - Copies entire directory to sandbox
   - Creates `/app/WORKSPACE/mirrors/<path>` in sandbox container

2. **Load as vanisher** (`/vanisher load @<path>`)
   - Loads mirrored content as vanisher context
   - Enables semantic filtering for relevance
   - Content available to LLM during session

3. **Create plan** (direct MCP call to `create_plan`)
   - Generates step-by-step implementation plan
   - Stores TODO_list in Redis for execution

4. **Execute plan** (direct MCP call to `execute_plan`)
   - Retrieves plan from Redis
   - Matches steps to available MCP tools
   - Executes plan with Ouroboros auto-executor

**Output:**
```
[1/4] Mirror: Synced 15 file(s) to sandbox 'myproject'

[2/4] Vanisher: Loaded 15 file(s) from @myproject

Coding session initialized for 'myproject'.
Task: Add user authentication with JWT tokens

[3/4] Creating implementation plan...
[3/4] Plan created: 5 steps (feature_implementation)

[4/4] Executing plan with Ouroboros auto-executor...
[4/4] Execution complete: 5/5 steps completed, 0 failed
```

The command directly calls MCP tools for reliable execution without LLM involvement in the tool calling process.

### `/code session exit @<path>`

End the coding session and sync all changes back to the host.

**Usage:**
```bash
/code session exit @<path>
```

**Examples:**
```bash
# End session and sync changes
/code session exit @myproject

# End session for webapp
/code session exit @webapp
```

**Workflow:**

1. **Revert+sync from sandbox** (`/mirror revert+sync @<path>`)
   - Downloads all modified files from sandbox
   - Applies changes to host directory
   - Deletes host files not present in sandbox (true sync)

2. **Display exit instructions**
   - Shows sync results
   - Prompts to type `exit` to leave CLI

**Output:**
```
Synced 12 file(s) from sandbox to host 'myproject/'
  Files deleted from host: 2

Coding session ended. Changes synced back to host.
Type 'exit' to leave the CLI.
```

## Complete Workflow Example

Here's a typical coding session from start to finish:

```bash
# 1. Start CLI in coding mode
$ vuhitra --coding

# 2. Initialize coding session
> /code init @my-api Add rate limiting to all API endpoints

# [CLI automatically:]
#   - Mirrors my-api/ to sandbox
#   - Loads as vanisher context
#   - Calls create_plan with task
#   - Calls execute_plan

# 3. LLM creates plan and begins execution
#    (automatic - you'll see the plan and execution progress)

# 4. When done, sync changes back
> /code session exit @my-api

# 5. Exit CLI
> exit
```

## Architecture

### Command Registration

The `/code` command is registered in `src/cli.py` within the `interactive_mode()` function:

```python
command_handler.register_command("code", code_command_handler)
```

### Direct MCP Tool Calls

The `/code init` command directly calls MCP tools via Python for reliable execution:

```python
# Initialize MCP server
mcp_server = MCPServer()

# Create plan
plan_result = mcp_server.planning.create_plan(target_name, task)

# Execute plan
exec_result = mcp_server.execute_plan.execute_plan(auto_execute=True)

return CommandResult(
    success=True,
    message="...",
    data={
        'plan_result': plan_result,
        'exec_result': exec_result
    }
)
```

This approach bypasses the LLM for tool calling, ensuring consistent and reliable execution of the workflow.

### MCP Tool Integration

The command directly calls these MCP tools:

1. **`create_plan`** (from Mirror+Vanisher MCP)
   - Generates step-by-step implementation plan
   - Stores TODO_list in Redis

2. **`execute_plan`** (from Mirror+Vanisher MCP)
   - Retrieves plan from Redis
   - Matches steps to available tools
   - Executes with Ouroboros auto-executor

## Error Handling

### Missing Coding Mode

```bash
> /code init @myproject Add feature
Error: Vanisher context is disabled. Enable coding mode with --coding flag to use /code init.
```

### Missing Task Description

```bash
> /code init @myproject
Error: Task description is required.
Usage: /code init @<path> <task description>
Example: /code init @myproject Add user authentication with JWT
```

### Missing @ Prefix

```bash
> /code init myproject Add feature
Error: Path must start with @ prefix. Example: /code init @myproject Add authentication
```

### Mirror Failure

If mirroring fails (e.g., path doesn't exist), the workflow stops immediately:

```bash
> /code init @nonexistent Add feature
Error: Failed to mirror folder:
Path not found: /path/to/nonexistent
```

### Vanisher Load Failure

If vanisher load fails after successful mirror:

```bash
> /code init @myproject Add feature
[1/4] Mirror: Synced 10 file(s) to sandbox 'myproject'

[2/4] Vanisher load failed: <error details>
```

The mirror remains in sandbox for manual recovery.

## Related Commands

- `/mirror` - Direct mirror operations
- `/vanisher` - Direct vanisher context loading
- `/show vanisher` - Show loaded vanisher contexts
- `/show TODO_list` - Show current implementation plan

## Related Documentation

- [Mirror Command](mirror-command.md) - Detailed mirror operations
- [Coding Mode](coding-mode.md) - Overview of coding mode features
- [MCP Usage Guide](mcp_usage_guide.md) - MCP tool documentation

## Implementation Details

### File Location

- Command handler: `src/cli.py` (lines ~1642-1848)

### Dependencies

- `mirror_command_handler` - For mirror operations
- `vanisher_command_handler` - For vanisher loading
- `vanisher_context` - For enabled check
- `MCPServer` - For direct MCP tool calls
- `handle_exception` - For error handling

### CommandResult Data

The `/code init` command uses the `data` field of `CommandResult`:

```python
@dataclass
class CommandResult:
    success: bool
    message: str = ""
    data: Any = None  # Contains {'plan_result': dict, 'exec_result': dict}
```

This provides access to the raw results from `create_plan` and `execute_plan` for inspection or debugging.
