# Plan Generator Tool Implementation

## Overview

This document describes the implementation of the LLM-powered plan generator tool for the vuhitra-cli MCP (Model Context Protocol) server. The tool uses Ollama (local LLM) to generate comprehensive, context-aware implementation plans based on the 8-pillar methodology.

## Features

### 1. Prompt Injection Prefix (`&plan` + TAB)

**Location:** `data/prompt_injections.yaml:166-180`

A new category has been added to the prompt injection system that allows users to quickly inject planning-related prompts:

- **Prefix:** `:plan` or `&plan` + TAB
- **Emoji:** 📋
- **Phrases:** 10 different plan-related phrases that start with `[plan]`

Example phrases:
- `[plan] Create a detailed, step-by-step implementation plan following the 8-pillar methodology.`
- `[plan] Analyze the task and generate a comprehensive plan with file-specific steps.`
- `[plan] Design a strategic approach with testing requirements and risk assessment.`

### 2. Enhanced Prompt Injection Completer

**Files Modified:**
- `src/utils/prompt_injection_completer.py`
- `src/cli.py`

**Changes:**
- Updated regex pattern from `:(\w+)` to `[:&](\w+)` to support both `:` and `&` prefixes
- Modified `get_completions()` method
- Modified `replace_category_with_phrase()` method
- Updated `process_prompt_injections()` in CLI

This allows users to use either `:plan` or `&plan` followed by TAB to inject planning prompts.

### 3. LLM Plan Generator Module

**Location:** `mcps/mirror_vanisher_dev/src/llm_plan_generator.py`

A comprehensive 500+ line module that handles AI-powered plan generation using Ollama.

#### Key Components:

##### Initialization
```python
class LLMPlanGenerator:
    def __init__(self, manager):
        self.manager = manager
        self.config = ConfigLoader()  # Load Ollama config
        self.ollama_model = None      # Selected model
        self.embedding_model = None   # For semantic similarity
        self.tool_embeddings = None   # Cached tool embeddings
```

##### Model Selection
The generator automatically selects the best available model for plan generation:

Priority order:
1. `qwen2.5-coder:7b` - Best for coding tasks
2. `qwen2.5-coder:7b-instruct-q5_K_M` - Alternative coding model
3. `llama3.1:8b` - General purpose, good reasoning
4. `qwen3:latest` - Latest Qwen model

Falls back to `llama3.1:8b` if none are available.

##### Core Methods

**`generate_plan(task, path, tools)`**
- Main entry point for plan generation
- Validates vanisher is loaded and is directory type
- Loads context (pillars docs, tool descriptions, vanisher files)
- Calls Ollama LLM
- Enhances plan with tool recommendations
- Returns comprehensive plan with metadata

**`_load_pillars_documentation()`**
- Loads key pillar documents from `pillars/` directory
- Focuses on: `00_overview.md`, `04_planning.md`, `09_prompts.md`, `10_advanced_tips.md`
- Returns combined documentation as string

**`_get_mcp_tool_descriptions(tools)`**
- Formats all available MCP tools into readable descriptions
- Includes tool names, descriptions, and parameters
- Used as context for LLM

**`_create_tool_embeddings(tools)`**
- Uses sentence-transformers to create embeddings for each MCP tool
- Model: `all-MiniLM-L6-v2` (lightweight, fast)
- Caches embeddings for reuse
- Used for semantic similarity matching

**`_find_relevant_tools(step_description, tools, top_k=3)`**
- Uses cosine similarity to find relevant MCP tools for a plan step
- Returns top-k most similar tools
- Helps recommend which tools to use for each step

**`_get_vanisher_context(path)`**
- Reads files from loaded vanisher directory
- Extracts file list and sample content
- Limits to 20 files and 1000 chars per file to avoid context overflow

**`_call_llm_for_plan(task, pillars_docs, tool_descriptions, vanisher_context)`**
- Constructs comprehensive prompt with all context
- Calls Ollama using `src.agent.generate()`
- Parses JSON response (handles markdown code blocks)
- Returns structured plan or fallback plan on error

**`_enhance_plan_with_tools(plan, tools)`**
- Adds `recommended_mcp_tools` field to each plan step
- Uses embedding similarity to match steps to tools
- Returns enhanced plan

#### Prompt Structure

The LLM prompt includes:
1. **Task**: User's task description
2. **Codebase Context**: File list and sample content from vanisher
3. **Pillars Methodology**: Relevant documentation (8KB limit)
4. **Available MCP Tools**: Tool descriptions (6KB limit)
5. **Instructions**: Detailed requirements for plan format
6. **Example**: JSON structure example

#### Plan Output Format

