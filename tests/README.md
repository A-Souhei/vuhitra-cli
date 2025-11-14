# Vuhitra CLI Test Suite

This directory contains the test suite for the Vuhitra CLI project, organized to minimize CI/CD resource consumption.

## Test Organization

### Non-Container Tests (Mocked)
These tests use mocks and do NOT require Docker containers. They run in CI/CD:

- `test_config_loader.py` - Configuration loading tests
- `test_error_handler.py` - Error handling tests
- `test_feedback_collector.py` - Feedback collection tests
- `test_heuristics.py` - Heuristics system tests
- `test_heuristics_retriever.py` - Heuristics retrieval tests
- `test_heuristic_chaining.py` - Heuristic chaining feature tests
- `test_insight_extractor.py` - Insight extraction tests
- `test_nlp_analyzer.py` - NLP analysis tests
- `test_elasticsearch_client.py` - ElasticSearch client tests (unit tests with mocks)
- **`test_sandbox_endpoints_mocked.py`** - Mocked sandbox endpoint tests
- **`test_sandbox_redis_mocked.py`** - Mocked Redis operation tests

### Container Tests (Integration)
These tests require Docker containers and are SKIPPED in CI/CD to reduce resource consumption:

- `test_sandbox_endpoints.py` - Actual sandbox container endpoint tests
- `test_sandbox_redis.py` - Actual Redis container operation tests
- `test_heuristics_endpoints.py` - Flask integration tests (currently skipped)

## Running Tests

### Using the Test Runner Script

The `run_tests.sh` script provides a convenient way to run tests:

```bash
# Run non-container tests only (default for CI/CD)
./run_tests.sh

# Run with verbose output
./run_tests.sh --verbose

# Run with coverage report
./run_tests.sh --coverage

# Run ALL tests including container tests (requires containers running)
./run_tests.sh --with-containers

# Combine options
./run_tests.sh --with-containers --coverage --verbose
```

### Using pytest directly

```bash
# Run all non-container tests
pytest --ignore=tests/test_sandbox_endpoints.py --ignore=tests/test_sandbox_redis.py

# Run a specific test file
pytest tests/test_config_loader.py

# Run with coverage
pytest --cov=src --cov=services/sandbox/src --cov-report=html

# Run only container tests (requires containers)
pytest tests/test_sandbox_endpoints.py tests/test_sandbox_redis.py
```

## Container Setup for Integration Tests

If you want to run the actual container tests locally:

```bash
# Start containers
cd services
docker compose up -d

# Wait for services to be ready
sleep 10

# Run container tests
pytest tests/test_sandbox_endpoints.py tests/test_sandbox_redis.py

# Stop containers
docker compose down -v
```

## CI/CD Strategy

GitHub Actions workflow runs only non-container tests to minimize:
- Build time
- Resource consumption
- GitHub Actions minutes usage

Mocked tests (`*_mocked.py`) provide equivalent coverage without needing containers.

## Adding New Tests

### For non-container functionality
Create a standard test file in `tests/`:

```python
import pytest

class TestMyFeature:
    def test_something(self):
        assert True
```

### For container-dependent functionality
1. Create the actual container test: `test_feature.py`
2. Create the mocked version: `test_feature_mocked.py`
3. The mocked version will run in CI/CD, the actual version runs locally

Example:
```python
# test_feature_mocked.py
from unittest.mock import Mock, patch

class TestFeatureMocked:
    @pytest.fixture
    def mock_client(self):
        return Mock()
    
    def test_something(self, mock_client):
        mock_client.do_something.return_value = "success"
        assert mock_client.do_something() == "success"
```

## Test Coverage

Generate coverage reports:

```bash
./run_tests.sh --coverage
# Open htmlcov/index.html in browser
```

## Troubleshooting

### Tests fail with import errors
Make sure you've installed dependencies:
```bash
pip install -r requirements.txt
```

### Container tests fail
Ensure containers are running:
```bash
cd services
docker compose ps
```

### Redis authentication errors
Check your `.env` file has the correct `REDIS_PASSWORD`:
```bash
cd services
cat .env | grep REDIS_PASSWORD
```
