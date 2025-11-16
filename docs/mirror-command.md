# Mirror Command

The `/mirror` command enables synchronization of files and directories between the host system and the sandbox container's mirrors volume.

## Overview

The mirror feature provides a persistent workspace within the sandbox container at `/app/WORKSPACE/mirrors`, allowing you to:

- Copy files/directories to the sandbox for processing
- Synchronize changes between host and sandbox
- Retrieve modified files from the sandbox back to the host
- Manage persistent data across sandbox sessions

## Docker Volume Configuration

The mirrors functionality uses a dedicated Docker volume:

```yaml
volumes:
  mirrors:
    driver: local
```

This volume is mounted in the sandbox container at `/app/WORKSPACE/mirrors`.

## Commands

The `/mirror` command provides seven subcommands for managing file synchronization between host and sandbox:

1. **do** - Copy files to sandbox
2. **destroy** - Remove mirror from sandbox
3. **sync** - Update sandbox with host changes
4. **revert+sync** - Update host with sandbox changes
5. **exists** - Check if mirror exists
6. **synced** - Check if host and mirror are in sync
7. **list** - List all registered mirrors

### `/mirror do @<path>`

Copy a file or directory to the sandbox mirror.

**Usage:**
```bash
/mirror do @data
/mirror do @config.json
/mirror do @src/models
```

**Behavior:**
- Creates a mirror of the specified file/directory in the sandbox
- If the path is a directory, recursively copies all files
- If a mirror already exists, it will be updated
- Files are stored at `/app/WORKSPACE/mirrors/<name>` in the sandbox

**Example:**
```bash
# Copy the data/ directory to sandbox
/mirror do @data

# Result: Creates /app/WORKSPACE/mirrors/data with all contents
```

### `/mirror destroy @<path>`

Remove a mirror from the sandbox.

**Usage:**
```bash
/mirror destroy @data
/mirror destroy @config.json
```

**Behavior:**
- Deletes the specified mirror from the sandbox
- Does NOT affect the original files on the host
- Returns an error if the mirror doesn't exist

**Example:**
```bash
# Remove the data mirror from sandbox
/mirror destroy @data

# Result: Removes /app/WORKSPACE/mirrors/data from sandbox
```

### `/mirror sync @<path>`

Synchronize changes from host to sandbox mirror.

**Usage:**
```bash
/mirror sync @data
/mirror sync @config.json
```

**Behavior:**
- Updates existing files in the sandbox mirror
- Adds new files that exist on host but not in mirror
- Deletes files from mirror that no longer exist on host
- Maintains directory structure

**Example:**
```bash
# Make changes to host data/ directory:
# - Modify data/file1.txt
# - Add data/file3.txt
# - Delete data/file2.txt

/mirror sync @data

# Result in sandbox mirror:
# - data/file1.txt updated
# - data/file3.txt added
# - data/file2.txt removed
```

**Use Cases:**
- Incremental updates after making changes to source files
- Keeping sandbox data in sync with development changes
- Efficient updates without re-uploading entire directory

### `/mirror exists @<path>`

Check if a file or directory has been mirrored to the sandbox.

**Usage:**
```bash
/mirror exists @data
/mirror exists @config.json
```

**Behavior:**
- Queries the sandbox to check if the mirror exists
- Returns information about the mirror type (file or directory)
- Shows file count for directories
- Does not modify anything

**Example:**
```bash
/mirror exists @data

# If exists:
# ✓ Mirror 'data' exists in sandbox (directory)
#   Contains 15 file(s)

# If doesn't exist:
# Mirror 'data' does not exist in sandbox
```

**Use Cases:**
- Check if mirroring is needed before running `/mirror do`
- Verify mirror creation was successful
- Conditional logic in scripts or workflows

### `/mirror synced @<path>`

Check if the host and sandbox mirror are exactly in sync.

**Usage:**
```bash
/mirror synced @data
```

**Behavior:**
- Compares files between host and sandbox mirror
- Checks file names, sizes, and modification times
- Reports differences in detail
- Does not modify anything

**Example - When Synced:**
```bash
/mirror synced @data

# Output:
# ✓ Host and sandbox mirror 'data' are in sync
```

**Example - When Not Synced:**
```bash
/mirror synced @data

# Output:
# ✗ Host and sandbox mirror 'data' are NOT in sync:
#   Files only in host: 2
#     - new_file1.txt
#     - new_file2.txt
#   Files only in mirror: 1
#     - old_file.txt
#   Files with different sizes: 1
#     - modified.txt (host: 1234, mirror: 1000)
```

**Use Cases:**
- Verify synchronization before critical operations
- Check if `/mirror sync` or `/mirror revert+sync` is needed
- Monitor data consistency between host and sandbox
- Debugging sync issues

### `/mirror revert+sync @<path>`

Download files from sandbox mirror and overwrite them on the host.

**Usage:**
```bash
/mirror revert+sync @data
```

