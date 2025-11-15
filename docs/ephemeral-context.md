# Ephemeral Context: Session-Scoped RAG Dimension

## Overview

Ephemeral Context is a new dimension in the vuhitra-cli RAG (Retrieval-Augmented Generation) system that provides session-scoped, file-based context injection. Unlike the existing conversation history (dynamic, incremental) and heuristics (cross-session, retrieved), ephemeral context is:

- **Manually loaded** from files via CLI commands
- **Fully injected** into every prompt (no similarity-based retrieval)
- **Session-scoped** and persists until explicitly cleared
- **File-based** to support documentation, specifications, and reference materials

## Architecture

### Three-Layer RAG Context

```
┌─────────────────────────────────────────────────────────┐
│                    Enhanced Prompt                       │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │
┌───────────────────────────┴──────────────────────────────┐
│                                                           │
│  1. Ephemeral Context (Full Injection)                   │
│     • Loaded from files                                  │
│     • Always present in every prompt                     │
│     • Session-scoped                                     │
│                                                           │
│  2. Conversation History (Top-k Retrieval)               │
│     • Recent conversation turns                          │
│     • Semantic similarity search                         │
│     • In-memory, session-scoped                          │
│                                                           │
│  3. Heuristics (kNN Retrieval)                           │
│     • Historical knowledge                               │
│     • Cross-session persistence                          │
│     • Elasticsearch storage                              │
│                                                           │
│  4. User Query (Original Prompt)                         │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Conversation History | Heuristics | **Ephemeral Context** |
|---------|---------------------|------------|----------------------|
| **Scope** | Session | Cross-session | Session |
| **Storage** | In-memory | Elasticsearch | In-memory |
| **Embedding** | Per-turn, incremental | Per-heuristic | Full document or chunked |
| **Retrieval** | Top-k similarity | kNN + rating filter | **Full injection (no retrieval)** |
| **First prompt** | Empty | Retrieved | **Always present** |
| **Loading** | Automatic | Automatic | **Manual via `/load`** |
| **Clearing** | `/clear context` | Manual deletion | `/clear ephemeral` |

## Usage

### Commands

#### Loading Files

```bash
# Load a file with auto-generated label (filename)
> /load ./docs/api_spec.md

# Load a file with custom label
> /load ./docs/coding_standards.md standards

# Load multiple files
> /load ./docs/database_schema.md schema
> /load ./docs/authentication.md auth
```

#### Viewing Loaded Contexts

```bash
# Show all loaded ephemeral contexts
> /show ephemeral

# Example output:
# Loaded ephemeral contexts:
#   1. api_spec (12.5 KB, 3 chunks) - /path/to/docs/api_spec.md
#   2. standards (5.2 KB, 1 chunk) - /path/to/docs/coding_standards.md
#
# Total size: 17.7 KB
# Contexts: 2/10
```

#### Clearing Contexts

```bash
# Clear specific context by label
> /clear ephemeral api_spec

# Clear all ephemeral contexts
> /clear ephemeral --all
```

### Example Workflow

```bash
$ vuhitra-cli

# Load project documentation
> /load ./docs/project_requirements.md requirements
✓ Loaded 'requirements' (8.3 KB, 2 chunks, 2 embeddings)

# Load API specifications
> /load ./docs/api_endpoints.md api
✓ Loaded 'api' (15.7 KB, 4 chunks, 4 embeddings)

# First prompt - both contexts already present!
> How should I implement the user authentication endpoint?

# The LLM receives:
# [Ephemeral Context: requirements.md + api_endpoints.md]  ← Full injection
# [Conversation History: (empty - first prompt)]
# [Heuristics: Similar past implementations]
# [User query: How should I implement the user authentication endpoint?]

# Continue conversation - ephemeral context persists
> What validation should I add to the login form?

# The LLM still receives the full ephemeral context
# [Ephemeral Context: requirements.md + api_endpoints.md]  ← Still present
# [Conversation History: Previous Q&A about authentication]
# [Heuristics: Similar validation implementations]
# [User query: What validation should I add to the login form?]

# View loaded contexts
> /show ephemeral
Loaded ephemeral contexts:
  1. requirements (8.3 KB, 2 chunks) - ./docs/project_requirements.md
  2. api (15.7 KB, 4 chunks) - ./docs/api_endpoints.md

Total size: 24.0 KB
Contexts: 2/10

# Clear specific context when no longer needed
> /clear ephemeral requirements
✓ Removed ephemeral context 'requirements'

# Or clear all
> /clear ephemeral --all
✓ Cleared all ephemeral contexts (2 contexts removed)
```

## Configuration

Configuration is located in `config.yaml`:

```yaml
# Ephemeral context configuration
ephemeral_context:
  # Enable/disable ephemeral context feature
  enabled: true

  # Maximum file size in MB that can be loaded
  max_file_size_mb: 10

  # Maximum number of simultaneous contexts
  max_contexts: 10

  # Text chunking configuration (for large files)
  chunking:
    enabled: true
    # Chunk size in words
    chunk_size: 1000
    # Overlap between chunks in words
    overlap: 200
