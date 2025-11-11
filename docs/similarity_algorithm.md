# Heuristics Similarity Algorithm

## Overview

The heuristics system uses a sophisticated multi-stage similarity algorithm to find the most relevant historical interactions for a given user prompt. This allows the system to inject relevant context from past high-quality responses to improve future answers.

## Architecture

The similarity algorithm operates in three sequential stages:

1. **Stage 1: Elasticsearch Keyword Filtering** - Fast filtering using full-text search
2. **Stage 2: Levenshtein Distance Scoring** - Edit distance similarity calculation
3. **Stage 3: Semantic Similarity with spaCy** - Deep semantic matching using word vectors

## Stage 1: Elasticsearch Keyword Filtering

### Purpose
Quickly reduce the search space from potentially thousands of documents to ~100 relevant candidates.

### Process
1. Extract keywords from the user's prompt using spaCy NLP
   - Filter: Only NOUN, PROPN, and VERB tokens
   - Filter: Remove stopwords and punctuation
   - Filter: Minimum length of 3 characters
   - Apply lemmatization for better matching

2. Build Elasticsearch query:
   ```json
   {
     "bool": {
       "must": [
         {"range": {"rating": {"gte": 3}}}  // Only high-quality responses
       ],
       "should": [
         {"match": {"prompt": {"query": "<user_prompt>", "boost": 2.0}}},
         {"term": {"prompt_keywords": {"value": "<keyword>", "boost": 1.5}}}
       ]
     }
   }
   ```

3. Return top 100 candidates based on Elasticsearch relevance score

### Configuration
- `filtering.min_rating`: Minimum rating threshold (default: 3)
- `filtering.max_stage1_candidates`: Maximum results to return (default: 100)

## Stage 2: Levenshtein Distance Scoring

### Purpose
Calculate character-level similarity between prompts using edit distance.

### Process
1. For each candidate from Stage 1:
   - Normalize both prompts (lowercase, strip whitespace)
   - Calculate Levenshtein similarity ratio using `rapidfuzz`
   - Convert to 0-1 scale

2. Formula:
   ```
   similarity_score = fuzz.ratio(prompt_lower, candidate_prompt_lower) / 100.0
   ```

3. Sort candidates by Levenshtein score
4. Select top N candidates for semantic analysis

### Configuration
- `filtering.max_stage2_candidates`: Maximum candidates for Stage 3 (default: 10)

## Stage 3: Semantic Similarity with spaCy

### Purpose
Deep semantic understanding using word embeddings and weighted keyword matching.

### Components

#### 3.1 Semantic Similarity (spaCy Word Vectors)
Uses spaCy's `en_core_web_lg` model for vector-based similarity:
```python
prompt_doc = nlp(prompt)
candidate_doc = nlp(candidate_prompt)
semantic_score = prompt_doc.similarity(candidate_doc)
```

This captures semantic meaning, e.g.:
- "what is Python?" ≈ "tell me about Python programming"
- "how to sort a list?" ≈ "list sorting methods"

#### 3.2 Weighted Keyword Overlap

**Problem Solved**: Simple keyword overlap treats all words equally, but subjects (like "Python" vs "Java") should have much higher importance than generic verbs (like "is", "what").

**Solution**: Apply different weights based on part-of-speech (POS) tags and dependency parsing.

##### Keyword Weights

| Type | Weight | Description | Example |
|------|--------|-------------|---------|
| **Subject Noun** | 5.0x | Main topic of the sentence (nsubj, dobj, pobj, attr) | "Python", "Java", "C++" in "what is Python?" |
| **Proper Noun** | 4.0x | Named entities (PROPN) | "Django", "React", "TensorFlow" |
| **Common Noun** | 2.0x | General nouns (NOUN) | "language", "framework", "library" |
| **Verb** | 1.0x | Action words (VERB) | "is", "use", "create" |

##### Algorithm

1. **Identify Subject Tokens**:
   ```python
   subject_tokens = set()
   for token in prompt_doc:
       if token.dep_ in ['nsubj', 'nsubjpass', 'dobj', 'pobj', 'attr']:
           subject_tokens.add(token.lemma_.lower())
   ```

2. **Extract and Weight Keywords**:
   ```python
   prompt_keyword_weights = {}
   for token in prompt_doc:
       if token is valid:
           lemma = token.lemma_.lower()
           if lemma in subject_tokens:
               prompt_keyword_weights[lemma] = 5.0  # Highest priority
           elif token.pos_ == 'PROPN':
               prompt_keyword_weights[lemma] = 4.0
           elif token.pos_ == 'NOUN':
               prompt_keyword_weights[lemma] = 2.0
           elif token.pos_ == 'VERB':
               prompt_keyword_weights[lemma] = 1.0
   ```

3. **Combine Candidate Keywords**:
   - Uses both `prompt_keywords` and `response_keywords` from candidate
   - This handles cases where `prompt_keywords` might be empty
   ```python
   candidate_keywords = set(prompt_keywords) | set(response_keywords)
   ```

4. **Calculate Weighted Overlap**:
   ```python
   intersection = sum(
       prompt_keyword_weights[kw]
       for kw in candidate_keywords & prompt_set
   )
   total_weight = sum(prompt_keyword_weights.values())
   keyword_score = intersection / total_weight
   ```

##### Example

**User Prompt**: "what is Java?"

Keywords extracted:
- "java" → Subject noun → 5.0x weight
- "what" → (filtered out as stopword)

