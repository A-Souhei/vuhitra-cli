#!/bin/bash

# Test runner script for vuhitra-cli
# Runs all tests in the tests/ directory using pytest

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Running vuhitra-cli Tests${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo -e "${YELLOW}Install it with: pip install pytest pytest-mock${NC}"
    exit 1
fi

# Parse command line arguments
VERBOSE=""
COVERAGE=""
PATTERN=""
SPECIFIC_TEST=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -vv|--very-verbose)
            VERBOSE="-vv -s"
            shift
            ;;
        -c|--coverage)
            COVERAGE="--cov=src --cov-report=term-missing"
            shift
            ;;
        --html-coverage)
            COVERAGE="--cov=src --cov-report=html"
            shift
            ;;
        -k|--pattern)
            PATTERN="-k $2"
            shift 2
            ;;
        -t|--test)
            SPECIFIC_TEST="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose          Run with verbose output"
            echo "  -vv, --very-verbose    Run with very verbose output and show prints"
            echo "  -c, --coverage         Run with coverage report"
            echo "  --html-coverage        Generate HTML coverage report"
            echo "  -k, --pattern PATTERN  Run tests matching pattern"
            echo "  -t, --test FILE        Run specific test file"
            echo "  -h, --help             Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Run all tests"
            echo "  $0 -v                        # Run with verbose output"
            echo "  $0 -c                        # Run with coverage"
            echo "  $0 -k sentry                 # Run tests matching 'sentry'"
            echo "  $0 -t test_error_handler.py  # Run specific test file"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest tests/"

if [ -n "$SPECIFIC_TEST" ]; then
    PYTEST_CMD="pytest tests/$SPECIFIC_TEST"
fi

if [ -n "$VERBOSE" ]; then
    PYTEST_CMD="$PYTEST_CMD $VERBOSE"
fi

if [ -n "$COVERAGE" ]; then
    # Check if pytest-cov is installed
    if ! python -c "import pytest_cov" &> /dev/null; then
        echo -e "${YELLOW}Warning: pytest-cov is not installed${NC}"
        echo -e "${YELLOW}Install it with: pip install pytest-cov${NC}"
        echo ""
    else
        PYTEST_CMD="$PYTEST_CMD $COVERAGE"
    fi
fi

if [ -n "$PATTERN" ]; then
    PYTEST_CMD="$PYTEST_CMD $PATTERN"
fi

# Run tests
echo -e "${BLUE}Running command:${NC} $PYTEST_CMD"
echo ""

if $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✓ All tests passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # If HTML coverage was generated, show instructions
    if [[ $COVERAGE == *"html"* ]]; then
        echo ""
        echo -e "${YELLOW}HTML coverage report generated in: htmlcov/index.html${NC}"
        echo -e "${YELLOW}View it with:${NC}"
        echo "  xdg-open htmlcov/index.html  # Linux"
        echo "  open htmlcov/index.html      # macOS"
    fi
    
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}  ✗ Tests failed!${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
