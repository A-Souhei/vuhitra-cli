# Semantic Context Filtering

## Overview

Semantic filtering allows the system to intelligently select which eternal and ephemeral contexts to include in prompts based on their relevance to the user's query. This helps manage token limits and improves response quality by only including contextually relevant information.

## How It Works

### Embedding Generation

1. **Description Embeddings**: When a file is loaded as an eternal or ephemeral context, the system:
   - Auto-generates a 1-2 sentence description using the LLM
   - Generates a vector embedding of this description using the transformer service
   - Stores the embedding for future similarity comparisons

2. **Prompt Embeddings**: When a user submits a prompt:
   - The system generates an embedding for the prompt
   - Compares it against stored context description embeddings
   - Returns only contexts that exceed the similarity threshold

### Similarity Calculation

The system uses cosine similarity to compare embeddings:
- Score of 1.0 = perfectly similar
- Score of 0.0 = completely dissimilar
- Default threshold: 0.5 (configurable)

### Caching

Embeddings are cached in Redis for 30 days to improve performance:
- Reduces repeated calls to the transformer service
- Significantly speeds up context filtering
- Falls back gracefully if Redis is unavailable

## Configuration

### Eternal Context

Edit `config.yaml`:

```yaml
eternal_context:
  enabled: true
  semantic_filtering:
    enabled: true  # Enable/disable semantic filtering
    similarity_threshold: 0.5  # Minimum similarity score (0.0-1.0)
```

### Ephemeral Context

```yaml
ephemeral_context:
  enabled: true
  semantic_filtering:
    enabled: true
    similarity_threshold: 0.5
```

### Embedding Cache

```yaml
redis:
  host: localhost
  port: 6379
  # password: configured in secrets.yaml (optional)
```

## Usage Examples

### Loading with Auto-Generated Description

```bash
# System auto-generates description
/load ./docs/api_spec.md api

# System generates: "REST API specification for user endpoints..."
```

### Loading with Manual Description

```bash
# Provide custom description for better semantic matching
/load ./docs/api_spec.md api "REST API endpoints for user management"
```

### Querying with Semantic Filtering

When semantic filtering is enabled, only relevant contexts are included:

```bash
>>> /load ./docs/api_spec.md api "REST API endpoints"
>>> /load ./docs/database.md db "Database schema documentation"
>>> /load ./docs/deployment.md deploy "Deployment and infrastructure guide"

# Only includes api and db contexts (relevant)
>>> How do I create a new user?
[System includes: api_spec.md, database.md]

# Only includes deploy context (relevant)
>>> What's the deployment process?
[System includes: deployment.md]
```

### Disabling Semantic Filtering

To include all contexts regardless of relevance:

```yaml
eternal_context:
  semantic_filtering:
    enabled: false  # All contexts always included
```

## Architecture

### Shared Utilities

The `src/utils/embedding_utils.py` module provides:

- **`EmbeddingCacheMixin`**: Redis-based caching for embeddings
- **`cosine_similarity()`**: Robust similarity calculation with zero-vector handling
- Constants for cache TTL and description length

### Type Consistency

- **Eternal Context**: Stores embeddings as `List[float]` for JSON serialization
- **Ephemeral Context**: Stores embeddings as `np.ndarray` for in-memory operations
- Automatic type conversion ensures compatibility

## Performance Considerations

### With Redis Caching

- First embedding generation: ~100-500ms (transformer API call)
- Subsequent retrievals: ~1-5ms (Redis cache hit)
- Context filtering: ~5-20ms for 10 contexts

### Without Redis Caching

- Every embedding generation: ~100-500ms
- Can become slow with many contexts
- Consider enabling Redis for production use

## Troubleshooting

### Embedding Generation Fails

If embedding generation fails, the system falls back gracefully:
- Returns all contexts unfiltered
- Logs a warning message
- Continues operation normally

Example log:
```
WARNING: Failed to generate embedding for prompt, returning all contexts unfiltered
```

### No Contexts Match Threshold

If no contexts exceed the similarity threshold:
- No contexts are included
- Empty context string returned
- Consider lowering the threshold

### Redis Connection Issues

If Redis is unavailable:
- Caching is disabled automatically
- Embeddings generated fresh each time
- System continues to function (slower)

## Best Practices

1. **Description Quality**: Better descriptions → better matching
   - Be specific about content and purpose
   - Use keywords relevant to expected queries
   - Keep descriptions concise (1-2 sentences)

2. **Threshold Tuning**: Adjust based on your use case
   - Higher threshold (0.7-0.9): More selective, fewer matches
   - Lower threshold (0.3-0.5): More inclusive, more matches
   - Default (0.5): Balanced for most scenarios

3. **Redis Setup**: Enable for production
   - Significantly improves performance
   - Reduces load on transformer service
   - 30-day cache provides good balance

4. **Monitoring**: Watch for warnings
   - Embedding generation failures
   - Slow transformer responses
   - Cache misses

## API Reference

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | `true` | Enable semantic filtering |
| `similarity_threshold` | float | `0.5` | Minimum similarity score (0.0-1.0) |
| `max_file_size_mb` | int | `10` | Maximum file size to load |
| `max_contexts` | int | `20` (eternal), `10` (ephemeral) | Maximum number of contexts |

### Embedding Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `EMBEDDING_CACHE_TTL_SECONDS` | `2592000` (30 days) | Redis cache expiration |
| `DESCRIPTION_PREVIEW_LENGTH` | `1000` | Characters used for LLM description |
| `DESCRIPTION_MAX_LENGTH` | `200` | Maximum description length |

## Related Documentation

- [Context Dimensions](context-dimensions.md) - Understanding different context types
- [Ephemeral Context](ephemeral-context.md) - Session-scoped context management
- [Embedding Testing](EMBEDDING_TESTING.md) - Testing embedding functionality
- [Similarity Algorithm](similarity_algorithm.md) - Deep dive into similarity calculation
