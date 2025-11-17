# Vuhitra CLI - Codebase Architecture Summary

## Overview
Vuhitra CLI is an LLM-based CLI application that provides context management, heuristic-based prompt enhancement, and auto-iteration for improved LLM responses.

---

## 1. START.SH Script and CLI Entry Point

**File:** `/home/user/vuhitra-cli/start.sh`

The start.sh script is a simple bash wrapper that:
1. Creates/activates a Python virtual environment (.venv)
2. Installs dependencies from requirements.txt
3. Executes `python main.py "$@"` with all CLI arguments

**Flow:**
```
start.sh → main.py → src.cli.main()
```

**CLI Argument Parsing:**

**File:** `/home/user/vuhitra-cli/src/utils/arg_parser.py`

The ArgumentParser class handles CLI flags:
- `-m, --model`: Specify the model to use (defaults to config value)
- `-p, --prompt`: Provide prompt for non-interactive mode (if omitted, interactive mode)
- `-v, --verbose`: Enable verbose debugging output

**Key Function:** `main()` in `/home/user/vuhitra-cli/src/cli.py`
- Initializes error handler
- Parses arguments
- Waits for services (sandbox, transformer)
- Routes to either interactive or non-interactive mode

---

## 2. Eternals - Persistent Cross-Session Context

**File:** `/home/user/vuhitra-cli/src/utils/eternal_context.py`

### EternalContext Dataclass
Represents a single eternal context with:
- `label`: User-friendly identifier
- `file_path`: Original file path
- `content`: Full text content
- `timestamp`: ISO format creation time
- `description`: Auto-generated or user-provided summary
- `description_embedding`: Semantic embedding (numpy array)
- `chunks`: Large content split into overlapping segments

### EternalContextManager Class

**Loading:**
- `load_file(file_path, label, description)`:
  - Validates file size (max: config default 10MB)
  - Auto-generates description via LLM if not provided
  - Creates semantic embedding of description
  - Chunks content if larger than chunk_size (default: 1000 words)
  - Persists to JSON files in storage directory: `.vuhitra/eternal_contexts/`
  - Returns (success: bool, message: str)

**Storage:**
- `_save_to_storage(context)`: Writes JSON to disk
- `_load_from_storage()`: Loads all .json files from storage on startup
- `_delete_from_storage(label)`: Deletes persistent storage file

**Management:**
- `get_relevant_contexts(prompt)`: Returns contexts sorted by semantic similarity
- `get_context_string(prompt)`: Formats contexts for LLM injection
- `clear_all()`, `remove_by_label()`: Remove specific/all contexts
- `get_summary()`: Display loaded contexts

**Configuration (config.yaml):**
```yaml
eternal_context:
  enabled: true
  storage_dir: .vuhitra/eternal_contexts
  max_file_size_mb: 10
  max_contexts: 20
  chunking:
    enabled: true
    chunk_size: 1000       # words
    overlap: 200           # words
  semantic_filtering:
    enabled: true
    similarity_threshold: 0.5
```

---

## 3. Ephemerals - Session-Scoped Context

**File:** `/home/user/vuhitra-cli/src/utils/ephemeral_context.py`

### EphemeralContext Dataclass
Similar to EternalContext but:
- In-memory only (no disk persistence)
- Includes full document embedding
- Per-chunk embeddings for semantic operations

### EphemeralContextManager Class

**Loading:**
- `load_file(file_path, label, description)`:
  - Similar validation to eternal context
  - Auto-generates description via LLM
  - Generates embeddings for all chunks
  - Session-scoped (cleared on exit or `/clear ephemeral`)

**Retrieval:**
- `get_relevant_contexts(prompt)`: Similarity-based filtering
- `get_context_string(prompt)`: Formats for LLM injection
- `get_embeddings()`: Returns all generated embeddings

**Configuration (config.yaml):**
```yaml
ephemeral_context:
  enabled: true
  max_file_size_mb: 10
  max_contexts: 10
  chunking:
    enabled: true
    chunk_size: 1000
    overlap: 200
  semantic_filtering:
    enabled: true
    similarity_threshold: 0.5
```

---

