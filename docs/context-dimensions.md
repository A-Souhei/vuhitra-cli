## Ephemeral, Eternal & Spark Context: Extended RAG Dimensions

## Overview

Vuhitra-CLI features a comprehensive **five-layer RAG (Retrieval-Augmented Generation) system** that provides different types of context to enhance LLM interactions:

1. **Eternal Context** - Permanent, cross-session reference materials
2. **Ephemeral Context** - Session-scoped, temporary reference materials
3. **Spark Context** - In-memory, lightweight ephemeral context (NEW!)
4. **Conversation History** - Dynamic, recent conversation turns
5. **Heuristics** - Historical knowledge learned from past interactions

This document focuses on the **Eternal**, **Ephemeral**, and **Spark** context dimensions, which enable file-based context injection.

## Architecture

### Five-Layer RAG Context

```
┌─────────────────────────────────────────────────────────┐
│                    Enhanced Prompt                       │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │
┌───────────────────────────┴──────────────────────────────┐
│                                                           │
│  1. Eternal Context (Full Injection, Permanent)          │
│     • Loaded from files                                  │
│     • Always present (survives CLI restarts)             │
│     • Stored on disk                                     │
│     • Cross-session persistence                          │
│                                                           │
│  2. Ephemeral Context (Full Injection, Session)          │
│     • Loaded from files                                  │
│     • Always present in every prompt                     │
│     • In-memory only                                     │
│     • Session-scoped                                     │
│                                                           │
│  3. Spark Context (Full Injection, In-Memory) NEW!       │
│     • Loaded from files via @ prefix                     │
│     • Always present in every prompt                     │
│     • In-memory only (no Redis, no disk)                 │
│     • Dies with /clear context                           │
│                                                           │
│  4. Conversation History (Top-k Retrieval)               │
│     • Recent conversation turns                          │
│     • Semantic similarity search                         │
│     • In-memory, session-scoped                          │
│                                                           │
│  5. Heuristics (kNN Retrieval)                           │
│     • Historical knowledge                               │
│     • Cross-session persistence                          │
│     • Elasticsearch storage                              │
│                                                           │
│  User Query (Original Prompt)                            │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### Comparison Matrix

| Feature | **Eternal Context** | **Ephemeral Context** | **Spark Context** | Conversation History | Heuristics |
|---------|---------------------|----------------------|-------------------|---------------------|------------|
| **Scope** | **Cross-session** | **Session** | **Session** | Session | Cross-session |
| **Storage** | **Disk (JSON)** | **In-memory** | **In-memory only** | In-memory | Elasticsearch |
| **Persistence** | **Permanent** | **Session only** | **Session only** | Session only | Permanent |
| **Retrieval** | **Full injection** | **Full injection** | **Full injection** | Top-k similarity | kNN + rating filter |
| **First prompt** | **Always present** | **Always present** | **Always present** | Empty | Retrieved |
| **Loading** | **Manual: `/load-eternal` or `@`** | **Manual: `/load` or `@`** | **Auto: `@prefix` in prompt** | Automatic | Automatic |
| **Clearing** | **`/clear eternal`** | **`/clear ephemeral`** | **`/clear context` or `/clear spark`** | `/clear context` | Manual deletion |
| **Auto-load on startup** | **Yes** | **No** | **No** | No | No |
| **Use case** | **Permanent docs/specs** | **Temporary references** | **Quick file references** | Recent discussion | Historical knowledge |

## Usage

### Eternal Context Commands

#### Loading Eternal Contexts

```bash
# Load a file into eternal context (persists across sessions)
> /load-eternal ./docs/api_spec.md

# Load with custom label
> /load-eternal ./docs/coding_standards.md standards

# Load multiple files
> /load-eternal ./docs/database_schema.md schema
> /load-eternal ./docs/authentication.md auth
```

#### Viewing Eternal Contexts

```bash
# Show all loaded eternal contexts
> /show eternal

# Example output:
# Loaded eternal contexts:
#   1. api_spec (12.5 KB, 3 chunks) - /path/to/docs/api_spec.md
#   2. standards (5.2 KB, 1 chunk) - /path/to/docs/coding_standards.md
#
# Total size: 17.7 KB
# Contexts: 2/20
# Storage: /path/to/.vuhitra/eternal_contexts
```

#### Clearing Eternal Contexts

```bash
# Clear specific eternal context by label (deletes from storage)
> /clear eternal api_spec

