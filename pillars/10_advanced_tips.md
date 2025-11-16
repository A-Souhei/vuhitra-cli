# Advanced Tips for LLM Codebase Interaction

## 1. Iterative Refinement

Don't expect perfection on the first try. Use this iterative approach:

```
Initial request → LLM response → Review → Refine prompt → Improved response
```

**Example refinement:**
- Initial: "Add user authentication"
- Refined: "Add JWT-based authentication using the existing database schema, following the middleware pattern used in src/middleware/*, with tests matching the style in tests/middleware/*"

---

## 2. Context Preservation

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

---

## 3. Dependency Mapping

Ask the LLM to create a dependency graph before modifications:

```
Map the dependencies for [module/feature]:

1. Direct dependencies: What does this module import?
2. Reverse dependencies: What imports this module?
3. External dependencies: Third-party libraries used
4. Impact radius: What will be affected by changes here?
```

---

## 4. Code Review Prompts

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

---

## 5. Progressive Disclosure

For complex changes, use progressive disclosure:

```
Level 1: "What needs to change?" (Overview)
Level 2: "How should it change?" (Plan)
Level 3: "Show me the code" (Implementation)
Level 4: "What could go wrong?" (Review)
Level 5: "How do we verify?" (Testing)
```

---

## 6. Pattern Recognition

Ask the LLM to identify patterns:

```
Analyze the codebase for patterns:

1. **Design patterns**: Which patterns are used? (Singleton, Factory, Observer, etc.)
2. **Naming conventions**: How are variables, functions, classes named?
3. **Error handling**: What error handling approach is used?
4. **Testing patterns**: What testing style is followed?
5. **Code organization**: How is code structured and organized?

Use these patterns when generating new code.
```

---

## 7. Impact Analysis

Before making changes:

```
Analyze the impact of changing [module/function]:

1. **Direct impact**: What code directly calls this?
2. **Indirect impact**: What depends on the direct callers?
3. **Data impact**: What data structures are affected?
4. **API impact**: Does this change any public interfaces?
5. **Breaking changes**: Will this break existing code?
6. **Migration path**: How can users migrate if needed?
```

---

## 8. Incremental Implementation

Break large features into small, testable increments:

```
Instead of: "Add complete authentication system"

Break into:
1. Add password hashing utility
2. Create user model with auth fields
3. Implement login endpoint
4. Add JWT token generation
5. Create auth middleware
6. Protect routes with middleware
7. Add refresh token logic
8. Implement logout endpoint
```

---

## 9. Documentation Generation

Ask for documentation alongside code:

```
For the changes made, provide:

1. **Inline documentation**: Updated docstrings/comments
2. **API documentation**: If public APIs changed
3. **README updates**: If user-facing features added
4. **Migration guide**: If breaking changes introduced
5. **Example usage**: Code examples showing how to use new features
```

---

## 10. Performance Considerations

Include performance analysis:

```
Analyze the performance implications of [change]:

1. **Time complexity**: Big O notation for algorithms
2. **Space complexity**: Memory usage implications
3. **Database queries**: N+1 queries, indexing needs
4. **Caching opportunities**: What can be cached?
5. **Bottlenecks**: Potential performance bottlenecks
6. **Optimization suggestions**: How to improve performance
```

---

*Part of the LLM Codebase Interaction Guide - Advanced Techniques*