## 4. Sparks - In-Memory Ephemeral Context

**File:** `/home/user/vuhitra-cli/src/utils/spark_context.py`

### SparkContext Dataclass
Lightweight in-memory context with:
- `label`, `file_path`, `content`, `timestamp`
- `embedding`: Full document embedding
- `chunks`, `chunk_embeddings`: For large files

### SparkContextManager Class

**Loading Methods:**
- `load_file(file_path, label)`: Load single file
- `load_directory(dir_path, label_prefix)`: Load all files in directory

**Key Features:**
- Auto-created when using @ prefix in prompts (e.g., `@docs/api.md`)
- In-memory only - dies with `/clear context`
- Generates embeddings for semantic operations
- No persistence/storage

**Configuration (config.yaml):**
```yaml
spark_context:
  enabled: true
  max_file_size_mb: 10
  max_contexts: 20
  embed:
    enabled: true
  chunking:
    enabled: true
    chunk_size: 1000        # characters
    overlap: 200            # characters
```

---

## 5. Configuration and Settings Management

**File:** `/home/user/vuhitra-cli/src/utils/config_loader.py`

### ConfigLoader Class

**Configuration Sources:**
- `config.yaml`: Main configuration file
- `secrets.yaml`: Secret values (passwords, API keys)

**Key Methods:**
```python
get(*keys, default=None)           # Get nested config values
get_secret(*keys, default=None)    # Get nested secret values

# Ollama configuration
get_ollama_host()
get_ollama_port()
get_default_model()
get_available_models()

# Service URLs
get_sandbox_url()          # Heuristics service
get_transformer_url()      # Embedding service

# CLI settings
get_cli_timeout()
get_feedback_enabled()
get_auto_iteration_timeout()
get_auto_iteration_max_iterations()
get_auto_iteration_negative_weight_increment()

# Context settings
get('eternal_context')
get('ephemeral_context')
get('spark_context')
```

**Configuration File Structure:**
```yaml
cli:
  default_timeout: 30
  enable_feedback: true
  auto_iteration_timeout_seconds: 3
  auto_iteration_max_iterations: 5
  auto_iteration_negative_weight_increment: 0.1

model:
  default:
    local: tinyllama
    remote: llama3.1:8b

ollama:
  use: local|remote
  local/remote:
    host, protocol, port, api_path

environment:
  mode: DEV|PROD
  enable_logging: true

sandbox, transformer, redis, elasticsearch:
  [service configuration]
```

---

## 6. Command Implementation

**File:** `/home/user/vuhitra-cli/src/cli.py` (lines 297-660)

### CommandHandler Architecture
- `register_command(command_name, handler)`: Register command
- `execute(text)`: Parse and execute command
- `is_command(text)`: Check if text starts with /

### Eternal Context Commands

**`/load-eternal <file_path> [label] [description]`**
```python
def load_eternal_command_handler(args):
    """Handle /load-eternal command to load eternal context from file."""
    if not eternal_context.is_enabled():
        return CommandResult(success=False, ...)
    
    # Parse arguments
    # Resolve paths (supports @ prefix and directories)
    # Call eternal_context.load_file()
    # Return CommandResult
```

**`/clear eternal [label|--all]`**
- `--all`: Clear all eternal contexts from storage
- `<label>`: Remove specific context by label

**`/show eternal`**
- Display summary of loaded eternal contexts
- Shows: label, size (KB), chunks, file path, storage location

### Ephemeral Context Commands

**`/load <file_path> [label] [description]`**
- Similar to `/load-eternal` but session-scoped
- No persistence to disk

**`/clear ephemeral [label|--all]`**
- Clear session ephemeral contexts

**`/show ephemeral`**
- Display loaded ephemeral contexts

### Spark Context Commands

**`/show spark`**
- Display in-memory Spark contexts loaded via @ prefix

**`/clear spark [label|--all]`**
- Remove Spark contexts

**`/clear context`**
- Special: Clears conversation history AND all Sparks
- Sparks "die with /clear context" (requirement)

---

## 7. Auto-Iteration and Reasoning Boost

**File:** `/home/user/vuhitra-cli/src/cli.py` (lines 1403-1760)

