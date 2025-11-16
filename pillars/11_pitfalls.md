# Common Pitfalls to Avoid

## 1. Information Overload

❌ **Don't**: Dump entire codebase at once
```
Here are all 200 files, tell me everything about this project
```

✅ **Do**: Provide structured, chunked information
```
Here's the top-level structure. Let's start with the core module:
[paste module overview]
```

---

## 2. Vague Requests

❌ **Don't**: "Make the code better"

✅ **Do**: "Refactor the `process_data` function to handle empty lists and add type hints"

---

## 3. Skipping Tests

❌ **Don't**: Accept code without tests
```
LLM: Here's the new function.
You: Great! *applies code*
```

✅ **Do**: Always require tests for every code change
```
LLM: Here's the new function.
You: Please also provide comprehensive tests including edge cases.
```

---

## 4. Trusting Blindly

❌ **Don't**: Apply LLM code without review
```
*Copy-paste entire response*
*Git commit -m "AI changes"*
*Git push*
```

✅ **Do**: Review, test, and verify all generated code
```
1. Review the diff carefully
2. Run linting and type checking
3. Run all tests
4. Manual testing
5. Then commit
```

---

## 5. Ignoring Context

❌ **Don't**: Ask for changes without showing existing code
```
Add authentication to the API
[no context provided]
```

✅ **Do**: Provide relevant existing code and patterns
```
Here's our current API structure:
[paste existing routes]

Add authentication following this middleware pattern:
[paste existing middleware example]
```

---

## 6. Missing Verification

❌ **Don't**: Assume the code works
```
LLM generated it, so it must be correct!
```

✅ **Do**: Run all quality checks and tests
```
1. pytest tests/
2. mypy src/
3. ruff check .
4. Manual testing
```

---

## 7. Security Blind Spots

❌ **Don't**: Ignore security implications
```
Just add a password field to the user model
[stores passwords in plain text]
```

✅ **Do**: Explicitly check for security issues
```
Add a password field with proper hashing.
Requirements:
- Use bcrypt or argon2
- Salt passwords
- Never store plain text
- Add password validation
```

---

## 8. No Rollback Plan

❌ **Don't**: Make changes without version control
```
*Modifies 10 files*
*Something breaks*
*Can't remember what changed*
```

✅ **Do**: Commit atomically, plan rollback steps
```
Git workflow:
1. Create feature branch
2. Make one logical change
3. Test thoroughly
4. Commit with clear message
5. Repeat for next change
```

---

## 9. Ignoring Edge Cases

❌ **Don't**: Only test happy path
```
def divide(a, b):
    return a / b

# Test: assert divide(10, 2) == 5
```

✅ **Do**: Test edge cases and errors
```
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

# Tests:
# - Normal: divide(10, 2)
# - Zero divisor: divide(10, 0) raises ValueError
# - Negative numbers: divide(-10, 2)
# - Floats: divide(10.5, 2.5)
```

---

## 10. Mixing Concerns

❌ **Don't**: Try to do too much in one change
```
Add authentication + refactor database + update UI + fix bug in logging
```

✅ **Do**: One logical change at a time
```
Step 1: Add authentication (complete, test, commit)
Step 2: Refactor database (complete, test, commit)
Step 3: Update UI (complete, test, commit)
Step 4: Fix logging bug (complete, test, commit)
```

---

## 11. Forgetting Documentation

❌ **Don't**: Code without documentation
```
[Creates complex algorithm]
[No comments, no docstring]
```

✅ **Do**: Document as you code
```
def complex_algorithm(data: List[int]) -> Dict[str, Any]:
    """
    Process data using advanced algorithm.

    Args:
        data: List of integers to process

    Returns:
        Dictionary with results and metadata

    Raises:
        ValueError: If data is empty

    Example:
        >>> complex_algorithm([1, 2, 3])
        {'result': 6, 'count': 3}
    """
```

---

## 12. Inconsistent Style

❌ **Don't**: Mix coding styles
```
# File 1: camelCase
def getUserData(): ...

# File 2: snake_case
def get_user_data(): ...
```

✅ **Do**: Follow project conventions
```
Check existing code first:
grep -r "def " src/ | head -20

Follow the dominant pattern consistently
```

---

*Part of the LLM Codebase Interaction Guide - Common Pitfalls*