**Behavior:**
- Downloads all files from the sandbox mirror
- Overwrites existing files on the host
- Adds new files that exist in mirror but not on host
- Deletes files from host that no longer exist in mirror
- Provides true bidirectional synchronization

**Example:**
```bash
# Initial state:
# Host data/: file1.txt, file2.txt, file3.txt
# Sandbox modifies mirror: updates file1.txt, adds file4.txt, deletes file2.txt

/mirror revert+sync @data

# Result on host data/:
# - file1.txt (updated from sandbox)
# - file3.txt (unchanged)
# - file4.txt (added from sandbox)
# - file2.txt (deleted, no longer in mirror)

# Output:
# ✓ Synced 3 file(s) from sandbox to host '/path/to/data'
#   Files deleted from host: 1
```

**Use Cases:**
- Retrieve processed data from sandbox
- Apply sandbox modifications to host code
- Get results of sandbox computations
- Bidirectional development workflow

### `/mirror list`

List all registered mirrors with their status and metadata.

**Usage:**
```bash
/mirror list
```

**Behavior:**
- Queries Redis registry for all mirrors
- Displays mirror name, type, file count, creation date, and sync status
- Shows when each mirror was last checked
- Does not require a path argument
- Provides an overview of all active mirrors

**Example:**
```bash
/mirror list

# Output:
# Registered mirrors:
#
#   ✓ data (directory)
#     Files: 15
#     Created: 2025-01-16 10:30:45
#     Status: synced
#     Last checked: 2025-01-16 10:35:12
#
#   ✗ config (directory)
#     Files: 3
#     Created: 2025-01-16 09:15:22
#     Status: not_synced
#     Last checked: 2025-01-16 10:35:12
#
#   ✓ model.pkl (file)
#     Files: 1
#     Created: 2025-01-16 08:00:10
#     Status: synced
#     Last checked: 2025-01-16 10:35:12
```

**Use Cases:**
- Check which mirrors are currently active
- Monitor sync status of all mirrors at a glance
- Identify mirrors that need synchronization
- Review mirror metadata before operations

**Note:** The list command requires Redis to be available. If Redis is not configured, it will return an empty list. The sync status is automatically updated by a background monitor that checks mirrors periodically (default: every 5 minutes).

## Web Interface

A web-based management interface is available for viewing and managing mirrors through a browser.

**Access:**
```
http://localhost:18001/mirrors
```

**Features:**
- **View All Mirrors:** Grid layout showing all registered mirrors with metadata
- **Sync Status:** Visual indicators (✓ for synced, ✗ for not synced)
- **Delete Mirrors:** Remove mirrors directly from the interface
- **Sync Reminder:** Instructions for syncing mirrors from host (requires CLI)
- **Auto-Refresh:** Refresh button to reload mirror status
- **Responsive Design:** Modern, card-based layout

**Interface Details:**
- **Name & Type:** Shows mirror name and whether it's a file or directory
- **File Count:** Number of files in the mirror
- **Created:** Timestamp when the mirror was first created
- **Status:** Current sync status with color coding
- **Last Checked:** When the background monitor last verified the mirror
- **Actions:**
  - "Sync from Host" button (provides CLI command to run)
  - "Delete" button (removes mirror immediately)

**Note:** Creating new mirrors must be done through the CLI using `/mirror do`. The web interface is designed for monitoring and cleanup operations only.

## Redis Integration

The mirror system uses Redis for persistent tracking of mirror metadata and sync status.

**Configuration:**
```bash
# Environment variables for Redis connection
REDIS_HOST=localhost        # Default: localhost
REDIS_PORT=6379             # Default: 6379
REDIS_PASSWORD=             # Optional password
MIRROR_SYNC_CHECK_INTERVAL=300  # Sync check interval in seconds (default: 5 minutes)
```

**Tracked Data:**
- **name:** Mirror identifier
- **type:** file or directory
- **file_count:** Number of files in the mirror
- **created_at:** ISO format timestamp of creation
- **sync_status:** "synced" or "not_synced"
- **last_checked:** ISO format timestamp of last sync check
- **differences:** Detailed diff information (if not synced)

**Background Monitor:**
The sandbox service runs a background thread that:
- Periodically checks all registered mirrors (default: every 5 minutes)
- Updates sync status in Redis
- Logs any changes or errors
- Continues running even if individual checks fail
- Can be configured via `MIRROR_SYNC_CHECK_INTERVAL` environment variable

**Behavior Without Redis:**
- Mirrors will still function normally
- `/mirror do`, `/mirror sync`, `/mirror destroy`, etc. work as expected
- `/mirror list` will return an empty list
- Web interface will show no mirrors
- Background monitoring is disabled
- A warning is logged on startup

## Workflow Examples

### Example 1: Development with Sandbox Processing