### Auto-Iteration Flow

**Configuration:**
```yaml
cli:
  auto_iteration_timeout_seconds: 3           # Wait before auto-retry
  auto_iteration_max_iterations: 5            # Max retry attempts
  auto_iteration_negative_weight_increment: 0.1  # Weight penalty per iteration
```

### Algorithm (simplified):
```python
iteration_number = 0
max_iterations = config.get_auto_iteration_max_iterations()  # default 5
negative_weight_boost = 0.0

while iteration_number < max_iterations:
    # Fetch heuristics with negative_weight_boost
    heuristic_data = fetch_similar_heuristic(prompt, negative_weight_boost=negative_weight_boost)
    
    # Inject reasoning for retries (iteration_number > 0)
    if iteration_number > 0 and not has_user_feedback:
        reasoning_phrase = completer.get_random_phrase('reasoning')
        reasoning_emoji = completer.get_category_emoji('reasoning')
        enhanced_prompt += f"\n\n{reasoning_emoji} {reasoning_phrase}"
    
    # Generate LLM response
    response = generate(model, enhanced_prompt)
    
    # Collect feedback (rating 0-5)
    feedback_data = feedback_collector.collect_feedback(prompt, response)
    rating = feedback_data.get('rating')
    
    # Add auto-iteration metadata
    feedback_data['iteration_number'] = iteration_number
    feedback_data['is_auto_iteration'] = (iteration_number > 0 or could_retry)
    
    # Send feedback to sandbox (force sync during iterations)
    send_feedback_to_sandbox(feedback_data, force_sync=True)
    
    # Check if should retry
    if rating == 0 and iteration_number + 1 < max_iterations:
        # Wait for confirmation (3 second timeout)
        if user_confirms_retry():
            negative_weight_boost += increment  # default 0.1
            iteration_number += 1
            continue
    
    # Success or max iterations reached
    break
```

### Reasoning Injection

**File:** `/home/user/vuhitra-cli/data/prompt_injections.yaml`

**Prompt Injection System:**
- `:category` syntax in prompts replaced with random phrases
- `reasoning` category used for auto-iteration retries
- Example: `:reasoning` → "🧠 Think step by step..."

**Implementation:**
```python
# In interactive_mode()
def process_prompt_injections(prompt_text: str) -> str:
    """Replace :category with random phrase from that category."""
    import re
    completer = PromptInjectionCompleter()
    pattern = r':(\w+)'
    
    def replace_with_phrase(match):
        category = match.group(1)
        phrase = completer.get_random_phrase(category)
        emoji = completer.get_category_emoji(category)
        return f"{emoji} {phrase}" if phrase else match.group(0)
    
    return re.sub(pattern, replace_with_phrase, prompt_text)
```

**Reasoning Boost (Auto-Iteration):**
```python
if iteration_number > 0 and not has_user_feedback:
    # Get reasoning phrase from prompt_injections.yaml
    reasoning_phrase = completer.get_random_phrase('reasoning')
    reasoning_emoji = completer.get_category_emoji('reasoning')
    
    if reasoning_phrase:
        reasoning_injection = f"{reasoning_emoji} {reasoning_phrase}"
        enhanced_prompt = f"{enhanced_prompt}\n\n{reasoning_injection}"
        
        if verbose:
            print_info(f"🍒 Auto-iteration boost: Added reasoning prompt - '{reasoning_phrase}'")
```

### Auto-Iteration Metadata

**Feedback Data:**
```python
feedback_data = {
    'prompt': original_prompt,
    'response': llm_response,
    'rating': 0-5,
    'execution_time_ms': milliseconds,
    'iteration_number': 0|1|2|...,
    'is_auto_iteration': True|False,  # True if iteration > 0 OR rating==0 and can retry
    'negative_weight_boost': float,   # Accumulated penalty for heuristic weighting
    'parent_heuristic_id': str,       # ID of matched heuristic
    'chain_ids': [str, ...],          # Related heuristic chain
    'chain_depth': int,               # Depth in heuristic chain
    'contexted_heuristic_ids': [str]  # Which heuristics provided context
}
```

