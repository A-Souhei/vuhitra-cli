# Step 4: Planning - Establish a Detailed Plan of Action

Before generating code, the LLM **must** create a comprehensive, step-by-step plan.

## Good Plan Properties

✅ **Stepwise and atomic**: Each step is clear and independent
✅ **File-specific**: References exact files to modify
✅ **Test-aware**: Mentions tests to add/update
✅ **Behavior-focused**: Describes expected outcomes
✅ **Risk-conscious**: Notes potential issues or edge cases
✅ **Reversible**: Can be undone if needed

## Plan Generation Prompt

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

## Example Plan Output

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

**Step 3: Add user login endpoint**
- Files: src/api/auth.py (new), src/services/user_service.py (modify)
- Changes: Create login endpoint, add user lookup and password verification
- Tests: tests/api/test_auth.py (new) - test login success/failure paths
- Verification: pytest tests/api/test_auth.py -v
```

## Plan Review Checklist

Before proceeding, verify the plan includes:
- [ ] Clear file paths for all changes
- [ ] Specific code changes described
- [ ] Test files and test scenarios listed
- [ ] Verification commands provided
- [ ] Edge cases and risks noted
- [ ] Rollback approach documented

---

*Part of the LLM Codebase Interaction Guide - Step 4 of 8*
