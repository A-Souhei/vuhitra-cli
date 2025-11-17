# Step 3: Chunking - Making Large Codebases Understandable

If your repository is large (>50 files or >10,000 lines), feed it to the LLM in strategic chunks to avoid token limits and maintain context quality.

## Chunking Strategies

| Strategy | When to Use | Example |
|----------|-------------|---------|
| **By folder/module** | Modular codebases | `src/auth/`, `src/api/`, `src/database/` |
| **By feature** | Feature-based organization | `user-management/`, `payment-processing/` |
| **By layer** | Layered architecture | `models/`, `services/`, `controllers/` |
| **Split long files** | Files >400–800 lines | Break into logical sections (imports, classes, functions) |
| **Summarize first, detail later** | Complex systems | Create module summaries, then dive into specifics |

## Chunking Best Practices

### 1. Start broad, then narrow
- First pass: High-level summaries of each module
- Second pass: Detailed analysis of target modules
- Third pass: Line-by-line review of modified code

### 2. Maintain context between chunks
- Include brief summaries of related modules
- Reference interfaces and contracts
- Note dependencies explicitly

### 3. Use hierarchical summarization
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

## Chunking Prompt Template

```
I'm providing code in chunks. For this chunk (Module: [name]):

1. Summarize the module's purpose in 2–3 sentences
2. List the main classes/functions and their responsibilities
3. Identify dependencies on other modules
4. Note any patterns, design decisions, or potential issues

[paste code chunk]
```

## Token Management Tips

- Keep chunks under 4000 tokens when possible
- Provide cross-references between chunks
- Summarize previous chunks when needed
- Use file paths as context anchors

---

*Part of the LLM Codebase Interaction Guide - Step 3 of 8*
