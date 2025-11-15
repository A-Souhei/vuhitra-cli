# Project README

## Overview

This is a sample README file for testing context loading features in vuhitra-cli.

## Features

- Spark Context: Lightweight, in-memory ephemeral context
- Ephemeral Context: Session-scoped context with Redis persistence
- Eternal Context: Permanent context stored on disk

## Usage

You can load this file using:

```bash
# As a Spark context (automatic with @ prefix)
What does @README.md say about features?

# As ephemeral context
/load @data/README.md

# As eternal context
/load-eternal @data/README.md project_readme
```

## Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the CLI: `python main.py`

## Testing

Run tests with: `./run_tests.sh`

## License

MIT License - See LICENSE file for details.
