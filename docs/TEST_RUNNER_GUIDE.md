# Test Runner Guide - run_tests.sh

## Quick Reference

### Basic Usage
```bash
./run_tests.sh              # Run all tests
./run_tests.sh -v           # Verbose output
./run_tests.sh -vv          # Very verbose + show prints
./run_tests.sh -c           # With coverage report
./run_tests.sh --html-coverage  # Generate HTML coverage
./run_tests.sh -h           # Show help
```

### Advanced Usage
```bash
# Run specific test file
./run_tests.sh -t test_error_handler.py

# Run tests matching pattern
./run_tests.sh -k "sentry"
./run_tests.sh -k "config"

# Combine options
./run_tests.sh -v -c        # Verbose with coverage
./run_tests.sh -vv -k "error"  # Very verbose, pattern match
```

## Options

- `-v, --verbose` - Run with verbose output
- `-vv, --very-verbose` - Run with very verbose output and show print statements
- `-c, --coverage` - Run with coverage report (terminal)
- `--html-coverage` - Generate HTML coverage report
- `-k, --pattern PATTERN` - Run tests matching pattern
- `-t, --test FILE` - Run specific test file
- `-h, --help` - Show help message

## Features

✅ Colored output (green for pass, red for fail)
✅ Checks if pytest is installed
✅ Validates pytest-cov for coverage reports
✅ Shows helpful instructions for viewing HTML coverage
✅ Exit codes (0 for success, 1 for failure)
✅ Works from project root directory

## Requirements

Install dependencies:
```bash
pip install pytest pytest-mock pytest-cov
```

## Examples

### Development Workflow
```bash
# Quick test run
./run_tests.sh

# Before commit (with coverage)
./run_tests.sh -v -c

# Debugging specific test
./run_tests.sh -vv -t test_error_handler.py

# Check Sentry tests
./run_tests.sh -k "sentry" -v
```

## Coverage Reports

### Terminal Coverage
```bash
./run_tests.sh -c
```

### HTML Coverage
```bash
./run_tests.sh --html-coverage
# Then open htmlcov/index.html in browser
```

## Troubleshooting

### "pytest is not installed"
```bash
pip install pytest pytest-mock
```

### "pytest-cov is not installed" (when using -c)
```bash
pip install pytest-cov
```

### Permission denied
```bash
chmod +x run_tests.sh
```
