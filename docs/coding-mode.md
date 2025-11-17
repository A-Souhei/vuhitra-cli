# Coding Mode

Coding mode is a special mode in vuhitra-cli designed for software development tasks. It provides different context management features optimized for coding workflows.

## Overview

When coding mode is enabled:
- **Zero-rating auto-iteration is disabled** - Failed responses (rating=0) don't trigger automatic retries
- **Eternals are disabled** - Regular eternal contexts are not available
- **Ephemerals are disabled** - Regular ephemeral contexts are not available
- **Pillars are enabled** - Coding mode persistent contexts (auto-loaded from `pillars/` directory)
- **Vanishers are enabled** - Coding mode session contexts (requires mirrored files)
- **Sparks remain enabled** - In-memory contexts still work as normal

## Enabling Coding Mode

Start the CLI with the `--coding` flag:

```bash
./start.sh --coding
```

Or with verbose mode:

```bash
./start.sh --coding --verbose
```

## Pillars

Pillars are the coding mode equivalent of eternals - they provide persistent cross-session context.

### Key Features

- **Persistent**: Pillars survive CLI restarts (stored in `.vuhitra/pillar_contexts/`)
- **Auto-loading**: Files in `pillars/` directory are automatically loaded on CLI startup
- **Semantic filtering**: Context is filtered by relevance to your prompt
- **Manual loading**: You can also load files manually using `/pillar load`

### Auto-Loading from pillars/ Directory

Files placed in the `pillars/` directory are automatically loaded when you start the CLI in coding mode:

```bash
mkdir -p pillars
cp docs/API_SPEC.md pillars/
cp docs/CODING_STANDARDS.md pillars/
./start.sh --coding
```

When the CLI starts, it will automatically:
1. Scan the `pillars/` directory for files
2. Load and embed each file as a pillar context
3. Skip files that were already loaded in previous sessions (no re-embedding)
4. Show a summary of loaded pillars

### Manual Loading

You can also load pillars manually during your session:

```bash
# Load a single file
/pillar load @docs/architecture.md

# Load a file with a custom label
/pillar load @docs/api.md api_docs

# Load a file with label and description
/pillar load @docs/guidelines.md guidelines "Coding guidelines and best practices"

# Load all files from a directory
/pillar load @docs/
```

### Managing Pillars

```bash
# Show loaded pillars
/show pillar

# Clear a specific pillar
/clear pillar api_docs

# Clear all pillars
/clear pillar --all
```

### Example Output

```
$ ./start.sh --coding

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃              vuhitra-cli (claude-4o)              ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

🔧 Coding mode enabled - Using Pillars & Vanishers, auto-iteration disabled
✓ Auto-loaded 2 pillar(s) from pillars/ directory

Ready! Type your prompt or use /help for commands.
>
```

## Vanishers

Vanishers are the coding mode equivalent of ephemerals - they provide session-scoped context.

### Key Features

- **Session-scoped**: Vanishers are cleared when the session ends
- **Requires mirrors**: Files must be mirrored to sandbox before loading as vanishers
- **Semantic filtering**: Context is filtered by relevance to your prompt
- **Mirror verification**: CLI checks if file is mirrored before allowing load

### Usage

Vanishers can only be loaded if the file/directory is already mirrored:

```bash
# First, mirror the file
/mirror do @data/config.json

# Then load it as a vanisher
/vanisher load @data/config.json

# Load with custom label
/vanisher load @data/config.json my_config

# Load with label and description
/vanisher load @data/file.txt myfile "Configuration file for feature X"
```

### Managing Vanishers

```bash
# Show loaded vanishers
/show vanisher

# Clear a specific vanisher
/clear vanisher my_config

# Clear all vanishers
/clear vanisher --all
```

### Why Mirrors Are Required

Vanishers require files to be mirrored first because:
1. **Sandbox integration**: Mirrored files are accessible in the sandbox environment
2. **Data consistency**: Ensures the file is synchronized with the sandbox
3. **Workflow alignment**: Aligns with the mirror feature for bidirectional sync