# Clear all eternal contexts (deletes all from storage)
> /clear eternal --all
```

### Ephemeral Context Commands

#### Loading Ephemeral Contexts

```bash
# Load a file into ephemeral context (session only)
> /load ./docs/temp_notes.md

# Load with custom label
> /load ./docs/meeting_notes.md notes
```

#### Viewing Ephemeral Contexts

```bash
# Show all loaded ephemeral contexts
> /show ephemeral

# Example output:
# Loaded ephemeral contexts:
#   1. temp_notes (8.3 KB, 2 chunks) - ./docs/temp_notes.md
#   2. notes (4.1 KB, 1 chunk) - ./docs/meeting_notes.md
#
# Total size: 12.4 KB
# Contexts: 2/10
```

#### Clearing Ephemeral Contexts

```bash
# Clear specific ephemeral context by label
> /clear ephemeral temp_notes

# Clear all ephemeral contexts
> /clear ephemeral --all
```

## Example Workflows

### Workflow 1: Permanent Project Documentation (Eternal)

```bash
$ vuhitra-cli

# Load permanent project documentation (survives restarts)
> /load-eternal ./docs/architecture.md architecture
✓ Loaded eternal context 'architecture' (15.2 KB, 4 chunks, persisted)

> /load-eternal ./docs/api_reference.md api
✓ Loaded eternal context 'api' (22.8 KB, 6 chunks, persisted)

# These contexts are now permanently available
> How should I structure the new user service?

# The LLM receives:
# [Eternal: architecture.md + api_reference.md]  ← Permanent, always present
# [Ephemeral: (none)]
# [Conversation: (empty - first prompt)]
# [Heuristics: Similar past implementations]
# [User query: How should I structure the new user service?]

# Exit and restart CLI
> exit

# ---- CLI RESTARTED ----

$ vuhitra-cli

# Eternal contexts are automatically loaded!
> /show eternal
Loaded eternal contexts:
  1. architecture (15.2 KB, 4 chunks) - ./docs/architecture.md
  2. api (22.8 KB, 6 chunks) - ./docs/api_reference.md

# Continue working with same context
> What are the authentication requirements?
# The LLM still has access to both eternal contexts
```

### Workflow 2: Temporary Session Notes (Ephemeral)

```bash
$ vuhitra-cli

# Load temporary meeting notes for this session only
> /load ./temp/meeting_notes.md notes
✓ Loaded 'notes' (3.5 KB, 1 chunk, embedding generated)

# Use during session
> What action items did we discuss?

# Clear when session ends
> /clear ephemeral --all
✓ Cleared all ephemeral contexts (1 contexts removed)

# Exit CLI - ephemeral contexts are gone
> exit

# ---- CLI RESTARTED ----

$ vuhitra-cli

# Ephemeral contexts are NOT auto-loaded (session-only)
> /show ephemeral
No ephemeral contexts loaded
```

### Workflow 3: Combined Usage

```bash
$ vuhitra-cli

# Eternal contexts auto-loaded from previous session
> /show eternal
Loaded eternal contexts:
  1. architecture (15.2 KB, 4 chunks) - ./docs/architecture.md
  2. api (22.8 KB, 6 chunks) - ./docs/api_reference.md

# Load ephemeral context for today's work
> /load ./temp/sprint_23_goals.md sprint
✓ Loaded 'sprint' (2.1 KB, 1 chunk, embedding generated)

# Load another eternal context (permanent addition)
> /load-eternal ./docs/security_guidelines.md security
✓ Loaded eternal context 'security' (8.7 KB, 2 chunks, persisted)

# Now all contexts are available
> /show eternal
Loaded eternal contexts:
  1. architecture (15.2 KB, 4 chunks)
  2. api (22.8 KB, 6 chunks)
  3. security (8.7 KB, 2 chunks)  ← NEW

> /show ephemeral
Loaded ephemeral contexts:
  1. sprint (2.1 KB, 1 chunk)

# Ask a question - LLM receives ALL contexts
> How should I implement OAuth2 authentication following our guidelines?

