# create_plan Tool with TODO_list Feature

## Overview

The `create_plan` tool in the Mirror+Vanisher Development MCP server has been enhanced to generate structured TODO lists and provide beautiful formatted plan outputs. This feature enables better task tracking and integration with the CLI.

## Features

### 1. **TODO_list Generation**
- Automatically generates a structured TODO list from plan steps
- Each TODO item contains:
  - `step_number`: Sequential step identifier
  - `action`: Brief description of the action
  - `details`: Detailed implementation notes
  - `status`: Current status (`pending` by default)

### 2. **Persistent Storage**
- TODO lists are stored in Redis for persistence across MCP server calls
- Uses connection pooling for efficient Redis operations
- Graceful fallback if Redis is unavailable

### 3. **Beautiful Formatting**
- Rich, emoji-enhanced plan output with clear sections:
  - 📋 Task information
  - 💻 Detected tech stack
  - 🏗️  Architecture patterns
  - 📝 Implementation steps (bullet points with sub-bullets for details)
  - 🧪 Testing requirements
  - ⚠️  Potential risks
  - 📄 Files to modify
- Clean bullet point format without status/step numbers for better readability

### 4. **CLI Integration**
- New `/show TODO_list` command to display current TODO items
- Formatted output with status indicators (⏳ pending, ✅ completed)

## Architecture

### Redis Connection Management

#### Planning Tools (MCP Server)
```python
# Configuration loaded at module level with error handling
# Falls back to defaults if config files are missing
REDIS_HOST = 'localhost'  # Default
REDIS_PORT = 6379         # Default
REDIS_PASSWORD = None     # Default

# Connection validated on initialization
class PlanningTools:
    def __init__(self, manager):
        self.redis_client = redis.Redis(...)
        self.redis_client.ping()  # Validate connection
```

#### CLI Application
```python
# Uses connection pooling via redis_helper module
from src.utils.redis_helper import get_redis_client

def get_todo_list_from_redis():
    redis_client = get_redis_client()  # Reuses pool
    # ... retrieve TODO list
```

### Error Handling

All Redis operations include comprehensive error handling:

1. **Configuration Loading**
   - Handles missing `config.yaml` or `secrets.yaml`
   - Falls back to sensible defaults
   - Logs warnings for missing files

2. **Connection Errors**
   - Validates Redis connection on initialization
   - Distinguishes between connection and parsing errors
   - Graceful degradation (plan still succeeds even if Redis storage fails)

3. **Data Retrieval**
   - Separate error handling for Redis GET operations
   - JSON parsing errors caught and reported
   - Empty TODO list returned if no data exists

## Usage

### 1. Creating a Plan (MCP Tool)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_plan",
    "arguments": {
      "path": "/path/to/project",
      "task": "Implement user authentication with JWT tokens"
    }
  }
}
```

**Response includes:**
- `plan`: Complete implementation plan
- `TODO_list`: Array of TODO items
- `formatted_plan`: Beautiful formatted output
- `message`: Success message

### 2. Retrieving TODO List (MCP Tool)

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_todo_list",
    "arguments": {}
  }
}
```

**Response includes:**
- `TODO_list`: Array of TODO items
- `count`: Number of items
- `success`: Boolean status

### 3. Viewing TODO List (CLI Command)

```bash
# In the vuhitra CLI interactive mode
/show TODO_list
```

**Output format:**
```
� STEPS:
--------------------------------------------------------------------------------
  • Design API/interface
    ◦ Define function signatures and data structures

  • Implement core logic
    ◦ Write main functionality

  • Add error handling
    ◦ Handle edge cases and errors

  • Write tests
    ◦ Unit and integration tests

  • Update documentation
    ◦ Add docstrings and comments

🧪 TESTING REQUIREMENTS:
```

## Implementation Details

### Files Modified

1. **`mcps/mirror_vanisher_dev/src/planning.py`**
   - Added Redis configuration loading with error handling
   - Enhanced `create_plan()` to generate TODO_list
   - Added `_format_plan_beautifully()` method
   - Implemented `get_todo_list()` tool
   - Added Redis connection validation

2. **`mcps/mirror_vanisher_dev/server.py`**
   - Registered `get_todo_list` as MCP tool

3. **`src/cli.py`**
   - Added `get_todo_list_from_redis()` helper function
   - Updated `/show` command handler to support `TODO_list` option
   - Integrated Redis connection pooling

4. **`src/utils/redis_helper.py`** (New)
   - Connection pooling implementation
   - Centralized configuration loading
   - Error handling for Redis operations

### Redis Storage

**Key:** `mcp:mirror_vanisher:todo_list`

**Data Structure:**
```json
[
  {
    "step_number": 1,
    "action": "Design API/interface",
    "details": "Define function signatures and data structures",
    "status": "pending"
  },
  ...
]
```

