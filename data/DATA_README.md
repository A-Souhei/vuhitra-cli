# Sample Data Files

This directory contains sample documents for testing vuhitra-cli context loading features.

## Directory Structure

```
data/
├── README.md                 # Sample project README
├── docs/                     # Documentation samples
│   ├── api.md               # API documentation
│   ├── coding_standards.md  # Coding guidelines
│   └── configuration.md     # Config guide
└── examples/                 # Example files
    └── simple.txt           # Simple test file
```

## Usage

### Spark Context (Automatic with @ Prefix)

```bash
# Load automatically when mentioned in prompts
What does @data/README.md say about testing?

# Load multiple files
Compare @data/docs/api.md and @data/docs/configuration.md
```

### Ephemeral Context (Session-scoped)

```bash
# Load single file
/load @data/docs/coding_standards.md

# Load directory
/load @data/docs/

# View loaded
/show ephemeral
```

### Eternal Context (Permanent)

```bash
# Load permanently
/load-eternal @data/docs/coding_standards.md standards

# View eternal contexts
/show eternal
```

## Test Usage

These files are used in `tests/test_data_files.py` to verify:
- File loading functionality
- @ prefix resolution
- Embedding generation
- Directory loading
- Context string formatting

Run tests with:
```bash
pytest tests/test_data_files.py -v
```

## File Descriptions

- **README.md** (~0.8 KB): Sample project README with features overview
- **docs/api.md** (~1.2 KB): REST API documentation with endpoints
- **docs/coding_standards.md** (~1.4 KB): Python style guide and best practices
- **docs/configuration.md** (~0.6 KB): Configuration examples for contexts
- **examples/simple.txt** (~0.2 KB): Simple text file for basic tests