# The LLM receives:
# [Eternal: architecture.md + api_reference.md + security_guidelines.md]  ← Permanent
# [Ephemeral: sprint_23_goals.md]  ← Session-only
# [Conversation: (empty - first prompt)]
# [Heuristics: Similar OAuth implementations]
# [User query: How should I implement OAuth2 authentication...]

# End of day - clear ephemeral but keep eternal
> /clear ephemeral --all
✓ Cleared all ephemeral contexts (1 contexts removed)

> exit

# ---- NEXT DAY ----

$ vuhitra-cli

# Eternal contexts still present, ephemeral gone
> /show eternal
Loaded eternal contexts:
  1. architecture (15.2 KB, 4 chunks)
  2. api (22.8 KB, 6 chunks)
  3. security (8.7 KB, 2 chunks)

> /show ephemeral
No ephemeral contexts loaded

# Load new ephemeral for today
> /load ./temp/sprint_24_goals.md sprint
```

## Configuration

### Ephemeral Context

Located in `config.yaml`:

```yaml
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
    chunk_size: 1000  # Words per chunk
    overlap: 200      # Word overlap
```

### Eternal Context

Located in `config.yaml`:

```yaml
eternal_context:
  # Enable/disable eternal context feature
  enabled: true
  # Storage directory for eternal contexts (relative or absolute path)
  storage_dir: .vuhitra/eternal_contexts
  # Maximum file size in MB that can be loaded
  max_file_size_mb: 10
  # Maximum number of eternal contexts
  max_contexts: 20
  # Text chunking configuration (for large files)
  chunking:
    enabled: true
    chunk_size: 1000  # Words per chunk
    overlap: 200      # Word overlap
```

## Implementation Details

### EphemeralContextManager Class

Located in `src/utils/ephemeral_context.py`

**Key Methods:**
- `load_file(file_path, label)` - Load a file (in-memory only)
- `get_context_string()` - Get formatted context for prompt injection
- `clear_all()` - Clear all contexts (memory only)
- `remove_by_label(label)` - Remove specific context
- `get_summary()` - Get summary of loaded contexts

**Storage:** In-memory only, no persistence

### EternalContextManager Class

Located in `src/utils/eternal_context.py`

**Key Methods:**
- `load_file(file_path, label)` - Load and persist a file
- `get_context_string()` - Get formatted context for prompt injection
- `clear_all()` - Clear all contexts and delete from storage
- `remove_by_label(label)` - Remove and delete from storage
- `reload_from_file(label)` - Reload context from original file
- `get_summary()` - Get summary with storage location

**Storage:** JSON files in `.vuhitra/eternal_contexts/`
- Auto-loaded on CLI startup
- Each context is a separate JSON file
- Includes content, metadata, and chunks

## Use Cases

### Eternal Context - Permanent References

1. **Project Documentation**
   ```bash
   > /load-eternal ./docs/ARCHITECTURE.md
   > /load-eternal ./docs/API_REFERENCE.md
   > /load-eternal ./docs/CODING_STANDARDS.md
   ```
   Use for: Permanent project knowledge that should always be available

2. **Company Guidelines**
   ```bash
   > /load-eternal ./company/security_policy.md security
   > /load-eternal ./company/code_review_checklist.md checklist
   ```
   Use for: Company-wide standards that apply to all projects

3. **Database Schemas**
   ```bash
   > /load-eternal ./db/schema.sql schema
   > /load-eternal ./db/migrations/README.md migrations
   ```
   Use for: Infrastructure knowledge needed across sessions

### Ephemeral Context - Temporary References

1. **Sprint/Task-Specific Notes**
   ```bash
   > /load ./sprints/current_sprint_goals.md
   > /load ./tasks/feature_xyz_notes.md
   ```
   Use for: Temporary context for current work

2. **Meeting Notes**
   ```bash
   > /load ./meetings/standup_2025-01-15.md
   ```
   Use for: Today's discussion points, cleared after session

3. **Experimental/Draft Documents**
   ```bash
   > /load ./drafts/proposed_api_changes.md
   ```
   Use for: WIP documents that may change frequently

## Technical Details

### Text Chunking

Both eternal and ephemeral contexts support automatic chunking for large files:

- **Trigger**: File exceeds `chunk_size` words
- **Method**: Word-based with configurable overlap
- **Storage**:
  - Ephemeral: Chunks stored in-memory
  - Eternal: Chunks persisted to JSON

### Embedding Generation

- **Model**: `all-MiniLM-L6-v2` (384-dimensional)
- **Endpoint**: Transformer service `/api/generate-embedding`
- **Storage**:
  - Ephemeral: Embeddings in-memory only
  - Eternal: Embeddings NOT persisted (regenerated on load)

**Why Embeddings?**
Even though contexts are fully injected (not retrieved), embeddings enable:
- Future semantic deduplication
- Intelligent truncation if token limits exceeded
- Relevance scoring for advanced features

### Storage Format (Eternal Only)

Each eternal context is stored as `{label}.json`:

```json
{
  "label": "api_spec",
  "file_path": "/path/to/docs/api_spec.md",
  "content": "Full file content...",
  "timestamp": "2025-01-15T10:30:00",
  "chunks": ["chunk1...", "chunk2..."]
}
```

## Error Handling

All operations use the error handler feature for robust error management:

```python
try:
    # Operation
