# Quick Start Guide - vuhitra-cli

## 🚀 Running Tests

### Simple Way
```bash
./run_tests.sh
```

### With Options
```bash
./run_tests.sh -v           # Verbose
./run_tests.sh -c           # With coverage
./run_tests.sh -h           # Help
```

## 🛠️ Setup

### Install Dependencies
```bash
pip install requests pyyaml sentry-sdk pytest pytest-mock
```

### Configure
Edit `config.yaml`:
```yaml
environment:
  mode: DEV  # or PROD

sentry:
  dsn: ""  # Add your Sentry DSN (optional)
```

## 🎯 Environment Modes

### DEV Mode (Default)
- Full logging enabled
- Detailed error output
- Stack traces shown

### PROD Mode
- Minimal logging
- Production-safe errors
- Sentry-only reporting

Set mode:
```bash
# Via environment variable
export VUHITRA_MODE=PROD

# Or in config.yaml
environment:
  mode: PROD
```

## 🐛 Error Handling

### Basic Usage
```python
from src.errors_handler import handle_exception

try:
    risky_operation()
except Exception as e:
    handle_exception(e, context={'operation': 'risky_operation'})
```

### Capture Messages
```python
from src.errors_handler import capture_message

capture_message("Important event", level="info")
```

## 📁 Project Structure

```
vuhitra-cli/
├── src/
│   ├── errors_handler/      # Error handler module
│   │   ├── error_handler.py
│   │   ├── __init__.py
│   │   └── README.md
│   ├── utils/
│   │   └── config_loader.py
│   ├── agent.py
│   └── cli.py
├── tests/                   # Test files (pytest)
│   ├── test_error_handler.py
│   ├── test_config_loader.py
│   └── README.md
├── config.yaml              # Configuration
├── run_tests.sh            # Test runner script
├── pytest.ini              # Pytest config
└── IMPLEMENTATION.md       # Full implementation docs
```

## 📚 Documentation

- `IMPLEMENTATION.md` - Complete implementation guide
- `TEST_RUNNER_GUIDE.md` - Test runner documentation
- `src/errors_handler/README.md` - Error handler docs
- `tests/README.md` - Testing guide

## 🧪 Testing

### Run All Tests
```bash
./run_tests.sh
```

### Run Specific Tests
```bash
./run_tests.sh -t test_error_handler.py
./run_tests.sh -k "sentry"
```

### Generate Coverage Report
```bash
./run_tests.sh --html-coverage
```

## 🔧 Common Commands

```bash
# Run the CLI
python main.py

# Run tests
./run_tests.sh -v

# Run with coverage
./run_tests.sh -c

# Set PROD mode
export VUHITRA_MODE=PROD
python main.py
```

## ⚙️ Optional: Sentry Setup

1. Create account at [sentry.io](https://sentry.io)
2. Get your DSN
3. Add to `config.yaml`:
   ```yaml
   sentry:
     dsn: "https://your-dsn@sentry.io/project-id"
   ```

## 🎓 Learn More

- Error handler features: `src/errors_handler/README.md`
- Testing guide: `tests/README.md`
- Full implementation: `IMPLEMENTATION.md`
