# Step 5: Code Generation - Using Diffs or Full File Rewrites

The LLM should provide code changes in a **safe and traceable** format.

## Recommended Methods

| Method | When to Use | Example |
|--------|-------------|---------|
| **Unified diff** | Small, targeted changes | `--- a/file.py` / `+++ b/file.py` |
| **Full file overwrite** | Small files (<100 lines) or complete rewrites | Entire file content |
| **Search-and-replace** | Specific pattern changes | Old code block → New code block |

## Patch Generation Prompt

```
Generate changes for [file/module] to implement [feature/fix].

Requirements:
- Provide a unified diff format (--- a/file / +++ b/file)
- Only modify necessary lines - no unrelated changes
- Preserve existing code style and formatting
- Add comments for complex logic
- Include error handling where appropriate
- Follow project conventions (check existing code)

Original file: [file path]
Change description: [what and why]
```

## What the LLM Should Ensure

- ✅ No unrelated formatting changes
- ✅ No hidden logic alterations
- ✅ Code is consistent with project style
- ✅ Proper error handling included
- ✅ Comments added for complex sections
- ✅ Type hints/annotations preserved (if used)
- ✅ Imports updated correctly

## Example Diff Output

```diff
--- a/src/utils/validator.py
+++ b/src/utils/validator.py
@@ -10,6 +10,14 @@ class Validator:
        self.rules = rules

+    def validate_email(self, email: str) -> bool:
+        """Validate email format using regex pattern."""
+        import re
+        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
+        if not re.match(pattern, email):
+            raise ValidationError(f"Invalid email format: {email}")
+        return True
+
    def validate(self, data: dict) -> bool:
        """Validate data against defined rules."""
        for field, rule in self.rules.items():
```

## Code Quality Standards

All generated code must:
1. Follow project style conventions
2. Include docstrings/comments
3. Handle errors appropriately
4. Use proper type hints (if applicable)
5. Avoid unnecessary complexity
6. Be testable and maintainable

---

*Part of the LLM Codebase Interaction Guide - Step 5 of 8*
