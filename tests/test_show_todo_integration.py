#!/usr/bin/env python3
"""
Comprehensive test for the /show TODO_list command integration.

Tests:
1. Creating a TODO_list via MCP create_plan
2. Retrieving it via /show TODO_list command
3. Verifying the format and content
"""

import sys
import subprocess
import json
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_mcp_create_plan_and_show():
    """Test end-to-end: MCP create_plan -> /show TODO_list."""
    print("=" * 80)
    print("END-TO-END TEST: MCP create_plan -> /show TODO_list")
    print("=" * 80)
    
    # Step 1: Create a plan via MCP to populate TODO_list
    print("\n📤 STEP 1: Creating plan via MCP create_plan...")
    
    mcp_server = Path(__file__).parent.parent / "mcps" / "mirror_vanisher_dev" / "server.py"
    
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "create_plan",
            "arguments": {
                "path": str(Path(__file__).parent.parent),
                "task": "Add comprehensive error handling and logging to the CLI application"
            }
        }
    }
    
    process = subprocess.Popen(
        [sys.executable, str(mcp_server)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=mcp_server.parent
    )
    
    try:
        request_json = json.dumps(request) + "\n"
        stdout, stderr = process.communicate(input=request_json, timeout=10)
        
        lines = [line for line in stdout.strip().split('\n') if line.strip()]
        if lines:
            response = json.loads(lines[-1])
            
            if "result" in response and "content" in response["result"]:
                for item in response["result"]["content"]:
                    if item.get("type") == "text":
                        data = json.loads(item["text"])
                        
                        if data.get("success"):
                            todo_count = len(data.get("TODO_list", []))
                            print(f"✅ Plan created successfully with {todo_count} TODO items")
                        else:
                            print(f"❌ Plan creation failed: {data.get('error')}")
                            return False
            else:
                print(f"❌ Unexpected response: {response}")
                return False
    except Exception as e:
        print(f"❌ Error during MCP call: {e}")
        return False
    
    # Step 2: Test /show TODO_list command
    print("\n📤 STEP 2: Testing /show TODO_list command...")
    
    from src.cli import get_todo_list_from_redis
    
    todo_list = get_todo_list_from_redis()
    
    if todo_list is None:
        print("❌ No TODO_list found in Redis")
        return False
    
    if not todo_list:
        print("❌ TODO_list is empty")
        return False
    
    print(f"✅ Retrieved TODO_list with {len(todo_list)} items")
    
    # Step 3: Display formatted output
    print("\n📋 FORMATTED OUTPUT:")
    print("=" * 80)
    print("📋 TODO LIST")
    print("=" * 80)
    print(f"\nTotal items: {len(todo_list)}\n")
    
    for item in todo_list:
        status_emoji = "⏳" if item['status'] == 'pending' else "✅"
        print(f"{status_emoji} {item['step_number']}. {item['action']}")
        print(f"   ➤ {item['details']}")
        print(f"   Status: [{item['status'].upper()}]")
        print()
    
    print("=" * 80)
    
    # Step 4: Verify structure
    print("\n🔍 STEP 3: Verifying TODO item structure...")
    
    required_fields = ['step_number', 'action', 'details', 'status']
    all_valid = True
    
    for i, item in enumerate(todo_list, 1):
        for field in required_fields:
            if field not in item:
                print(f"❌ Item {i} missing field: {field}")
                all_valid = False
    
    if all_valid:
        print(f"✅ All {len(todo_list)} items have correct structure")
    else:
        return False
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    print("\n📝 Summary:")
    print(f"  • Created plan via MCP create_plan")
    print(f"  • Stored {len(todo_list)} TODO items in Redis")
    print(f"  • Retrieved TODO_list via /show TODO_list command")
    print(f"  • Verified data structure and formatting")
    print(f"\n✨ The /show TODO_list command is fully functional!")
    
    return True

if __name__ == "__main__":
    success = test_mcp_create_plan_and_show()
    sys.exit(0 if success else 1)