**Sent to Sandbox Service:**
- Endpoint: `POST {sandbox_url}/analyze/feedback`
- Force synchronous processing during iterations
- Used to refine heuristic database

---

## 8. Spark Loading via @ Prefix

**File:** `/home/user/vuhitra-cli/src/cli.py` (lines 1249-1307)

### Automatic Spark Loading

**Pattern:**
- User types: `What does @docs/api.md say about authentication?`
- Regex finds: `@docs/api.md` matches pattern `@([^\s]+)`
- Automatically loads as Spark context (unless already loaded)

**Implementation:**
```python
def detect_and_load_spark_references(prompt_text: str) -> tuple:
    """Detect and load @ references in prompt as Sparks."""
    import re
    
    pattern = r'@([^\s]+)'
    matches = re.findall(pattern, prompt_text)
    
    loaded_sparks = []
    errors = []
    
    for match in matches:
        path = f"@{match}"
        path_without_at = match
        
        # Check if already loaded as spark/ephemeral/eternal
        if spark_context.get_context_by_label(path_without_at):
            continue  # Skip duplicates
        
        # Resolve path using PathResolver
        success, resolved_path, error = path_resolver.resolve_path(path)
        
        if path_resolver.is_directory(resolved_path):
            # Load all files in directory
            spark_context.load_directory(resolved_path, label_prefix=path_without_at)
        else:
            # Load single file
            spark_context.load_file(resolved_path, label=path_without_at)
    
    return prompt_text, loaded_sparks, errors
```

**Behavior:**
- @ references remain in prompt (not removed)
- Context is auto-injected into LLM prompt
- Sparks are in-memory only (die with `/clear context`)
- Error handling: reports which files failed to load

---

## 9. Context Injection into LLM Prompts

**File:** `/home/user/vuhitra-cli/src/cli.py` (lines 1400-1550)

### Enhanced Prompt Construction

**Order of Context Injection:**
1. **Eternal Context** (if enabled and semantically relevant)
   - Retrieved via `eternal_context.get_context_string(prompt)`
   - Semantic filtering by description embedding
   - Fully injected into every prompt

2. **Heuristic Context** (from sandbox service)
   - Retrieved via `fetch_similar_heuristic(prompt, negative_weight_boost)`
   - LLM-driven insights from previous feedback
   - Updated with negative_weight_boost during auto-iterations

3. **Ephemeral Context** (if enabled and semantically relevant)
   - Retrieved via `ephemeral_context.get_context_string(prompt)`
   - Session-scoped, similar filtering to eternal

4. **Spark Context** (if auto-loaded via @ prefix)
   - Retrieved via `spark_context.get_context_string()`
   - All Spark contexts injected (no filtering)

5. **Conversation History** (if enabled, NOT during iterations > 0)
   - Previous turns in current session
   - Disabled during auto-iteration retries (heuristics-only mode)

6. **Reasoning Injection** (auto-iteration only)
   - Added only if `iteration_number > 0`
   - Random reasoning phrase + emoji
   - Skipped if user provided feedback

**Final Prompt Format:**
```
[ETERNAL CONTEXT]

[HEURISTIC CONTEXT]

[EPHEMERAL CONTEXT]

[SPARK CONTEXT]

[CONVERSATION HISTORY - NOT if iteration > 0]

[REASONING INJECTION - ONLY if iteration > 0]

[USER PROMPT]
```

---

## 10. Error Handling

**File:** `/home/user/vuhitra-cli/src/errors_handler/error_handler.py`

**Key Functions:**
- `handle_exception(exception, context={})`: Log exception with context
- `capture_message(message, level, context={})`: Log general messages
- `get_error_handler()`: Get singleton instance

**Usage Pattern (per CLAUDE.md):**
```python
from src.errors_handler import handle_exception

try:
    # operation
except Exception as e:
    handle_exception(e, context={
        'function': 'function_name',
        'operation': 'what was being done',
        'relevant_data': value
    })
```

**Initialization:**
- Called in `main()` before argument parsing
- Configured with sentry DSN from config.yaml
- Environment: DEV or PROD

---

## 11. File Structure Summary

