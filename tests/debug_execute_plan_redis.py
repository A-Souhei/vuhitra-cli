#!/usr/bin/env python3
"""
Debug script to test execute_plan Redis connection.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add MCP mirror_vanisher to path
mcp_path = project_root / "mcps" / "mirror_vanisher_dev" / "src"
sys.path.insert(0, str(mcp_path))

import logging
logging.basicConfig(level=logging.DEBUG)

# Now import execute_plan
from execute_plan import ExecutePlan, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, TODO_LIST_KEY
from mirror_vanisher import MirrorVanisherManager

print("=" * 80)
print("DEBUG: Testing execute_plan Redis Connection")
print("=" * 80)

print(f"\nRedis Configuration:")
print(f"  Host: {REDIS_HOST}")
print(f"  Port: {REDIS_PORT}")
print(f"  Password: {'*' * len(REDIS_PASSWORD) if REDIS_PASSWORD else 'None'}")
print(f"  TODO_LIST_KEY: {TODO_LIST_KEY}")

# Create a minimal manager
print(f"\nCreating MirrorVanisherManager...")
manager = MirrorVanisherManager()

# Create ExecutePlan instance
print(f"\nCreating ExecutePlan instance...")
executor = ExecutePlan(manager=manager)

print(f"\nExecutePlan Redis Status:")
print(f"  redis_available: {executor.redis_available}")
print(f"  redis_client: {executor.redis_client}")

# Try to get TODO_list
print(f"\nTrying to get TODO_list...")
todo_list = executor.get_todo_list()

print(f"\nResult:")
print(f"  TODO_list length: {len(todo_list)}")
if todo_list:
    print(f"  TODO_list items:")
    for i, item in enumerate(todo_list, 1):
        print(f"    {i}. {item.get('action', 'N/A')}")
else:
    print(f"  ❌ TODO_list is empty!")
    
    # Try direct Redis connection
    print(f"\n  Trying direct Redis connection...")
    import redis
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=True)
        r.ping()
        print(f"  ✅ Direct Redis ping successful")
        
        todo_data = r.get(TODO_LIST_KEY)
        if todo_data:
            print(f"  ✅ TODO_list found in Redis (length: {len(todo_data)})")
            import json
            todo_list_data = json.loads(todo_data)
            print(f"  Items: {len(todo_list_data)}")
        else:
            print(f"  ❌ TODO_list not found in Redis")
    except Exception as e:
        print(f"  ❌ Direct Redis connection failed: {e}")
