# Complex Heuristics Lookup System

## Overview

The Complex Heuristics Lookup System is a sophisticated multi-stage retrieval mechanism that enhances LLM responses by injecting relevant context from similar past high-quality interactions. The system uses a hybrid approach combining keyword matching, edit distance, and semantic similarity to find the most relevant historical responses.

## Architecture

### High-Level Flow

```
User Prompt
    ↓
[Stage 0] Pre-LLM Heuristics Lookup
    ↓
[Stage 1] Elasticsearch Keyword Filter (rating ≥3, keyword match)
    ↓ (up to 100 candidates)
[Stage 2] Levenshtein Distance Scoring
    ↓ (top 10 candidates)
[Stage 3] spaCy Semantic Similarity
    ↓ (weighted scoring)
[Best Match] Insight Extraction & Summarization
    ↓
Enhanced Prompt = Original Prompt + Context
    ↓
LLM (Ollama)
    ↓
Enhanced Response
    ↓
[Optional] Post-LLM Validation
```

## Components

### 1. HeuristicsRetriever (`services/sandbox/src/heuristics_retriever.py`)

The core retrieval engine implementing a three-stage pipeline.

#### Stage 1: Keyword Filtering

**Purpose**: Quickly filter candidates using Elasticsearch's built-in text matching

**Process**:
1. Extract keywords from prompt using spaCy NLP
   - Focus on: NOUN, PROPN, VERB tokens
   - Filter: stop words, punctuation, words < 3 chars
2. Build Elasticsearch query with:
   - **Must clause**: `rating >= min_rating` (default: 3)
   - **Should clause**: Full text match on prompt (boost: 2.0)
   - **Should clause**: Keyword terms match (boost: 1.5 each)
3. Limit results to 100 candidates

**Performance**: ~50-100ms (Elasticsearch optimized)

#### Stage 2: Levenshtein Distance Scoring

**Purpose**: Calculate edit distance between prompts

**Process**:
1. For each candidate from Stage 1:
   - Calculate Levenshtein distance between normalized prompts
   - Normalize by max string length
   - Convert to similarity: `similarity = 1 - (distance / max_len)`
2. Sort by Levenshtein score
3. Select top 10 candidates

**Performance**: ~10-20ms for 100 candidates

**Library**: `rapidfuzz>=3.0.0` (faster than python-Levenshtein, pre-built wheels)

#### Stage 3: Semantic Similarity

**Purpose**: Deep semantic understanding using word embeddings

**Process**:
1. Generate spaCy document vectors for:
   - User's input prompt
   - Each candidate's prompt
2. Calculate cosine similarity between vectors
3. Compute weighted final score:

```python
final_score = (
    0.50 * semantic_similarity +
    0.25 * levenshtein_similarity +
    0.15 * keyword_overlap +
    0.10 * rating_normalized
)
```

**Performance**: ~50-100ms for 10 candidates

**Model**: `en_core_web_lg` (400MB, includes 685k word vectors)

#### Scoring Weights

| Method | Weight | Rationale |
|--------|--------|-----------|
| Semantic Similarity | 50% | Most important - captures intent and meaning |
| Levenshtein Distance | 25% | Rewards similar phrasing and structure |
| Keyword Overlap | 15% | Ensures topical relevance |
| Rating (normalized) | 10% | Prioritizes high-quality responses |

### 2. InsightExtractor (`services/sandbox/src/insight_extractor.py`)

Extracts actionable insights from matched heuristics for LLM context injection.

#### Extraction Pipeline

1. **Key Techniques Extraction**
   - Identifies verb phrases (action-oriented)
   - For code responses: detects code patterns (function, class, async, etc.)
   - Returns top 10 techniques

2. **Named Entity Recognition**
   - Extracts: PRODUCT, ORG, GPE, PERSON, WORK_OF_ART entities
   - Identifies technical terms (capitalized, non-stop words)
   - Returns top 5 entities

3. **Action Items Extraction**
   - Finds imperative sentences (starting with verbs)
   - Identifies instructional patterns: "you should", "try to", etc.
   - Returns top 5 action items

4. **Summary Building**
   - For code: highlights code purpose
   - For text: extracts first meaningful sentence
   - Adds primary technique
   - Max length: 150 words

5. **Confidence Indicators**
   - Rating-based: "High user satisfaction (rated 5/5)"
   - Content-based: "Contains working code example"
   - Length-based: "Detailed explanation provided"

#### Output Format

```python
{
    'summary': str,                      # Concise summary (<150 words)
    'key_techniques': List[str],         # Technical approaches
    'entities': List[Dict],              # Named entities
    'action_items': List[str],           # Actionable steps
    'confidence_indicators': List[str],  # Quality signals
    'formatted_insight': str             # Ready-to-inject context
}
```

#### Formatted Insight Example

