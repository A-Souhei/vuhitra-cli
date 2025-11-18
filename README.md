
# vuhitra-cli

[![Tests](https://github.com/A-Souhei/vuhitra-cli/actions/workflows/tests.yml/badge.svg)](https://github.com/A-Souhei/vuhitra-cli/actions/workflows/tests.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A minimalist CLI tool to interact with Ollama LLMs, featuring comprehensive error handling and environment-aware logging.

## ✨ Features

- 🤖 **Interactive and non-interactive modes** for LLM interaction
- 🔧 **DEV/PROD environment modes** with intelligent logging
- 🐛 **Advanced error handling** with rich context and stack traces
- 📊 **Sentry.io integration** for production error tracking
- 🧪 **Comprehensive test suite** with pytest
- ⚙️ **YAML-based configuration** for easy customization
- 🎨 **Clean, maintainable codebase** with modern Python practices
- 🧠 **Semantic context filtering** with embedding-based relevance matching
- 💾 **Redis caching** for high-performance embedding storage
- 🔌 **MCP Servers** for code execution and development operations

## 🔌 MCP Servers

vuhitra-cli includes three Model Context Protocol (MCP) servers for code execution and development operations. These are available in **coding mode only**.

### 1. Executor MCP (26 tools)

Code execution and file operations on mirror+vanisher directories.

**Mirror+Vanisher Management (2 tools)**
- `list_mirror_vanishers` - List all mirror+vanisher directories
- `verify_mirror_vanisher` - Verify directory setup

**Code Execution (4 tools)**
- `execute_python_code` - Run Python scripts
- `execute_javascript_code` - Run JavaScript/Node.js scripts
- `execute_shell_command` - Execute shell commands
- `execute_code_snippet` - Run code snippets dynamically

**File Operations (6 tools)**
- `create_file` - Create new files
- `update_file` - Update existing files
- `append_to_file` - Append to files
- `delete_file` - Delete files with backup
- `copy_file` - Copy files
- `move_file` - Move/rename files

**Build Operations (6 tools)**
- `install_pip_packages` - Install Python packages
- `install_npm_packages` - Install Node.js packages
- `run_build_command` - Run build tools
- `compile_python` - Compile Python to bytecode
- `create_virtual_env` - Create Python venv
- `run_docker_build` - Build Docker images

**Directory Operations (6 tools)**
- `create_directory` - Create directories
- `create_directory_structure` - Create directory trees
- `delete_directory` - Delete directories with backup
- `copy_directory` - Copy directory trees
- `move_directory` - Move/rename directories
- `list_directory_contents` - List directory contents

### 2. Mirror+Vanisher Development MCP (31 tools)

LLM-driven development operations implementing an 8-step methodology.

**Step 1: Exploration (4 tools)**
- `explore_structure` - Generate directory tree
- `detect_tech_stack` - Identify languages and frameworks
- `find_entrypoints` - Locate main executable files
- `full_exploration` - Combined exploration

**Step 2: Architecture (3 tools)**
- `analyze_architecture` - Identify architectural patterns
- `map_dependencies` - Map imports and dependencies
- `identify_patterns` - Find design patterns

**Step 3: Chunking (2 tools)**
- `chunk_file` - Break large file into chunks
- `chunk_directory` - Create chunking strategy

**Step 4: Planning (2 tools)**
- `create_plan` - Generate implementation plan
- `validate_plan` - Check plan completeness

**Step 5: Code Generation (3 tools)**
- `generate_diff` - Create code diff preview
- `apply_changes` - Apply changes with backups
- `rewrite_file` - Completely rewrite a file

**Step 6: Testing (3 tools)**
- `generate_tests` - Create test templates
- `run_tests` - Execute tests
- `verify_changes` - Run tests for changed files

**Step 7: Quality Checks (4 tools)**
- `run_linter` - Run linter
- `run_formatter` - Format code
- `run_type_checker` - Check types
- `full_quality_check` - Combined quality checks

**Step 8: Security (3 tools)**
- `scan_secrets` - Find hardcoded secrets
- `check_vulnerabilities` - Scan dependencies
- `security_audit` - Complete security scan

**Multi-Step Workflows (3 tools)**
- `complete_feature_workflow` - End-to-end feature implementation
- `bugfix_workflow` - Bug analysis and fix workflow
- `refactor_workflow` - Refactoring workflow

### 3. Python Executor MCP (7 tools)

Lightweight code execution in vanisher directories with venv auto-detection.

**Code Operations (4 tools)**
- `write_code` - Write code to a file
- `update_code` - Update code with find-and-replace
- `run_code` - Execute code (Python, JavaScript, R, Shell)
- `pip_install` - Install Python packages

**Vanisher Management (3 tools)**
- `list_vanishers` - List all vanisher directories
- `list_files` - List files in a vanisher directory
- `delete_vanisher` - Delete a vanisher directory

**Features:**
- Auto-detects and uses venv for Python (venv, .venv, env, .env)
- Supports Python (.py), JavaScript (.js), R (.r, .R), Shell (.sh, .bash)
- 300 second timeout for package installation

### MCP Configuration

Add to your Claude Desktop MCP settings:

```json
{
  "mcpServers": {
    "executor": {
      "command": "python",
      "args": ["/path/to/vuhitra-cli/mcps/executor/server.py"]
    },
    "mirror-vanisher-dev": {
      "command": "python",
      "args": ["/path/to/vuhitra-cli/mcps/mirror_vanisher_dev/server.py"]
    },
    "python-executor": {
      "command": "python",
      "args": ["/path/to/vuhitra-cli/mcps/python_executor/server.py"]
    }
  }
}
```

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd vuhitra-cli

# Install dependencies
pip install -r requirements.txt

```

### Basic Usage

```bash
# Interactive mode
python main.py

# Non-interactive mode
python main.py -p "What is Python?"

# Specify a model
python main.py -m qwen2.5-coder:7b -p "Explain recursion"
```

## 📖 Usage

### Interactive Mode

Start an interactive session with the LLM:

```bash
python main.py
```

```
vuhitra-cli interactive mode (model: llama3.1:8b)
Type 'exit' or 'quit' to leave, Ctrl+C to interrupt

>>> What is the capital of France?
Paris is the capital of France.

>>> exit
```

### Non-Interactive Mode

Get a single response and exit:

```bash
python main.py -p "Explain machine learning in one sentence"
```

### Available Models

Configure available models in `config.yaml`:
- `llama3.1:8b` (default)
- `qwen3-vl:8b`
- `qwen2.5-coder:7b`
- `qwen2-math:7b`
- And more...

## 🎯 Environment Modes

### DEV Mode (Default)

Perfect for development and debugging:
- ✅ Detailed logging to stderr
- ✅ Full stack traces
- ✅ Error context displayed
- ✅ Breadcrumb tracking

```bash
# Default mode
python main.py

# Or explicitly set
export VUHITRA_MODE=DEV
python main.py
```

### PROD Mode

Production-ready with minimal logging:
- ✅ Minimal console output
- ✅ Sentry error reporting (if configured)
- ✅ Production-safe error messages
- ✅ Clean user experience

```bash
export VUHITRA_MODE=PROD
python main.py
```

## ⚙️ Configuration

Edit `config.yaml` to customize settings:

```yaml
# CLI settings
cli:
  default_timeout: 30

# Model configuration
model:
  default: llama3.1:8b
  available:
    - llama3.1:8b
    - qwen2.5-coder:7b
    # Add more models...

# Ollama server
ollama:
  host: 192.168.31.23
  protocol: http
  port: 11434
  api_path: /api/generate

# Environment (DEV/PROD)
environment:
  mode: DEV
  enable_logging: true

# Sentry.io (optional)
sentry:
  dsn: ""  # Add your DSN here
  environment: development
  traces_sample_rate: 1.0
```

## 🐛 Error Handling

The project includes a sophisticated error handling system:

### Basic Usage

```python
from src.errors_handler import handle_exception

try:
    risky_operation()
except Exception as e:
    handle_exception(e, context={
        'operation': 'risky_operation',
        'user_id': '12345'
    })
```

### Capture Messages

```python
from src.errors_handler import capture_message

capture_message(
    "User action completed",
    level="info",
    context={'action': 'login'}
)
```

### Advanced Features

```python
from src.errors_handler import get_error_handler

handler = get_error_handler()

# Add breadcrumbs for debugging
handler.add_breadcrumb("User clicked submit", category="ui")

# Set user context
handler.set_user_context(user_id="123", username="john")

# Handle with context
try:
    process_data()
except Exception as e:
    handler.handle_exception(e, context={'step': 'processing'})
```

## 🧪 Testing

### Run Tests

```bash
# Simple way
./run_tests.sh

# With verbose output
./run_tests.sh -v

# With coverage report
./run_tests.sh -c

# Generate HTML coverage
./run_tests.sh --html-coverage

# Run specific tests
./run_tests.sh -t test_error_handler.py

# Pattern matching
./run_tests.sh -k "sentry"
```

### Using pytest directly

```bash
pytest                          # Run all tests
pytest -v                       # Verbose
pytest --cov=src               # With coverage
pytest tests/test_error_handler.py  # Specific file
```

### Test Coverage

The project includes comprehensive test coverage:
- ✅ 27 test cases
- ✅ Error handler tests
- ✅ Configuration loader tests
- ✅ Integration tests
- ✅ Mocked Sentry tests

## 📊 Sentry Integration (Optional)

### Setup

1. Create account at [sentry.io](https://sentry.io)
2. Create a new project
3. Copy your DSN
4. Add to `config.yaml`:

```yaml
sentry:
  dsn: "https://your-key@sentry.io/your-project-id"
  environment: production
```

### Features

When Sentry is configured:
- 🔍 Automatic error reporting
- 📊 Performance monitoring
- 🔔 Real-time alerts
- 📈 Error trends and analytics
- 👤 User context tracking
- 🍞 Breadcrumb trails

## 📁 Project Structure

```
vuhitra-cli/
├── main.py                 # Entry point
├── config.yaml            # Configuration
├── run.sh                 # Run script
├── run_tests.sh          # Test runner
├── pytest.ini            # Pytest configuration
├── pyproject.toml        # Project metadata
├── requirements.txt      # Dependencies
│
├── src/
│   ├── cli.py           # CLI interface
│   ├── agent.py         # LLM interaction
│   ├── errors_handler/  # Error handling module
│   │   ├── error_handler.py
│   │   ├── __init__.py
│   │   └── README.md
│   └── utils/
│       ├── arg_parser.py
│       └── config_loader.py
│
├── tests/               # Test suite
│   ├── test_error_handler.py
│   ├── test_config_loader.py
│   ├── __init__.py
│   └── README.md
│
└── docs/               # Documentation
    ├── IMPLEMENTATION.md
    ├── TEST_RUNNER_GUIDE.md
    └── QUICK_START.md
```

## 🛠️ Development

### Prerequisites

- Python 3.12+
- Ollama server running
- pip or poetry for dependency management

### Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd vuhitra-cli

# Install dependencies
pip install -r requirements.txt

# Or use poetry
poetry install

# Run tests
./run_tests.sh -v

# Run linter (if configured)
# pylint src/
```

### Running in DEV Mode

```bash
# Set environment
export VUHITRA_MODE=DEV

# Run with logging
python main.py
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for public functions
- Keep functions small and focused
- Add tests for new features

## 📚 Documentation

- **[QUICK_START.md](QUICK_START.md)** - Quick reference guide
- **[docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md)** - Complete implementation details
- **[docs/TEST_RUNNER_GUIDE.md](docs/TEST_RUNNER_GUIDE.md)** - Test runner documentation
- **[docs/SEMANTIC_FILTERING.md](docs/SEMANTIC_FILTERING.md)** - Semantic context filtering guide
- **[src/errors_handler/README.md](src/errors_handler/README.md)** - Error handler guide
- **[tests/README.md](tests/README.md)** - Testing guide

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`./run_tests.sh -v`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 🔧 Troubleshooting

### "Connection refused" error

- Ensure Ollama server is running
- Check `ollama.host` in `config.yaml`
- Verify network connectivity

### "Model not found" error

- Check model name in `config.yaml`
- Ensure model is available on Ollama server
- Try `ollama list` to see available models

### Tests failing

```bash
# Install test dependencies
pip install pytest pytest-mock pytest-cov

# Run tests with verbose output
./run_tests.sh -vv
```

### Import errors

```bash
# Ensure you're in the project root
cd /path/to/vuhitra-cli

# Install dependencies
pip install -r requirements.txt
```

## 📝 License

MIT

## 👥 Authors

- a-souhei - *Initial work*



## 📮 Support

For issues, questions, or contributions:
- Open an issue on GitHub

---

**Built with ❤️ using Python and Ollama**