```bash
# Check if already mirrored
/mirror exists @data
# Mirror 'data' does not exist in sandbox

# Initial setup: Copy project data to sandbox
/mirror do @data
# ✓ Mirrored 'data' to sandbox

# Verify it exists
/mirror exists @data
# ✓ Mirror 'data' exists in sandbox (directory)
#   Contains 10 file(s)

# Work in sandbox, process data...
# (sandbox modifies files, adds outputs, removes temp files)

# Check if changes were made
/mirror synced @data
# ✗ Host and sandbox mirror 'data' are NOT in sync:
#   Files only in mirror: 2
#   Files with different sizes: 3

# Retrieve processed data back to host
/mirror revert+sync @data
# ✓ Synced 8 file(s) from sandbox to host

# Verify sync
/mirror synced @data
# ✓ Host and sandbox mirror 'data' are in sync

# Clean up sandbox mirror when done
/mirror destroy @data
```

### Example 2: Iterative Development

```bash
# Initial copy
/mirror do @src/models

# Make changes to host files
# Edit src/models/model.py
# Add src/models/new_model.py

# Sync changes to sandbox
/mirror sync @src/models

# Continue development...
```

### Example 3: Configuration Management

```bash
# Mirror config file
/mirror do @config.json

# Test in sandbox with modified config...

# Destroy when testing complete
/mirror destroy @config.json
```

## Technical Details

### Path Resolution

The `/mirror` command uses the `@` prefix path resolution system:
- `@data` resolves to `<working_directory>/data`
- `@config.json` resolves to `<working_directory>/config.json`
- Paths are resolved relative to the current working directory

### Sandbox Endpoints

The mirror functionality uses these sandbox HTTP endpoints:

1. **POST /sync** - Synchronize files to mirror
   - Uploads files with multipart/form-data
   - Supports directory structure
   - Deletes orphaned files

2. **POST /revert-sync** - Retrieve mirror metadata
   - Returns file list with metadata
   - Lists all files in mirror

3. **GET /download-mirror/<name>** - Download mirror files
   - Returns single file directly
   - Returns directory as ZIP archive
   - Supports specific file download via query parameter

4. **DELETE /remove/<name>** - Remove mirror
   - Deletes mirror directory/file
   - Validates path safety

5. **GET /mirror-exists/<name>** - Check mirror existence
   - Returns whether mirror exists
   - Provides file count and type information
   - Fast operation (no file transfer)

6. **POST /mirror-synced** - Check sync status
   - Compares host file list with mirror
   - Returns detailed differences
   - Used by `/mirror synced` command

7. **GET /mirror-list** - List all mirrors
   - Returns all registered mirrors from Redis
   - Includes metadata and sync status
   - Used by `/mirror list` command

8. **GET /mirrors** - Web interface
   - Returns HTML interface for mirror management
   - Allows viewing and deleting mirrors
   - Provides sync instructions

### File Transfer

**Upload (host → sandbox):**
- Files transferred using HTTP multipart/form-data
- Large files supported (up to 100MB configured limit)
- Binary files handled correctly
- Directory structure preserved

**Download (sandbox → host):**
- Single files returned directly
- Directories packaged as ZIP archives
- Files extracted maintaining directory structure
- Orphaned files on host deleted for true sync

### Error Handling

All operations use the project's error handler:
- Exceptions are logged with context
- User-friendly error messages returned
- No internal details exposed to users

### Security

- Path validation prevents directory traversal
- `secure_filename()` sanitizes all filenames
- Paths validated within allowed directories
- Network errors handled gracefully

## Limitations

1. **Performance:**
   - No progress indication for large transfers
   - Large ZIP extraction may take time
   - No streaming/chunked downloads

2. **Size Constraints:**
   - Max file size: 100MB (configurable)
   - Large directories may timeout (60s limit)
   - ZIP memory usage scales with directory size

3. **Concurrency:**
   - No locking mechanism for concurrent access
   - Multiple syncs to same mirror may conflict
   - Race conditions possible with simultaneous operations

4. **File Deletion:**
   - `/mirror revert+sync` deletes host files not in mirror
   - No backup or confirmation prompt
   - Deletions are permanent

## Requirements

- Docker containers must be running
- Sandbox service must be accessible
- Sufficient disk space in Docker volumes
- Valid `@` prefix paths

## Troubleshooting

**Error: "Cannot connect to sandbox service"**
- Ensure Docker containers are running: `cd services && docker compose up -d`
- Check sandbox health: `curl http://localhost:18001/health`

**Error: "Path not found"**
- Verify the path exists relative to working directory
- Use absolute paths or ensure correct working directory
- Check file/directory permissions

**Error: "Sandbox request timed out"**
- Large directories may exceed timeout
- Try syncing smaller subsets
- Check network connectivity

**Error: "Mirror not found"**
- Mirror must be created with `/mirror do` first
- Use `/mirror do` instead of `/mirror sync` for initial copy
- Check mirror name matches exactly

## See Also

- [Context Management](./context-management.md) - Related @ prefix usage
- [Sandbox Architecture](./sandbox-architecture.md) - Technical details
- [Docker Configuration](./docker-setup.md) - Volume setup