**Candidate 1**: "what is Python?" (prompt_keywords: ["python"])
- Match: None
- Score: 0/5 = **0.0** ✗

**Candidate 2**: "Java tutorial" (prompt_keywords: ["java", "tutorial"])
- Match: "java" (5.0 weight)
- Score: 5/5 = **1.0** ✓

This prevents mixing up different programming languages!

### Final Scoring

Combine all metrics with configurable weights:

```python
final_score = (
    SEMANTIC_WEIGHT * semantic_score +           # 0.50 (default)
    LEVENSHTEIN_WEIGHT * levenshtein_score +     # 0.25 (default)
    KEYWORD_WEIGHT * keyword_score +             # 0.15 (default)
    RATING_WEIGHT * rating_score                 # 0.10 (default)
)
```

**Note**: All weights must sum to 1.0 for proper normalization.

### Configuration
- `scoring_weights.semantic_weight`: Weight for semantic similarity (default: 0.50)
- `scoring_weights.levenshtein_weight`: Weight for edit distance (default: 0.25)
- `scoring_weights.keyword_weight`: Weight for keyword overlap (default: 0.15)
- `scoring_weights.rating_weight`: Weight for user rating (default: 0.10)
- `keyword_weights.subject_noun`: Weight for subject nouns (default: 5.0)
- `keyword_weights.proper_noun`: Weight for proper nouns (default: 4.0)
- `keyword_weights.common_noun`: Weight for common nouns (default: 2.0)
- `keyword_weights.verb`: Weight for verbs (default: 1.0)

## Context Injection

After finding the best match, the system decides whether to inject context:

```python
if confidence_score > CONFIDENCE_THRESHOLD:
    inject_context(formatted_insight)
```

**Default Threshold**: 0.75 (75% confidence)

This high threshold ensures only highly relevant context is injected, preventing confusion like injecting Python context when the user asks about Java.

### Configuration
- `confidence.threshold`: Minimum confidence for context injection (default: 0.75)
- CLI config: `sandbox.confidence_threshold` (default: 0.75)

## Configuration Files

### Heuristics Config (`services/sandbox/heuristics_config.yaml`)
All weights and thresholds for the similarity algorithm:

```yaml
scoring_weights:
  semantic_weight: 0.50
  levenshtein_weight: 0.25
  keyword_weight: 0.15
  rating_weight: 0.10

keyword_weights:
  subject_noun: 5.0
  proper_noun: 4.0
  common_noun: 2.0
  verb: 1.0

filtering:
  min_rating: 3
  max_stage1_candidates: 100
  max_stage2_candidates: 10

confidence:
  threshold: 0.75
```

### CLI Config (`config.yaml`)
```yaml
sandbox:
  host: localhost
  port: 18001
  protocol: http
  confidence_threshold: 0.75
```

## Tuning Guide

### Increase Precision (Fewer False Positives)
- Increase `confidence.threshold` (e.g., 0.80 or 0.85)
- Increase `keyword_weights.subject_noun` (e.g., 6.0 or 7.0)
- Increase `scoring_weights.keyword_weight` (e.g., 0.20)

### Increase Recall (More Matches)
- Decrease `confidence.threshold` (e.g., 0.65 or 0.70)
- Decrease `filtering.min_rating` (e.g., 2)
- Increase `scoring_weights.semantic_weight` (e.g., 0.60)

### Prioritize Exact Matches
- Increase `scoring_weights.levenshtein_weight` (e.g., 0.35)
- Decrease `scoring_weights.semantic_weight` (e.g., 0.40)

### Prioritize Semantic Understanding
- Increase `scoring_weights.semantic_weight` (e.g., 0.60)
- Decrease `scoring_weights.levenshtein_weight` (e.g., 0.15)

## Dependencies

- **spaCy** (`en_core_web_lg`): Word vectors and NLP
- **rapidfuzz**: Fast Levenshtein distance calculation
- **Elasticsearch**: Full-text search and filtering
- **PyYAML**: Configuration loading

## Performance

| Stage | Candidates | Time (avg) |
|-------|-----------|-----------|
| Stage 1 (Elasticsearch) | 1000s → 100 | ~50ms |
| Stage 2 (Levenshtein) | 100 → 10 | ~10ms |
| Stage 3 (Semantic) | 10 → 1 | ~100ms |
| **Total** | - | **~160ms** |

## Example Flow

**User Query**: "what is Rust?"

1. **Stage 1**:
   - Extract keywords: ["rust"]
   - ES query finds 50 candidates with "rust" keyword
   - Filter by rating ≥ 3 → 30 candidates

2. **Stage 2**:
   - Calculate Levenshtein for all 30
   - Top 10 by edit distance selected

3. **Stage 3**:
   - Semantic similarity calculated for each
   - Keyword overlap:
     - "what is Rust?" vs "what is Python?" → subject "rust" ≠ "python" → low score
     - "what is Rust?" vs "Rust tutorial" → subject "rust" = "rust" → high score
   - Final scores computed with weights
   - Best match: confidence = 0.82

4. **Context Injection**:
   - 0.82 > 0.75 threshold → ✓ Inject context
   - Format insight from best match
   - Prepend to user's prompt

## References

- [spaCy Documentation](https://spacy.io/)
- [Elasticsearch Text Analysis](https://www.elastic.co/guide/en/elasticsearch/reference/current/analysis.html)
- [Levenshtein Distance](https://en.wikipedia.org/wiki/Levenshtein_distance)
- [Word Embeddings](https://en.wikipedia.org/wiki/Word_embedding)
