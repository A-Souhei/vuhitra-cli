#!/usr/bin/env python3
"""
Simple manual test for execute_plan via MCP server.
"""

import subprocess
import json
import sys
from pathlib import Path

SERVER_PATH = Path(__file__).parent.parent / "mcps" / "mirror_vanisher_dev" / "server.py"

# Test 1: Call execute_plan directly
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "execute_plan",
        "arguments": {
            "auto_execute": False
        }
    }
}

print("Calling execute_plan via MCP...")
print(f"Request: {json.dumps(request, indent=2)}")
print("\nStarting MCP server...")

process = subprocess.Popen(
    [sys.executable, str(SERVER_PATH)],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd=SERVER_PATH.parent
)

try:
    request_json = json.dumps(request) + "\n"
    stdout, stderr = process.communicate(input=request_json, timeout=30)
    
    print("\n" + "=" * 80)
    print("STDOUT:")
    print("=" * 80)
    print(stdout)
    
    print("\n" + "=" * 80)
    print("STDERR:")
    print("=" * 80)
    print(stderr)
    
    # Try to parse the response
    if stdout.strip():
        lines = [line for line in stdout.strip().split('\n') if line.strip()]
        if lines:
            try:
                response = json.loads(lines[-1])
                print("\n" + "=" * 80)
                print("PARSED RESPONSE:")
                print("=" * 80)
                print(json.dumps(response, indent=2))
            except json.JSONDecodeError as e:
                print(f"\nFailed to parse response: {e}")
    
except subprocess.TimeoutExpired:
    process.kill()
    print("Timeout!")
except Exception as e:
    print(f"Error: {e}")
