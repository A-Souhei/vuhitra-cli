# Ouroboros Auto-Execution System

The Ouroboros Auto-Execution System is a powerful feature that automatically matches TODO_list steps with available tools and executes them in sequence with full context awareness.

## Overview

The Ouroboros system consists of two main phases:

1. **Tool Matching Phase**: Recursively matches each TODO_list step with the best available tool using semantic similarity
2. **Execution Phase**: Automatically executes each matched step with RAG context history and LLM explanations

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Ouroboros System                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │ TODO_list   │ -> │  Ouroboros  │ -> │  DETAILED_  │     │
│  │ (from plan) │    │   Matcher   │    │  TODO_list  │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│                            │                    │           │
│                     ┌──────┴──────┐     ┌───────┴───────┐  │
│                     │  Semantic   │     │  Auto-Execute │  │
│                     │ Similarity  │     │     Loop      │  │
│                     └─────────────┘     └───────────────┘  │
│                                                │            │
│                          ┌─────────────────────┼─────┐      │
│                          │                     │     │      │
│                    ┌─────┴─────┐    ┌──────────┴─┐  │      │
│                    │ RAG       │    │ LLM        │  │      │
│                    │ Context   │    │ Explanation│  │      │
│                    └───────────┘    └────────────┘  │      │
│                                                     │      │
│                               ┌─────────────────────┘      │
│                               │                            │
│                    ┌──────────┴──────────┐                 │
│                    │  Failure Handler    │                 │
│                    │  + Exploiter Func   │                 │
│                    └─────────────────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

Add the following to your `config.yaml`:

```yaml
# Ouroboros auto-execution settings
ouroboros:
  # Maximum number of auto-iterations before stopping
  max_auto_iterations: 25
  # Similarity threshold for tool matching (0.0-1.0)
  tool_matching_threshold: 0.3
  # Minimum relevant history similarity threshold
  history_similarity_threshold: 0.5
  # Number of relevant history items to retrieve
  history_top_k: 3
```

### Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_auto_iterations` | 25 | Maximum steps allowed in a single execution run |
| `tool_matching_threshold` | 0.3 | Minimum cosine similarity score for tool matching |
| `history_similarity_threshold` | 0.5 | Minimum similarity for RAG context retrieval |
| `history_top_k` | 3 | Number of relevant history items to include |

## Ouroboros Tool Matching Function

The ouroboros function matches each TODO_list step with the best available tool using semantic similarity.

### How It Works

1. **Collect All Tools**: Gathers tools from both Mirror+Vanisher MCP and Executor MCP
2. **Generate Embeddings**: Creates embeddings for each step and tool description
3. **Calculate Similarity**: Uses cosine similarity to find the best match
4. **Filter Results**: Only steps with matching tools (above threshold) are added to DETAILED_TODO_list

### Tool Sources

- **Mirror+Vanisher MCP**: 30+ tools for code analysis, generation, testing, etc.
- **Executor MCP**: 24 tools for file operations, code execution, package management

### Matching Algorithm

```python
def find_best_matching_tool(step_text, tools):
    step_embedding = generate_embedding(step_text)

    best_match = None
    best_score = 0.0

    for tool in tools:
        tool_embedding = generate_embedding(tool.description)
        similarity = cosine_similarity(step_embedding, tool_embedding)

        if similarity >= threshold and similarity > best_score:
            best_score = similarity
            best_match = tool

    return (best_match, best_score) if best_match else None
```

### Fallback Mechanism

When embeddings are unavailable, the system falls back to keyword-based Jaccard similarity matching with a lower threshold (0.1).

## Auto-Execution Loop

### Execution Flow

1. **Retrieve TODO_list** from Redis or memory
2. **Run Ouroboros Matching** to create DETAILED_TODO_list
3. **Validate Iteration Count** against max_auto_iterations
4. **For Each Step**:
   - Check for ESC cancellation
   - Pretty print step information
   - Retrieve RAG context from history
   - Generate LLM explanation
   - Execute the tool
   - Handle success or failure
   - Update execution history

### ESC Cancellation

Users can press the **ESC key** at any time to cancel execution. The system will:

1. Stop at the current iteration
2. Display cancellation message
3. Return partial results with `cancelled: true`

**Note**: ESC cancellation only works when running in a terminal (TTY).

### Pretty Printing

Each step displays:

```
────────────────────────────────────────────────────────────────
┃ ITERATION 3/10
────────────────────────────────────────────────────────────────
┃ Action: Create utility function
┃ Details: Add factorial calculation helper
┃ Tool: create_file
┃ Source: executor
┃ Similarity: 85.30%
────────────────────────────────────────────────────────────────
┃ Explanation: This step will create a new Python file with a function...
```