## Context Injection Order

When coding mode is enabled, contexts are injected into prompts in this order:

1. **Pillar Context** - Persistent coding references (auto-loaded + manually loaded)
2. **Vanisher Context** - Session-scoped mirrored files
3. **Spark Context** - In-memory ephemeral contexts (from @ references)
4. **Conversation History** - Relevant previous turns
5. **Heuristics** - Retrieved similar patterns
6. **User Prompt** - Your actual query

## Comparison with Normal Mode

| Feature | Normal Mode | Coding Mode |
|---------|-------------|-------------|
| Eternals | ✅ Enabled | ❌ Disabled |
| Ephemerals | ✅ Enabled | ❌ Disabled |
| Pillars | ❌ Disabled | ✅ Enabled + Auto-load |
| Vanishers | ❌ Disabled | ✅ Enabled |
| Sparks | ✅ Enabled | ✅ Enabled |
| Auto-iteration | ✅ Enabled | ❌ Disabled |
| Persistent storage | `.vuhitra/eternal_contexts/` | `.vuhitra/pillar_contexts/` |
| Auto-load directory | N/A | `pillars/` |

## Use Cases

### 1. Code Review with Standards

```bash
# Set up pillars
mkdir -p pillars
cp docs/CODING_STANDARDS.md pillars/
cp docs/ARCHITECTURE.md pillars/

# Start coding mode
./start.sh --coding

# The LLM now has access to your standards and architecture docs
> Review this code for compliance with our coding standards
```

### 2. Working with Project Documentation

```bash
# Auto-load project docs
cp docs/API_SPEC.md pillars/
cp docs/DATABASE_SCHEMA.md pillars/

./start.sh --coding

> How should I implement the user authentication endpoint?
```

### 3. Temporary File References

```bash
./start.sh --coding

# Mirror and load a config file temporarily
/mirror do @config/staging.yml
/vanisher load @config/staging.yml staging_config

> What database connection string is configured in staging?

# Later, clear it
/clear vanisher staging_config
```

## Best Practices

### Pillars

1. **Keep pillars focused**: Load only relevant documentation/specifications
2. **Use descriptive labels**: Makes it easier to manage multiple pillars
3. **Leverage auto-loading**: Place frequently used docs in `pillars/` directory
4. **Monitor context size**: Too many pillars can exceed token limits

### Vanishers

1. **Mirror first**: Always use `/mirror do` before loading as vanisher
2. **Use for temporary data**: Vanishers are session-scoped, perfect for temporary refs
3. **Clear when done**: Free up context space by clearing unneeded vanishers
4. **Sync changes**: Use `/mirror sync` to update mirrored files

## Configuration

Pillars and vanishers inherit configuration from eternals and ephemerals respectively:

```yaml
# config.yaml
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

## Troubleshooting

### Pillars not auto-loading

**Problem**: Pillars directory exists but files aren't loading

**Solutions**:
- Ensure you started with `--coding` flag
- Check files are readable (not hidden, proper permissions)
- Use `--verbose` to see loading details
- Check `.vuhitra/pillar_contexts/` for persisted pillars

### Vanisher load fails

**Problem**: `/vanisher load` returns "not mirrored" error

**Solutions**:
- Mirror the file first: `/mirror do @path/to/file`
- Verify mirror exists: `/mirror exists @path/to/file`
- Check mirror is synced: `/mirror synced @path/to/file`

### Context size too large

**Problem**: Token limit exceeded with many pillars/vanishers

**Solutions**:
- Clear unused contexts: `/clear pillar <label>`
- Use more specific prompts to trigger semantic filtering
- Adjust `similarity_threshold` in config
- Split large files into smaller chunks

## See Also

- [Eternal Context](./eternal-context.md) - Normal mode persistent contexts
- [Ephemeral Context](./ephemeral-context.md) - Normal mode session contexts
- [Mirror Feature](./mirror-command.md) - File mirroring for vanishers
- [Spark Context](./spark-context.md) - In-memory contexts (works in both modes)