```
[RELEVANT CONTEXT FROM SIMILAR PAST INTERACTION]
Summary: Solution involves function definition, using implement tests
Approach: implement tests, use assertions, define function
Related tools/technologies: pytest, unittest, Mock
Quality: High user satisfaction (rated 5/5)
[END CONTEXT]
```

### 3. API Endpoints (`services/sandbox/src/main.py`)

#### POST /retrieve/similar

Retrieve the most similar heuristic for a given prompt.

**Request**:
```json
{
    "prompt": "How to test Python code?",
    "min_rating": 3,       // optional, default: 3
    "max_results": 1       // optional, default: 1
}
```

**Response**:
```json
{
    "matched_heuristic": {
        "prompt": "Python testing best practices",
        "response": "Use pytest framework...",
        "rating": 5,
        "prompt_keywords": ["python", "testing"],
        // ... other fields
    },
    "confidence_score": 0.85,
    "insights": {
        "summary": "Use pytest for testing",
        "key_techniques": ["implement tests", "use assertions"],
        "formatted_insight": "[RELEVANT CONTEXT...]"
    },
    "scoring_breakdown": {
        "semantic_similarity": 0.88,
        "levenshtein_similarity": 0.82,
        "keyword_overlap": 0.75,
        "rating_normalized": 1.0
    }
}
```

**Status Codes**:
- 200: Success (match found or no match)
- 400: Invalid request (missing/invalid fields)
- 500: Internal error

#### POST /validate/response

Validate a response by comparing with similar past high-quality interactions.

**Request**:
```json
{
    "prompt": "How to test?",
    "response": "Use pytest framework",
    "original_rating": 4   // optional
}
```

**Response**:
```json
{
    "quality_assessment": "Excellent - Very similar to past high-quality response",
    "similar_matches": [
        {
            "prompt": "Python testing guide",
            "rating": 5,
            "confidence": 0.82,
            "key_techniques": ["implement tests", "use pytest"]
        }
    ],
    "recommendations": [
        "Consider incorporating techniques from similar past response"
    ]
}
```

**Quality Assessment Levels**:
- **Excellent** (confidence > 0.8): Very similar to past high-quality response
- **Good** (confidence > 0.6): Comparable to past successful responses
- **Moderate** (confidence ≤ 0.6): Less similar to past high-quality responses

### 4. CLI Integration (`src/cli.py`)

#### Enhanced Prompt Flow

**Before** (without heuristics):
```
User Prompt → LLM → Response
```

**After** (with heuristics):
```
User Prompt → Fetch Heuristics → Enhanced Prompt → LLM → Response
```

#### Implementation

```python
# Fetch similar heuristic
heuristic_context = fetch_similar_heuristic(prompt)

# Enhance prompt if good match found (confidence > 0.5)
if heuristic_context:
    enhanced_prompt = f"{heuristic_context}\n\nUser query: {prompt}"
else:
    enhanced_prompt = prompt

# Generate response with enhanced context
response, execution_time_ms = generate(model, enhanced_prompt)
```

#### Graceful Degradation

- If heuristics fetch fails → continue with original prompt
- If confidence < 0.5 → don't inject context
- Timeout: 5 seconds
- Errors logged to stderr, don't crash CLI

## Performance Metrics

### Target Latencies

| Stage | Target | Typical |
|-------|--------|---------|
| Stage 1 (ES) | <100ms | 50-80ms |
| Stage 2 (Levenshtein) | <50ms | 10-20ms |
| Stage 3 (Semantic) | <100ms | 50-80ms |
| Insight Extraction | <50ms | 20-30ms |
| **Total** | **<500ms** | **150-250ms** |

### Confidence Score Interpretation

| Score | Interpretation | Action |
|-------|---------------|--------|
| > 0.8 | Excellent match | High confidence injection |
| 0.6-0.8 | Good match | Inject with moderate confidence |
| 0.5-0.6 | Moderate match | Consider injection |
| < 0.5 | Weak match | Don't inject (false positive risk) |

## Configuration

### Elasticsearch Settings

**config.yaml**:
```yaml
elasticsearch:
  host: localhost
  port: 9200
  index: llm_feedback
```

### Rating Thresholds

- **Default minimum**: 3/5 (good and above)
- **Validation queries**: 4/5 (excellent only)
- **Rationale**: Balance between coverage and quality

### Candidate Limits

- **Stage 1 (ES)**: 100 candidates (performance vs. coverage)
- **Stage 2 (Semantic)**: 10 candidates (computational cost)

## Testing

### Unit Tests

**HeuristicsRetriever** (`tests/test_heuristics_retriever.py`):
- 20+ test cases
- Stage-by-stage testing
- Edge cases: empty prompts, no candidates, ES disconnected
- Scoring weight validation