```json
{
  "type": "bugfix|refactoring|feature_implementation|general",
  "task": "Task description",
  "steps": [
    {
      "step": 1,
      "action": "Brief action",
      "details": "Detailed explanation",
      "files": ["file1.py", "file2.py"],
      "verification": "pytest tests/",
      "recommended_mcp_tools": ["explore_structure", "generate_diff"]
    }
  ],
  "estimated_files_to_modify": ["file1.py"],
  "testing_requirements": ["Unit tests", "Integration tests"],
  "potential_risks": ["Breaking changes"],
  "mcp_tools_suggested": ["tool1", "tool2"]
}
```

### 4. MCP Server Integration

**Location:** `mcps/mirror_vanisher_dev/server.py`

Changes:
1. Import `LLMPlanGenerator` module
2. Initialize `self.llm_planner = LLMPlanGenerator(self.manager)` in `__init__`
3. Register `generate_llm_plan` tool in `_register_tools()`

Tool registration:
```python
"generate_llm_plan": {
    "description": "Generate comprehensive, AI-powered implementation plans using Ollama LLM...",
    "inputSchema": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "Task description"},
            "path": {"type": "string", "description": "Path to vanisher directory"}
        },
        "required": ["task", "path"]
    },
    "handler": lambda task, path: self.llm_planner.generate_plan(task, path, self.tools)
}
```

### 5. Dependencies

**Location:** `mcps/mirror_vanisher_dev/requirements.txt`

Required packages:
```
requests>=2.32.0
pyyaml>=6.0
pathlib>=1.0.1
flask>=3.0.0
sentence-transformers>=2.2.0  # For embeddings
numpy>=1.24.0                  # For similarity calculations
```

**Removed:** `anthropic>=0.39.0` (replaced with Ollama)

## Workflow

### User Perspective

1. **Load a vanisher**:
   ```bash
   /mirror do @/path/to/project
   /vanisher load @/path/to/project
   ```

2. **Trigger plan generation**:
   - Type `&plan` + TAB to inject `[plan]` prefix
   - Or type `:plan` + TAB
   - Add task description: `&plan + TAB` → `📋 [plan] ... implement user authentication`

3. **MCP receives request**:
   - Claude Code detects `[plan]` prefix
   - Calls `generate_llm_plan` MCP tool with task and vanisher path

4. **Plan generation**:
   - Validates vanisher is loaded
   - Loads context (pillars, tools, files)
   - Calls Ollama with comprehensive prompt
   - Parses JSON response
   - Enhances with tool recommendations

5. **Response**:
   - Receives comprehensive plan with:
     - Task type classification
     - Step-by-step implementation guide
     - File-specific actions
     - Testing requirements
     - Risk assessment
     - Tool recommendations per step

### Technical Flow

```
User Input: &plan + TAB → "📋 [plan] implement authentication"
    ↓
CLI processes prompt injection
    ↓
Claude Code detects [plan] prefix
    ↓
Calls MCP tool: generate_llm_plan(task="implement authentication", path="...")
    ↓
LLMPlanGenerator.generate_plan()
    ↓
├─ Validate vanisher (directory type)
├─ Load pillars documentation
├─ Get MCP tool descriptions
├─ Create tool embeddings (if not cached)
├─ Get vanisher context (files + content)
│
├─ Call Ollama LLM
│   ├─ Construct comprehensive prompt
│   ├─ Call src.agent.generate()
│   └─ Parse JSON response
│
└─ Enhance plan with tool recommendations
    ├─ For each step
    ├─ Calculate similarity with tools
    └─ Add top-3 relevant tools
    ↓
Return comprehensive plan
```

## Requirements

### System Requirements

1. **Ollama installed and running**:
   - Local: `cd services && docker compose --profile ollama up -d`
   - Remote: Configure in `config.yaml`

2. **Model availability**:
   - At least one of: `qwen2.5-coder:7b`, `llama3.1:8b`, `qwen3:latest`
   - Check: `ollama list`
   - Pull: `ollama pull qwen2.5-coder:7b`

3. **Config setup** (`config.yaml`):
   ```yaml
   ollama:
     use: local  # or remote
     local:
       host: localhost
       protocol: http
       port: 11434
       api_path: /api/generate

   model:
     default:
       local: tinyllama
       remote: llama3.1:8b
     available:
       - qwen2.5-coder:7b
       - llama3.1:8b
       - qwen3:latest
   ```

### MCP Requirements

1. **Vanisher loaded**: A directory-type vanisher must be loaded
2. **Pillars documentation**: Located in `pillars/` directory
3. **MCP tools registered**: All tools in server.py

## Error Handling

### Vanisher Validation Errors

```json
{
  "success": false,
  "error": "A vanisher of directory type must be loaded to generate a plan",
  "details": "Path not found or not a directory"
}
```