### Overwrite Behavior

Each call to `create_plan` overwrites the previous TODO_list in Redis. This ensures:
- Only one active TODO list at a time
- Latest plan takes precedence
- No confusion from multiple concurrent plans

## Error Handling Patterns

### 1. Configuration Loading
```python
try:
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
except (yaml.YAMLError, IOError) as e:
    logger.error(f"Error loading configuration: {e}")
    # Use defaults
```

### 2. Redis Connection
```python
try:
    self.redis_client.ping()
except RedisError as e:
    logger.error(f"Failed to connect to Redis: {e}")
    raise
```

### 3. Data Operations
```python
try:
    self.redis_client.set(TODO_LIST_KEY, json.dumps(todo_list))
except RedisError as e:
    logger.warning(f"Failed to store TODO_list: {e}")
    # Continue - plan still succeeds
```

### 4. JSON Parsing
```python
try:
    todo_list = json.loads(str(todo_list_json))
except json.JSONDecodeError as e:
    logger.error(f"JSON parsing error: {e}")
    return {'success': False, 'error': str(e)}
```

## Testing

### Test Files

1. **`tests/manual_test_create_plan.py`**
   - Direct function call tests
   - Verifies TODO_list generation
   - Tests formatted output
   - Validates JSON serialization
   - Tests overwrite behavior

2. **`tests/test_mcp_create_plan_integration.py`**
   - MCP server integration tests
   - Simulates Claude/LLM interactions
   - Tests JSON-RPC protocol
   - Validates TODO_list persistence

3. **`tests/test_show_todo_integration.py`**
   - End-to-end test: MCP → CLI
   - Creates plan via MCP
   - Retrieves via CLI command
   - Validates data flow

4. **`tests/test_show_todo_command.py`**
   - Unit test for `/show TODO_list` command
   - Tests Redis retrieval
   - Validates formatting

### Running Tests

```bash
# Manual test (direct function calls)
.venv/bin/python tests/manual_test_create_plan.py

# MCP integration test
.venv/bin/python tests/test_mcp_create_plan_integration.py

# End-to-end integration test
.venv/bin/python tests/test_show_todo_integration.py

# CLI command test
.venv/bin/python tests/test_show_todo_command.py
```

## Configuration

### config.yaml
```yaml
redis:
  host: localhost
  port: 6379
```

### secrets.yaml
```yaml
redis:
  password: your_redis_password  # Optional
```

## Dependencies

- `redis>=4.0.0`: Python Redis client
- `pyyaml>=6.0`: Configuration file parsing

## Future Enhancements

### Potential Features
1. **Status Updates**
   - `/update TODO_list <step_number> <status>` command
   - Status options: `pending`, `in-progress`, `completed`, `blocked`

2. **TODO_list History**
   - Track multiple TODO lists with timestamps
   - `/show TODO_list --history` command
   - Ability to restore previous lists

3. **Filtering**
   - `/show TODO_list --status pending`
   - `/show TODO_list --status completed`

4. **Export Functionality**
   - Export to Markdown format
   - Export to JSON file
   - Integration with task tracking systems

5. **Clear Command**
   - `/clear TODO_list` to remove current list

## Best Practices

1. **Always check Redis availability** before deployment
2. **Use connection pooling** for CLI operations to avoid connection overhead
3. **Handle errors gracefully** - plan creation should succeed even if Redis storage fails
4. **Validate configuration files** exist before attempting to load
5. **Use portable paths** in tests (e.g., `Path(__file__).parent.parent`)

## Troubleshooting

### Redis Connection Issues

**Problem:** Cannot connect to Redis

**Solutions:**
1. Check if Redis is running: `redis-cli ping`
2. Verify `config.yaml` has correct host/port
3. Check if password is required and set in `secrets.yaml`
4. Review logs for specific error messages

### TODO_list Not Persisting

**Problem:** TODO_list disappears between calls

**Solutions:**
1. Verify Redis is running and accepting connections
2. Check Redis logs for errors
3. Ensure TODO_LIST_KEY is consistent across modules
4. Verify `decode_responses=True` in Redis client

### Empty TODO_list

**Problem:** `/show TODO_list` shows empty list

**Solutions:**
1. Create a plan first using `create_plan` tool
2. Check if plan creation succeeded
3. Verify Redis storage operation completed
4. Check Redis directly: `redis-cli GET mcp:mirror_vanisher:todo_list`

## Related Documentation

- [MCP Usage Guide](mcp_usage_guide.md)
- [Pillars Methodology](../pillars/04_planning.md)
- [CLI Quick Reference](QUICK_REFERENCE.md)
- [Mirror+Vanisher Implementation](MIRROR_IMPLEMENTATION.md)