```

### Configuration Parameters

- **`enabled`**: Enable/disable the ephemeral context feature (default: `true`)
- **`max_file_size_mb`**: Maximum file size in MB that can be loaded (default: `10`)
- **`max_contexts`**: Maximum number of simultaneous contexts (default: `10`)
- **`chunking.enabled`**: Enable automatic chunking for large files (default: `true`)
- **`chunking.chunk_size`**: Size of each chunk in words (default: `1000`)
- **`chunking.overlap`**: Overlap between chunks in words (default: `200`)

## Implementation Details

### EphemeralContextManager Class

Located in `src/utils/ephemeral_context.py`

**Key Methods:**

```python
# Load a file into ephemeral context
load_file(file_path: str, label: Optional[str] = None) -> Tuple[bool, str]

# Get formatted context string for prompt injection
get_context_string() -> str

# Get all embeddings (for advanced operations)
get_embeddings() -> List[np.ndarray]

# Clear all contexts
clear_all() -> int

# Remove specific context by label
remove_by_label(label: str) -> bool

# Get context count
get_context_count() -> int

# Get summary of loaded contexts
get_summary() -> str
```

### Text Chunking

For large files that exceed the configured chunk size, the system automatically:

1. Splits the text into overlapping chunks
2. Generates embeddings for each chunk
3. Stores chunk metadata for context assembly

**Chunking Strategy:**
- **Semantic chunking**: Word-based with configurable overlap
- **Overlap**: Ensures context continuity between chunks
- **Embedding**: Each chunk gets its own embedding vector

### Embedding Generation

Ephemeral contexts use the same transformer service as conversation history and heuristics:

- **Model**: `all-MiniLM-L6-v2` (384-dimensional embeddings)
- **Endpoint**: `POST /api/generate-embedding`
- **Service**: Centralized transformer service (port 16050)

**Why Embeddings?**

Even though ephemeral context is fully injected (not retrieved), embeddings enable:
- Future semantic deduplication with conversation history
- Intelligent truncation if token limits are exceeded
- Relevance scoring for advanced features

## Use Cases

### 1. **API Development with Specifications**

```bash
> /load ./openapi.yaml api-spec
> /load ./authentication_requirements.md auth-req

> How do I implement OAuth2 authentication according to our specs?
# LLM has immediate access to both specs
```

### 2. **Codebase Standards Enforcement**

```bash
> /load ./coding_standards.md standards
> /load ./architecture_patterns.md patterns

> Write a new user service following our standards
# LLM applies standards automatically
```

### 3. **Database Schema Reference**

```bash
> /load ./database_schema.sql schema
> /load ./migration_guide.md migrations

> How should I query user subscriptions?
# LLM knows the exact schema structure
```

### 4. **Project-Specific Context**

```bash
> /load ./project_glossary.md glossary
> /load ./business_rules.md rules

> Explain how the billing cycle works
# LLM uses project-specific terminology
```

## Technical Comparison

### Ephemeral Context vs. Conversation History

**Ephemeral Context:**
- Loaded from files
- Persists across entire session
- No similarity retrieval
- Available from first prompt

**Conversation History:**
- Generated from interactions
- Dynamic and incremental
- Top-k similarity retrieval
- Starts empty

### Ephemeral Context vs. Heuristics

**Ephemeral Context:**
- Session-scoped
- Manually managed
- File-based
- Full injection

**Heuristics:**
- Cross-session
- Automatically learned
- Elasticsearch-backed
- kNN retrieval

## Error Handling

The implementation uses the error handler feature for robust error management:

```python
try:
    # Operation
except Exception as e:
    handle_exception(e, context={
        'function': 'function_name',
        'file_path': file_path,
        'label': label
    })
```

All errors are logged and handled gracefully without crashing the CLI.

## Testing

Comprehensive tests are available in `tests/test_ephemeral_context.py`:

```bash
# Activate venv
source .venv/bin/activate

# Run tests
python tests/test_ephemeral_context.py
```

**Test Coverage:**
- Dataclass functionality
- Manager initialization (enabled/disabled)
- File loading and validation
- Context retrieval and management
- Chunking for large files
- Maximum context limits
- Size calculations
- Command integration

## Future Enhancements

Potential improvements for future versions:

1. **Redis Persistence**: Store ephemeral contexts in Redis for session recovery
2. **TTL Support**: Auto-clear contexts after a time period
3. **Smart Truncation**: Use embeddings to intelligently truncate when token limits are exceeded
4. **Semantic Deduplication**: Detect overlap between ephemeral and conversation contexts
5. **Context Versioning**: Track changes to loaded files
6. **Batch Loading**: Load multiple files with one command
7. **Context Prioritization**: Weight different contexts based on relevance
8. **Export/Import**: Save and restore ephemeral context sets

## Troubleshooting

### "Ephemeral context is disabled"

**Solution:** Enable in `config.yaml`:
```yaml
ephemeral_context:
  enabled: true
```

### "File too large"

**Solution:** Increase `max_file_size_mb` in config or split the file into smaller parts.

### "Maximum number of contexts reached"

**Solution:** Clear some contexts with `/clear ephemeral <label>` or increase `max_contexts` in config.

### "File not found"

**Solution:** Verify the file path is correct. Use absolute paths or paths relative to the CLI working directory.

## Summary

Ephemeral Context provides a powerful third dimension to the vuhitra-cli RAG system, enabling:

- **Persistent session context** from files
- **Immediate availability** in every prompt
- **Manual control** over loaded materials
- **Flexible management** via CLI commands

This complements the existing conversation history (dynamic) and heuristics (learned) dimensions, creating a comprehensive context management system for enhanced LLM interactions.
