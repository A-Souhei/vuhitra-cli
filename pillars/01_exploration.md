# Step 1: Exploration - Get a Quick Overview

Before asking an LLM to generate or update code, first give it a structured view of the repository.

## What to Collect

| Information Type | Purpose | Tools |
|-----------------|---------|-------|
| **Folder tree** (top 2–3 levels) | Understand project structure | `tree -a -L 2` |
| **Languages used** | Identify tech stack | File extensions, `package.json`, `pyproject.toml` |
| **Frameworks** | Detect from config files | `requirements.txt`, `package.json`, `Gemfile` |
| **Entrypoints** | Find main execution files | `main.py`, `index.js`, `app.py`, CLI scripts |
| **Tests folder structure** | Understand testing approach | `tests/`, `__tests__/`, `spec/` |
| **Environment files** | Configuration approach (sanitized) | `.env.example`, `config.yaml` |
| **Configuration files** | Project settings | YAML, JSON, TOML, INI files |

## Typical Exploration Commands

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

## Exploration Prompt Template

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

## Expected Output

The LLM should provide:
- Clear identification of tech stack
- Top-level folder purposes
- Main entry points with explanations
- Priority list of files to read next
- Initial observations about architecture

---

*Part of the LLM Codebase Interaction Guide - Step 1 of 8*