except Exception as e:
    handle_exception(e, context={
        'function': 'function_name',
        'details': {...}
    })
```

Errors are logged and handled gracefully without crashing the CLI.

## Testing

### Ephemeral Context Tests

Located in `tests/test_ephemeral_context.py`:

```bash
python tests/test_ephemeral_context.py
```

### Eternal Context Tests

Located in `tests/test_eternal_context.py`:

```bash
python tests/test_eternal_context.py
```

**Test Coverage:**
- File loading and validation
- Context management operations
- Persistence (eternal only)
- Chunking for large files
- Size calculations and limits
- Storage operations (eternal only)
- Error handling

## Troubleshooting

### "Ephemeral/Eternal context is disabled"

**Solution:** Enable in `config.yaml`:
```yaml
ephemeral_context:
  enabled: true

eternal_context:
  enabled: true
```

### "File too large"

**Solution:** Increase `max_file_size_mb` in config or split the file.

### "Maximum number of contexts reached"

**Solution:** Clear some contexts or increase `max_contexts` in config.

### "Failed to persist eternal context"

**Causes:**
- Storage directory not writable
- Disk space full
- Permission issues

**Solution:** Check storage directory permissions and disk space.

### Eternal contexts not auto-loading

**Checks:**
1. Verify storage directory exists and contains `.json` files
2. Check `eternal_context.enabled = true` in config
3. Verify JSON files are valid
4. Check CLI startup logs for errors

## Best Practices

### When to Use Eternal Context

✅ **Use eternal context for:**
- Project documentation that rarely changes
- Company-wide standards and guidelines
- Database schemas and infrastructure docs
- API specifications and contracts
- Security policies and checklists

❌ **Don't use eternal context for:**
- Temporary notes or drafts
- Session-specific information
- Frequently changing documents
- Large files that will exceed token limits

### When to Use Ephemeral Context

✅ **Use ephemeral context for:**
- Sprint or task-specific notes
- Meeting notes and action items
- Experimental or draft documents
- Temporary reference materials
- Session-specific context

❌ **Don't use ephemeral context for:**
- Permanent project documentation
- Information needed across sessions
- Files that should survive CLI restarts

### Managing Context Size

1. **Monitor total size**: Use `/show eternal` and `/show ephemeral` regularly
2. **Clear unused contexts**: Remove contexts no longer needed
3. **Use chunking**: Enable for large files (default: on)
4. **Set appropriate limits**: Configure `max_file_size_mb` and `max_contexts`

## Summary

The ephemeral and eternal context dimensions provide powerful, flexible context management:

| Aspect | Eternal | Ephemeral |
|--------|---------|-----------|
| **Lifetime** | Permanent (until deleted) | Session only |
| **Persistence** | Disk storage | Memory only |
| **Auto-load** | Yes (on startup) | No |
| **Best for** | Permanent docs/specs | Temporary references |
| **Commands** | `/load-eternal`, `/show eternal`, `/clear eternal` | `/load`, `/show ephemeral`, `/clear ephemeral` |

Together with conversation history and heuristics, they create a comprehensive **four-layer RAG system** that provides both permanent knowledge and flexible, session-specific context for enhanced LLM interactions.
