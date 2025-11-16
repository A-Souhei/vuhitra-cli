#!/bin/bash
# Quick Reference: Mirror Feature Testing Commands
# Save this for quick copy-paste testing

# ============================================
# BASIC OPERATIONS
# ============================================

# 1. Sync files to sandbox
curl -X POST http://localhost:18001/sync \
  -F "target_name=my_mirror" \
  -F "files=@/path/to/file.txt;filename=file.txt"

# 2. Check if mirror exists
curl http://localhost:18001/mirror-exists/my_mirror | jq .

# 3. Get mirror info
curl -X POST http://localhost:18001/revert-sync \
  -H "Content-Type: application/json" \
  -d '{"target_name": "my_mirror"}' | jq .

# 4. Download entire mirror
curl http://localhost:18001/download-mirror/my_mirror -o mirror.zip

# 5. Download specific file
curl "http://localhost:18001/download-mirror/my_mirror?file_path=file.txt" -o file.txt

# ============================================
# DOCKER EXEC COMMANDS
# ============================================

# View all mirrors
docker exec vuhitra-sandbox find /app/WORKSPACE/mirrors -type f

# View specific mirror
docker exec vuhitra-sandbox ls -la /app/WORKSPACE/mirrors/my_mirror

# Read file
docker exec vuhitra-sandbox cat /app/WORKSPACE/mirrors/my_mirror/file.txt

# Create file in sandbox
docker exec vuhitra-sandbox sh -c "echo 'content' > /app/WORKSPACE/mirrors/my_mirror/new.txt"

# Update file in sandbox
docker exec vuhitra-sandbox sh -c "echo 'updated' > /app/WORKSPACE/mirrors/my_mirror/existing.txt"

# ============================================
# WITH SUBFOLDERS
# ============================================

# Sync with subfolder structure
curl -X POST http://localhost:18001/sync \
  -F "target_name=my_mirror" \
  -F "files=@/path/to/file.txt;filename=file.txt" \
  -F "files=@/path/to/docs/api.md;filename=docs/api.md"

# Read file in subfolder
docker exec vuhitra-sandbox cat /app/WORKSPACE/mirrors/my_mirror/docs/api.md

# ============================================
# TEST WITH DATA FOLDER
# ============================================

# Sync data/docs to sandbox
curl -X POST http://localhost:18001/sync \
  -F "target_name=test_docs" \
  -F "files=@/home/toavina/Apps/vuhitra-cli/data/docs/api.md;filename=api.md" \
  -F "files=@/home/toavina/Apps/vuhitra-cli/data/docs/coding_standards.md;filename=coding_standards.md" \
  -F "files=@/home/toavina/Apps/vuhitra-cli/data/docs/configuration.md;filename=configuration.md"

# Verify
docker exec vuhitra-sandbox find /app/WORKSPACE/mirrors/test_docs -type f

# ============================================
# COMPREHENSIVE TEST SCRIPT
# ============================================

# Run full bidirectional sync test
bash /home/toavina/Apps/vuhitra-cli/scripts/test_mirror_bidirectional_sync.sh

# ============================================
# TROUBLESHOOTING
# ============================================

# Fix permissions
docker exec -u root vuhitra-sandbox chown -R vuhitra:vuhitra /app/WORKSPACE

# Rebuild sandbox (if endpoints missing)
cd /home/toavina/Apps/vuhitra-cli/services
docker compose --profile app build sandbox
docker compose --profile app up -d sandbox

# Check sandbox logs
docker logs vuhitra-sandbox --tail 50

# Check if route exists
docker exec vuhitra-sandbox grep -n "@app.route('/sync'" /app/main.py