**InsightExtractor** (`tests/test_insight_extractor.py`):
- 25+ test cases
- Extraction pipeline testing
- Fallback mechanism validation
- Special character handling

### Integration Tests

**API Endpoints** (`tests/test_heuristics_endpoints.py`):
- 20+ test cases
- Success scenarios
- Error handling
- Parameter validation
- Response structure verification

### Running Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_heuristics_retriever.py

# With coverage
pytest --cov=services/sandbox/src tests/
```

## Usage Examples

### CLI Usage (Automatic)

```bash
# Interactive mode (heuristics automatically enabled)
vuhitra-cli

>>> How to test Python code?
# System fetches similar heuristic, enhances prompt, then calls LLM
# User sees improved response
```

### API Usage

**Retrieve Similar Heuristic**:
```bash
curl -X POST http://localhost:18001/retrieve/similar \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "How to test Python code?",
    "min_rating": 3
  }'
```

**Validate Response**:
```bash
curl -X POST http://localhost:18001/validate/response \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "How to test?",
    "response": "Use pytest framework for unit testing"
  }'
```

### Python Usage

```python
from heuristics_retriever import HeuristicsRetriever
from insight_extractor import InsightExtractor
from elasticsearch import Elasticsearch

# Initialize
es = Elasticsearch(["http://localhost:9200"])
retriever = HeuristicsRetriever(es, "llm_feedback")
extractor = InsightExtractor(nlp_model=retriever.nlp)

# Retrieve best match
result = retriever.retrieve_best_match(
    prompt="How to test Python?",
    min_rating=3
)

if result:
    # Extract insights
    insights = extractor.extract_insights(result['matched_heuristic'])

    # Use formatted insight
    enhanced_prompt = f"{insights['formatted_insight']}\n\nUser query: {original_prompt}"
```

## Dependencies

### New Dependencies

- **rapidfuzz** (>=3.0.0): Fast fuzzy string matching and edit distance
  - Pre-built binary wheels (no compilation needed)
  - Faster than python-Levenshtein
  - ~100x faster than pure Python implementations

### Existing Dependencies (Leveraged)

- **spacy** (>=3.7.0): NLP, word vectors, semantic similarity
- **elasticsearch** (>=8.0.0): Storage and keyword search
- **vaderSentiment** (>=3.3.2): Sentiment analysis

## Error Handling

All components use centralized error handler:

```python
from src.errors_handler.error_handler import get_error_handler

error_handler = get_error_handler()

try:
    # risky operation
except Exception as e:
    error_handler.handle_exception(e, context={
        "operation": "retrieve_heuristics",
        "prompt_length": len(prompt)
    })
    return None  # Graceful degradation
```

## Future Enhancements

### Potential Improvements

1. **Caching Layer**
   - Cache prompt vectors for repeated queries
   - Redis-based caching (~100ms improvement)

2. **Async Processing**
   - Non-blocking heuristics fetch
   - Stream results as they arrive

3. **Multi-match Support**
   - Return top N matches instead of just one
   - Aggregate insights from multiple sources

4. **Personalization**
   - User-specific heuristics
   - Domain-specific indexing

5. **Feedback Loop**
   - Track whether injected context improved ratings
   - Adjust confidence thresholds dynamically

6. **Advanced NLP**
   - Use transformer models (BERT, sentence-transformers)
   - Better semantic understanding
   - Multilingual support

## Monitoring

### Health Checks

**GET /health**:
```json
{
    "status": "healthy",
    "service": "sandbox",
    "heuristics": {
        "nlp_analyzer": true,
        "elasticsearch": true
    },
    "retriever": {
        "elasticsearch_connected": true,
        "spacy_loaded": true,
        "index_exists": true
    }
}
```

### Metrics to Track

- Average confidence scores
- Retrieval latencies (by stage)
- Cache hit rates (if implemented)
- Heuristics injection rate (% of queries)
- User ratings before/after heuristics

## Troubleshooting

### Common Issues

**Issue**: No matches found
- **Cause**: Insufficient historical data (rating ≥3)
- **Solution**: Lower min_rating or wait for more feedback

**Issue**: Low confidence scores
- **Cause**: Queries too unique, poor keyword overlap
- **Solution**: Check prompt keywords, verify ES index quality

**Issue**: Slow retrieval (>500ms)
- **Cause**: Large ES index, too many candidates
- **Solution**: Reduce MAX_STAGE1_CANDIDATES, optimize ES queries

**Issue**: spaCy model not loaded
- **Cause**: en_core_web_lg not installed
- **Solution**: `python -m spacy download en_core_web_lg`

## References

- Elasticsearch documentation: https://www.elastic.co/guide/
- spaCy documentation: https://spacy.io/usage
- Levenshtein distance: https://en.wikipedia.org/wiki/Levenshtein_distance
- Original heuristics documentation: `docs/heuristics_services.md`
