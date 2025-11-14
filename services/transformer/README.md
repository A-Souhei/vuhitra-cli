# Transformer NLP Service

A Flask-based microservice that provides transformer-based NLP capabilities for context compaction, code recognition, and text processing.

## Overview

The Transformer NLP Service enhances the vuhitra-cli by:

- **Code Recognition**: Separates source code from natural language text
- **Context Compaction**: Reduces context size while preserving meaning
- **Keyword Extraction**: Identifies key concepts from text
- **Typo Fixing**: Corrects common typos and grammar issues
- **Matrix Context Generation**: Creates structured, LLM-ready context

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Transformer Service                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐       ┌───────────────────┐          │
│  │ Code Recognizer  │       │ Context Compacter │          │
│  │                  │       │                   │          │
│  │ • Pattern-based  │       │ • KeyBERT         │          │
│  │ • Language       │       │ • Sentence        │          │
│  │   detection      │       │   Transformers    │          │
│  │ • Code block     │       │ • Text dedup      │          │
│  │   extraction     │       │ • Typo fixing     │          │
│  └──────────────────┘       └───────────────────┘          │
│           │                           │                      │
│           └───────────┬───────────────┘                      │
│                       │                                      │
│              ┌────────▼─────────┐                           │
│              │   Flask API      │                           │
│              │   (8 Endpoints)  │                           │
│              └──────────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

## Features

### 1. Code Recognition

Intelligently identifies and separates code from natural language:

- Detects programming languages (Python, JavaScript, Java, Go, etc.)
- Extracts code blocks (markdown, inline, or mixed)
- Preserves code formatting and structure
- Identifies file paths

### 2. Context Compaction

Reduces context size without losing meaning:

- **Keyword Extraction**: Uses KeyBERT for semantic keyword identification
- **Sentence Deduplication**: Removes redundant sentences using semantic similarity
- **Typo Correction**: Fixes common spelling and grammar errors
- **Smart Compression**: Keeps most important sentences based on keyword density

### 3. Matrix Context Generation

Creates structured context for LLM consumption:

```
[CONTEXT - Best Practices]
<compacted heuristics>

[CONTEXT - Additional Information]
<compacted context>

[SOURCE CODE - DO NOT MODIFY]
Code Block 1 (python):
```python
def example():
    pass
```

[USER QUERY]
<compacted prompt>
```

## API Endpoints

### Health Check

```bash
GET /health
```

Returns service status and version.

### Code Recognition

```bash
POST /api/recognize-code
Content-Type: application/json

{
  "text": "Here's a Python function:\n```python\ndef hello():\n    print('hello')\n```"
}
```

Returns code blocks and text segments separately.

### Keyword Extraction

```bash
POST /api/extract-keywords
Content-Type: application/json

{
  "text": "Machine learning is transforming artificial intelligence...",
  "top_n": 5
}
```

Returns top keywords with confidence scores.

### Text Compaction

```bash
POST /api/compact-text
Content-Type: application/json

{
  "text": "Long verbose text...",
  "max_sentences": 5
}
```

Returns compacted text with compression statistics.

### Prompt Compaction

```bash
POST /api/compact-prompt
Content-Type: application/json

{
  "prompt": "Very long user prompt..."
}
```

Compacts prompts exceeding 500 characters.

### Heuristics Compaction

```bash
POST /api/compact-heuristics
Content-Type: application/json

{
  "heuristics": "Heuristics text from sandbox..."
}
```

Compacts heuristics to maximum 3 sentences.

### Matrix Context Creation (Main Endpoint)

```bash
POST /api/create-matrix-context
Content-Type: application/json

{
  "prompt": "User's question...",
  "heuristics": "Best practices from sandbox...",
  "context": "Additional context...",
  "raw_text": "Mixed text with code..."
}
```

Returns complete matrix context ready for LLM.

### Typo Fixing

```bash
POST /api/fix-typos
Content-Type: application/json

{
  "text": "Text with typos and grammar issues..."
}
```

Returns corrected text.

## Models Used

### Sentence Transformers
- **Model**: `all-MiniLM-L6-v2`
- **Purpose**: Semantic embeddings for similarity and deduplication
- **Size**: ~80MB
- **Speed**: Fast, CPU-friendly

### KeyBERT
- **Purpose**: Keyword extraction with semantic understanding
- **Backed by**: Sentence Transformers
- **Features**: Max Sum Similarity for diverse keywords

## Configuration

Configure in `config.yaml`:

