# User Feedback for Anti-Pattern Correction

## Overview

When users provide negative feedback (rating ≤ 2), they can optionally provide context explaining what's wrong or what the correct answer should be. This user feedback is now fully integrated into the anti-pattern system to help the LLM learn from mistakes.

## How It Works

### 1. User Provides Negative Feedback

When a user rates a response as 0, 1, or 2 (dissatisfied):

```
Rate satisfaction (0=Irrelevant, 1=Very dissatisfied, ..., or Enter to skip): 0
Can you provide context to help improve? (e.g., 'dogs are omnivorous', or Enter to skip): 
```

The user can:
- Provide a correction or context (e.g., "dogs are omnivorous")
- Press Enter to skip (optional)

### 2. Storage in Elasticsearch

The feedback is stored with the following structure:

```json
{
  "prompt": "Why do dogs kill small animals?",
  "response": "Dogs are herbivorous animals...",
  "rating": 0,
  "user_feedback": "dogs are omnivorous",
  "timestamp": "2025-11-15T...",
  ...
}
```

**Key fields:**
- `rating`: 0-2 (marks as anti-pattern)
- `user_feedback`: User-provided correction/context (new field!)
- Indexed as `text` type for searchability

### 3. Anti-Pattern Retrieval

When a similar prompt is encountered:
1. System searches for anti-patterns (rating ≤ 2)
2. Finds best match using embedding similarity
3. Extracts insights including `user_feedback`

### 4. Context Injection to LLM

The anti-pattern is formatted as a system directive:

```
# SYSTEM DIRECTIVE - ANTI-PATTERN ALERT

CRITICAL: A similar question was previously answered INCORRECTLY.
Problem: This approach was completely unsuccessful

INCORRECT answer that must be AVOIDED:
```
Dogs are herbivorous animals that only eat plants.
```

✓ USER CORRECTION - What is actually correct:
   dogs are omnivorous

DIRECTIVE: Use the USER CORRECTION above as the factually accurate information.
```

## Benefits

### Before (Without User Feedback)
❌ System knows response was bad, but not WHY
❌ LLM has to guess what's correct
❌ May repeat similar mistakes

### After (With User Feedback)
✅ System knows exactly what's wrong
✅ User provides the correct information
✅ LLM gets factual correction to use
✅ Learning is more effective

## Example Scenario

**User Query:**
```
"Why do dogs kill small animals?"
```

**LLM Response (Incorrect):**
```
"Dogs are herbivorous animals that only eat plants and do not kill animals."
```

**User Feedback:**
```
Rating: 0 (Irrelevant)
Context: "dogs are omnivorous"
```

**Next Time Similar Query:**
System injects anti-pattern context:
- Shows the INCORRECT answer to avoid
- Highlights USER CORRECTION: "dogs are omnivorous"
- Directs LLM to use the correction

**Result:**
```
"Dogs are omnivorous animals that eat both plants and meat. Their predatory 
instinct from their wolf ancestry drives them to chase and kill small animals..."
```

## Implementation Details

### Elasticsearch Index Mapping

```python
"user_feedback": {"type": "text"}  # Added to llm_feedback index
```

### Insight Extraction

The `InsightExtractor.extract_negative_insights()` method now:
1. Extracts `user_feedback` from matched heuristic
2. Includes it in the summary
3. Formats it prominently in the context injection
4. Returns it in the insights dictionary

### Key Code Changes

1. **elasticsearch_client.py**: Added `user_feedback` to index mapping
2. **insight_extractor.py**: 
   - Updated `extract_negative_insights()` to extract user_feedback
   - Updated `_format_negative_for_injection()` to display user correction
   - Updated `_build_negative_summary()` to accept user_feedback
3. **feedback_collector.py**: Already collects user_feedback (no changes needed)

## Testing

Comprehensive tests verify:
- User feedback is properly extracted
- Formatted context includes USER CORRECTION section
- Works with and without user feedback
- Handles all rating levels (0, 1, 2)
- Preserves special characters

Run tests:
```bash
source .venv/bin/activate
python -m pytest tests/test_user_feedback_anti_pattern.py -v
```

## Usage Guidelines

### For Users

**When to provide feedback:**
- Rating ≤ 2 (dissatisfied with response)
- You know what's correct
- Want to help the system learn

**What to provide:**
- Concise corrections (e.g., "dogs are omnivorous")
- Factual information
- Key missing details
- NOT: Long explanations or complaints

**Examples:**

Good ✅
```
"Python 3.8 introduced walrus operator"
"dogs are omnivorous"
"use context manager for file handling"
```

Not as helpful ❌
```
"This answer is completely wrong and useless"
"I don't like this response"
```

### For Developers

The `user_feedback` field:
- Is optional (can be empty string or None)
- Stored in Elasticsearch as text
- Included in anti-pattern insights
- Displayed prominently in LLM context
- Should be treated as authoritative correction

## Configuration

No additional configuration needed! The feature works automatically when:
- Feedback is enabled: `enable_feedback: true` (config.yaml)
- User provides rating ≤ 2
- User optionally provides context

## Future Enhancements

Potential improvements:
1. Generate embeddings for user_feedback for better retrieval
2. Use user_feedback as additional search signal
3. Weight corrections higher in ranking
4. Track correction effectiveness
5. Allow users to edit/improve corrections

## Migration Notes

**Existing Data:**
- Old anti-patterns without `user_feedback` still work
- Field defaults to empty string if missing
- No migration needed (dynamic mapping)

**Re-indexing:**
If you want to ensure proper indexing, you can:
1. Delete and recreate the index
2. Or: Add mapping for `user_feedback` to existing index

```bash
# Option 1: Delete and recreate (data loss!)
# Services will recreate index automatically

# Option 2: Add mapping (recommended)
curl -X PUT "localhost:9200/llm_feedback/_mapping" -H 'Content-Type: application/json' -d'
{
  "properties": {
    "user_feedback": {"type": "text"}
  }
}
'
```

## Related Documentation

- [Feedback Collection](../TESTING_GUIDE.md)
- [Heuristics System](heuristics_services.md)
- [Anti-Pattern Detection](complex_heuristics_lookup.md)