## RAG Context Integration

The system maintains conversation history and uses it to provide context for each execution step.

### Context Sources

1. **Conversation History**: Past prompts and responses with similar content
2. **Execution History**: Results from previous steps in the current run

### How Context Is Used

- Passed to LLM for explanation generation
- Available to tool handlers for informed execution
- Helps prevent repeating mistakes

### Configuration

```yaml
ouroboros:
  history_similarity_threshold: 0.5
  history_top_k: 3
```

## Failure Handling

When a step fails, the system offers two options:

### Option 1: Continue

Skip the failed step and continue with the next iteration:

```
❌ Step 3 failed: File not found
⚠️  Continuing with next step...
```

### Option 2: Find Another Way (Exploiter Function)

Generate an alternative plan that:

1. Avoids the failed approach
2. Uses alternative tools or methods
3. Still achieves the same goal

The exploiter function:
1. Takes failure context + original TODO_list
2. Prompts LLM for alternative approach
3. Runs ouroboros on new plan
4. Returns new DETAILED_TODO_list

## Usage

### Basic Execution

```python
from mcps.mirror_vanisher_dev.src.execute_plan import ExecutePlan

# Create instance
executor = ExecutePlan(manager, server_instance)

# Execute with auto-iteration
result = executor.execute_plan(auto_execute=True)

# Check results
if result['success']:
    print(f"Completed: {result['completed_count']}/{result['detailed_todo_list_count']}")
    print(result['output'])
else:
    print(f"Error: {result['error']}")
```

### Build DETAILED_TODO_list Only

```python
result = executor.execute_plan(auto_execute=False)

if result['success']:
    detailed_list = result['DETAILED_TODO_list']
    for item in detailed_list:
        print(f"Step {item['step_number']}: {item['tool_name']} ({item['similarity_score']:.2%})")
```

### MCP Tool Call

```json
{
  "name": "execute_plan",
  "arguments": {
    "auto_execute": true
  }
}
```

## Response Format

```json
{
  "success": true,
  "todo_list_count": 5,
  "detailed_todo_list_count": 4,
  "DETAILED_TODO_list": [
    {
      "step_number": 1,
      "original_action": "Explore codebase",
      "original_details": "Analyze project structure",
      "tool_source": "mirror_vanisher",
      "tool_name": "explore_codebase",
      "tool_description": "Explore and analyze codebase structure",
      "similarity_score": 0.92,
      "status": "completed",
      "execution_result": {...}
    }
  ],
  "auto_execute": true,
  "execution_results": [...],
  "completed_count": 4,
  "failed_count": 0,
  "cancelled": false,
  "execution_history": [...],
  "output": "...",
  "message": "Ouroboros matched 4 tools from 5 steps, executed 4/4 successfully"
}
```

## Limitations

1. **Max Iterations**: Execution stops after 25 steps (configurable)
2. **Tool Execution**: Currently simulated; full implementation requires tool handler integration
3. **User Interaction**: In MCP context, failure handling defaults to 'continue'
4. **ESC Key**: Only works in TTY environments

## Testing

Run the test suite:

```bash
# Run all ouroboros tests
python -m pytest tests/test_ouroboros_execute_plan.py -v

# Run specific test class
python -m pytest tests/test_ouroboros_execute_plan.py::TestOuroborosToolMatching -v
```

## Best Practices

1. **Plan Quality**: Better plans result in better tool matches
2. **Specific Actions**: Use specific action descriptions for accurate matching
3. **Monitor Progress**: Watch the pretty-printed output for execution status
4. **Handle Failures**: Consider using the exploiter function for complex failures
5. **Review Results**: Always review the execution history for issues

## Troubleshooting

### No Tool Matches Found

- Check that step descriptions are specific enough
- Lower the `tool_matching_threshold` in config
- Review available tools to match your task

### Exceeds Max Iterations

- Increase `max_auto_iterations` in config
- Split the plan into smaller chunks
- Use `auto_execute=False` to review the plan first

### ESC Key Not Working

- Ensure you're running in a terminal (TTY)
- Check that stdin is available

### Embeddings Unavailable

- Verify transformer service is running
- Check transformer URL in config
- System will fall back to keyword matching

## Related Documentation

- [CREATE_PLAN_TODO_FEATURE.md](CREATE_PLAN_TODO_FEATURE.md) - Plan creation
- [MCP_MANAGEMENT.md](MCP_MANAGEMENT.md) - MCP tools overview
- [EXECUTE_PLAN_TEST_RESULTS.md](EXECUTE_PLAN_TEST_RESULTS.md) - Test results
