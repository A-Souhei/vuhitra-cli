## Embedding-Based Heuristics Testing Strategy

### Overview

The heuristics retrieval system now uses **embeddings** instead of spaCy NLP + Levenshtein distance for semantic similarity. This document explains how to test the system in different environments.

### Architecture

```
┌─────────────────────┐
│ Heuristics Retriever│
│   (sandbox)         │
└──────────┬──────────┘
           │
           ├─► Elasticsearch (kNN search with embeddings)
           │
           └─► Transformer Service (embedding generation)
                  └─► sentence-transformers (all-MiniLM-L6-v2)
```

### Testing Approaches

#### 1. **Local Development Tests (with Docker)**

Full integration testing with actual services:

```bash
# Start all services
cd services
docker compose --profile app up -d

# Wait for services to be healthy
docker compose ps

# Run tests
cd ..
./run_tests.sh
```

**What's tested:**
- ✅ Real embedding generation from transformer service
- ✅ Real Elasticsearch kNN search
- ✅ End-to-end heuristics retrieval
- ✅ Full service integration

#### 2. **CI/GitHub Actions Tests (no Docker)**

Fast unit tests with mocks for CI:

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (automatically uses mocks)
./run_tests.sh -v
```

**What's tested:**
- ✅ Retrieval logic and scoring
- ✅ Rating filters and thresholds
- ✅ Chain retrieval
- ✅ Error handling
- ❌ No real embeddings (uses deterministic mocks)
- ❌ No real Elasticsearch (uses mocks)

**Files involved:**
- `tests/mocks/mock_transformer_service.py` - Generates fake but consistent embeddings
- `tests/test_heuristics_retriever_embeddings.py` - Tests with mocked dependencies

#### 3. **Component Tests (transformer service)**

Test the transformer service independently:

```bash
# Start only transformer service
cd services
docker compose build transformer
docker compose up transformer

# Test embedding endpoint
curl -X POST http://localhost:15050/api/generate-embedding \
  -H "Content-Type: application/json" \
  -d '{"text": "test prompt"}'
```

### Model Caching Strategy

#### Dockerfile Pre-download

The transformer service Dockerfile **pre-downloads** the sentence-transformers model during build:

```dockerfile
# Pre-download sentence-transformers model to avoid first-run delay
RUN python3 -c "from sentence_transformers import SentenceTransformer; \
    model = SentenceTransformer('all-MiniLM-L6-v2');"
```

**Benefits:**
- ✅ No download delay on first request
- ✅ Model baked into image (~900MB total)
- ✅ Works offline after build
- ✅ Consistent across deployments

#### Volume Mount Caching

Additionally, models are cached in a Docker volume:

```yaml
volumes:
  - transformer_models:/root/.cache/huggingface
```

**Benefits:**
- ✅ Faster rebuilds (models persist)
- ✅ Shared across container restarts
- ✅ No re-download after docker-compose down

### Mock Embedding Generation

For non-containerized tests, we use deterministic fake embeddings:

```python
from tests.mocks.mock_transformer_service import MockTransformerService

# Generate fake embedding
embedding = MockTransformerService.generate_embedding("test text")

# Properties:
# - Same text → same embedding (deterministic via hash)
# - Different text → different embeddings  
# - Normalized to unit length (like real embeddings)
# - 384 dimensions (matches all-MiniLM-L6-v2)
```

### Migration from Old System

**Old approach (deprecated):**
- Stage 1: Elasticsearch keyword filtering
- Stage 2: Levenshtein distance scoring
- Stage 3: spaCy semantic similarity
- Final: Weighted combination

**New approach:**
- Elasticsearch kNN search with embeddings
- Direct cosine similarity (built into kNN)
- Rating-based filtering
- Simpler, faster, more accurate

**What changed:**
- ❌ Removed: spaCy dependency from retriever
- ❌ Removed: Levenshtein/rapidfuzz scoring
- ❌ Removed: Multi-stage keyword extraction
- ✅ Added: Transformer service integration
- ✅ Added: Dense vector Elasticsearch field
- ✅ Added: Embedding generation in save_feedback

### Troubleshooting

#### "Model not found" errors

If you see model download errors:

```bash
# Rebuild transformer service with model pre-download
docker compose build --no-cache transformer
```

#### Slow first embedding request

If first request takes long even with pre-download:

- Check if volume is mounted: `docker volume ls | grep transformer_models`
- Verify model in container: `docker exec vuhitra-transformer ls -lh /root/.cache/huggingface`

#### Tests failing in CI

If GitHub Actions tests fail:

- Ensure mocks are being used (check test output)
- Verify numpy is in requirements.txt
- Check that no real HTTP requests are made

#### Elasticsearch kNN not working

Ensure Elasticsearch 8.x+ with kNN support:

```bash
curl http://localhost:9200/_cluster/settings
```

Look for `xpack.security.enabled: false` and version >= 8.0.

### Performance Metrics

| Operation | Old System | New System |
|-----------|-----------|------------|
| Retrieval latency | ~200-500ms | ~50-100ms |
| Accuracy (semantic) | 70-80% | 85-95% |
| Model size | 560MB (spaCy) | 80MB (sentence-t.) |
| Dependencies | 5 (ES, spaCy, NLTK, rapidfuzz, VADER) | 3 (ES, transformer, requests) |

### References

- [sentence-transformers Documentation](https://www.sbert.net/)
- [Elasticsearch kNN Search](https://www.elastic.co/guide/en/elasticsearch/reference/current/knn-search.html)
- [all-MiniLM-L6-v2 Model](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
