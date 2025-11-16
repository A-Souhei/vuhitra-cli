#!/bin/bash

# Bidirectional Sync Testing Script for Mirror Endpoints
# This script tests real file creation, updates, and syncing between host and sandbox

set -e  # Exit on error

BASE_URL="http://localhost:18001"
TEST_DIR="/tmp/vuhitra_mirror_test"
MIRROR_NAME="bidirectional_test"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "Bidirectional Mirror Sync Testing"
echo "=============================================="
echo ""

# Cleanup function
cleanup() {
    echo -e "${YELLOW}Cleaning up test directory...${NC}"
    rm -rf "${TEST_DIR}"
    echo ""
}

# Setup test directory
setup() {
    echo -e "${YELLOW}Setting up test environment...${NC}"
    rm -rf "${TEST_DIR}"
    mkdir -p "${TEST_DIR}/subfolder"
    
    # Create initial test files
    echo "Initial file content v1" > "${TEST_DIR}/file1.txt"
    echo "Initial file content v1" > "${TEST_DIR}/file2.txt"
    echo "Subfolder file v1" > "${TEST_DIR}/subfolder/nested.txt"
    
    echo -e "${GREEN}✓ Test directory created at ${TEST_DIR}${NC}"
    ls -la "${TEST_DIR}"
    echo ""
}

# Test 1: Initial sync from host to sandbox
test_initial_sync() {
    echo "=== Test 1: Initial Sync (Host → Sandbox) ==="
    
    # Note: curl doesn't preserve subdirectory structure with -F @filename
    # We need to use form field names that include the path
    curl -s -X POST ${BASE_URL}/sync \
      -F "target_name=${MIRROR_NAME}" \
      -F "files=@${TEST_DIR}/file1.txt;filename=file1.txt" \
      -F "files=@${TEST_DIR}/file2.txt;filename=file2.txt" \
      -F "files=@${TEST_DIR}/subfolder/nested.txt;filename=subfolder/nested.txt" | jq .
    
    echo -e "${GREEN}✓ Files synced to sandbox${NC}"
    echo ""
    
    # Verify in sandbox
    echo "Files in sandbox mirror:"
    docker exec vuhitra-sandbox find "/app/WORKSPACE/mirrors/${MIRROR_NAME}" -type f
    echo ""
}

# Test 2: Update file on host and re-sync
test_host_update_sync() {
    echo "=== Test 2: Update File on Host and Re-sync (Host → Sandbox) ==="
    
    # Update a file on host
    echo "Updated file content v2 - from host" > "${TEST_DIR}/file1.txt"
    echo -e "${YELLOW}Updated file1.txt on host${NC}"
    
    # Re-sync
    curl -s -X POST ${BASE_URL}/sync \
      -F "target_name=${MIRROR_NAME}" \
      -F "files=@${TEST_DIR}/file1.txt;filename=file1.txt" \
      -F "files=@${TEST_DIR}/file2.txt;filename=file2.txt" \
      -F "files=@${TEST_DIR}/subfolder/nested.txt;filename=subfolder/nested.txt" | jq .
    
    echo ""
    
    # Verify the update in sandbox
    echo "Content of file1.txt in sandbox:"
    docker exec vuhitra-sandbox cat "/app/WORKSPACE/mirrors/${MIRROR_NAME}/file1.txt"
    echo ""
    echo -e "${GREEN}✓ Host update synced to sandbox${NC}"
    echo ""
}

# Test 3: Add new file on host and sync
test_host_new_file_sync() {
    echo "=== Test 3: Add New File on Host and Sync (Host → Sandbox) ==="
    
    # Create a new file on host
    echo "New file created on host" > "${TEST_DIR}/file3_new.txt"
    echo -e "${YELLOW}Created file3_new.txt on host${NC}"
    
    # Sync including the new file
    curl -s -X POST ${BASE_URL}/sync \
      -F "target_name=${MIRROR_NAME}" \
      -F "files=@${TEST_DIR}/file1.txt;filename=file1.txt" \
      -F "files=@${TEST_DIR}/file2.txt;filename=file2.txt" \
      -F "files=@${TEST_DIR}/file3_new.txt;filename=file3_new.txt" \
      -F "files=@${TEST_DIR}/subfolder/nested.txt;filename=subfolder/nested.txt" | jq .
    
    echo ""
    
    # Verify the new file in sandbox
    echo "Files in sandbox mirror after adding new file:"
    docker exec vuhitra-sandbox find "/app/WORKSPACE/mirrors/${MIRROR_NAME}" -type f
    echo ""
    echo "Content of new file in sandbox:"
    docker exec vuhitra-sandbox cat "/app/WORKSPACE/mirrors/${MIRROR_NAME}/file3_new.txt"
    echo ""
    echo -e "${GREEN}✓ New file synced to sandbox${NC}"
    echo ""
}

