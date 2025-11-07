# Error Handler Module

This module provides a comprehensive error handling system with support for:

- **DEV/PROD modes**: Environment-aware error handling
- **Sentry.io integration**: Optional error tracking and monitoring
- **Detailed logging**: Rich error context and stack traces (DEV mode only)
- **Breadcrumbs**: Track user actions leading to errors
- **User context**: Associate errors with specific users

## Configuration

Error handler configuration is stored in `config.yaml`:

```yaml
# Environment configuration
environment:
  mode: DEV  # DEV or PROD (default: DEV)
  enable_logging: true  # Enable console logging (only in DEV mode)

# Sentry configuration
sentry:
  dsn: ""  # Your Sentry DSN (leave empty to disable)
  environment: development
  traces_sample_rate: 1.0
  send_default_pii: false
  attach_stacktrace: true
```

## Usage

### Basic Error Handling

```python
from src.errors_handler import handle_exception

try:
    # Your code here
    result = risky_operation()
except Exception as e:
    handle_exception(e, context={
        'operation': 'risky_operation',
        'user_id': '12345',
        'additional_info': 'any relevant data'
    })
```

### Capture Messages

```python
from src.errors_handler import capture_message

capture_message(
    "User performed action", 
    level="info",
    context={'action': 'login', 'user': 'john'}
)
```

### Using ErrorHandler Directly

```python
from src.errors_handler import get_error_handler

error_handler = get_error_handler()

# Add breadcrumbs for debugging
error_handler.add_breadcrumb(
    message="User clicked submit",
    category="ui",
    level="info",
    data={'form': 'contact'}
)

# Set user context
error_handler.set_user_context(
    user_id="12345",
    username="john_doe",
    email="john@example.com"
)

# Handle exceptions with context
try:
    process_data()
except Exception as e:
    error_handler.handle_exception(
        e,
        context={'step': 'processing', 'data_size': 1000}
    )
```

## Environment Modes

### DEV Mode (Default)
- Detailed console logging enabled
- Stack traces printed to stderr
- All errors logged locally
- Sentry errors sent if DSN configured

### PROD Mode
- Console logging disabled
- Errors only sent to Sentry (if configured)
- Minimal output to user
- Set via environment variable: `VUHITRA_MODE=PROD`

## Sentry Integration

To enable Sentry integration:

1. Install sentry-sdk (already in dependencies):
   ```bash
   pip install sentry-sdk
   ```

2. Add your Sentry DSN to `config.yaml`:
   ```yaml
   sentry:
     dsn: "https://your-sentry-dsn@sentry.io/project-id"
     environment: production
   ```

3. Errors will automatically be sent to Sentry

If DSN is empty or sentry-sdk is not installed, errors will only be logged locally (DEV mode) or printed to stderr (PROD mode).

## Features

### Error Context
Attach relevant context to any error:
```python
handle_exception(error, context={
    'user_id': '12345',
    'request_path': '/api/data',
    'params': {'limit': 10}
})
```

### Breadcrumbs
Track the sequence of events leading to an error:
```python
error_handler = get_error_handler()
error_handler.add_breadcrumb("User logged in", category="auth")
error_handler.add_breadcrumb("Requested data", category="api", data={'endpoint': '/data'})
error_handler.add_breadcrumb("Error occurred", category="error", level="error")
```

### User Context
Associate errors with specific users:
```python
error_handler.set_user_context(
    user_id="user123",
    username="john_doe",
    email="john@example.com"
)
```

### Message Levels
- `debug`: Debugging information
- `info`: Informational messages
- `warning`: Warning messages
- `error`: Error messages
- `fatal`: Critical errors

## Best Practices

1. **Always provide context**: Include relevant information about the state when the error occurred
2. **Use appropriate levels**: Choose the right severity level for messages
3. **Add breadcrumbs**: Track user actions for better debugging
4. **Set user context**: Associate errors with users for better support
5. **Keep DSN secure**: Don't commit Sentry DSN to version control
6. **Test both modes**: Verify behavior in both DEV and PROD modes

## Example Integration

See `src/cli.py` and `src/agent.py` for integration examples throughout the application.
