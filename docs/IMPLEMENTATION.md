# DEV/PROD Mode and Error Handler Implementation

## Summary

This implementation adds a comprehensive DEV/PROD mode system with an advanced error handling framework integrated with Sentry.io.

## Features Implemented

### 1. Environment Modes (DEV/PROD)
- **DEV Mode** (default): Full logging, detailed error output
- **PROD Mode**: Minimal logging, production-ready error handling
- Configurable via `config.yaml` or `VUHITRA_MODE` environment variable

### 2. Error Handler System
Located in `src/errors_handler/`:
- **Singleton pattern** for global error handling
- **Rich error context** with metadata
- **Stack trace capture** in DEV mode
- **Breadcrumb system** for tracking user actions
- **Sentry.io integration** (optional)
- **Convenience functions** for easy usage

### 3. Sentry.io Integration
- Optional DSN configuration
- Automatic error reporting when configured
- Graceful fallback when not available
- Context and tags support
- User identification support

### 4. Configuration
All configuration in `config.yaml`:
```yaml
environment:
  mode: DEV  # or PROD
  enable_logging: true

sentry:
  dsn: ""  # Add your Sentry DSN
  environment: development
  traces_sample_rate: 1.0
  send_default_pii: false
  attach_stacktrace: true
```

### 5. Testing
- Migrated to **pytest** framework
- 27 test cases covering all functionality
- Fixtures for setup/teardown
- Conditional Sentry tests (skip if not installed)
- Mock-based testing for isolation

## Files Modified/Created

### Created:
- `src/errors_handler/error_handler.py` - Main error handler class
- `src/errors_handler/__init__.py` - Module exports
- `src/errors_handler/README.md` - Error handler documentation
- `tests/test_error_handler.py` - Error handler tests (pytest)
- `tests/test_config_loader.py` - Config loader tests (pytest)
- `tests/__init__.py` - Tests package
- `tests/README.md` - Testing documentation
- `pytest.ini` - Pytest configuration

### Modified:
- `config.yaml` - Added environment and sentry config
- `src/cli.py` - Integrated error handler
- `src/agent.py` - Added error handling with context
- `src/utils/config_loader.py` - Added error handling, new getters
- `pyproject.toml` - Added sentry-sdk, pytest, pytest-mock

## Usage Examples

### Basic Error Handling
```python
from src.errors_handler import handle_exception

try:
    risky_operation()
except Exception as e:
    handle_exception(e, context={
        'operation': 'risky_operation',
        'user': 'john',
        'data_size': 1000
    })
```

### Capture Messages
```python
from src.errors_handler import capture_message

capture_message(
    "Important event occurred",
    level="info",
    context={'event': 'user_login'}
)
```

### Direct Handler Usage
```python
from src.errors_handler import get_error_handler

handler = get_error_handler()
handler.add_breadcrumb("User clicked button", category="ui")
handler.set_user_context(user_id="123", username="john")
```

## Running Tests

```bash
# Using the test runner script (recommended)
./run_tests.sh

# With verbose output
./run_tests.sh -v

# With coverage report
./run_tests.sh -c

# Using pytest directly
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_error_handler.py

# Run with coverage
pytest --cov=src --cov-report=html
```

## Environment Setup

### Install Dependencies
```bash
# Install runtime dependencies
pip install -r requirements.txt

# Or install individually
pip install requests pyyaml sentry-sdk pytest pytest-mock
```

### Set Mode
```bash
# Via environment variable
export VUHITRA_MODE=PROD

# Or in config.yaml
environment:
  mode: PROD
```

### Configure Sentry (Optional)
1. Create account at sentry.io
2. Get your DSN
3. Add to `config.yaml`:
```yaml
sentry:
  dsn: "https://your-dsn@sentry.io/project-id"
```

## Key Features by Mode

### DEV Mode
- ✅ Detailed logging to stderr
- ✅ Full stack traces
- ✅ Error context displayed
- ✅ Breadcrumbs logged
- ✅ Sentry reporting (if configured)

### PROD Mode
- ✅ Minimal console output
- ✅ Sentry reporting only (if configured)
- ✅ No detailed stack traces to users
- ✅ Production-safe error messages

## Error Handler Methods

- `handle_exception(error, context, reraise)` - Handle exceptions with context
- `capture_message(message, level, context)` - Log messages
- `add_breadcrumb(message, category, level, data)` - Track actions
- `set_user_context(user_id, username, email)` - Associate with user
- `configure(config_loader, sentry_dsn, mode)` - Configure handler

## Best Practices

1. **Always provide context**: Include relevant state information
2. **Use appropriate levels**: debug, info, warning, error, fatal
3. **Add breadcrumbs**: Track user journey
4. **Set user context**: When user info available
5. **Test both modes**: Verify DEV and PROD behavior
6. **Keep DSN secure**: Use environment variables in production

## Documentation

- `src/errors_handler/README.md` - Detailed error handler docs
- `tests/README.md` - Testing guide
- Code docstrings for all public methods

## Dependencies

### Runtime:
- `requests` - HTTP client
- `pyyaml` - YAML configuration
- `sentry-sdk` - Error tracking (optional)

### Development:
- `pytest` - Testing framework
- `pytest-mock` - Mocking utilities