```
/home/user/vuhitra-cli/
├── start.sh                           # Bash entry point (venv + python main.py)
├── main.py                            # Simple wrapper to src.cli.main()
├── config.yaml                        # Main configuration file
├── secrets.yaml                       # Secret values (gitignored)
├── src/
│   ├── cli.py                         # Main CLI logic (interactive/non-interactive)
│   ├── agent.py                       # LLM generation interface
│   ├── utils/
│   │   ├── arg_parser.py              # CLI argument parsing (-m, -p, -v)
│   │   ├── config_loader.py           # Config/secrets loading
│   │   ├── eternal_context.py         # Persistent cross-session context
│   │   ├── ephemeral_context.py       # Session-scoped context
│   │   ├── spark_context.py           # In-memory ephemeral context
│   │   ├── command_handler.py         # /command execution system
│   │   ├── prompt_injection_completer.py  # :category → phrase replacement
│   │   ├── conversation_history.py    # Previous conversation turns
│   │   ├── prompt_history.py          # Previous prompts (for auto-complete)
│   │   ├── token_limit_manager.py     # Discover/track model token limits
│   │   ├── feedback_collector.py      # Collect user ratings (0-5)
│   │   ├── input_with_timeout.py      # Timeout for confirmation prompts
│   │   ├── embedding_utils.py         # Embedding generation & similarity
│   │   ├── path_resolver.py           # Resolve @ prefix paths
│   │   └── ui_formatter.py            # Rich formatting (colors, tables, etc)
│   └── errors_handler/
│       └── error_handler.py           # Exception logging with Sentry
├── data/
│   ├── prompt_injections.yaml         # :category definitions and phrases
│   ├── docs/                          # Documentation
│   └── examples/                      # Example files
├── tests/
│   ├── test_eternal_context.py        # Eternal context tests
│   ├── test_auto_iteration_reasoning_boost.py  # Auto-iteration tests
│   └── test_spark_context*.py         # Spark context tests
└── services/
    ├── docker-compose.yml             # Services orchestration
    ├── sandbox/                       # Heuristics/feedback service
    └── transformer/                   # Embedding generation service
```

---

## 12. Key Interactions Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ User Input (Interactive Mode)                               │
└────────────────────────┬────────────────────────────────────┘
                         │
                    PromptHistoryManager
                    (auto-complete & history)
                         │
                    Process :category → phrase
                    (prompt_injection_completer)
                         │
              Detect @ references → Load Sparks
              (detect_and_load_spark_references)
                         │
         ┌────────────────┼────────────────┐
         │                │                │
      /command?       Spark loaded?    Normal prompt?
         │                │                │
         V                V                V
   CommandHandler    continue        Fetch contexts
         │                              │
         │              ┌───────────────┼───────────────┐
         │              │               │               │
         │         EternalContext  HeuristicContext EphemeralContext
         │         (persistent)     (from sandbox)   (session)
         │              │               │               │
         │              └───────────────┼───────────────┘
         │                              │
         │                    Build enhanced_prompt
         │                    (inject all contexts)
         │                              │
         │                    Auto-iteration loop
         │                    (iteration_number = 0, 1, 2, ...)
         │                              │
         │                    ┌─────────┴────────┐
         │                    │                  │
         │            iteration > 0?     Inject reasoning
         │                    │          (if no user feedback)
         │                    │                  │
         │                    └─────────┬────────┘
         │                              │
         │                      Generate LLM Response
         │                              │
         │                      Collect Feedback (0-5)
         │                              │
         │                    ┌─────────┴─────────┐
         │                    │                   │
         │                rating==0 &       Other ratings
         │                iteration < max?        │
         │                    │                   │
         │            ┌───────V────────┐         │
         │            │ Retry? (confirm │         │
         │            │  3sec timeout)  │         │
         │            │ neg_weight += 0.1        │
         │            └────────┬────────┘         │
         │                     │                   │
         │                ┌────V───────────────────┘
         │                │
         │         Send Feedback to Sandbox
         │         (force_sync during iterations)
         │                │
         └────────────────┤
                          │
                     Next prompt

