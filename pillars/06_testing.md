# Step 6: Testing and Verification

The LLM should generate or update tests **every time** it changes code.

## Testing Requirements

| Test Type | Coverage | Example |
|-----------|----------|---------|
| **Unit tests** | Individual functions/methods | Test `validate_email()` with valid/invalid inputs |
| **Integration tests** | Component interactions | Test API endpoint with authentication middleware |
| **Edge cases** | Boundary conditions | Empty strings, null values, max lengths |
| **Error paths** | Exception handling | Invalid input, missing data, timeouts |

## Test Generation Prompt

```
Write comprehensive tests for [module/function] covering:

1. **Normal/happy path**: Expected successful execution
2. **Edge cases**: Boundary values, empty inputs, special characters
3. **Error cases**: Invalid input, exceptions, error handling
4. **Integration**: If applicable, interactions with other components

Provide:
- Test file path: [where to save]
- Test code: [complete test implementation]
- Test commands: [how to run, e.g., pytest, npm test]
- Expected output: [what passing tests should show]

Follow project's testing conventions (check existing test files).
```

## Example Test Output

```python
# tests/utils/test_validator.py

import pytest
from src.utils.validator import Validator, ValidationError


class TestEmailValidation:
    """Test email validation functionality."""

    def test_valid_email(self):
        """Test that valid emails pass validation."""
        validator = Validator({})
        assert validator.validate_email("user@example.com") is True

    def test_invalid_email_no_at(self):
        """Test that emails without @ are rejected."""
        validator = Validator({})
        with pytest.raises(ValidationError, match="Invalid email format"):
            validator.validate_email("userexample.com")

    def test_invalid_email_no_domain(self):
        """Test that emails without domain are rejected."""
        validator = Validator({})
        with pytest.raises(ValidationError, match="Invalid email format"):
            validator.validate_email("user@")

    def test_empty_email(self):
        """Test that empty emails are rejected."""
        validator = Validator({})
        with pytest.raises(ValidationError, match="Invalid email format"):
            validator.validate_email("")


# Run with: pytest tests/utils/test_validator.py -v
```

## Test Coverage Goals

- **Minimum**: 80% line coverage
- **Target**: 90%+ line coverage
- **Critical paths**: 100% coverage
- **Edge cases**: All identified scenarios

## Testing Best Practices

1. **Test one thing per test** - Keep tests focused
2. **Use descriptive names** - Explain what is tested
3. **Arrange-Act-Assert** - Structure tests clearly
4. **Avoid test interdependence** - Each test should be isolated
5. **Mock external dependencies** - Don't rely on external services
6. **Test error messages** - Verify exception details

---

*Part of the LLM Codebase Interaction Guide - Step 6 of 8*
