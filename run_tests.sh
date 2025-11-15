#!/bin/bash
#
# Test runner script for CI/CD - runs only non-container tests
# This script excludes tests that require Docker containers to be running,
# reducing GitHub Actions consumption.
#
# Usage:
#   ./run_tests.sh                    # Run all non-container tests
#   ./run_tests.sh --with-containers  # Run all tests including container tests
#   ./run_tests.sh --coverage         # Run with coverage report
#

set -e  # Exit on error

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
WITH_CONTAINERS=false
WITH_COVERAGE=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-containers)
            WITH_CONTAINERS=true
            shift
            ;;
        --coverage)
            WITH_COVERAGE=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--with-containers] [--coverage] [--verbose]"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== Vuhitra CLI Test Runner ===${NC}"
echo ""

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Please install with: pip install pytest pytest-cov"
    exit 1
fi

# Determine which tests to run
if [ "$WITH_CONTAINERS" = true ]; then
    echo -e "${YELLOW}Running ALL tests (including container tests)${NC}"
    IGNORE_OPTS=""
    TEST_PATTERN="tests/"
else
    echo -e "${YELLOW}Running NON-CONTAINER tests only${NC}"
    echo "  - Excluding: test_sandbox_endpoints.py (requires sandbox container)"
    echo "  - Excluding: test_sandbox_redis.py (requires Redis container)"
    echo "  - Excluding: test_heuristics_endpoints.py (Flask integration tests)"
    echo "  - Excluding: test_heuristics_retriever_old.py (old implementation)"
    echo "  - Including: test_sandbox_endpoints_mocked.py (mocked version)"
    echo "  - Including: test_sandbox_redis_mocked.py (mocked version)"
    echo "  - Including: test_heuristics_retriever_embeddings.py (new embedding tests)"
    IGNORE_OPTS="--ignore=tests/test_sandbox_endpoints.py --ignore=tests/test_sandbox_redis.py --ignore=tests/test_heuristics_endpoints.py --ignore=tests/test_heuristics_retriever_old.py"
    TEST_PATTERN="tests/"
fi

echo ""

# Build pytest command
PYTEST_CMD="pytest"

# Add ignore options
if [ -n "$IGNORE_OPTS" ]; then
    PYTEST_CMD="$PYTEST_CMD $IGNORE_OPTS"
fi

# Add verbosity
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
else
    PYTEST_CMD="$PYTEST_CMD -q"
fi

# Add coverage options
if [ "$WITH_COVERAGE" = true ]; then
    echo -e "${YELLOW}Generating coverage report${NC}"
    PYTEST_CMD="$PYTEST_CMD --cov=src --cov=services/sandbox/src --cov-report=term-missing --cov-report=html"
fi

# Add test pattern
PYTEST_CMD="$PYTEST_CMD $TEST_PATTERN"

# Show command
echo -e "${GREEN}Running:${NC} $PYTEST_CMD"
echo ""

# Run tests
if eval $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}✓ All tests passed!${NC}"

    if [ "$WITH_COVERAGE" = true ]; then
        echo ""
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
    fi

    exit 0
else
    echo ""
    echo -e "${RED}✗ Tests failed!${NC}"
    exit 1
fi