```

---

## 13. Testing Entry Points

**Test Files:**
1. `/home/user/vuhitra-cli/tests/test_eternal_context.py` - Eternal context loading/storage
2. `/home/user/vuhitra-cli/tests/test_auto_iteration_reasoning_boost.py` - Auto-iteration reasoning injection
3. `/home/user/vuhitra-cli/tests/test_spark_context.py` - Spark context loading
4. `/home/user/vuhitra-cli/tests/test_spark_context_embeddings.py` - Spark embeddings

**Run tests:**
```bash
python -m pytest tests/
```

---

## 15. Key Design Patterns

1. **Manager Pattern**: EternalContextManager, EphemeralContextManager, SparkContextManager
   - Encapsulate context lifecycle
   - Consistent interface for load/clear/retrieve

2. **Config Pattern**: ConfigLoader
   - Centralized configuration access
   - Fallback to defaults
   - Support for nested keys with dot notation

3. **Command Handler Pattern**: CommandHandler
   - Dynamic command registration
   - Parse /command syntax
   - Route to handler functions

4. **Context Injection Pattern**:
   - Multiple context sources
   - Semantic filtering via embeddings
   - Prioritized order for enhanced prompt

5. **Auto-Iteration Pattern**:
   - Rating-based feedback loop
   - Negative weighting for heuristic refinement
   - Reasoning boost on retries
   - Synchronous feedback to sandbox

---

## 16. Important Configuration Notes

1. **Embedding Service**: Transformer service at `/generate-embedding` endpoint
2. **Heuristic Service**: Sandbox service at `/retrieve/similar` endpoint
3. **Redis**: Used for embedding caching and token limit discovery
4. **Virtual Environment**: Required (setup done by start.sh)
5. **Error Handling**: All exceptions logged via error_handler
   - Includes function name, operation, and relevant context
   - Sends to Sentry if DSN configured


---

## 14. Coding Mode - Pillars and Vanishers

**Enabled with:** `./start.sh --coding`

Coding mode is a specialized mode for software development workflows that replaces eternals/ephemerals with pillars/vanishers.

### Key Differences

| Feature | Normal Mode | Coding Mode |
|---------|-------------|-------------|
| **Eternals** | ✅ Enabled | ❌ Disabled |
| **Ephemerals** | ✅ Enabled | ❌ Disabled |
| **Pillars** | ❌ Disabled | ✅ Enabled + Auto-load |
| **Vanishers** | ❌ Disabled | ✅ Enabled |
| **Sparks** | ✅ Enabled | ✅ Enabled |
| **Auto-iteration (rating=0)** | ✅ Enabled | ❌ Disabled |

### Pillar Context Manager

**File:** `/home/user/vuhitra-cli/src/utils/pillar_context.py`

Pillars are the coding mode equivalent of eternals - persistent cross-session contexts.

**Key Features:**
1. **Persistent Storage**: Saved in `.vuhitra/pillar_contexts/`
2. **Auto-loading**: Files in `pillars/` directory are automatically loaded on startup
3. **Semantic Filtering**: Only relevant pillars are injected based on prompt similarity
4. **Duplicate Prevention**: Checks both auto-loaded and manually loaded contexts
5. **Label Collision Handling**: Auto-generates unique labels with counters

**Auto-Load Process:**
```python
# On CLI startup in coding mode:
1. Scan pillars/ directory recursively
2. Skip hidden files (starting with '.')
3. Check if file already loaded (by file_path, not just auto_loaded_files)
4. Generate label from relative path using hyphens (e.g., "docs-api-spec")
5. Handle collisions by appending counter (e.g., "api-spec-1", "api-spec-2")
6. Load and embed each new file
7. Track in auto_loaded_files set to skip on subsequent scans
```

**Label Validation:**
- Path separator rejection: Labels cannot contain `/` or `\`
- Maximum length: 64 characters
- Path traversal prevention: Validates storage path stays within storage_dir
- Sanitization: Non-alphanumeric chars (except `-` and `_`) replaced with `_`

**Configuration (config.yaml):**
```yaml
pillar_context:
  enabled: true  # Overridden by --coding flag
  storage_dir: .vuhitra/pillar_contexts
  pillars_dir: pillars
  max_file_size_mb: 10
  max_contexts: 20
  semantic_filtering:
    enabled: true
    similarity_threshold: 0.5
  chunking:
    enabled: true
    chunk_size: 1000
    overlap: 200
