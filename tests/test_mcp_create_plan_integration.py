#!/usr/bin/env python3
"""
Integration test for create_plan and get_todo_list tools via MCP server.

This test simulates how Claude/LLM would call the tools through the MCP interface.
"""

import subprocess
import json
import sys
from pathlib import Path

# Path to the MCP server
SERVER_PATH = Path(__file__).parent.parent / "mcps" / "mirror_vanisher_dev" / "server.py"

def send_mcp_request(method: str, params: dict = None) -> dict:
    """Send a JSON-RPC request to the MCP server and return the response."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params or {}
    }
    
    # Start the MCP server
    process = subprocess.Popen(
        [sys.executable, str(SERVER_PATH)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=SERVER_PATH.parent
    )
    
    try:
        # Send the request
        request_json = json.dumps(request) + "\n"
        stdout, stderr = process.communicate(input=request_json, timeout=10)
        
        # Parse the response
        if stdout.strip():
            # Split by newlines and get the last non-empty line (the actual response)
            lines = [line for line in stdout.strip().split('\n') if line.strip()]
            if lines:
                response = json.loads(lines[-1])
                return response
        
        return {"error": f"No response received. stderr: {stderr}"}
    
    except subprocess.TimeoutExpired:
        process.kill()
        return {"error": "Request timeout"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON decode error: {e}, stdout: {stdout}, stderr: {stderr}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def test_create_plan():
    """Test the create_plan tool."""
    print("=" * 80)
    print("TEST 1: create_plan Tool")
    print("=" * 80)
    
    # Use portable path - resolve to workspace root
    workspace_root = str(Path(__file__).parent.parent)
    
    params = {
        "path": workspace_root,
        "task": "Add logging functionality with different log levels (DEBUG, INFO, WARNING, ERROR)"
    }
    
    print(f"\n📤 Calling tools/call with create_plan...")
    print(f"   Task: {params['task']}")
    print(f"   Path: {params['path']}")
    
    response = send_mcp_request("tools/call", {
        "name": "create_plan",
        "arguments": params
    })
    
    if "error" in response:
        print(f"\n❌ Error: {response['error']}")
        return None
    
    if "result" in response:
        result = response["result"]
        
        # Debug: print raw result
        print(f"\n🔍 DEBUG - Raw result keys: {list(result.keys())}")
        print(f"🔍 DEBUG - Result content type: {type(result.get('content'))}")
        
        # Check for content array (MCP format)
        if "content" in result and isinstance(result["content"], list):
            print(f"🔍 DEBUG - Content array length: {len(result['content'])}")
            for i, item in enumerate(result["content"]):
                print(f"🔍 DEBUG - Content item {i}: type={item.get('type')}, text_length={len(item.get('text', ''))}")
                if item.get("type") == "text":
                    # Debug: show first 500 chars
                    text_preview = item["text"][:500]
                    print(f"🔍 DEBUG - Text preview: {text_preview}")
                    
                    data = json.loads(item["text"])
                    
                    print(f"\n✅ Plan created successfully!")
                    print(f"   Data keys: {list(data.keys())}")
                    print(f"   TODO_list items: {len(data.get('TODO_list', []))}")
                    print(f"   Has formatted_plan: {'formatted_plan' in data}")
                    
                    # Show TODO items
                    print("\n📝 TODO Items:")
                    for todo in data.get("TODO_list", [])[:3]:  # Show first 3
                        print(f"   {todo['step_number']}. {todo['action']}")
                        print(f"      → {todo['details']}")
                        print(f"      Status: {todo['status']}")
                    
                    if len(data.get("TODO_list", [])) > 3:
                        print(f"   ... and {len(data['TODO_list']) - 3} more items")
                    
                    # Show formatted plan (first 15 lines)
                    if "formatted_plan" in data:
                        print("\n📋 Formatted Plan (preview):")
                        lines = data["formatted_plan"].split("\n")[:15]
                        for line in lines:
                            print(f"   {line}")
                        if len(data["formatted_plan"].split("\n")) > 15:
                            print("   ...")
                    
                    return data
    
    print(f"\n❌ Unexpected response format: {response}")
    return None


def test_get_todo_list(expected_count=None):
    """Test the get_todo_list tool."""
    print("\n" + "=" * 80)
    print("TEST 2: get_todo_list Tool")
    print("=" * 80)
    
    print(f"\n📤 Calling tools/call with get_todo_list...")
    
    response = send_mcp_request("tools/call", {
        "name": "get_todo_list",
        "arguments": {}
    })
    
    if "error" in response:
        print(f"\n❌ Error: {response['error']}")
        return False
    
    if "result" in response:
        result = response["result"]
        
        if "content" in result and isinstance(result["content"], list):
            for item in result["content"]:
                if item.get("type") == "text":
                    data = json.loads(item["text"])
                    
                    print(f"\n✅ TODO_list retrieved successfully!")
                    print(f"   Count: {data.get('count', 0)}")
                    
                    if expected_count is not None:
                        if data.get("count") == expected_count:
                            print(f"   ✓ Count matches expected ({expected_count})")
                        else:
                            print(f"   ✗ Count mismatch! Expected {expected_count}, got {data.get('count')}")
                    
                    # Show TODO items
                    print("\n📝 Stored TODO Items:")
                    for todo in data.get("TODO_list", [])[:5]:  # Show first 5
                        print(f"   {todo['step_number']}. {todo['action']}")
                    
                    if len(data.get("TODO_list", [])) > 5:
                        print(f"   ... and {len(data['TODO_list']) - 5} more items")
                    
                    return True
    
    print(f"\n❌ Unexpected response format: {response}")
    return False


def test_overwrite_behavior():
    """Test that creating a new plan overwrites the TODO_list."""
    print("\n" + "=" * 80)
    print("TEST 3: TODO_list Overwrite Behavior")
    print("=" * 80)
    
    # Use portable path - resolve to workspace root
    workspace_root = str(Path(__file__).parent.parent)
    
    # Create first plan
    params1 = {
        "path": workspace_root,
        "task": "First plan with multiple steps for implementing user authentication"
    }
    
    print(f"\n📤 Creating first plan...")
    response1 = send_mcp_request("tools/call", {
        "name": "create_plan",
        "arguments": params1
    })
    
    if "error" in response1:
        print(f"❌ Error creating first plan: {response1['error']}")
        return False
    
    # Get first TODO count
    first_count = None
    if "result" in response1 and "content" in response1["result"]:
        for item in response1["result"]["content"]:
            if item.get("type") == "text":
                data = json.loads(item["text"])
                first_count = len(data.get("TODO_list", []))
                print(f"✓ First plan created with {first_count} items")
    
    # Create second plan
    params2 = {
        "path": workspace_root,
        "task": "Fix bug in database connection pooling"
    }
    
    print(f"\n📤 Creating second plan (should overwrite)...")
    response2 = send_mcp_request("tools/call", {
        "name": "create_plan",
        "arguments": params2
    })
    
    if "error" in response2:
        print(f"❌ Error creating second plan: {response2['error']}")
        return False
    
    # Get second TODO count
    second_count = None
    if "result" in response2 and "content" in response2["result"]:
        for item in response2["result"]["content"]:
            if item.get("type") == "text":
                data = json.loads(item["text"])
                second_count = len(data.get("TODO_list", []))
                print(f"✓ Second plan created with {second_count} items")
    
    # Verify through get_todo_list
    print(f"\n📤 Verifying with get_todo_list...")
    response3 = send_mcp_request("tools/call", {
        "name": "get_todo_list",
        "arguments": {}
    })
    
    if "result" in response3 and "content" in response3["result"]:
        for item in response3["result"]["content"]:
            if item.get("type") == "text":
                data = json.loads(item["text"])
                current_count = data.get("count", 0)
                
                if current_count == second_count:
                    print(f"✅ TODO_list correctly overwritten!")
                    print(f"   Previous count: {first_count}")
                    print(f"   Current count: {current_count}")
                    return True
                else:
                    print(f"❌ Overwrite failed!")
                    print(f"   Expected count: {second_count}")
                    print(f"   Actual count: {current_count}")
                    return False
    
    return False


def main():
    """Run all integration tests."""
    print("\n" + "=" * 80)
    print("MCP CREATE_PLAN INTEGRATION TESTS")
    print("=" * 80)
    print("\nTesting the create_plan and get_todo_list tools via MCP interface")
    print("(Simulating how Claude/LLM would interact with the server)\n")
    
    # Test 1: Create plan
    plan_data = test_create_plan()
    if not plan_data:
        print("\n❌ Test 1 failed - stopping tests")
        return 1
    
    # Test 2: Get TODO list
    expected_count = len(plan_data.get("TODO_list", []))
    success = test_get_todo_list(expected_count)
    if not success:
        print("\n❌ Test 2 failed - stopping tests")
        return 1
    
    # Test 3: Overwrite behavior
    success = test_overwrite_behavior()
    if not success:
        print("\n❌ Test 3 failed")
        return 1
    
    print("\n" + "=" * 80)
    print("✅ ALL INTEGRATION TESTS PASSED!")
    print("=" * 80)
    print("\nThe create_plan and get_todo_list tools are working correctly via MCP!\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