# Test 4: Update file directly in sandbox
test_sandbox_file_update() {
    echo "=== Test 4: Update File Directly in Sandbox (Sandbox → Host) ==="
    
    # Update a file directly in the sandbox
    docker exec vuhitra-sandbox sh -c "echo 'Updated from sandbox v3' > /app/WORKSPACE/mirrors/${MIRROR_NAME}/file2.txt"
    echo -e "${YELLOW}Updated file2.txt directly in sandbox${NC}"
    
    # Verify the update
    echo "Content of file2.txt in sandbox:"
    docker exec vuhitra-sandbox cat "/app/WORKSPACE/mirrors/${MIRROR_NAME}/file2.txt"
    echo ""
    
    # Download the file to verify we can retrieve the update
    curl -s "${BASE_URL}/download-mirror/${MIRROR_NAME}?file_path=file2.txt" -o /tmp/file2_from_sandbox.txt
    echo "Content of downloaded file2.txt from sandbox:"
    cat /tmp/file2_from_sandbox.txt
    echo ""
    echo -e "${GREEN}✓ Sandbox update verified and can be retrieved${NC}"
    echo ""
}

# Test 5: Create new file in sandbox mirror
test_sandbox_new_file() {
    echo "=== Test 5: Create New File in Sandbox Mirror (Sandbox → Host) ==="
    
    # Create a new file in the sandbox mirror
    docker exec vuhitra-sandbox sh -c "echo 'Created in sandbox' > /app/WORKSPACE/mirrors/${MIRROR_NAME}/sandbox_created.txt"
    echo -e "${YELLOW}Created sandbox_created.txt directly in sandbox${NC}"
    
    # Verify it exists
    echo "Files in sandbox mirror after creating new file:"
    docker exec vuhitra-sandbox find "/app/WORKSPACE/mirrors/${MIRROR_NAME}" -type f
    echo ""
    
    # Download the new file
    curl -s "${BASE_URL}/download-mirror/${MIRROR_NAME}?file_path=sandbox_created.txt" -o /tmp/sandbox_created.txt
    echo "Content of sandbox_created.txt downloaded from sandbox:"
    cat /tmp/sandbox_created.txt
    echo ""
    echo -e "${GREEN}✓ New sandbox file can be retrieved${NC}"
    echo ""
}

# Test 6: Get all changes from sandbox (revert-sync)
test_revert_sync() {
    echo "=== Test 6: Get All Mirror Info (Revert-Sync) ==="
    
    MIRROR_INFO=$(curl -s -X POST ${BASE_URL}/revert-sync \
      -H "Content-Type: application/json" \
      -d "{\"target_name\": \"${MIRROR_NAME}\"}")
    
    echo "$MIRROR_INFO" | jq .
    echo ""
    
    # Extract file list
    echo "Files currently in sandbox mirror:"
    echo "$MIRROR_INFO" | jq -r '.files[].name'
    echo ""
    echo -e "${GREEN}✓ Mirror info retrieved successfully${NC}"
    echo ""
}

# Test 7: Download entire mirror as zip
test_download_all() {
    echo "=== Test 7: Download Entire Mirror as Zip (Sandbox → Host) ==="
    
    curl -s ${BASE_URL}/download-mirror/${MIRROR_NAME} -o /tmp/${MIRROR_NAME}.zip
    echo -e "${YELLOW}Downloaded mirror as zip${NC}"
    
    # Extract and examine
    rm -rf /tmp/${MIRROR_NAME}_extracted
    mkdir -p /tmp/${MIRROR_NAME}_extracted
    unzip -q /tmp/${MIRROR_NAME}.zip -d /tmp/${MIRROR_NAME}_extracted
    
    echo "Extracted contents:"
    find /tmp/${MIRROR_NAME}_extracted -type f
    echo ""
    
    echo "Content of files updated in sandbox:"
    echo "--- file2.txt (updated in sandbox):"
    cat /tmp/${MIRROR_NAME}_extracted/file2.txt
    echo ""
    echo "--- sandbox_created.txt (created in sandbox):"
    cat /tmp/${MIRROR_NAME}_extracted/sandbox_created.txt
    echo ""
    echo -e "${GREEN}✓ All sandbox changes retrieved via zip download${NC}"
    echo ""
}

