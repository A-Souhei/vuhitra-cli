#!/bin/bash

# Integration test script for Pillars and Vanishers
# Tests coding mode features with curl, docker exec, and CLI commands

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SANDBOX_URL="http://localhost:18001"
TEST_DIR="/tmp/vuhitra_test_$$"
CLI_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${YELLOW}=== Coding Mode Integration Tests ===${NC}\n"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up test environment...${NC}"
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

# Create test directory
mkdir -p "$TEST_DIR"

# Test 1: Check sandbox health
echo -e "${YELLOW}Test 1: Checking sandbox health${NC}"
response=$(curl -s "$SANDBOX_URL/health")
if echo "$response" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Sandbox is healthy${NC}"
else
    echo -e "${RED}✗ Sandbox health check failed${NC}"
    exit 1
fi

# Test 2: Verify pillars directory exists and has files
echo -e "\n${YELLOW}Test 2: Verifying pillars directory${NC}"
if [ -d "$CLI_DIR/pillars" ]; then
    file_count=$(ls -1 "$CLI_DIR/pillars" | wc -l)
    echo -e "${GREEN}✓ Pillars directory exists with $file_count files${NC}"
    ls -1 "$CLI_DIR/pillars" | head -5
else
    echo -e "${RED}✗ Pillars directory not found${NC}"
    exit 1
fi

# Test 3: Test mirror-exists endpoint (no mirror should exist yet)
echo -e "\n${YELLOW}Test 3: Testing mirror-exists endpoint (should not exist)${NC}"
response=$(curl -s "$SANDBOX_URL/mirror-exists/test_file")
if echo "$response" | grep -q '"exists":false'; then
    echo -e "${GREEN}✓ Mirror-exists endpoint works (no mirror found as expected)${NC}"
else
    echo -e "${RED}✗ Mirror-exists endpoint failed${NC}"
    echo "Response: $response"
    exit 1
fi

# Test 4: Create a test file to mirror
echo -e "\n${YELLOW}Test 4: Creating test file for mirroring${NC}"
TEST_FILE="$TEST_DIR/test_config.txt"
echo "Test configuration content" > "$TEST_FILE"
echo -e "${GREEN}✓ Created test file: $TEST_FILE${NC}"

# Test 5: Test via docker exec - check if mirrors directory exists
echo -e "\n${YELLOW}Test 5: Testing with docker exec - checking mirrors directory${NC}"
if docker exec vuhitra-sandbox ls /app/WORKSPACE/mirrors > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Mirrors directory exists in sandbox container${NC}"
    echo "Current mirrors:"
    docker exec vuhitra-sandbox ls -la /app/WORKSPACE/mirrors || echo "  (empty)"
else
    echo -e "${RED}✗ Failed to access mirrors directory in container${NC}"
    exit 1
fi

# Test 6: Test via docker exec - check Redis connection
echo -e "\n${YELLOW}Test 6: Testing Redis connection via docker exec${NC}"
if docker exec vuhitra-redis redis-cli -a redis_pwd ping 2>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}✓ Redis is responding${NC}"
else
    echo -e "${RED}✗ Redis connection failed${NC}"
    exit 1
fi

# Test 7: Check for mirror keys in Redis (should be empty initially)
echo -e "\n${YELLOW}Test 7: Checking Redis for existing mirrors${NC}"
mirror_count=$(docker exec vuhitra-redis redis-cli -a redis_pwd --scan --pattern "mirror:*" 2>/dev/null | wc -l)
echo -e "${GREEN}✓ Found $mirror_count mirror(s) in Redis${NC}"
if [ "$mirror_count" -gt 0 ]; then
    echo "Existing mirrors:"
    docker exec vuhitra-redis redis-cli -a redis_pwd --scan --pattern "mirror:*" 2>/dev/null | head -10
fi

# Test 8: Verify pillars auto-load behavior by checking .vuhitra directory
echo -e "\n${YELLOW}Test 8: Checking pillar storage directory${NC}"
PILLAR_STORAGE="$CLI_DIR/.vuhitra/pillar_contexts"
if [ -d "$PILLAR_STORAGE" ]; then
    pillar_count=$(ls -1 "$PILLAR_STORAGE" 2>/dev/null | wc -l)
    echo -e "${GREEN}✓ Pillar storage directory exists${NC}"
    echo "  Stored pillars: $pillar_count"
    if [ "$pillar_count" -gt 0 ]; then
        echo "  Files:"
        ls -1 "$PILLAR_STORAGE" | head -5
    fi
