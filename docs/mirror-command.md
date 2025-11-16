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

## Workflow Examples

### Example 1: Development with Sandbox Processing

```bash
# Initial setup: Copy project data to sandbox
/mirror do @data

# Work in sandbox, process data...
# (sandbox modifies files, adds outputs, removes temp files)

# Retrieve processed data back to host
/mirror revert+sync @data

# Host now has all sandbox modifications!

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
