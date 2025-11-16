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
