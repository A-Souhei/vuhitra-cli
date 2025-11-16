# Permission Fix for Mirror Feature

## Problem
The initial implementation of the mirror feature encountered a permission error when trying to create directories:

```
PermissionError: [Errno 13] Permission denied: '/app/WORKSPACE/mirrors/test_docs'
```

## Root Cause
The Docker volume `mirrors:/app/WORKSPACE/mirrors` was mounted with root ownership, but the Flask application runs as the `vuhitra` user, causing permission denied errors when trying to create directories.

## Solution
Implemented a Docker entrypoint script that:
1. Starts the container as root
2. Ensures `/app/WORKSPACE/mirrors` directory exists
3. Changes ownership to `vuhitra:vuhitra`
4. Switches to `vuhitra` user using `gosu`
5. Executes the Flask application

### Files Modified

#### 1. `/services/sandbox/docker-entrypoint.sh` (New File)
```bash
#!/bin/bash
set -e

# Ensure WORKSPACE and mirrors directories exist with proper permissions
mkdir -p /app/WORKSPACE/mirrors

# Fix permissions for mounted volumes if running as root (during startup)
if [ "$(id -u)" = "0" ]; then
    # We're root, so we can change ownership
    chown -R vuhitra:vuhitra /app/WORKSPACE
    # Now switch to vuhitra user and execute the main command
    exec gosu vuhitra "$@"
else
    # Already running as vuhitra, just execute
    exec "$@"
fi
```

#### 2. `/services/sandbox/Dockerfile`

**Added `gosu` package:**
```dockerfile
RUN apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3.12-dev python3-pip curl gosu
```

**Copied entrypoint script:**
```dockerfile
# Copy entrypoint script
COPY ./services/sandbox/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
```

**Set entrypoint:**
```dockerfile
# Set entrypoint
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Start the Flask application
CMD ["python", "main.py"]
```

**Removed `USER vuhitra` directive:**
The container now starts as root and the entrypoint script switches to `vuhitra` after fixing permissions.

## Verification

### 1. Check Directory Permissions
```bash
docker exec vuhitra-sandbox ls -la /app/WORKSPACE/
```

Expected output:
```
drwxr-xr-x 3 vuhitra vuhitra 4096 Nov 16 07:46 .
drwxr-xr-x 1 vuhitra vuhitra 4096 Nov 16 08:06 ..
drwxr-xr-x 7 vuhitra vuhitra 4096 Nov 16 08:08 mirrors
```

### 2. Check Process Owner
```bash
docker exec vuhitra-sandbox ps aux | grep python
```

Expected output:
```
vuhitra        1  4.4  4.2 2166248 1389612 ?     Ssl  08:07   0:03 python main.py
```

### 3. Test File Upload
```bash
curl -X POST http://localhost:18001/sync \
  -F "target_name=test" \
  -F "files=@/path/to/file.txt;filename=file.txt"
```

Expected: Success without permission errors.

## Why This Approach?

### Alternative Approaches Considered

1. **Run as root permanently** ❌
   - Security risk
   - Not recommended for production

2. **Pre-create volume with correct permissions** ❌
   - Doesn't work well with Docker volumes
   - Requires manual intervention

3. **Use volume driver options** ❌
   - Limited support across platforms
   - Complex configuration

4. **Entrypoint script with gosu** ✅
   - Industry standard approach
   - Used by official Docker images (postgres, mysql, etc.)
   - Secure: runs as non-root after fixing permissions
   - Portable across platforms

### How gosu Works

`gosu` is a lightweight alternative to `su` and `sudo` designed for use in Docker containers:

- Properly handles signals
- Doesn't create additional processes
- Simpler than `su-exec` or `sudo`
- Standard in Debian/Ubuntu repositories

```bash
# Before gosu (runs as root)
USER         PID COMMAND
root           1 /bin/bash entrypoint.sh
vuhitra       15 python main.py    # Subprocess

# With gosu (runs as vuhitra from PID 1)
USER         PID COMMAND
vuhitra        1 python main.py    # Direct execution
```

## Security Considerations

1. **Container starts as root**: Only briefly, to fix permissions
2. **Application runs as vuhitra**: Non-privileged user
3. **Volume permissions fixed on startup**: Ensures consistency
4. **No SUID binaries**: gosu is safe for container use

## Rebuild Instructions

After making these changes, rebuild and restart:

```bash
cd /home/toavina/Apps/vuhitra-cli/services
docker compose --profile app build sandbox
docker compose --profile app up -d sandbox
```

## Testing

Run the permission test:

```bash
curl -X POST http://localhost:18001/sync \
  -F "target_name=permission_test" \
  -F "files=@/path/to/file.txt;filename=file.txt"
```

Should return:
```json
{
  "deleted": [],
  "message": "Synced 1 file(s), deleted 0 orphaned file(s)",
  "synced": ["file.txt"],
  "target_name": "permission_test"
}
```

## Troubleshooting

### Permission still denied
```bash
# Check if entrypoint is being used
docker inspect vuhitra-sandbox | jq '.[0].Config.Entrypoint'

# Should show:
[
  "/usr/local/bin/docker-entrypoint.sh"
]

# If not, rebuild the image
docker compose --profile app build --no-cache sandbox
```

### gosu not found
```bash
# Check if gosu is installed
docker exec vuhitra-sandbox which gosu

# Should show:
/usr/bin/gosu
```

### Process running as root
```bash
# Check process user
docker exec vuhitra-sandbox ps aux | head -2

# If running as root, check entrypoint script execution
docker logs vuhitra-sandbox | head -20
```

## Status

✅ **Fixed** - Permission error resolved
✅ **Tested** - All mirror operations work correctly
✅ **Secure** - Application runs as non-root user
✅ **Production Ready** - Using industry-standard approach