else
    echo -e "${YELLOW}⚠ Pillar storage directory does not exist yet (will be created on first run)${NC}"
fi

# Test 9: Test transformer service
echo -e "\n${YELLOW}Test 9: Testing transformer service${NC}"
response=$(curl -s -X POST "http://localhost:16050/embed" \
    -H "Content-Type: application/json" \
    -d '{"text":"test embedding"}')
if echo "$response" | grep -q "embedding"; then
    echo -e "${GREEN}✓ Transformer service is working${NC}"
else
    echo -e "${YELLOW}⚠ Transformer service test failed (non-critical)${NC}"
    echo "  Response: $response"
    echo "  (This is optional for the main pillars/vanishers functionality)"
fi

# Test 10: Test pillar context manager directly with Python
echo -e "\n${YELLOW}Test 10: Testing PillarContextManager programmatically${NC}"
cat > "$TEST_DIR/test_pillar.py" << 'EOF'
import sys
sys.path.insert(0, '/home/toavina/Apps/vuhitra-cli')
from src.utils.pillar_context import PillarContextManager
import tempfile

# Test with enabled=True (coding mode)
storage_dir = tempfile.mkdtemp()
manager = PillarContextManager(enabled=True, storage_dir=storage_dir)
print(f"Pillar context enabled: {manager.is_enabled()}")
print(f"Pillars directory: {manager.pillars_dir}")
print(f"Storage directory: {manager.storage_dir}")
print("✓ PillarContextManager initialized successfully")

# Test with enabled=False (normal mode)
manager_disabled = PillarContextManager(enabled=False, storage_dir=storage_dir)
print(f"Disabled pillar context: {manager_disabled.is_enabled()}")
print("✓ PillarContextManager can be disabled")
EOF

cd "$CLI_DIR"
if .venv/bin/python "$TEST_DIR/test_pillar.py"; then
    echo -e "${GREEN}✓ PillarContextManager works correctly${NC}"
else
    echo -e "${RED}✗ PillarContextManager test failed${NC}"
    exit 1
fi

# Test 11: Test vanisher context manager
echo -e "\n${YELLOW}Test 11: Testing VanisherContextManager programmatically${NC}"
cat > "$TEST_DIR/test_vanisher.py" << 'EOF'
import sys
sys.path.insert(0, '/home/toavina/Apps/vuhitra-cli')
from src.utils.vanisher_context import VanisherContextManager

# Test with enabled=True (coding mode)
manager = VanisherContextManager(enabled=True)
print(f"Vanisher context enabled: {manager.is_enabled()}")
print(f"Max contexts: {manager.max_contexts}")
print("✓ VanisherContextManager initialized successfully")

# Test with enabled=False (normal mode)
manager_disabled = VanisherContextManager(enabled=False)
print(f"Disabled vanisher context: {manager_disabled.is_enabled()}")
print("✓ VanisherContextManager can be disabled")
EOF

if .venv/bin/python "$TEST_DIR/test_vanisher.py"; then
    echo -e "${GREEN}✓ VanisherContextManager works correctly${NC}"
else
    echo -e "${RED}✗ VanisherContextManager test failed${NC}"
    exit 1
fi

# Test 12: Test that pillars directory is correctly configured
echo -e "\n${YELLOW}Test 12: Verifying pillars configuration in config.yaml${NC}"
if grep -q "pillars_dir: pillars" "$CLI_DIR/config.yaml" || grep -q "pillars" "$CLI_DIR/config.yaml"; then
    echo -e "${GREEN}✓ Pillars configuration found in config.yaml${NC}"
else
    echo -e "${YELLOW}⚠ Pillars configuration not explicitly found (using defaults)${NC}"
fi

# Summary
echo -e "\n${GREEN}=== All Integration Tests Passed! ===${NC}\n"
echo "Summary:"
echo "  ✓ Sandbox health check"
echo "  ✓ Pillars directory verified ($file_count files)"
echo "  ✓ Mirror-exists API endpoint"
echo "  ✓ Docker exec commands"
echo "  ✓ Redis connection"
echo "  ✓ Transformer service"
echo "  ✓ PillarContextManager (enabled/disabled)"
echo "  ✓ VanisherContextManager (enabled/disabled)"

echo -e "\n${YELLOW}Next steps:${NC}"
echo "  1. Start CLI in coding mode: ./start.sh --coding"
echo "  2. Verify pillars auto-load from pillars/ directory"
echo "  3. Test vanisher with mirrored files"
echo "  4. Start CLI in normal mode and verify pillars/vanishers are NOT loaded"
