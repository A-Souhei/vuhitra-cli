# /code Command - Issues and Improvements Needed

## Current Behavior

The `/code init @testing Add a power function to calculator.py` command successfully:
1. Mirrors the directory to sandbox
2. Loads files as vanishers
3. Creates a 5-step implementation plan
4. Matches 4/5 steps to tools
5. Executes all 4 matched tools

**But no actual code changes were made.**

## Root Cause Analysis

### Issue 1: Generic Plan Steps Don't Match Code-Editing Tools

The `create_plan` function generates generic steps:

```python
plan['steps'] = [
    {'step': 1, 'action': 'Design API/interface', 'details': 'Define function signatures and data structures'},
    {'step': 2, 'action': 'Implement core logic', 'details': 'Write main functionality'},
    {'step': 3, 'action': 'Add error handling', 'details': 'Handle edge cases and errors'},
    {'step': 4, 'action': 'Write tests', 'details': 'Unit and integration tests'},
    {'step': 5, 'action': 'Update documentation', 'details': 'Add docstrings and comments'}
]
```

These steps are too abstract and match analysis tools instead of action tools:

| Step | Matched Tool | Issue |
|------|-------------|-------|
| Design API/interface | `identify_patterns` (39%) | Analysis only - doesn't design anything |
| Implement core logic | `full_quality_check` (32%) | Quality check only - doesn't implement |
| Add error handling | `run_linter` (38%) | Linter only - doesn't add code |
| Write tests | `generate_tests` (44%) | Generates templates, may not create files |
| Update documentation | No match | - |

### Issue 2: Low Similarity Scores

All matches are in the 32-44% range - barely above the 0.3 threshold. This indicates:
- Step descriptions don't semantically match tool descriptions
- Better prompting needed for plan generation

### Issue 3: Executor MCP Tools Not Being Matched

The Executor MCP has actual code-editing tools that should be used:

```python
executor_tools = [
    {'name': 'create_file', 'description': 'Create and write a new file with specified content'},
    {'name': 'update_file', 'description': 'Update and replace the complete content of an existing file'},
    {'name': 'execute_python_code', 'description': 'Execute and run Python scripts'},
    # ... etc
]
```

But the generic plan steps like "Implement core logic" don't match "update_file" semantically.

### Issue 4: No Code Generation Step

The workflow is missing a crucial step: **actually generating the code** before writing it.

Current flow:
```
Plan → Match Tools → Execute Analysis Tools → Done (no code written)
```

Required flow:
```
Plan → Explore Codebase → Generate Code → Write to File → Run Tests → Done
```

## Proposed Improvements

### 1. Improve Plan Generation with Task-Specific Steps

Instead of generic steps, generate task-specific actionable steps:

```python
# For "Add a power function to calculator.py"
plan['steps'] = [
    {'step': 1, 'action': 'Read calculator.py', 'details': 'Understand existing function patterns', 'tool_hint': 'explore_structure'},
    {'step': 2, 'action': 'Generate power function code', 'details': 'Create def power(a, b) following existing patterns', 'tool_hint': 'generate_diff'},
    {'step': 3, 'action': 'Update calculator.py', 'details': 'Add power function to file', 'tool_hint': 'update_file'},
    {'step': 4, 'action': 'Update main.py', 'details': 'Import and demonstrate power function', 'tool_hint': 'update_file'},
    {'step': 5, 'action': 'Run tests', 'details': 'Execute python main.py to verify', 'tool_hint': 'execute_python_code'}
]
```

### 2. Add Tool Hints to Plan Steps

Allow `create_plan` to include `tool_hint` in each step to guide the Ouroboros matcher:

```python
def find_best_matching_tool(self, step_text, tools, tool_hint=None):
    # If tool_hint provided, prioritize that tool
    if tool_hint:
        for tool in tools:
            if tool['name'] == tool_hint:
                return (tool, 1.0)  # Perfect match

    # Fall back to semantic matching
    ...
```

### 3. Integrate LLM for Code Generation

The `generate_diff` tool should use the LLM to actually generate code:

```python
def generate_diff(self, file_path, changes, context=None):
    # Use LLM to generate actual code based on:
    # - Current file content (from vanisher)
    # - Requested changes
    # - Code patterns identified

    prompt = f"""
    Given this file content:
    {current_content}

    Generate code for: {changes}
    Following the existing patterns and style.
    """

    generated_code = self.call_llm(prompt)
    return {'diff': generated_code, 'success': True}
```