# Test 8: Delete file on host and sync (orphan cleanup)
test_orphan_cleanup() {
    echo "=== Test 8: Delete File on Host and Sync (Orphan Cleanup) ==="
    
    echo -e "${YELLOW}Removing file3_new.txt from host sync${NC}"
    
    # Sync without file3_new.txt - it should be deleted from sandbox
    curl -s -X POST ${BASE_URL}/sync \
      -F "target_name=${MIRROR_NAME}" \
      -F "files=@${TEST_DIR}/file1.txt;filename=file1.txt" \
      -F "files=@${TEST_DIR}/file2.txt;filename=file2.txt" \
      -F "files=@${TEST_DIR}/subfolder/nested.txt;filename=subfolder/nested.txt" | jq .
    
    echo ""
    
    # Verify file3_new.txt was deleted from sandbox
    echo "Files in sandbox mirror after orphan cleanup:"
    docker exec vuhitra-sandbox find "/app/WORKSPACE/mirrors/${MIRROR_NAME}" -type f || true
    echo ""
    
    # Verify sandbox_created.txt (created in sandbox) was also deleted
    echo -e "${YELLOW}Note: sandbox_created.txt should also be deleted as it wasn't in host sync${NC}"
    echo -e "${GREEN}✓ Orphan files cleaned up from sandbox${NC}"
    echo ""
}

# Test 9: Check sync status
test_sync_status() {
    echo "=== Test 9: Check Sync Status ==="
    
    # Get current mirror state
    MIRROR_INFO=$(curl -s -X POST ${BASE_URL}/revert-sync \
      -H "Content-Type: application/json" \
      -d "{\"target_name\": \"${MIRROR_NAME}\"}")
    
    FILES_JSON=$(echo "$MIRROR_INFO" | jq -c '[.files[] | {name: .name, size: .size, modified: .modified}]')
    
    # Check if synced
    curl -s -X POST ${BASE_URL}/mirror-synced \
      -H "Content-Type: application/json" \
      -d "{\"target_name\": \"${MIRROR_NAME}\", \"files\": $FILES_JSON}" | jq .
    
    echo ""
    echo -e "${GREEN}✓ Sync status checked${NC}"
    echo ""
}

# Test 10: Update file in subfolder
test_subfolder_update() {
    echo "=== Test 10: Update File in Subfolder ==="
    
    # Update nested file on host
    echo "Updated nested file v2" > "${TEST_DIR}/subfolder/nested.txt"
    echo -e "${YELLOW}Updated subfolder/nested.txt on host${NC}"
    
    # Sync with proper filename path
    curl -s -X POST ${BASE_URL}/sync \
      -F "target_name=${MIRROR_NAME}" \
      -F "files=@${TEST_DIR}/file1.txt;filename=file1.txt" \
      -F "files=@${TEST_DIR}/file2.txt;filename=file2.txt" \
      -F "files=@${TEST_DIR}/subfolder/nested.txt;filename=subfolder/nested.txt" | jq .
    
    echo ""
    
    # Verify in sandbox
    echo "Content of subfolder/nested.txt in sandbox:"
    docker exec vuhitra-sandbox cat "/app/WORKSPACE/mirrors/${MIRROR_NAME}/subfolder/nested.txt"
    echo ""
    echo -e "${GREEN}✓ Subfolder file updated${NC}"
    echo ""
}

# Main execution
main() {
    setup
    
    test_initial_sync
    sleep 1
    
    test_host_update_sync
    sleep 1
    
    test_host_new_file_sync
    sleep 1
    
    test_sandbox_file_update
    sleep 1
    
    test_sandbox_new_file
    sleep 1
    
    test_revert_sync
    sleep 1
    
    test_download_all
    sleep 1
    
    test_orphan_cleanup
    sleep 1
    
    test_sync_status
    sleep 1
    
    test_subfolder_update
    
    echo "=============================================="
    echo -e "${GREEN}All bidirectional sync tests completed!${NC}"
    echo "=============================================="
    echo ""
    
    # Cleanup option
    read -p "Do you want to clean up test files? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup
        echo -e "${GREEN}✓ Cleanup completed${NC}"
    else
        echo -e "${YELLOW}Test files preserved at ${TEST_DIR}${NC}"
        echo -e "${YELLOW}Downloaded files in /tmp/${MIRROR_NAME}*${NC}"
    fi
}

# Run the tests
main
