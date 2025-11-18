#!/usr/bin/env python3
"""
Integration test for execute_plan tool via MCP server.

This test validates the full workflow:
1. Create a plan using create_plan
2. Execute the plan using execute_plan
3. Verify semantic matching and DETAILED_TODO_list generation
4. Check execution results
"""

import subprocess
import json
import sys
import time
from pathlib import Path
from typing import Optional, Dict, Any

# Path to the MCP server
SERVER_PATH = Path(__file__).parent.parent / "mcps" / "mirror_vanisher_dev" / "server.py"


def send_mcp_request(method: str, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
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
    
    stdout_data = ""
    stderr_data = ""
    
    try:
        # Send the request
        request_json = json.dumps(request) + "\n"
        stdout_data, stderr_data = process.communicate(input=request_json, timeout=timeout)
        
        # Parse the response
        if stdout_data.strip():
            # Split by newlines and get the last non-empty line (the actual response)
            lines = [line for line in stdout_data.strip().split('\n') if line.strip()]
            if lines:
                response = json.loads(lines[-1])
                return response
        
        return {"error": f"No response received. stderr: {stderr_data}"}
    
    except subprocess.TimeoutExpired:
        process.kill()
        return {"error": f"Request timeout after {timeout}s"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON decode error: {e}, stdout: {stdout_data}, stderr: {stderr_data}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def extract_result_data(response: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the actual result data from MCP response."""
    if "error" in response:
        return {"error": response["error"]}
    
    if "result" not in response:
        return {"error": "No result in response"}
    
    result = response["result"]
    
    # MCP format: result.content[0].text contains JSON string
    if "content" in result and isinstance(result["content"], list) and len(result["content"]) > 0:
        text_content = result["content"][0].get("text", "{}")
        try:
            return json.loads(text_content)
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse result text: {e}", "raw_text": text_content}
    
    return {"error": "Unexpected result format", "raw_result": result}


def test_step_1_create_plan():
    """Step 1: Create a plan using create_plan tool."""
    print("=" * 80)
    print("STEP 1: Create Plan")
    print("=" * 80)
    
    workspace_root = str(Path(__file__).parent.parent)
    
    params = {
        "path": workspace_root,
        "task": "Implement a simple calculator with add, subtract, multiply, and divide functions"
    }
    
    print(f"\n📤 Calling create_plan...")
    print(f"   Task: {params['task']}")
    print(f"   Path: {params['path']}")
    
    response = send_mcp_request("tools/call", {
        "name": "create_plan",
        "arguments": params
    })
    
    result_data = extract_result_data(response)
    
    if "error" in result_data:
        print(f"\n❌ Error: {result_data['error']}")
        return False
    
    if "success" in result_data and result_data["success"]:
        print(f"\n✅ Plan created successfully!")
        
        if "TODO_list" in result_data:
            todo_list = result_data["TODO_list"]
            print(f"\n📋 TODO_list contains {len(todo_list)} steps:")
            for i, item in enumerate(todo_list, 1):
                print(f"   {i}. {item.get('action', 'N/A')}")
                if item.get('details'):
                    print(f"      Details: {item['details'][:100]}...")
        
        if "storage" in result_data:
            print(f"\n💾 Storage: {result_data['storage']}")
        
        return True
    else:
        print(f"\n❌ Plan creation failed: {result_data}")
        return False


def test_step_2_execute_plan_without_auto_execute():
    """Step 2: Execute plan without auto-execution to inspect DETAILED_TODO_list."""
    print("\n" + "=" * 80)
    print("STEP 2: Execute Plan (auto_execute=False)")
    print("=" * 80)
    
    params = {
        "auto_execute": False
    }
    
    print(f"\n📤 Calling execute_plan with auto_execute=False...")
    print(f"   This will build DETAILED_TODO_list without executing")
    
    response = send_mcp_request("tools/call", {
        "name": "execute_plan",
        "arguments": params
    }, timeout=60)  # Longer timeout for embedding processing
    
    result_data = extract_result_data(response)
    
    if "error" in result_data:
        print(f"\n❌ Error: {result_data['error']}")
        return False
    
    if "success" in result_data and result_data["success"]:
        print(f"\n✅ DETAILED_TODO_list created successfully!")
        
        if "summary" in result_data:
            summary = result_data["summary"]
            print(f"\n📊 Summary:")
            print(f"   Total steps: {summary.get('total_steps', 0)}")
            print(f"   Matched tools: {summary.get('matched_steps', 0)}")
            print(f"   Unmatched: {summary.get('unmatched_steps', 0)}")
            print(f"   Executed: {summary.get('executed_steps', 0)}")
        
        if "DETAILED_TODO_list" in result_data:
            detailed_list = result_data["DETAILED_TODO_list"]
            print(f"\n📋 DETAILED_TODO_list sample (first 3 items):")
            for i, item in enumerate(detailed_list[:3], 1):
                print(f"\n   Item {i}:")
                print(f"      Original Step: {item.get('original_step', {}).get('action', 'N/A')}")
                print(f"      Matched Tool: {item.get('matched_tool', {}).get('name', 'None')}")
                print(f"      Tool Type: {item.get('tool_type', 'N/A')}")
                print(f"      Similarity: {item.get('similarity_score', 0):.3f}")
                print(f"      Status: {item.get('execution_status', 'N/A')}")
        
        if "storage" in result_data:
            print(f"\n💾 Storage: {result_data['storage']}")
        
        return True
    else:
        print(f"\n❌ Execution failed: {result_data}")
        return False


def test_step_3_execute_plan_with_auto_execute():
    """Step 3: Execute plan with auto-execution enabled."""
    print("\n" + "=" * 80)
    print("STEP 3: Execute Plan (auto_execute=True)")
    print("=" * 80)
    
    params = {
        "auto_execute": True
    }
    
    print(f"\n📤 Calling execute_plan with auto_execute=True...")
    print(f"   This will build and execute DETAILED_TODO_list")
    print(f"   ⚠️  Note: Execution may take longer depending on plan complexity")
    
    response = send_mcp_request("tools/call", {
        "name": "execute_plan",
        "arguments": params
    }, timeout=120)  # Much longer timeout for actual execution
    
    result_data = extract_result_data(response)
    
    if "error" in result_data:
        print(f"\n❌ Error: {result_data['error']}")
        # Check if it's a timeout or other error
        if "timeout" in str(result_data['error']).lower():
            print(f"   💡 This may be normal for complex plans. Check Redis for results.")
        return False
    
    if "success" in result_data and result_data["success"]:
        print(f"\n✅ Plan executed successfully!")
        
        if "summary" in result_data:
            summary = result_data["summary"]
            print(f"\n📊 Execution Summary:")
            print(f"   Total steps: {summary.get('total_steps', 0)}")
            print(f"   Matched tools: {summary.get('matched_steps', 0)}")
            print(f"   Successfully executed: {summary.get('executed_steps', 0)}")
            print(f"   Failed executions: {summary.get('failed_steps', 0)}")
            print(f"   Unmatched: {summary.get('unmatched_steps', 0)}")
        
        if "execution_results" in result_data:
            results = result_data["execution_results"]
            print(f"\n🔧 Execution Results (first 3):")
            for i, res in enumerate(results[:3], 1):
                status_icon = "✅" if res.get('success') else "❌"
                print(f"\n   {status_icon} Result {i}:")
                print(f"      Tool: {res.get('tool_name', 'N/A')}")
                print(f"      Success: {res.get('success', False)}")
                if res.get('error'):
                    print(f"      Error: {res['error'][:100]}...")
        
        if "storage" in result_data:
            print(f"\n💾 Storage: {result_data['storage']}")
        
        return True
    else:
        print(f"\n❌ Execution failed: {result_data}")
        return False


def test_step_4_verify_storage():
    """Step 4: Verify that results are stored in Redis."""
    print("\n" + "=" * 80)
    print("STEP 4: Verify Storage")
    print("=" * 80)
    
    # We can use get_todo_list to verify the TODO_list is still there
    print(f"\n📤 Calling get_todo_list to verify storage...")
    
    response = send_mcp_request("tools/call", {
        "name": "get_todo_list",
        "arguments": {}
    })
    
    result_data = extract_result_data(response)
    
    if "error" in result_data:
        print(f"\n⚠️  Could not verify storage: {result_data['error']}")
        return False
    
    if "success" in result_data and result_data["success"]:
        print(f"\n✅ TODO_list still accessible in storage")
        
        if "TODO_list" in result_data:
            todo_list = result_data["TODO_list"]
            print(f"   Contains {len(todo_list)} steps")
        
        if "storage" in result_data:
            print(f"   Storage location: {result_data['storage']}")
        
        return True
    
    return False


def run_all_tests():
    """Run all integration tests in sequence."""
    print("\n" + "🧪" * 40)
    print("EXECUTE_PLAN INTEGRATION TEST SUITE")
    print("🧪" * 40 + "\n")
    
    print("This test suite validates the complete execute_plan workflow:")
    print("1. Create a plan with create_plan")
    print("2. Build DETAILED_TODO_list without execution")
    print("3. Execute the plan automatically")
    print("4. Verify storage and persistence")
    
    time.sleep(2)  # Give user time to read
    
    results = {
        "create_plan": False,
        "execute_without_auto": False,
        "execute_with_auto": False,
        "verify_storage": False
    }
    
    # Run tests in sequence
    results["create_plan"] = test_step_1_create_plan()
    
    if results["create_plan"]:
        time.sleep(1)  # Brief pause between tests
        results["execute_without_auto"] = test_step_2_execute_plan_without_auto_execute()
    
    if results["execute_without_auto"]:
        time.sleep(1)
        results["execute_with_auto"] = test_step_3_execute_plan_with_auto_execute()
    
    if results["execute_with_auto"]:
        time.sleep(1)
        results["verify_storage"] = test_step_4_verify_storage()
    
    # Print final summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    
    for test_name, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"{icon} {test_name.replace('_', ' ').title()}")
    
    print(f"\n📊 Results: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! The execute_plan tool is working correctly.")
        return 0
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