### 4. Add Code Writing Execution

The Executor MCP's `update_file` tool needs to actually write to the sandbox:

```python
def update_file(self, path, file_path, content, backup=True):
    full_path = self.resolve_path(path) / file_path

    if backup:
        # Create backup
        backup_path = f"{full_path}.bak"
        shutil.copy(full_path, backup_path)

    # Write new content
    with open(full_path, 'w') as f:
        f.write(content)

    return {'success': True, 'message': f'Updated {file_path}'}
```

### 5. Implement Full Workflow Pipeline

Create a higher-level orchestrator that:

1. **Explores** the codebase to understand structure
2. **Analyzes** the task and existing code patterns
3. **Generates** actual code using LLM
4. **Writes** the code to files in sandbox
5. **Tests** by running the code
6. **Validates** with linters/formatters

```python
class CodeWorkflowOrchestrator:
    def execute_coding_task(self, path, task):
        # Step 1: Explore
        structure = self.mcp_server.exploration.explore_structure(path)
        patterns = self.mcp_server.exploration.identify_patterns(path)

        # Step 2: Analyze
        architecture = self.mcp_server.architecture.analyze_architecture(path)

        # Step 3: Generate code
        diff = self.mcp_server.code_generation.generate_diff(
            file_path=f"{path}/calculator.py",
            changes=task,
            context={'patterns': patterns, 'architecture': architecture}
        )

        # Step 4: Write code
        self.executor.update_file(
            path=path,
            file_path="calculator.py",
            content=diff['new_content']
        )

        # Step 5: Test
        result = self.executor.execute_python_code(
            path=path,
            script_path="main.py"
        )

        # Step 6: Validate
        quality = self.mcp_server.quality.full_quality_check(path)

        return {'success': True, 'result': result, 'quality': quality}
```

## Immediate Action Items

### Priority 1: Fix Tool Matching
- [ ] Add `tool_hint` support to plan steps
- [ ] Improve Executor MCP tool descriptions for better semantic matching
- [ ] Lower threshold or use different matching algorithm

### Priority 2: Implement Code Generation
- [ ] Connect `generate_diff` to actual LLM for code generation
- [ ] Pass vanisher content as context for code generation
- [ ] Return actual code diffs, not just descriptions

### Priority 3: Implement File Operations
- [ ] Make `update_file` actually write to sandbox
- [ ] Implement `create_file` for new files
- [ ] Add proper error handling and rollback

### Priority 4: End-to-End Testing
- [ ] Test complete workflow: plan → generate → write → test
- [ ] Verify files are actually modified in sandbox
- [ ] Verify `/code session exit` syncs changes back

## Expected Behavior After Fixes

```bash
/code init @testing Add a power function to calculator.py

# Should:
# 1. Mirror and load files ✓
# 2. Create actionable plan with tool hints
# 3. Read calculator.py to understand patterns
# 4. Generate actual power() function code using LLM
# 5. Write the code to calculator.py in sandbox
# 6. Update main.py to import and demo power()
# 7. Run main.py to verify it works
# 8. Run linter to check code quality
# 9. Show success with file changes summary

# Then:
/code session exit @testing
# Should sync the modified calculator.py back to host
```

## Files to Modify

1. `mcps/mirror_vanisher_dev/src/planning.py` - Improve plan generation
2. `mcps/mirror_vanisher_dev/src/execute_plan.py` - Add tool_hint support
3. `mcps/mirror_vanisher_dev/src/code_generation.py` - Implement LLM code generation
4. `mcps/executor/server.py` - Implement actual file operations
5. `src/cli.py` - Potentially add CodeWorkflowOrchestrator

## Testing Plan

1. Unit test each improved component
2. Integration test: `/code init @testing Add power function`
3. Verify `calculator.py` in sandbox contains new `power()` function
4. Verify `python testing/main.py` runs successfully
5. Integration test: `/code session exit @testing`
6. Verify host `calculator.py` has the new function

## Conclusion

The Ouroboros auto-execution framework is working, but it's executing analysis tools instead of code-editing tools because:
1. Plan steps are too generic
2. Tool matching doesn't find code-editing tools
3. Code generation isn't implemented
4. File writing isn't implemented

The fix requires improving plan generation to be task-specific and implementing actual code generation and file operations.
