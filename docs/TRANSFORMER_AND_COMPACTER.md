# Transformer NLP Service & Context Compacter

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Components](#components)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Integration](#integration)
- [Testing](#testing)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)

## Overview

The Transformer NLP Service is a Flask-based microservice that provides advanced natural language processing capabilities to enhance vuhitra-cli's context management and sentiment analysis.

### Key Benefits

- **30-70% Context Reduction**: Intelligent compaction without losing meaning
- **Better Sentiment Analysis**: Transformer-based vs rule-based VADER
- **Code Preservation**: Never modifies source code blocks
- **Graceful Fallback**: Automatic failover to VADER when unavailable
- **Configurable**: Fine-grained control over all features

### Components

1. **Sentiment Analyzer**: Transformer-based sentiment analysis
2. **Context Compacter**: Intelligent text compaction
3. **Code Recognizer**: Source code detection and preservation
4. **Matrix Context Generator**: Structured context for LLM consumption

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     vuhitra-cli (Main)                       │
│                                                               │
│  ┌────────────┐       ┌──────────────┐                      │
│  │ User Input │──────>│ Fetch        │                      │
│  └────────────┘       │ Heuristics   │                      │
│                       └──────┬───────┘                      │
│                              │                               │
│                              ▼                               │
│                       ┌──────────────┐                      │
│                       │ Compact      │◄────────────────┐   │
│                       │ Context      │                  │   │
│                       └──────┬───────┘                  │   │
│                              │                           │   │
│                              ▼                           │   │
│                       ┌──────────────┐                  │   │
│                       │ LLM          │                  │   │
│                       │ Generation   │                  │   │
│                       └──────────────┘                  │   │
└─────────────────────────────────────────────────────────┼───┘
                                                          │
                                                          │
┌─────────────────────────────────────────────────────────┼───┐
│              Transformer NLP Service (Port 15050)       │   │
│                                                         │   │
│  ┌──────────────────┐       ┌───────────────────┐    │   │
│  │ Sentiment        │       │ Context           │    │   │
│  │ Analyzer         │       │ Compacter         │────┘   │
│  │                  │       │                   │        │
│  │ • DistilBERT     │       │ • KeyBERT         │        │
│  │ • VADER Fallback │       │ • Sentence-       │        │
│  │                  │       │   Transformers    │        │
│  └──────────────────┘       │ • Deduplication   │        │
│                             └───────────────────┘        │
│                                                           │
│  ┌──────────────────┐       ┌───────────────────┐       │
│  │ Code             │       │ Matrix            │       │
│  │ Recognizer       │       │ Generator         │       │
│  │                  │       │                   │       │
│  │ • Pattern-based  │       │ • Structured      │       │
│  │ • Language ID    │       │   Output          │       │
│  │ • Preservation   │       │ • LLM-ready       │       │
│  └──────────────────┘       └───────────────────┘       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              Sandbox Service (Port 18001)                │
│                                                           │
│  ┌──────────────────┐                                    │
│  │ NLP Analyzer     │────> Transformer Service           │
│  │                  │      (if enabled)                  │
│  │ Uses:            │                                    │
│  │ • Transformer OR │      ↓ Fallback                   │
│  │ • VADER          │                                    │
│  └──────────────────┘────> VADER (always available)     │
└─────────────────────────────────────────────────────────┘
```

## Features

### 1. Transformer-Based Sentiment Analysis

Replaces rule-based VADER with contextual transformer model.

**Model**: DistilBERT (distilbert-base-uncased-finetuned-sst-2-english)

**Advantages**:
- Contextual understanding
- Handles negations better ("not good" correctly identified as negative)
- Better with sarcasm and complex sentences
- Trained on Stanford Sentiment Treebank (SST-2)

**Comparison**:

| Aspect | VADER | Transformer |
|--------|-------|-------------|
| Speed | <1ms | ~100-200ms |
| Memory | ~1MB | ~250MB |
| Accuracy | Good for social media | Better for complex text |
| Context | ❌ Rule-based | ✅ Deep learning |
| Fallback | N/A | ✅ Automatic to VADER |

**Example**:

```python
# Positive sentiment
Input: "I love this! It's amazing!"
Output: {
  "label": "POSITIVE",
  "score": 0.9998,
  "compound": 0.9998  # VADER-compatible
}

# Negative sentiment
Input: "This is not good at all"
Output: {
  "label": "NEGATIVE",
  "score": 0.9921,
  "compound": -0.9921
}
```

### 2. Context Compaction

Intelligently reduces context size while preserving meaning.

**Techniques**:

1. **Keyword Extraction** (KeyBERT)
   - Semantic keyword identification
   - Diversity through Max Sum Similarity
   - Configurable minimum relevance threshold

2. **Sentence Deduplication**
   - Semantic similarity comparison
   - Removes redundant information
   - Configurable redundancy threshold (default: 0.7)

3. **Sentence Prioritization**
   - Ranks sentences by keyword density
   - Keeps most important information
   - Configurable max sentences

4. **Typo Correction**
   - Rule-based fixes for common errors
   - No LLM involvement (deterministic)
   - Punctuation normalization

**Example**:

```
Original (500 words):
"Python is a programming language. Python is used for many things.
It has great libraries. Python is popular. Many developers love Python.
The syntax is simple. Python can be used for web development. It's also
good for data science. Python has a large community..."

Compacted (150 words, 70% reduction):
"Python is a popular programming language with simple syntax, extensive
libraries, and a large community. Used for web development and data science."

Keywords: ["python", "programming", "development", "libraries", "syntax"]
```

### 3. Code Recognition & Preservation

Detects and separates source code from natural language.

**Capabilities**:
- Detects 10+ programming languages
- Preserves code formatting exactly
- Handles markdown code blocks
- Inline code detection
- File path identification

**Supported Languages**:
- Python, JavaScript, Java, C++, Go, Rust
- SQL, YAML, JSON
- And more...

**Example**:

````
Input:
"Here's how to sort a list:
```python
def sort_list(items):
    return sorted(items)
```
This uses the built-in sorted function."

Output:
code_blocks: [{
  "language": "python",
  "content": "def sort_list(items):\n    return sorted(items)",
  "original": "..."
}]

text_segments: [
  "Here's how to sort a list:",
  "This uses the built-in sorted function."
]
````

### 4. Matrix Context Generation

Creates structured, LLM-ready context.

**Structure**:

```
[CONTEXT - Best Practices]
<compacted heuristics - 3 sentences max>

[CONTEXT - Additional Information]
<compacted context - 10 sentences max>

[SOURCE CODE - DO NOT MODIFY]
Code Block 1 (python):
```python
<preserved code>
```

Code Block 2 (javascript):
```javascript
<preserved code>
```

[USER QUERY]
<compacted prompt - 5 sentences max>
```

**Benefits**:
- Clear section separation
- Code explicitly marked as "DO NOT MODIFY"
- Compacted text sections
- LLM-friendly structure

## Components

### Sentiment Analyzer

**File**: `services/transformer/src/sentiment_analyzer.py`

**Class**: `SentimentAnalyzer`

**Key Methods**:

```python
class SentimentAnalyzer:
    def analyze(text: str) -> Dict[str, float]:
        """
        Analyze single text.

        Returns:
        {
            'label': 'POSITIVE' | 'NEGATIVE',
            'score': float (0-1),
            'compound': float (-1 to 1)  # VADER-compatible
        }
        """

    def analyze_batch(texts: List[str]) -> List[Dict]:
        """Batch analysis for multiple texts."""

    def get_model_info() -> Dict[str, str]:
        """Get model information."""
```

**Model Loading**:
- Lazy loading (only when first used)
- First request: ~3-5 seconds
- Subsequent: ~100-200ms
- Memory: ~250MB when loaded

### Context Compacter

**File**: `services/transformer/src/context_compacter.py`

**Class**: `ContextCompacter`

**Key Methods**:

```python
class ContextCompacter:
    def extract_keywords(text: str, top_n: int) -> List[Dict]:
        """Extract semantic keywords with scores."""

    def compact_text(text: str, max_sentences: int) -> Dict:
        """Compact text while preserving meaning."""

    def compact_prompt(prompt: str) -> Dict:
        """Compact long prompts (>500 chars)."""

    def compact_heuristics(heuristics: str) -> Dict:
        """Compact heuristics to 3 sentences."""

    def create_matrix_context(
        prompt: str,
        heuristics: str,
        context: str,
        code_blocks: List[Dict]
    ) -> Dict:
        """Create full matrix context."""

    def fix_typos_and_grammar(text: str) -> str:
        """Fix common typos deterministically."""
```

**Configuration**:

```python
# Tunable parameters
max_keywords = 10
min_keyword_score = 0.3
redundancy_threshold = 0.7  # 0.0-1.0
```

### Code Recognizer

**File**: `services/transformer/src/code_recognizer.py`

**Class**: `CodeRecognizer`

**Key Methods**:

```python
class CodeRecognizer:
    def detect_code_language(text: str) -> str:
        """Identify programming language."""

    def is_code_block(text: str) -> bool:
        """Determine if text is code."""

    def extract_code_blocks(text: str) -> List[Dict]:
        """Extract markdown code blocks."""

    def separate_code_and_text(text: str) -> Tuple[List, List]:
        """Separate code from natural language."""

    def identify_file_paths(text: str) -> List[str]:
        """Find file paths in text."""
```

**Detection Strategies**:
1. Markdown code blocks (```language)
2. Code keywords (def, class, function, etc.)
3. Code symbols ({, }, ;, =>, etc.)
4. Language-specific patterns

## Configuration

### Main Configuration (config.yaml)

```yaml
# Transformer service connection
transformer:
  host: localhost
  port: 15050
  protocol: http
  endpoints:
    recognize_code: /api/recognize-code
    extract_keywords: /api/extract-keywords
    compact_text: /api/compact-text
    compact_prompt: /api/compact-prompt
    compact_heuristics: /api/compact-heuristics
    create_matrix: /api/create-matrix-context
    analyze_sentiment: /api/analyze-sentiment
    fix_typos: /api/fix-typos

# Context compacter settings
context_compacter:
  enabled: true                      # Master switch
  prompt_compact_threshold: 500      # Compact if > 500 chars
  max_sentences:
    prompt: 5
    heuristics: 3
    context: 10
  min_keyword_score: 0.3            # Keyword relevance (0.0-1.0)
  max_keywords: 10
  redundancy_threshold: 0.7          # Similarity (0.0-1.0)
  fix_typos: true
  preserve_code: true               # Always true!
```

### Heuristics Configuration (services/sandbox/heuristics_config.yaml)

```yaml
# Sentiment analysis settings
sentiment_analysis:
  use_transformer: true              # Use transformer or VADER
  transformer_url: "http://transformer:5050"
  timeout_seconds: 5
  fallback_to_vader: true           # Fallback on error
```

## API Reference

### Health Check

```http
GET /health

Response 200:
{
  "status": "healthy",
  "service": "transformer-nlp",
  "version": "1.0.0"
}
```

### Sentiment Analysis

```http
POST /api/analyze-sentiment
Content-Type: application/json

# Single text
{
  "text": "I love this product!"
}

Response 200:
{
  "label": "POSITIVE",
  "score": 0.9998,
  "compound": 0.9998
}

# Batch analysis
{
  "texts": ["Great!", "Terrible!", "Okay"]
}

Response 200:
{
  "results": [
    {"label": "POSITIVE", "score": 0.999, "compound": 0.999},
    {"label": "NEGATIVE", "score": 0.995, "compound": -0.995},
    {"label": "POSITIVE", "score": 0.723, "compound": 0.723}
  ]
}
```

### Code Recognition

```http
POST /api/recognize-code
Content-Type: application/json

{
  "text": "```python\ndef hello():\n    print('hi')\n```"
}

Response 200:
{
  "code_blocks": [{
    "language": "python",
    "content": "def hello():\n    print('hi')",
    ...
  }],
  "text_segments": [],
  "has_code": true,
  "code_block_count": 1
}
```

### Keyword Extraction

```http
POST /api/extract-keywords
Content-Type: application/json

{
  "text": "Python programming for data science",
  "top_n": 5
}

Response 200:
{
  "keywords": [
    {"keyword": "python programming", "score": 0.85},
    {"keyword": "data science", "score": 0.79},
    ...
  ],
  "count": 5
}
```

### Text Compaction

```http
POST /api/compact-text
Content-Type: application/json

{
  "text": "Long verbose text...",
  "max_sentences": 5
}

Response 200:
{
  "original_text": "...",
  "compacted_text": "...",
  "keywords": [...],
  "compression_ratio": 0.65,
  "sentence_count_before": 10,
  "sentence_count_after": 5
}
```

### Matrix Context (Main Endpoint)

```http
POST /api/create-matrix-context
Content-Type: application/json

{
  "prompt": "How do I sort a list?",
  "heuristics": "Use sorted() for best performance",
  "context": "",
  "raw_text": ""
}

Response 200:
{
  "prompt": {
    "original": "...",
    "compacted": "...",
    "keywords": [...]
  },
  "heuristics": {
    "original": "...",
    "compacted": "...",
    "keywords": [...]
  },
  "formatted_for_llm": "...",  # Ready to use!
  ...
}
```

## Integration

### CLI Integration

The transformer service is automatically integrated into the prompt processing pipeline.

**Flow**:

```python
# In cli.py interactive_mode()

1. User submits prompt
   ↓
2. fetch_similar_heuristic(prompt)  # Get from sandbox
   ↓
3. compact_context_with_transformer(prompt, heuristic_context)
   ↓
4. generate(model, compacted_context)  # Send to LLM
   ↓
5. Display response
```

**Code** (src/cli.py):

```python
# Compact context with transformer
compacted_context, matrix_data = compact_context_with_transformer(
    prompt=prompt,
    heuristic_context=heuristic_context,
    verbose=verbose
)

# Use compacted context if available
if compacted_context:
    enhanced_prompt = compacted_context
else:
    enhanced_prompt = f"{heuristic_context}\n\nUser query: {prompt}"
```

### Sandbox Integration

The sandbox NLP analyzer uses the transformer service for sentiment analysis.

**Flow**:

```python
# In sandbox/src/nlp_analyzer.py

1. analyze_sentiment(text) called
   ↓
2. Try transformer service (if enabled)
   ├─> Success: return transformer result
   └─> Fail: fall back to VADER
```

**Code**:

```python
def analyze_sentiment(self, text: str) -> Dict[str, float]:
    # Try transformer if enabled
    if self.sentiment_config.get('use_transformer', True):
        result = self._analyze_sentiment_transformer(text)
        if result is not None:
            return result

    # Fallback to VADER
    return self._analyze_sentiment_vader(text)
```

## Testing

Comprehensive test coverage included.

### Test Files

```
services/transformer/tests/
├── test_sentiment_analyzer.py    # 15+ tests
├── test_context_compacter.py     # 25+ tests
├── test_code_recognizer.py       # 20+ tests
└── test_api_endpoints.py         # 15+ tests

tests/
└── test_nlp_analyzer.py          # Updated with transformer tests
```

### Running Tests

```bash
# Run all transformer tests
cd services/transformer
pytest tests/ -v

# Run specific test file
pytest tests/test_sentiment_analyzer.py -v

# Run sandbox NLP tests
cd ../..
pytest tests/test_nlp_analyzer.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Test Categories

1. **Unit Tests**: Individual component functionality
2. **Integration Tests**: Service interaction and fallback
3. **API Tests**: Endpoint validation
4. **Fallback Tests**: VADER fallback mechanism

## Performance

### Benchmarks

| Operation | Time | Memory |
|-----------|------|--------|
| Sentiment Analysis (single) | ~100-200ms | +250MB (model) |
| Sentiment Analysis (batch 10) | ~500ms | +250MB |
| Context Compaction | ~50-100ms | +80MB (KeyBERT) |
| Code Recognition | <10ms | <1MB |
| Matrix Generation | ~150-300ms | +330MB (all models) |

### Model Loading

- **First Request**: 3-5 seconds (lazy loading)
- **Subsequent Requests**: Fast (models cached)
- **Memory Usage**: ~500MB total when all models loaded

### Optimization Tips

1. **Use Batch Analysis**: 5x faster for multiple texts
2. **Pre-warm Models**: Hit endpoints after startup
3. **Adjust Thresholds**: Lower `max_sentences` for faster compaction
4. **Disable if Not Needed**: Set `enabled: false` in config

## Troubleshooting

### Service Won't Start

**Symptom**: Container exits immediately

**Solutions**:
1. Check memory: Needs ~500MB minimum
2. Verify port 15050 available
3. Check logs: `docker compose logs transformer -f`

**Example**:
```bash
# Check if port is in use
lsof -i :15050

# View startup logs
docker compose logs transformer --tail=50
```

### Slow First Request

**Symptom**: First sentiment analysis takes 5-10 seconds

**Explanation**: Models are lazy-loaded on first use (intentional)

**Solutions**:
1. Pre-warm after startup:
   ```bash
   curl -X POST http://localhost:15050/api/analyze-sentiment \
     -H "Content-Type: application/json" \
     -d '{"text": "warmup"}'
   ```

2. Or wait for first real request

### Context Not Being Compacted

**Symptom**: Original context used despite service running

**Check**:
1. Is `context_compacter.enabled: true` in config.yaml?
2. Is prompt > 500 chars (threshold)?
3. Check CLI verbose output for compaction status
4. Verify transformer service is healthy

**Debug**:
```bash
# Check service health
curl http://localhost:15050/health

# Test compaction directly
curl -X POST http://localhost:15050/api/compact-prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "'"$(python3 -c 'print("test " * 100)')"'"}'
```

### VADER Always Used

**Symptom**: VADER scores even with transformer enabled

**Check**:
1. Is transformer service running?
   ```bash
   docker compose ps transformer
   ```

2. Is `use_transformer: true` in heuristics_config.yaml?

3. Check sandbox logs for connection errors:
   ```bash
   docker compose logs sandbox | grep -i transformer
   ```

4. Test transformer directly:
   ```bash
   curl -X POST http://localhost:15050/api/analyze-sentiment \
     -H "Content-Type: application/json" \
     -d '{"text": "test"}'
   ```

### High Memory Usage

**Symptom**: Container using >1GB RAM

**Explanation**: Multiple transformer models loaded

**Solutions**:
1. Normal for all features enabled
2. Restart service to clear cache:
   ```bash
   docker compose restart transformer
   ```

3. Reduce usage:
   - Disable features you don't need
   - Lower `max_sentences` in config
   - Process shorter texts

### Fallback Not Working

**Symptom**: Errors when transformer unavailable

**Check**:
1. Is `fallback_to_vader: true` in heuristics_config.yaml?
2. Is VADER installed in sandbox?
   ```bash
   docker compose exec sandbox pip show vaderSentiment
   ```

3. Check sandbox logs for fallback messages:
   ```bash
   docker compose logs sandbox | grep -i fallback
   ```

## Best Practices

### Configuration

1. **Start Conservative**: Use default settings initially
2. **Monitor Performance**: Watch response times and memory
3. **Tune Gradually**: Adjust thresholds based on usage
4. **Enable Verbose**: Use `-v` flag during development

### Development

1. **Write Tests**: Add tests for custom modifications
2. **Use Type Hints**: Maintain type safety
3. **Document Changes**: Update this file and README
4. **Version Control**: Track config changes in git

### Production

1. **Pre-warm Models**: Hit endpoints after deployment
2. **Monitor Health**: Set up /health endpoint checks
3. **Set Timeouts**: Configure appropriate timeouts
4. **Enable Fallback**: Always keep VADER fallback enabled
5. **Log Errors**: Monitor logs for service issues

## Additional Resources

- [Transformer Service README](../services/transformer/README.md)
- [DistilBERT Model Card](https://huggingface.co/distilbert-base-uncased-finetuned-sst-2-english)
- [KeyBERT Documentation](https://maartengr.github.io/KeyBERT/)
- [Sentence Transformers](https://www.sbert.net/)

## Support

For issues or questions:
1. Check this documentation
2. Review test files for examples
3. Check GitHub issues
4. Create new issue with logs and config
