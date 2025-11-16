# Mirror Feature Testing Guide

This document provides comprehensive testing instructions for the Mirror feature, which allows bidirectional file synchronization between the host and the sandbox container.

## Overview

The Mirror feature provides the following capabilities:

1. **Sync files from host to sandbox** - Upload and synchronize files to a mirror in the sandbox
2. **Track changes** - Automatic detection and cleanup of orphaned files
3. **Download from sandbox** - Retrieve individual files or entire mirrors as zip archives
4. **Bidirectional sync** - Files can be updated in either direction (host→sandbox, sandbox→host)
5. **Subfolder support** - Preserves directory structures

## API Endpoints

### 1. `/sync` - Sync Files to Mirror (POST)

Synchronizes files from host to sandbox mirror. Updates existing files, adds new ones, and deletes orphaned files.

**Request:**
```bash
curl -X POST http://localhost:18001/sync \
  -F "target_name=my_mirror" \
  -F "files=@/path/to/file1.txt;filename=file1.txt" \
  -F "files=@/path/to/subdir/file2.txt;filename=subdir/file2.txt"
```

**Response:**
```json
{
  "message": "Synced 2 file(s), deleted 0 orphaned file(s)",
  "target_name": "my_mirror",
  "synced": ["file1.txt", "subdir/file2.txt"],
  "deleted": []
}
```

### 2. `/mirror-exists/<target_name>` - Check Mirror Existence (GET)

Checks if a mirror exists in the sandbox.

**Request:**
```bash
curl http://localhost:18001/mirror-exists/my_mirror
```

**Response:**
```json
{
  "exists": true,
  "target_name": "my_mirror",
  "is_file": false,
  "file_count": 2
}
```

### 3. `/revert-sync` - Get Mirror Information (POST)

Retrieves detailed information about files in a mirror.

**Request:**
```bash
curl -X POST http://localhost:18001/revert-sync \
  -H "Content-Type: application/json" \
  -d '{"target_name": "my_mirror"}'
```

**Response:**
```json
{
  "message": "Mirror contents retrieved successfully",
  "target_name": "my_mirror",
  "file_count": 2,
  "files": [
    {
      "name": "file1.txt",
      "size": 1024,
      "modified": 1763279233.985,
      "is_file": true
    }
  ],
  "mirror_path": "/app/WORKSPACE/mirrors/my_mirror"
}
```

### 4. `/download-mirror/<target_name>` - Download Mirror (GET)

Downloads files from a mirror. Returns single files directly or directories as zip archives.

**Download entire mirror:**
```bash
curl http://localhost:18001/download-mirror/my_mirror -o my_mirror.zip
```

**Download specific file:**
```bash
curl "http://localhost:18001/download-mirror/my_mirror?file_path=subdir/file2.txt" -o file2.txt
```

### 5. `/mirror-synced` - Check Sync Status (POST)

Checks if host files are synchronized with the sandbox mirror.

**Request:**
```bash
curl -X POST http://localhost:18001/mirror-synced \
  -H "Content-Type: application/json" \
  -d '{
    "target_name": "my_mirror",
    "files": [
      {"name": "file1.txt", "size": 1024, "modified": 1763279233.985}
    ]
  }'
```

**Response:**
```json
{
  "synced": true,
  "target_name": "my_mirror"
}
```

Or if not synced:
```json
{
  "synced": false,
  "target_name": "my_mirror",
  "differences": {
    "only_in_host": ["new_file.txt"],
    "only_in_mirror": ["old_file.txt"],
    "different_size": [],
    "different_modified": []
  }
}
```

## Testing Scenarios

### Automated Testing

Run the comprehensive bidirectional sync test:

```bash
cd /home/toavina/Apps/vuhitra-cli
bash scripts/test_mirror_bidirectional_sync.sh
```

This script tests:
- ✅ Initial sync from host to sandbox
- ✅ File updates on host syncing to sandbox
- ✅ Adding new files on host
- ✅ Updating files directly in sandbox
- ✅ Creating new files in sandbox
- ✅ Retrieving mirror information
- ✅ Downloading entire mirror as zip
- ✅ Orphan file cleanup
- ✅ Sync status checking
- ✅ Subfolder structure preservation

### Manual Testing

#### Test 1: Host → Sandbox Sync

```bash
# Create test files
mkdir -p /tmp/test_mirror
echo "Content from host" > /tmp/test_mirror/test.txt

# Sync to sandbox
curl -X POST http://localhost:18001/sync \
  -F "target_name=manual_test" \
  -F "files=@/tmp/test_mirror/test.txt;filename=test.txt"

# Verify in sandbox
docker exec vuhitra-sandbox cat /app/WORKSPACE/mirrors/manual_test/test.txt
```

#### Test 2: Sandbox → Host Download

```bash
# Update file in sandbox
docker exec vuhitra-sandbox sh -c "echo 'Updated in sandbox' > /app/WORKSPACE/mirrors/manual_test/test.txt"

# Download from sandbox
curl "http://localhost:18001/download-mirror/manual_test?file_path=test.txt" -o /tmp/downloaded.txt

# Verify content
cat /tmp/downloaded.txt
```

