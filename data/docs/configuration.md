# Configuration Guide

## Spark Context Configuration

In-memory ephemeral context with embedding support:

```yaml
spark_context:
  enabled: true
  max_file_size_mb: 10
  max_contexts: 20
  embed:
    enabled: true
  chunking:
    enabled: true
    chunk_size: 1000
    overlap: 200
```

## Ephemeral Context

Session-scoped context:

```yaml
ephemeral_context:
  enabled: true
  max_file_size_mb: 10
  max_contexts: 10
```

## Eternal Context

Permanent disk-stored context:

```yaml
eternal_context:
  enabled: true
  storage_dir: .vuhitra/eternal_contexts
  max_file_size_mb: 10
  max_contexts: 20
```
