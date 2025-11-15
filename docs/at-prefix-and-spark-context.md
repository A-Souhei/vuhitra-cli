# @ Prefix and Spark Context

## Overview

The **@ prefix** feature provides a convenient way to reference files and directories in your working directory, with intelligent autocomplete. When combined with commands like `/load` and `/load-eternal`, it simplifies file path management. When used standalone (without commands), it automatically creates **Spark contexts** - lightweight, in-memory ephemeral contexts perfect for quick reference.

## Features

### 1. @ Prefix Autocomplete

When you type `@` in the CLI prompt, an autocomplete dropdown appears showing:
- All files in the working directory (recursively)
- All subdirectories and their files
- Hidden files (starting with `.` like `.env`)

The working directory is where the CLI was started from (`os.getcwd()`).

### 2. @ Prefix with /load and /load-eternal

You can use `@` as a shorthand for paths relative to the working directory:

```bash
# Traditional way
/load ./docs/api_spec.md

# With @ prefix (equivalent)
/load @docs/api_spec.md

# Same for eternal context
/load-eternal @docs/coding_standards.md
```

### 3. Directory Loading

If you reference a directory with `@`, all files in that directory will be loaded:

```bash
# Load all files in the docs directory as ephemeral contexts
/load @docs/

# Load all files in the docs directory as eternal contexts
/load-eternal @docs/
```

### 4. Spark Context - In-Memory Ephemeral

**Sparks** are created when you use `@` references in your prompt **without** `/load` or `/load-eternal` commands. They are:
- **In-memory only** (no Redis, no disk persistence)
- **Lightweight** and fast
- **Automatically loaded** when you reference them
- **Die with `/clear context`** command
- Perfect for quick, temporary context injection

Example:

```bash
# User prompt with @ reference
What does @README.md say about installation?

# Result:
# - README.md is automatically loaded as a Spark context
# - Its contents are injected into the LLM prompt
# - The LLM can reference the README content to answer
# - The Spark will be cleared when you run /clear context
```

## Context Hierarchy

The system now has **4 types of context**, injected in this order:

1. **Eternal Context** (Permanent, disk-persisted)
   - Survives CLI restarts
   - Cleared with `/clear eternal`

2. **Ephemeral Context** (Session-scoped, Redis + in-memory)
   - Lives until cleared or CLI exits
   - Cleared with `/clear ephemeral`

3. **Spark Context** (In-memory ephemeral)
   - Lives until `/clear context` or CLI exits
   - Cleared automatically with `/clear context`
   - Cleared manually with `/clear spark`

4. **Conversation History** (Retrieved via RAG)
5. **Heuristics** (Retrieved via Elasticsearch kNN)

## Commands

### Loading Files/Directories

```bash
# Load file as ephemeral context (with @ prefix)
/load @api_spec.md
/load @api_spec.md my_label

# Load file as eternal context (with @ prefix)
/load-eternal @coding_standards.md
/load-eternal @coding_standards.md standards

# Load all files in a directory
/load @docs/
/load-eternal @docs/
```

### Viewing Contexts

```bash
# Show all ephemeral contexts
/show ephemeral

# Show all eternal contexts
/show eternal

# Show all Spark contexts
/show spark
```

### Clearing Contexts

```bash
# Clear conversation history AND all Sparks
/clear context

# Clear specific ephemeral context
/clear ephemeral <label>
/clear ephemeral --all

# Clear specific eternal context
/clear eternal <label>
/clear eternal --all

# Clear specific Spark context
/clear spark <label>
/clear spark --all
```

## Examples

### Example 1: Quick File Reference

```bash
❯ How do I set up the project? Check @README.md and @INSTALL.md

# Automatically:
# - Loads README.md as Spark context
# - Loads INSTALL.md as Spark context
# - Injects both into LLM prompt
# - LLM answers based on the file contents
```

### Example 2: Load Directory as Eternal Context

```bash
❯ /load-eternal @docs/api/

✓ Loaded 5 eternal context(s) from @docs/api/
  Files: authentication.md, endpoints.md, models.md, errors.md, examples.md

❯ /show eternal
Eternal Contexts (5/20):
  • api_authentication    -   10.2KB - /home/user/project/docs/api/authentication.md
  • api_endpoints         -   25.3KB - /home/user/project/docs/api/endpoints.md
  • api_models            -   15.7KB - /home/user/project/docs/api/models.md
  • api_errors            -    8.1KB - /home/user/project/docs/api/errors.md
  • api_examples          -   12.4KB - /home/user/project/docs/api/examples.md

Total: 71.7KB
```

### Example 3: Mix of Contexts

```bash
# Load some files as eternal (permanent)
❯ /load-eternal @docs/coding_standards.md standards

# Load some files as ephemeral (session-only)
❯ /load @docs/current_sprint.md

# Reference a file inline (creates Spark)
❯ What's the bug status? Check @BUGS.md

# View all contexts
❯ /show eternal
Eternal Contexts (1/20):
  • standards    -   10.2KB - /home/user/project/docs/coding_standards.md

❯ /show ephemeral
Ephemeral Contexts (1/10):
  • current_sprint    -   5.3KB - /home/user/project/docs/current_sprint.md

❯ /show spark
Spark Contexts (1/20):
  • BUGS    -   3.2KB - /home/user/project/BUGS.md

# Clear just the Sparks
❯ /clear context

✓ Cleared 1 conversation turns from history
✓ Cleared 1 Spark(s)

# Eternal and ephemeral contexts remain
```

## Configuration

Configure Spark context in `config.yaml`:

```yaml
spark_context:
  # Enable/disable Spark context feature
  enabled: true
  # Maximum file size in MB that can be loaded
  max_file_size_mb: 10
  # Maximum number of Spark contexts (in-memory only)
  max_contexts: 20
```

## Technical Details

### Path Resolution

The `PathResolver` class handles `@` prefix resolution:
- `@file.txt` → `/path/to/working_dir/file.txt`
- `@subdir/file.txt` → `/path/to/working_dir/subdir/file.txt`
- `@.env` → `/path/to/working_dir/.env` (hidden files supported)

### Autocomplete

The `FilePathCompleter` class provides autocomplete:
- Scans working directory recursively (up to max depth of 5)
- Includes hidden files and directories
- Updates cache every 5 seconds
- Shows file/directory metadata in suggestions

### Spark Context Manager

The `SparkContextManager` class manages Spark contexts:
- Stores contexts in-memory (Python list)
- No Redis or disk persistence
- Automatically cleared with `/clear context`
- Can be manually managed with `/clear spark` and `/show spark`

### Integration with RAG Pipeline

Spark contexts are injected into the LLM prompt in this order:

1. Eternal Context
2. Ephemeral Context
3. **Spark Context** ← New!
4. Conversation History (retrieved)
5. Heuristics (retrieved)

## Benefits

1. **Convenience**: `@` prefix autocomplete makes file referencing fast and accurate
2. **Flexibility**: Choose between eternal, ephemeral, or Spark contexts based on persistence needs
3. **Speed**: Sparks are in-memory only, no Redis overhead
4. **Smart Loading**: Directories automatically load all files
5. **Context Awareness**: The CLI detects `@` references and loads them automatically

## Best Practices

- **Use Eternal Context** for documentation and coding standards that you always want loaded
- **Use Ephemeral Context** for project-specific files that change between sessions
- **Use Spark Context** (via `@`) for quick, one-off file references in prompts
- **Use Directory Loading** to bulk-load related files (e.g., all API docs)
- **Clear Sparks regularly** with `/clear context` to avoid context pollution
