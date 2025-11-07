# Tests

This directory contains test files for the vuhitra-cli project using pytest.

## Quick Start

### Run tests using the test runner script:
```bash
# From project root
./run_tests.sh

# With verbose output
./run_tests.sh -v

# With coverage report
./run_tests.sh -c

# Show help
./run_tests.sh --help
```

## Running Tests

### Using the test runner (recommended):
```bash
./run_tests.sh              # Run all tests
./run_tests.sh -v           # Verbose output
./run_tests.sh -vv          # Very verbose with print statements
./run_tests.sh -c           # With coverage report
./run_tests.sh --html-coverage  # Generate HTML coverage
./run_tests.sh -k "sentry"  # Run tests matching pattern
./run_tests.sh -t test_error_handler.py  # Run specific file
```

### Using pytest directly:
```bash
pytest
```

### Run specific test file:
```bash
pytest tests/test_error_handler.py
pytest tests/test_config_loader.py
```

### Run with verbose output:
```bash
pytest -v
```

### Run with detailed output and show print statements:
```bash
pytest -vv -s
```

### Run a specific test:
```bash
pytest tests/test_error_handler.py::TestErrorHandler::test_singleton_pattern
```

### Run tests matching a pattern:
```bash
pytest -k "sentry"
```

### Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

## Test Files

### test_error_handler.py
Tests for the error handling system including:
- Singleton pattern
- DEV/PROD mode behavior
- Exception handling with context
- Message capture
- Breadcrumb functionality
- Sentry integration (mocked, skipped if sentry-sdk not installed)
- Convenience functions

### test_config_loader.py
Tests for the configuration loader including:
- Loading YAML config files
- Nested value retrieval
- Default values
- Error handling for missing/invalid files
- Environment and Sentry configuration

## Test Coverage

To run tests with coverage:
```bash
pip install pytest-cov
pytest --cov=src --cov-report=term-missing
pytest --cov=src --cov-report=html  # Generate HTML report
```

View HTML coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Writing New Tests

When adding new tests:
1. Create test file in this directory: `test_<module>.py`
2. Import pytest
3. Create test class or functions
4. Use pytest fixtures for setup/teardown
5. Use assert statements for validation

Example with functions:
```python
import pytest

def test_example():
    result = some_function()
    assert result == expected_value
```

Example with classes:
```python
import pytest

class TestExample:
    def test_method(self):
        result = some_function()
        assert result == expected_value
    
    @pytest.fixture
    def setup_data(self):
        return {"key": "value"}
    
    def test_with_fixture(self, setup_data):
        assert setup_data["key"] == "value"
```

## Pytest Features Used

- **Fixtures**: Reusable setup/teardown code (e.g., `@pytest.fixture`)
- **Parametrization**: Run tests with different inputs
- **Markers**: Skip tests conditionally (e.g., `@pytest.mark.skipif`)
- **Capsys**: Capture stdout/stderr output
- **Monkeypatch**: Mock environment variables and attributes
- **Mocking**: Using unittest.mock with pytest

## Dependencies

Tests require:
- `pytest` (>=8.0.0)
- `pytest-mock` (>=3.12.0)
- `pytest-cov` (optional, for coverage)
- `sentry-sdk` (optional, for Sentry tests)

Install test dependencies:
```bash
pip install pytest pytest-mock pytest-cov
```

