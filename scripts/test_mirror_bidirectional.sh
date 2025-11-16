#!/bin/bash

# Manual Testing Script for Mirror Endpoints
# This script demonstrates all mirror functionality using curl

set -e  # Exit on error

BASE_URL="http://localhost:18001"
DATA_DIR="/home/toavina/Apps/vuhitra-cli/data"

echo "=============================================="
echo "Mirror Endpoints Manual Testing"
echo "=============================================="
echo ""

# Test 1: Sync multiple files to mirror
echo "=== Test 1: Sync multiple files to mirror ==="
curl -s -X POST ${BASE_URL}/sync \
  -F "target_name=test_docs" \
  -F "files=@${DATA_DIR}/docs/api.md" \
  -F "files=@${DATA_DIR}/docs/coding_standards.md" \
  -F "files=@${DATA_DIR}/docs/configuration.md" | jq .
echo ""

# Test 2: Check if mirror exists
echo "=== Test 2: Check if mirror exists ==="
curl -s ${BASE_URL}/mirror-exists/test_docs | jq .
echo ""

# Test 3: Get mirror information
echo "=== Test 3: Get mirror information (revert-sync) ==="
curl -s -X POST ${BASE_URL}/revert-sync \
  -H "Content-Type: application/json" \
  -d '{"target_name": "test_docs"}' | jq .
echo ""

# Test 4: Download entire mirror as zip
echo "=== Test 4: Download entire mirror as zip ==="
curl -s ${BASE_URL}/download-mirror/test_docs -o /tmp/test_docs.zip
echo "Downloaded to /tmp/test_docs.zip"
unzip -l /tmp/test_docs.zip
echo ""

# Test 5: Download specific file from mirror
echo "=== Test 5: Download specific file from mirror ==="
curl -s "${BASE_URL}/download-mirror/test_docs?file_path=api.md" -o /tmp/api.md
echo "Downloaded api.md, first 5 lines:"
head -5 /tmp/api.md
echo ""

# Test 6: Sync single file to mirror
echo "=== Test 6: Sync single file to mirror ==="
curl -s -X POST ${BASE_URL}/sync \
  -F "target_name=single_file_test" \
  -F "files=@${DATA_DIR}/examples/simple.txt" | jq .
echo ""

# Test 7: View mirrors directory structure in container
echo "=== Test 7: View mirrors directory structure in container ==="
docker exec vuhitra-sandbox find /app/WORKSPACE/mirrors -type f
echo ""

# Test 8: Check non-existent mirror
echo "=== Test 8: Check if non-existent mirror exists ==="
curl -s ${BASE_URL}/mirror-exists/non_existent_mirror | jq .
echo ""

# Test 9: Check if files are synced (should be true)
echo "=== Test 9: Check if files are synced (should be true) ==="
MIRROR_INFO=$(curl -s -X POST ${BASE_URL}/revert-sync \
  -H "Content-Type: application/json" \
  -d '{"target_name": "test_docs"}')

FILES_JSON=$(echo "$MIRROR_INFO" | jq -c '[.files[] | {name: .name, size: .size, modified: .modified}]')

curl -s -X POST ${BASE_URL}/mirror-synced \
  -H "Content-Type: application/json" \
  -d "{\"target_name\": \"test_docs\", \"files\": $FILES_JSON}" | jq .
echo ""

# Test 10: Check sync with different files (should be false)
echo "=== Test 10: Check sync with different files (should be false) ==="
curl -s -X POST ${BASE_URL}/mirror-synced \
  -H "Content-Type: application/json" \
  -d '{
    "target_name": "test_docs",
    "files": [
      {"name": "api.md", "size": 1228, "modified": 1763279233.9850733},
      {"name": "different_file.md", "size": 999, "modified": 1763279233.9851363}
    ]
  }' | jq .
echo ""

# Test 11: Update sync (remove a file and add another)
echo "=== Test 11: Update sync (remove a file and add another) ==="
curl -s -X POST ${BASE_URL}/sync \
  -F "target_name=test_docs" \
  -F "files=@${DATA_DIR}/docs/api.md" \
  -F "files=@${DATA_DIR}/docs/coding_standards.md" \
  -F "files=@${DATA_DIR}/README.md" | jq .
echo ""

# Test 12: Verify updated mirror structure
echo "=== Test 12: Verify updated mirror structure ==="
docker exec vuhitra-sandbox find /app/WORKSPACE/mirrors/test_docs -type f
echo ""

# Test 13: Download mirror for single file (direct file download)
echo "=== Test 13: Check single file mirror ==="
curl -s ${BASE_URL}/mirror-exists/single_file_test | jq .
echo ""

# Test 14: Download single file mirror (should return file directly, not zip)
echo "=== Test 14: Download single file mirror ==="
curl -s ${BASE_URL}/download-mirror/single_file_test -o /tmp/simple_downloaded.txt
echo "Downloaded single file:"
cat /tmp/simple_downloaded.txt
echo ""

echo "=============================================="
echo "All tests completed successfully!"
echo "=============================================="
