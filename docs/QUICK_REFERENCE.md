# Vuhitra CLI - Quick Reference Guide

## Entry Points

| Component | File | Purpose |
|-----------|------|---------|
| Script | `start.sh` | Creates venv, installs deps, runs `python main.py "$@"` |
| Entry | `main.py` | Wrapper calling `src.cli.main()` |
| CLI Logic | `src/cli.py` | Main interactive/non-interactive mode (1856 lines) |
| Args Parser | `src/utils/arg_parser.py` | CLI flags: `-m`, `-p`, `-v` |

## Context Management Systems

### 1. Eternals (Persistent Cross-Session)
**File:** `src/utils/eternal_context.py`

| Component | Description |
|-----------|-------------|
| **Load** | `/load-eternal <file_path> [label] [description]` |
| **Clear** | `/clear eternal <label> \| --all` |
| **Show** | `/show eternal` |
| **Storage** | `.vuhitra/eternal_contexts/*.json` |
| **Embedding** | Description + semantic filtering (similarity threshold: 0.5) |
| **Max Contexts** | 20 (configurable) |

**Key Classes:**
- `EternalContext`: Dataclass for single context
- `EternalContextManager`: Load/store/retrieve operations

### 2. Ephemerals (Session-Scoped)
**File:** `src/utils/ephemeral_context.py`

| Component | Description |
|-----------|-------------|
| **Load** | `/load <file_path> [label] [description]` |
| **Clear** | `/clear ephemeral <label> \| --all` |
| **Show** | `/show ephemeral` |
| **Storage** | In-memory only (cleared on exit/restart) |
| **Embedding** | Full embeddings + chunk embeddings |
| **Max Contexts** | 10 (configurable) |

### 3. Sparks (In-Memory Ephemeral)
**File:** `src/utils/spark_context.py`

| Component | Description |
|-----------|-------------|
| **Auto-Load** | `@docs/file.md` in prompts automatically loads |
| **Clear** | `/clear spark <label> \| --all` |
| **Show** | `/show spark` |
| **Storage** | In-memory only, dies with `/clear context` |
| **Features** | File/directory loading, embedding generation |
| **Max Contexts** | 20 (configurable) |

## Auto-Iteration Loop

**File:** `src/cli.py` (lines 1403-1760)

```
iteration_number = 0

LOOP:
  ├─ Fetch heuristics (with negative_weight_boost)
  ├─ Inject reasoning IF iteration_number > 0 (unless has user feedback)
  ├─ Generate LLM response
  ├─ Collect feedback (rating 0-5)
  ├─ Send to sandbox (force_sync=True)
  ├─ IF rating==0 AND iteration < max:
  │  └─ Wait 3 sec for user confirmation
  │     ├─ IF user confirms:
  │     │  ├─ negative_weight_boost += 0.1
  │     │  ├─ iteration_number += 1
  │     │  └─ GOTO LOOP
  │     └─ ELSE: break
  └─ ELSE: break
```

**Configuration:**
```yaml
cli:
  auto_iteration_timeout_seconds: 3          # Confirmation timeout
  auto_iteration_max_iterations: 5           # Max retries
  auto_iteration_negative_weight_increment: 0.1  # Penalty per iteration
```

## Commands Reference

| Command | Args | Description |
|---------|------|-------------|
| `/load` | `<file> [label] [desc]` | Load ephemeral context |
| `/load-eternal` | `<file> [label] [desc]` | Load persistent context |
| `/clear context` | - | Clear conversation history + Sparks |
| `/clear ephemeral` | `<label> \| --all` | Clear session contexts |
| `/clear eternal` | `<label> \| --all` | Clear persistent contexts |
| `/clear spark` | `<label> \| --all` | Clear Spark contexts |
| `/show ephemeral` | - | Display session contexts |
| `/show eternal` | - | Display persistent contexts |
| `/show spark` | - | Display Spark contexts |
| `/limit` | - | Show model's discovered token limit |
| `/clear tokenlimit` | - | Reset token limit discovery |

## Prompt Injection Features

**File:** `src/utils/prompt_injection_completer.py`

### :category Syntax
Users can type `:reasoning` or `:creative` etc. to inject random phrases:
```
User: "What is AI? :reasoning"
→ "What is AI? 🧠 Think through this step by step..."
```

**Configuration:** `data/prompt_injections.yaml`

## Context Injection Order (Priority)