### LLM Errors

If Ollama fails or returns invalid JSON:
```json
{
  "success": true,
  "plan": {
    "type": "general",
    "task": "...",
    "steps": [
      {"step": 1, "action": "Analyze task", "details": "Review requirements"},
      {"step": 2, "action": "Implement changes", "details": "Make code changes"},
      {"step": 3, "action": "Test changes", "details": "Run tests"}
    ],
    "error": "LLM generation failed: ..."
  }
}
```

Fallback plan is returned to ensure workflow continues.

### Configuration Errors

```json
{
  "success": false,
  "error": "Ollama model not configured. Check config.yaml for Ollama settings."
}
```

## Advantages of Ollama vs Anthropic

| Feature | Ollama | Anthropic API |
|---------|--------|---------------|
| **Cost** | Free (local) | Paid per token |
| **Privacy** | Complete (local) | Cloud-based |
| **API Key** | Not required | Required |
| **Offline** | ✅ Yes | ❌ No |
| **Speed** | Fast (local GPU) | Network latency |
| **Models** | Customizable | Fixed options |
| **Integration** | Existing infrastructure | External dependency |

## Testing

### Manual Test

1. Start Ollama:
   ```bash
   cd services
   docker compose --profile ollama up -d
   ```

2. Pull a coding model:
   ```bash
   docker exec ollama ollama pull qwen2.5-coder:7b
   ```

3. Load vanisher:
   ```bash
   python main.py --coding
   # In CLI:
   /mirror do @.
   /vanisher load @.
   ```

4. Test plan generation:
   ```bash
   &plan + TAB
   # Type: implement a new feature to track user sessions
   ```

5. Verify response:
   - Should return JSON plan
   - Check: type, steps, files, testing_requirements
   - Each step should have recommended_mcp_tools

### Expected Output

```json
{
  "success": true,
  "plan": {
    "type": "feature_implementation",
    "task": "implement a new feature to track user sessions",
    "steps": [
      {
        "step": 1,
        "action": "Design session tracking architecture",
        "details": "Define session data structure, storage mechanism...",
        "files": ["src/session.py", "src/models.py"],
        "verification": "Review design document",
        "recommended_mcp_tools": ["explore_structure", "analyze_architecture", "detect_patterns"]
      },
      ...
    ],
    "estimated_files_to_modify": ["src/session.py", "src/models.py", "src/api/routes.py"],
    "testing_requirements": ["Unit tests for session CRUD", "Integration tests for API"],
    "potential_risks": ["Session storage performance", "Memory leaks"]
  },
  "metadata": {
    "task": "implement a new feature to track user sessions",
    "path": ".",
    "pillars_docs_loaded": true,
    "tools_analyzed": 30,
    "vanisher_files": 45
  }
}
```

## Future Improvements

1. **Caching**: Cache tool embeddings across sessions
2. **Model selection**: Allow user to specify preferred model
3. **Context optimization**: Smarter file selection based on task relevance
4. **Plan refinement**: Interactive plan refinement with user feedback
5. **Execution tracking**: Track plan execution progress
6. **Plan templates**: Pre-built templates for common task types
7. **Multi-step planning**: Break large tasks into multiple sub-plans

## References

- **Pillars Methodology**: `/home/user/vuhitra-cli/pillars/`
- **Config**: `/home/user/vuhitra-cli/config.yaml`
- **MCP Server**: `/home/user/vuhitra-cli/mcps/mirror_vanisher_dev/server.py`
- **Agent**: `/home/user/vuhitra-cli/src/agent.py`

## Troubleshooting

### "Ollama model not configured"
- Check `config.yaml` has correct Ollama settings
- Verify Ollama is running: `curl http://localhost:11434/api/generate`

### "Vanisher not loaded"
- Ensure `/mirror do @path` was run
- Ensure `/vanisher load @path` was run
- Check vanisher is directory type

### "LLM response parsing failed"
- Model may be too small (use qwen2.5-coder:7b or llama3.1:8b)
- Check Ollama logs: `docker logs ollama`
- Try with simpler task description

### "Tool embeddings not working"
- Install: `pip install sentence-transformers`
- May require ~1GB download for model
- Check: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`

## Commit History

1. **Initial commit**: Added Anthropic-based plan generator
2. **Ollama migration**: Replaced Anthropic with Ollama for local, offline usage
   - Removed `anthropic>=0.39.0` dependency
   - Updated `llm_plan_generator.py` to use `src.agent.generate()`
   - Updated model selection to prefer coding models
   - Improved error handling and JSON parsing

---

**Implementation Status**: ✅ Complete
**Last Updated**: 2025-11-17
**Version**: 2.0 (Ollama-based)