```

### Vanisher Context Manager

**File:** `/home/user/vuhitra-cli/src/utils/vanisher_context.py`

Vanishers are the coding mode equivalent of ephemerals - session-scoped contexts.

**Key Features:**
1. **Mirror Requirement**: Can only load files that are mirrored in sandbox
2. **Session-scoped**: Cleared when session ends (no persistence)
3. **Semantic Filtering**: Only relevant vanishers are injected
4. **Mirror Verification**: Checks `/mirror-exists/{mirror_name}` endpoint

**Mirror Check Process:**
```python
def _check_mirror_exists(mirror_name):
    # Uses short timeout for quick existence check
    response = requests.get(
        f"{sandbox_url}/mirror-exists/{mirror_name}",
        timeout=(2, 2)  # (connect_timeout, read_timeout)
    )
    return (exists, mirror_info)
```

**Error Handling:**
- Shows full file path in error messages (not just filename)
- Example: `Cannot load vanisher: 'config' is not mirrored. Use '/mirror do @path/to/config.json' first to mirror it.`

**Configuration (config.yaml):**
```yaml
vanisher_context:
  enabled: true  # Overridden by --coding flag
  max_file_size_mb: 10
  max_contexts: 10
  semantic_filtering:
    enabled: true
    similarity_threshold: 0.5
  chunking:
    enabled: true
    chunk_size: 1000
    overlap: 200
```

### Context Injection Order (Coding Mode)

When coding mode is enabled, contexts are injected in this order:

```
1. Pillar Context (persistent coding references)
2. Vanisher Context (session-scoped mirrored files)
3. Spark Context (in-memory ephemeral)
4. Conversation History (relevant previous turns)
5. Heuristics (retrieved similar patterns)
6. User Prompt
```

### CLI Command Handlers

**Pillar Commands:**
- `/pillar load @file` - Load file as pillar (coding mode only)
- `/pillar load @dir/` - Load all files from directory with unique labels
- `/show pillar` - Display loaded pillars
- `/clear pillar <label>` - Remove specific pillar
- `/clear pillar --all` - Remove all pillars

**Vanisher Commands:**
- `/vanisher load @file` - Load mirrored file as vanisher (coding mode only)
- `/show vanisher` - Display loaded vanishers
- `/clear vanisher <label>` - Remove specific vanisher
- `/clear vanisher --all` - Remove all vanishers

**Directory Loading:**
When loading a directory, unique labels are auto-generated:
- If label provided: `{label}-{filename}` (e.g., `api-spec`, `api-types`)
- If no label: `{filename}` (e.g., `spec`, `types`)

### Coding Mode Initialization

**File:** `/home/user/vuhitra-cli/src/cli.py` (interactive_mode function)

```python
if coding:
    # Coding mode: disable eternals/ephemerals, enable pillars/vanishers
    ephemeral_context = EphemeralContextManager(enabled=False)
    eternal_context = EternalContextManager(enabled=False)
    pillar_context = PillarContextManager(enabled=True)
    vanisher_context = VanisherContextManager(enabled=True)

    # Auto-load pillars from pillars/ directory
    loaded_count, loaded_files = pillar_context.auto_load_from_pillars_directory(verbose=verbose)
    if loaded_count > 0:
        print_success(f"✓ Auto-loaded {loaded_count} pillar(s) from pillars/ directory")
else:
    # Normal mode: enable eternals/ephemerals, disable pillars/vanishers
    ephemeral_context = EphemeralContextManager()
    eternal_context = EternalContextManager()
    pillar_context = PillarContextManager(enabled=False)
    vanisher_context = VanisherContextManager(enabled=False)
```

### Non-Interactive Mode Limitation

Coding mode only works in interactive mode. When `--coding` is used with `-p` flag:
- Warning displayed: "⚠️  Coding mode is only available in interactive mode. Use ./start.sh --coding without -p flag."
- Falls back to normal non-interactive behavior

---

