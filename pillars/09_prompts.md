# Ready-to-Use LLM Prompt Sequence

Use this proven sequence for systematic codebase interaction.

## Step 1 — Explore

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

## Step 2 — Understand

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

## Step 3 — Plan

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

## Step 4 — Implement

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

## Step 5 — Test

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

## Step 6 — Verify

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

## Quick Copy-Paste Templates

### Exploration Quick Template
```
tree -a -L 2
[paste output]
Summarize: structure, entrypoints, tech stack, 5-8 key files
```

### Planning Quick Template
```
Feature: [description]
Plan: files, changes, tests, verification, risks
```

### Implementation Quick Template
```
Step [N]: [description]
Diff, explanation, decisions, conventions
```

### Testing Quick Template
```
Tests for [module]
Happy path + edge cases + errors
Include: path, code, commands, output
```

---

*Part of the LLM Codebase Interaction Guide - Prompt Templates*
