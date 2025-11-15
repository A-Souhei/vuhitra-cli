# Coding Standards

## Python Style Guide

### General Principles

1. **Follow PEP 8**: Use Python Enhancement Proposal 8 as the foundation
2. **Readability counts**: Code is read more often than written
3. **Explicit is better than implicit**: Clear code over clever code
4. **DRY (Don't Repeat Yourself)**: Avoid code duplication

### Naming Conventions

- **Variables**: `snake_case` (e.g., `user_count`, `api_key`)
- **Functions**: `snake_case` (e.g., `get_user_data()`, `process_request()`)
- **Classes**: `PascalCase` (e.g., `UserManager`, `DataProcessor`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRIES`, `API_VERSION`)

### Error Handling

Always use specific exception types and our error handler:

```python
from src.errors_handler import handle_exception

try:
    result = risky_operation()
except FileNotFoundError as e:
    handle_exception(e, context={'operation': 'file_read'})
except PermissionError as e:
    handle_exception(e, context={'operation': 'file_access'})
```

### Type Hints

Use type hints for function parameters and returns:

```python
from typing import List, Dict, Optional

def process_users(
    users: List[Dict[str, str]], 
    filter_active: bool = True
) -> Optional[List[Dict[str, str]]]:
    """Process and filter user data."""
    if not users:
        return None
    return [u for u in users if u.get('active')] if filter_active else users
```
