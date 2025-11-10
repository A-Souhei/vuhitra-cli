# Heuristics Service Implementation Plan

## Architecture

Extend sandbox service to handle all NLP analysis and ElasticSearch storage. CLI makes async HTTP calls to sandbox.

## Key Decisions

- **Sentiment Analysis**: Use both VADER and spaCy (store both scores for comparison)
- **Async Processing**: Wait for acknowledgment (brief wait to confirm delivery)
- **Code Detection**: 50% symbols/keywords threshold
- **Keyword Extraction**: Extract top 15 per text
- **Performance Tracking**: Track LLM model execution time
- **Word Count Metrics**: Track number of words in both prompt and response

## Files to Create

### Sandbox Service
1. `services/sandbox/src/elasticsearch_client.py` - ES connection & index management
2. `services/sandbox/src/nlp_analyzer.py` - Spacy + VADER sentiment + keyword extraction
3. `services/sandbox/src/heuristics.py` - Main orchestration class
4. `services/sandbox/requirements.txt` - Add: elasticsearch, vaderSentiment, nltk

### Main CLI
5. `src/cli.py` - Modify to send feedback to sandbox endpoint

### Config
6. `config.yaml` - Add elasticsearch and sandbox settings
7. `config.yaml.example` - Document new settings

### Tests
8. `tests/test_heuristics.py` - Heuristics class tests
9. `tests/test_nlp_analyzer.py` - NLP analysis tests
10. `tests/test_elasticsearch_client.py` - ES client tests

## Implementation Steps

1. **Update sandbox requirements.txt** - Add dependencies
2. **Create ElasticSearchClient** - Connection, index creation, save methods
3. **Create NLPAnalyzer** - Sentiment (VADER+spaCy), keywords, code detection
4. **Create Heuristics class** - Orchestrate analysis & ES storage (background thread)
5. **Add sandbox endpoint** - `POST /analyze/feedback` (returns ack immediately)
6. **Modify CLI** - Send feedback to sandbox, wait for ack
7. **Update config** - Add elasticsearch/sandbox settings
8. **Create tests** - Comprehensive test coverage

## Data Structure (ElasticSearch)

### Prompt Fields
- `prompt` - Original prompt text
- `prompt_keywords` - Extracted keywords
- `prompt_sentiment_vader` - VADER sentiment score
- `prompt_sentiment_spacy` - spaCy sentiment score
- `prompt_word_count` - Number of words in prompt

### Response Fields
- `response` - LLM response text
- `response_keywords` - Extracted keywords
- `is_code_response` - Boolean flag for code detection
- `code_purpose` - Inferred purpose if code detected
- `response_word_count` - Number of words in response

### Metadata Fields
- `rating` - User satisfaction rating
- `timestamp` - When feedback was created
- `processed_at` - When analysis was completed
- `execution_time_ms` - LLM model execution time in milliseconds