1. Eternal Context (persistent, semantically filtered)
2. Heuristic Context (from sandbox service)
3. Ephemeral Context (session, semantically filtered)
4. Spark Context (auto-loaded via @)
5. Conversation History (NOT during iterations > 0)
6. Reasoning Boost (ONLY during iterations > 0)
7. User Prompt

## Configuration Files

| File | Purpose |
|------|---------|
| `config.yaml` | Main configuration (ollama, services, context settings) |
| `secrets.yaml` | Secrets (Redis password, API keys) - GITIGNORED |
| `data/prompt_injections.yaml` | `:category` definitions |

## Key Utilities

| Utility | File | Purpose |
|---------|------|---------|
| ConfigLoader | `src/utils/config_loader.py` | Centralized config access |
| CommandHandler | `src/utils/command_handler.py` | /command execution |
| FeedbackCollector | `src/utils/feedback_collector.py` | Collect user ratings (0-5) |
| ConversationHistoryManager | `src/utils/conversation_history.py` | Previous conversation turns |
| PromptHistoryManager | `src/utils/prompt_history.py` | Prompt auto-complete history |
| TokenLimitManager | `src/utils/token_limit_manager.py` | Discover/track model limits |
| PathResolver | `src/utils/path_resolver.py` | Resolve @ prefix paths |
| EmbeddingUtils | `src/utils/embedding_utils.py` | Embedding generation + similarity |

## Error Handling (per CLAUDE.md)

**Usage Pattern:**
```python
from src.errors_handler import handle_exception

try:
    # operation
except Exception as e:
    handle_exception(e, context={
        'function': 'my_function',
        'operation': 'what_was_being_done',
        'relevant_data': some_value
    })
```

## Service Dependencies

| Service | Port | Purpose | Config Key |
|---------|------|---------|------------|
| Ollama | 11434 | LLM inference | ollama |
| Sandbox | 18001 (8000 internal) | Heuristics/feedback | sandbox |
| Transformer | 16050 (5050 internal) | Embeddings | transformer |
| Redis | 16379 (6379 internal) | Caching/limits | redis |
| Elasticsearch | 9200 | Feedback storage | elasticsearch |

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_eternal_context.py
python -m pytest tests/test_auto_iteration_reasoning_boost.py
python -m pytest tests/test_spark_context.py
```

## Key File Locations

```
├── start.sh                                    # Entry point
├── main.py                                     # Python entry
├── config.yaml                                 # Main config
├── src/
│   ├── cli.py                                  # Core logic (1856 lines)
│   ├── agent.py                                # LLM interface
│   ├── utils/
│   │   ├── arg_parser.py                       # CLI args (-m, -p, -v)
│   │   ├── config_loader.py                    # Config access
│   │   ├── eternal_context.py                  # Persistent context
│   │   ├── ephemeral_context.py                # Session context
│   │   ├── spark_context.py                    # In-memory context
│   │   ├── command_handler.py                  # /command execution
│   │   ├── prompt_injection_completer.py       # :category replacement
│   │   ├── conversation_history.py             # Previous turns
│   │   ├── prompt_history.py                   # Auto-complete
│   │   ├── token_limit_manager.py              # Token limits
│   │   ├── feedback_collector.py               # Rating collection
│   │   ├── embedding_utils.py                  # Embeddings
│   │   └── path_resolver.py                    # @ resolution
│   └── errors_handler/
│       └── error_handler.py                    # Exception logging
├── data/
│   └── prompt_injections.yaml                  # :category config
└── tests/
    ├── test_eternal_context.py
    ├── test_auto_iteration_reasoning_boost.py
    └── test_spark_context*.py
```

## CLI Usage Examples

```bash
# Interactive mode (default)
./start.sh

# Non-interactive with prompt
./start.sh -p "What is Python?"
./start.sh --prompt "What is Python?"

# With model selection
./start.sh -m llama3.1:8b
./start.sh --model tinyllama

# Verbose debugging
./start.sh -v
./start.sh --verbose

# Combined
./start.sh -m llama3.1:8b -v -p "Explain quantum computing"
```

## Important Notes

1. **Sparks die with `/clear context`** - Behavior requirement
2. **Conversation history disabled during iterations > 0** - Heuristics-only mode
3. **Reasoning injection only on retries** - iteration_number > 0
4. **Semantic filtering** - Threshold: 0.5 (configurable)
5. **Auto-description** - Uses LLM to generate context descriptions
6. **Chunking** - Large files split with overlaps (default: 1000 words/chars)
7. **Embedding caching** - Via Redis for performance
8. **Error handling** - All exceptions logged with context via error_handler

