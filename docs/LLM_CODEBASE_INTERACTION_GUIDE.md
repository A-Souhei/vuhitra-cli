# Best Practices for Using an LLM to Explore, Understand, and Modify a Whole Codebase

## 📋 Table of Contents

- [Overview](#overview)
- [1. Exploration — Get a Quick Overview of the Project](#1-exploration--get-a-quick-overview-of-the-project)
- [2. Summarize the Architecture & Major Components](#2-summarize-the-architecture--major-components)
- [3. Chunking — Making Large Codebases Understandable](#3-chunking--making-large-codebases-understandable)
- [4. Establish a Detailed Plan of Action](#4-establish-a-detailed-plan-of-action)
- [5. Code Generation — Using Diffs or Full File Rewrites](#5-code-generation--using-diffs-or-full-file-rewrites)
- [6. Testing and Verification](#6-testing-and-verification)
- [7. Quality Checks](#7-quality-checks)
- [8. Secret & Config Safety Check](#8-secret--config-safety-check)
- [Ready-to-Use LLM Prompt Sequence](#-ready-to-use-llm-prompt-sequence)
- [Advanced Tips](#-advanced-tips)
- [Common Pitfalls to Avoid](#-common-pitfalls-to-avoid)

---

## Overview

Working with Large Language Models (LLMs) to understand and modify codebases requires a structured approach. This guide provides a systematic methodology to maximize the effectiveness of LLM-assisted development while maintaining code quality and safety.

**Key Principles:**
- 🔍 Explore before modifying
- 📊 Provide structured context
- 🎯 Create clear, atomic plans
- ✅ Always verify and test
- 🔒 Maintain security awareness

---

## 1. Exploration — Get a Quick Overview of the Project

Before asking an LLM to generate or update code, first give it a structured view of the repository.

### What to Collect

| Information Type | Purpose | Tools |
|-----------------|---------|-------|
| **Folder tree** (top 2–3 levels) | Understand project structure | `tree -a -L 2` |
| **Languages used** | Identify tech stack | File extensions, `package.json`, `pyproject.toml` |
| **Frameworks** | Detect from config files | `requirements.txt`, `package.json`, `Gemfile` |
| **Entrypoints** | Find main execution files | `main.py`, `index.js`, `app.py`, CLI scripts |
| **Tests folder structure** | Understand testing approach | `tests/`, `__tests__/`, `spec/` |
| **Environment files** | Configuration approach (sanitized) | `.env.example`, `config.yaml` |
| **Configuration files** | Project settings | YAML, JSON, TOML, INI files |

### Typical Exploration Commands

```bash
# Get folder structure
tree -a -L 2

# List all files (shallow)
find . -maxdepth 2 -type f

# Find TODOs and FIXMEs
grep -R "TODO\|FIXME" -n --include="*.py" --include="*.js"

# Identify main dependencies
cat package.json pyproject.toml requirements.txt 2>/dev/null

# Find entry points
find . -name "main.*" -o -name "index.*" -o -name "app.*" -maxdepth 3
```

### 📝 Exploration Prompt Template

```
Here is the project structure:

[paste tree output]

Please analyze and provide:
1. Main languages and frameworks used
2. Purpose of each top-level folder
3. Likely functional entrypoints of the application
4. 5–8 most important files to understand first, with reasons for each
5. Any notable patterns or architectural decisions you observe
```

---

## 2. Summarize the Architecture & Major Components

Once the LLM sees the file list or key files, ask for a high-level summary.

### What to Request

- **1-paragraph purpose summary**: What does this application do?
- **High-level architecture**: Monolith, microservices, layered, MVC, etc.
- **Application flow**: Request → Response, or Module → Module interactions
- **Critical dependencies**: Database, APIs, external services
- **Data flow**: How information moves through the system

### 📝 Architecture Summary Prompt

```
Using the following file list and code snippets, produce:

1. One paragraph describing the application's purpose and main functionality
2. The architectural pattern used (e.g., MVC, microservices, layered architecture)
3. Three to five bullet points showing the typical system flow (e.g., request → routing → business logic → database → response)
4. A list of 8–10 key files/modules to understand, with 1-line reasons for each
5. Main external dependencies and integrations
```

---

## 3. Chunking — Making Large Codebases Understandable

If your repository is large (>50 files or >10,000 lines), feed it to the LLM in strategic chunks to avoid token limits and maintain context quality.

### Chunking Strategies

| Strategy | When to Use | Example |
|----------|-------------|---------|
| **By folder/module** | Modular codebases | `src/auth/`, `src/api/`, `src/database/` |
| **By feature** | Feature-based organization | `user-management/`, `payment-processing/` |
| **By layer** | Layered architecture | `models/`, `services/`, `controllers/` |
| **Split long files** | Files >400–800 lines | Break into logical sections (imports, classes, functions) |
| **Summarize first, detail later** | Complex systems | Create module summaries, then dive into specifics |

### Chunking Best Practices

1. **Start broad, then narrow**
   - First pass: High-level summaries of each module
   - Second pass: Detailed analysis of target modules
   - Third pass: Line-by-line review of modified code

2. **Maintain context between chunks**
   - Include brief summaries of related modules
   - Reference interfaces and contracts
   - Note dependencies explicitly

3. **Use hierarchical summarization**
   ```
   Project Overview (1 paragraph)
   ├── Module A Summary (2–3 bullets)
   │   ├── File A1 (1-line purpose)
   │   └── File A2 (1-line purpose)
   ├── Module B Summary (2–3 bullets)
   │   ├── File B1 (1-line purpose)
   │   └── File B2 (1-line purpose)
   └── Module C Summary (2–3 bullets)
   ```

### 📝 Chunking Prompt Template

```
I'm providing code in chunks. For this chunk (Module: [name]):

1. Summarize the module's purpose in 2–3 sentences
2. List the main classes/functions and their responsibilities
3. Identify dependencies on other modules
4. Note any patterns, design decisions, or potential issues

[paste code chunk]
```

---

## 4. Establish a Detailed Plan of Action

Before generating code, the LLM **must** create a comprehensive, step-by-step plan.

### Good Plan Properties

✅ **Stepwise and atomic**: Each step is clear and independent
✅ **File-specific**: References exact files to modify
✅ **Test-aware**: Mentions tests to add/update
✅ **Behavior-focused**: Describes expected outcomes
✅ **Risk-conscious**: Notes potential issues or edge cases
✅ **Reversible**: Can be undone if needed

### 📝 Plan Generation Prompt

```
Given the repository summary and the following request:

[feature/fix description]

Create a detailed, step-by-step implementation plan including:

1. **Files to read**: Which files need to be examined for context
2. **Files to modify**: Which files will be changed and why
3. **New files to create**: If any, with justification
4. **Logic changes**: What code logic will be adjusted or added
5. **Tests needed**: Unit and integration tests to write/update
6. **Validation commands**: How to verify correctness (linting, type-checking, tests)
7. **Rollback strategy**: How to undo changes if needed
8. **Potential risks**: Edge cases, breaking changes, or dependencies affected

Format each step as:
**Step N: [Action]**
- Files: [list]
- Changes: [description]
- Tests: [test file and approach]
- Verification: [command to run]
```

### Example Plan Output

```markdown
**Step 1: Add user authentication middleware**
- Files: src/middleware/auth.py (new), src/config/settings.py (modify)
- Changes: Create JWT validation middleware, add secret key config
- Tests: tests/middleware/test_auth.py (new) - test valid/invalid/expired tokens
- Verification: pytest tests/middleware/test_auth.py -v

**Step 2: Integrate middleware into API routes**
- Files: src/api/routes.py (modify)
- Changes: Apply @require_auth decorator to protected endpoints
- Tests: tests/api/test_protected_routes.py (update) - test auth enforcement
- Verification: pytest tests/api/ -v
```

---

## 5. Code Generation — Using Diffs or Full File Rewrites

The LLM should provide code changes in a **safe and traceable** format.

### Recommended Methods

| Method | When to Use | Example |
|--------|-------------|---------|
| **Unified diff** | Small, targeted changes | `--- a/file.py` / `+++ b/file.py` |
| **Full file overwrite** | Small files (<100 lines) or complete rewrites | Entire file content |
| **Search-and-replace** | Specific pattern changes | Old code block → New code block |

### 📝 Patch Generation Prompt

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

### What the LLM Should Ensure

- ✅ No unrelated formatting changes
- ✅ No hidden logic alterations
- ✅ Code is consistent with project style
- ✅ Proper error handling included
- ✅ Comments added for complex sections
- ✅ Type hints/annotations preserved (if used)
- ✅ Imports updated correctly

### Example Diff Output

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

---

## 6. Testing and Verification

The LLM should generate or update tests **every time** it changes code.

### Testing Requirements

| Test Type | Coverage | Example |
|-----------|----------|---------|
| **Unit tests** | Individual functions/methods | Test `validate_email()` with valid/invalid inputs |
| **Integration tests** | Component interactions | Test API endpoint with authentication middleware |
| **Edge cases** | Boundary conditions | Empty strings, null values, max lengths |
| **Error paths** | Exception handling | Invalid input, missing data, timeouts |

### 📝 Test Generation Prompt

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

### Example Test Output

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

---

## 7. Quality Checks

Before applying LLM-generated code, **always run** these verification steps.

### Pre-Commit Checklist

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

### 📝 Quality Check Prompt

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

---

## 8. Secret & Config Safety Check

Ask the LLM to scan for sensitive information **without printing** actual values.

### 📝 Safety Scanning Prompt

```
Scan the project structure for potentially sensitive files and data:

1. List files that might contain secrets (only file paths, no content):
   - .env files
   - API key files
   - Private keys (.pem, .key, .p12)
   - Configuration files with credentials
   - Database connection strings

2. Check if sensitive files are properly gitignored

3. Verify that example/template files exist for configuration:
   - .env.example
   - secrets.yaml.template
   - config.yaml.example

4. Recommendations for improving secret management

**Important**: Do NOT display actual secret values, only file paths and recommendations.
```

### Expected Output Format

```markdown
### Sensitive Files Found

**Properly Gitignored:**
- `.env` ✅
- `secrets.yaml` ✅
- `config/database.yml` ✅

**Missing .gitignore Entry:**
- `api_keys.json` ⚠️  (Recommendation: Add to .gitignore)

**Template Files Present:**
- `.env.example` ✅
- `secrets.yaml.template` ✅

**Recommendations:**
1. Add `api_keys.json` to `.gitignore`
2. Create `api_keys.json.example` with placeholder values
3. Consider using environment variables for all secrets
4. Document required secrets in README.md
```

---

## 📘 Ready-to-Use LLM Prompt Sequence

Use this proven sequence for systematic codebase interaction:

### **Step 1 — Explore**

```
Here is the output of `tree -a -L 2`:

[paste tree output]

Please summarize:
1. The project structure and key folders
2. Main entrypoints and their purposes
3. Languages, frameworks, and tools used
4. 5-8 most important files to understand first
```

---

### **Step 2 — Understand**

```
Here are the contents of the key files you identified:

[paste file contents]

Provide:
1. One paragraph summary of the application's purpose
2. The architectural pattern used
3. Data/request flow through the system (3-5 steps)
4. Key design patterns and conventions observed
5. Notable dependencies or integrations
```

---

### **Step 3 — Plan**

```
I want to implement the following feature/fix:

[describe feature/fix]

Create a detailed, step-by-step implementation plan including:
- Files to read/modify/create
- Logic changes needed
- Tests to write/update
- Verification commands
- Potential risks or edge cases
```

---

### **Step 4 — Implement**

```
Apply Step [N] of the plan: [step description]

Provide:
1. A unified diff showing the exact changes
2. A 2-3 sentence explanation of what changed and why
3. Any assumptions or design decisions made

Ensure:
- Only necessary lines are modified
- Code follows project conventions
- Error handling is included
- Comments explain complex logic
```

---

### **Step 5 — Test**

```
Write comprehensive tests for the changes in Step [N].

Include:
1. Test file path and complete test code
2. Tests for normal cases, edge cases, and error paths
3. Exact commands to run the tests
4. Expected test output

Follow existing test patterns in the project.
```

---

### **Step 6 — Verify**

```
Provide all quality check commands to verify the implementation:

1. Linting: [command]
2. Formatting: [command]
3. Type checking: [command]
4. Unit tests: [command]
5. Integration tests: [command]

Include expected output for each command when successful.
```

---

## 🎯 Advanced Tips

### 1. Iterative Refinement

Don't expect perfection on the first try. Use this iterative approach:

```
Initial request → LLM response → Review → Refine prompt → Improved response
```

**Example refinement:**
- Initial: "Add user authentication"
- Refined: "Add JWT-based authentication using the existing database schema, following the middleware pattern used in src/middleware/*, with tests matching the style in tests/middleware/*"

### 2. Context Preservation

Maintain a "context document" throughout the session:

```markdown
## Session Context

**Goal**: Implement user authentication

**Key Decisions**:
- Using JWT (not sessions) - discussed in Step 1
- Token expiry: 24 hours - decided in Step 2
- Storing in httpOnly cookies - security decision in Step 3

**Files Modified**:
- src/middleware/auth.py (created)
- src/api/routes.py (updated)
- tests/middleware/test_auth.py (created)

**Next Steps**:
- Add refresh token logic
- Implement logout endpoint
```

### 3. Dependency Mapping

Ask the LLM to create a dependency graph before modifications:

```
Map the dependencies for [module/feature]:

1. Direct dependencies: What does this module import?
2. Reverse dependencies: What imports this module?
3. External dependencies: Third-party libraries used
4. Impact radius: What will be affected by changes here?
```

### 4. Code Review Prompts

Use the LLM as a reviewer:

```
Review the following code changes as if in a code review:

[paste diff or code]

Check for:
1. Potential bugs or edge cases
2. Performance implications
3. Security vulnerabilities
4. Code style consistency
5. Missing error handling
6. Test coverage gaps
7. Documentation needs

Provide specific, actionable feedback.
```

### 5. Progressive Disclosure

For complex changes, use progressive disclosure:

```
Level 1: "What needs to change?" (Overview)
Level 2: "How should it change?" (Plan)
Level 3: "Show me the code" (Implementation)
Level 4: "What could go wrong?" (Review)
Level 5: "How do we verify?" (Testing)
```

---

## ⚠️ Common Pitfalls to Avoid

### 1. Information Overload

❌ **Don't**: Dump entire codebase at once
✅ **Do**: Provide structured, chunked information

### 2. Vague Requests

❌ **Don't**: "Make the code better"
✅ **Do**: "Refactor the `process_data` function to handle empty lists and add type hints"

### 3. Skipping Tests

❌ **Don't**: Accept code without tests
✅ **Do**: Always require tests for every code change

### 4. Trusting Blindly

❌ **Don't**: Apply LLM code without review
✅ **Do**: Review, test, and verify all generated code

### 5. Ignoring Context

❌ **Don't**: Ask for changes without showing existing code
✅ **Do**: Provide relevant existing code and patterns

### 6. Missing Verification

❌ **Don't**: Assume the code works
✅ **Do**: Run all quality checks and tests

### 7. Security Blind Spots

❌ **Don't**: Ignore security implications
✅ **Do**: Explicitly check for security issues (injection, XSS, auth, etc.)

### 8. No Rollback Plan

❌ **Don't**: Make changes without version control
✅ **Do**: Commit atomically, plan rollback steps

---

## 📚 Additional Resources

- **Project Testing Guide**: See `TESTING_GUIDE.md` for testing best practices
- **Security Practices**: See `SECRETS.md` for secret management
- **Implementation Details**: See `IMPLEMENTATION.md` for architecture details
- **Quick Start**: See `QUICK_START.md` for getting started with the project

---

## 📝 Summary

**Key Takeaways:**

1. 🔍 **Explore first**: Understand before modifying
2. 📊 **Structure context**: Provide organized, chunked information
3. 🎯 **Plan deliberately**: Create detailed, step-by-step plans
4. 💻 **Generate carefully**: Use diffs, follow conventions
5. ✅ **Test thoroughly**: Always write and run tests
6. 🔒 **Verify security**: Check for secrets and vulnerabilities
7. 🔄 **Iterate and refine**: Don't expect perfection on first try

**Remember**: The LLM is a powerful assistant, but **you** are responsible for:
- Reviewing all generated code
- Ensuring quality and security
- Making final decisions
- Maintaining project standards

---

*Last updated: 2025-11-16*
*Version: 1.0*