```yaml
# Transformer service connection
transformer:
  host: localhost
  port: 15050
  protocol: http

# Context compacter settings
context_compacter:
  enabled: true                      # Enable/disable compaction
  prompt_compact_threshold: 500      # Compact if > 500 chars
  max_sentences:
    prompt: 5                        # Max sentences in compacted prompt
    heuristics: 3                    # Max sentences in compacted heuristics
    context: 10                      # Max sentences in compacted context
  min_keyword_score: 0.3            # Minimum keyword relevance
  max_keywords: 10                   # Maximum keywords to extract
  redundancy_threshold: 0.7          # Similarity threshold (higher = more aggressive)
  fix_typos: true                    # Auto-fix typos
  preserve_code: true                # Always preserve code blocks
```

## Predictability & Hallucination Prevention

To minimize hallucinations and ensure predictable behavior:

1. **Deterministic Keyword Extraction**
   - Uses KeyBERT with fixed parameters
   - Minimum score threshold filters low-confidence keywords
   - Max Sum Similarity ensures diversity

2. **Rule-Based Typo Fixing**
   - No LLM-based corrections
   - Fixed typo dictionary
   - Predictable regex-based fixes

3. **Semantic Similarity Thresholds**
   - Configurable redundancy threshold
   - Cosine similarity for deduplication
   - Preserves unique information

4. **Code Preservation**
   - Never modifies code blocks
   - Pattern-based recognition
   - Multiple fallback detection methods

## Docker Deployment

### Build

```bash
cd services
docker compose build transformer
```

### Run

```bash
# Start with app profile (includes transformer)
docker compose --profile app up -d transformer

# Check health
curl http://localhost:15050/health
```

### Environment Variables

- `FLASK_DEBUG`: Enable Flask debug mode (default: false)
- `ENVIRONMENT`: Environment mode (DEV/PROD)
- `SENTRY_DSN`: Optional Sentry error tracking
- `PORT`: Service port (default: 5050)

## Performance

### Model Loading
- First request: ~5-10 seconds (lazy loading)
- Subsequent requests: <100ms for compaction

### Memory Usage
- Base: ~200MB
- With models loaded: ~500MB
- Peak (processing): ~800MB

### Optimization
- Pip cache mounts for faster rebuilds
- Lazy model loading
- Sentence batching for multiple texts

## Integration with vuhitra-cli

The service is automatically integrated into the CLI's prompt processing pipeline:

1. User submits prompt
2. Sandbox fetches similar heuristics
3. **Transformer compacts context** (new step)
4. LLM generates response with compacted context

### Benefits

- **Reduced Token Usage**: 30-70% compression typical
- **Faster LLM Processing**: Smaller context = faster generation
- **Better Focus**: Key information highlighted
- **Code Safety**: Source code never modified

## Development

### Project Structure

```
services/transformer/
├── Dockerfile              # Multi-stage build with caching
├── requirements.txt        # Python dependencies
├── app.py                 # Flask application
├── src/
│   ├── code_recognizer.py    # Code detection & extraction
│   └── context_compacter.py  # Text compaction & processing
└── README.md              # This file
```

### Testing Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
python app.py

# Test endpoint
curl -X POST http://localhost:5050/api/create-matrix-context \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "How do I sort a list in Python?",
    "heuristics": "Use the built-in sorted() function for best performance..."
  }'
```

## Monitoring

### Health Checks

```bash
# Docker health check (automatic)
curl -f http://localhost:5050/health

# Manual check
curl http://localhost:5050/health | jq
```

### Logs

```bash
# View service logs
docker compose logs transformer -f

# Check for errors
docker compose logs transformer | grep ERROR
```

## Troubleshooting

### Service Won't Start

**Symptom**: Container exits immediately

**Solutions**:
1. Check memory: Service needs ~500MB
2. Verify port 15050 is available
3. Check logs: `docker compose logs transformer`

### Slow First Request

**Symptom**: First API call takes 5-10 seconds

**Explanation**: Models are lazy-loaded on first use (by design)

**Solution**: Warm-up request after startup

### Context Not Being Compacted

**Symptom**: Original context used despite service running

**Check**:
1. Is `context_compacter.enabled: true` in config?
2. Is prompt > 500 chars (threshold)?
3. Check CLI verbose output for compaction status

### High Memory Usage

**Symptom**: Container using >1GB RAM

**Solutions**:
1. Reduce max_sentences in config
2. Process shorter texts
3. Restart service to clear cache

## Future Enhancements

- [ ] Multiple transformer model support
- [ ] Batch processing endpoint
- [ ] Custom model fine-tuning
- [ ] Caching for repeated prompts
- [ ] Language-specific compaction strategies
- [ ] Metrics and analytics dashboard

## License

Part of vuhitra-cli project.
