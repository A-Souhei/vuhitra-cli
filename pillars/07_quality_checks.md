# Step 7: Quality Checks

Before applying LLM-generated code, **always run** these verification steps.

## Pre-Commit Checklist

```bash
# 1. Linting (check code style)
# Python
ruff check .
pylint src/

# JavaScript/TypeScript
eslint .
npm run lint

# 2. Formatting (check code formatting)
# Python
black . --check
isort . --check-only

# JavaScript/TypeScript
prettier --check .

# 3. Type Checking (verify type safety)
# Python
mypy src/
pyright

# TypeScript
tsc --noEmit

# 4. Unit Tests (verify functionality)
pytest tests/ -v
npm test

# 5. Integration Tests (verify system behavior)
pytest tests/integration/ -v
npm run test:integration

# 6. Security Checks (optional but recommended)
# Python
bandit -r src/
safety check

# JavaScript
npm audit
```

## Quality Check Prompt

```
Before finalizing the code changes, provide:

1. **Linting commands**: How to check code style
2. **Formatting commands**: How to verify formatting
3. **Type checking commands**: How to verify type safety (if applicable)
4. **Test commands**: How to run all relevant tests
5. **Expected results**: What the output should show if all checks pass

Example format:
```bash
# Lint check
ruff check src/utils/validator.py
# Expected: All checks passed

# Type check
mypy src/utils/validator.py
# Expected: Success: no issues found

# Tests
pytest tests/utils/test_validator.py -v
# Expected: 4 passed in 0.23s
```
```

## Common Check Failures

### Linting Issues
- Unused imports
- Line length violations
- Naming convention violations
- Missing docstrings

### Type Checking Issues
- Missing type hints
- Incompatible type assignments
- Undefined variables
- Return type mismatches

### Test Failures
- Assertion errors
- Missing test fixtures
- Import errors
- Timeout issues

## Fixing Quality Issues

1. **Review the error message** - Understand what failed
2. **Fix systematically** - Address one category at a time
3. **Re-run checks** - Verify fixes work
4. **Commit when clean** - Only commit passing code

---

*Part of the LLM Codebase Interaction Guide - Step 7 of 8*