#### Test 3: Subfolder Structure

```bash
# Create nested structure
mkdir -p /tmp/test_mirror/subdir
echo "Nested content" > /tmp/test_mirror/subdir/nested.txt

# Sync with path preservation
curl -X POST http://localhost:18001/sync \
  -F "target_name=nested_test" \
  -F "files=@/tmp/test_mirror/subdir/nested.txt;filename=subdir/nested.txt"

# Verify structure in sandbox
docker exec vuhitra-sandbox find /app/WORKSPACE/mirrors/nested_test -type f
docker exec vuhitra-sandbox cat /app/WORKSPACE/mirrors/nested_test/subdir/nested.txt
```

#### Test 4: Orphan Cleanup

```bash
# Initial sync with 2 files
echo "File 1" > /tmp/test_mirror/file1.txt
echo "File 2" > /tmp/test_mirror/file2.txt

curl -X POST http://localhost:18001/sync \
  -F "target_name=cleanup_test" \
  -F "files=@/tmp/test_mirror/file1.txt;filename=file1.txt" \
  -F "files=@/tmp/test_mirror/file2.txt;filename=file2.txt"

# Re-sync with only file1 (file2 should be deleted)
curl -X POST http://localhost:18001/sync \
  -F "target_name=cleanup_test" \
  -F "files=@/tmp/test_mirror/file1.txt;filename=file1.txt"

# Verify file2 was deleted
docker exec vuhitra-sandbox find /app/WORKSPACE/mirrors/cleanup_test -type f
```

## Docker Exec Commands

### View All Mirrors

```bash
docker exec vuhitra-sandbox find /app/WORKSPACE/mirrors -type f
```

### View Specific Mirror Contents

```bash
docker exec vuhitra-sandbox ls -la /app/WORKSPACE/mirrors/my_mirror
```

### Read File in Sandbox

```bash
docker exec vuhitra-sandbox cat /app/WORKSPACE/mirrors/my_mirror/file.txt
```

### Create File in Sandbox

```bash
docker exec vuhitra-sandbox sh -c "echo 'Created in sandbox' > /app/WORKSPACE/mirrors/my_mirror/new_file.txt"
```

### Update File in Sandbox

```bash
docker exec vuhitra-sandbox sh -c "echo 'Updated content' > /app/WORKSPACE/mirrors/my_mirror/existing_file.txt"
```

### Check File Permissions

```bash
docker exec vuhitra-sandbox ls -l /app/WORKSPACE/mirrors/my_mirror/
```

## Common Issues and Solutions

### Issue 1: Permission Denied

**Error:** `PermissionError: [Errno 13] Permission denied`

**Solution:**
```bash
docker exec -u root vuhitra-sandbox chown -R vuhitra:vuhitra /app/WORKSPACE
```

### Issue 2: Subfolder Structure Not Preserved

**Problem:** Files uploaded without path information end up flat in the mirror.

**Solution:** Use the `;filename=` syntax in curl:
```bash
-F "files=@/local/path/file.txt;filename=desired/path/file.txt"
```

### Issue 3: Route Not Found

**Error:** `404 Not Found: The requested URL was not found`

**Solution:** Rebuild and restart the sandbox container:
```bash
cd /home/toavina/Apps/vuhitra-cli/services
docker compose --profile app build sandbox
docker compose --profile app up -d sandbox
```

## Integration with vuhitra-cli

The mirror feature integrates with the main CLI through the `mirror` command:

```bash
# Sync local directory to sandbox
vuhitra mirror sync /path/to/local/dir --name my_mirror

# Download from sandbox
vuhitra mirror download my_mirror --output /path/to/output

# Check sync status
vuhitra mirror status my_mirror --local /path/to/local/dir
```

See [mirror-command.md](./mirror-command.md) for full CLI documentation.

## Testing Checklist

- [ ] Files sync from host to sandbox
- [ ] File updates on host reflect in sandbox
- [ ] New files on host are added to sandbox
- [ ] Files can be updated directly in sandbox
- [ ] New files can be created in sandbox
- [ ] Mirror information can be retrieved
- [ ] Individual files can be downloaded
- [ ] Entire mirror can be downloaded as zip
- [ ] Orphaned files are cleaned up
- [ ] Sync status detection works correctly
- [ ] Subfolder structures are preserved
- [ ] Error handling works properly
- [ ] Permission issues are resolved

## Performance Considerations

- **Large files:** The sync endpoint handles multipart uploads efficiently
- **Many files:** Consider batching syncs or using zip download for retrieval
- **Subdirectories:** Deep nesting is supported but may impact upload time
- **Concurrent access:** Multiple mirrors can exist simultaneously

## Security Notes

- All target names are sanitized using `secure_filename()`
- Paths are validated to prevent directory traversal
- Mirror operations are confined to `/app/WORKSPACE/mirrors/`
- File permissions are managed by the sandbox user

## Future Enhancements

- [ ] Incremental sync (only changed files)
- [ ] Compression for large file transfers
- [ ] Async upload for better performance
- [ ] Mirror versioning/snapshots
- [ ] Conflict resolution strategies
- [ ] Watch mode for auto-sync
