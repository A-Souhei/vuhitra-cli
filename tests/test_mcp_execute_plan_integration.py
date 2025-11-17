#!/usr/bin/env python3
"""
Integration test for execute_plan tool via MCP server.

This test validates the full workflow:
1. Create a plan with create_plan
2. Execute the plan with execute_plan
3. Verify the DETAILED_TODO_list is generated
4. Check Redis persistence
"""

import subprocess
import json
import sys
import redis
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Path to the MCP server
SERVER_PATH = Path(__file__).parent.parent / "mcps" / "mirror_vanisher_dev" / "server.py"
CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
SECRETS_PATH = Path(__file__).parent.parent / "secrets.yaml"

# Load Redis configuration
def load_redis_config() -> Dict[str, Any]:
    """Load Redis configuration from config and secrets files."""
    config = {'host': 'localhost', 'port': 16379, 'password': None}
    
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config and 'redis' in yaml_config:
                config['host'] = yaml_config['redis'].get('host', config['host'])
                config['port'] = yaml_config['redis'].get('port', config['port'])
    
    if SECRETS_PATH.exists():
        with open(SECRETS_PATH, 'r') as f:
            secrets = yaml.safe_load(f)
            if secrets and 'redis' in secrets:
                config['password'] = secrets['redis'].get('password')
    
    return config


def send_mcp_request(method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        stdout_data, stderr_data = process.communicate(input=request_json, timeout=30)
        
        # Parse the response
        if stdout_data.strip():
            lines = [line for line in stdout_data.strip().split('\n') if line.strip()]
            if lines:
                response = json.loads(lines[-1])
                return response
        
        return {"error": f"No response received. stderr: {stderr_data}"}
    
    except subprocess.TimeoutExpired:
        process.kill()
        return {"error": "Request timeout"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON decode error: {e}, stdout: {stdout_data}, stderr: {stderr_data}"}
    except Exception as e:
        return {"error": f"Unexpected error: {e}"}


def extract_text_from_response(response: Dict[str, Any]) -> Optional[str]:
    """Extract text content from MCP response."""
    if "result" in response and "content" in response["result"]:
        content = response["result"]["content"]
        if isinstance(content, list):
            for item in content:
                if item.get("type") == "text":
                    return item.get("text", "")
    return None


def test_create_plan():
    """Test Step 1: Create a plan with create_plan tool."""
    print("=" * 80)
    print("TEST 1: create_plan Tool")
    print("=" * 80)
    
    workspace_root = str(Path(__file__).parent.parent)
    
    params = {
        "path": workspace_root,
        "task": "Add a simple utility function to calculate the factorial of a number"
    }
    
    print(f"\n📤 Calling create_plan...")
    print(f"   Task: {params['task']}")
    print(f"   Path: {params['path']}")
    
    response = send_mcp_request("tools/call", {
        "name": "create_plan",
        "arguments": params
    })
    
    if "error" in response:
        print(f"\n❌ Error: {response['error']}")
        return False
    
    text = extract_text_from_response(response)
    if text:
        try:
            result = json.loads(text)
            if result.get("success"):
                print(f"\n✅ Plan created successfully!")
                
                # The TODO_list is at the top level of the result
                todo_list = result.get('TODO_list', [])
                print(f"   TODO items: {len(todo_list)}")
                
                # Show the TODO items
                for i, item in enumerate(todo_list, 1):
                    print(f"   {i}. {item.get('action', 'N/A')} - {item.get('details', '')}")
                
                return True
            else:
                print(f"\n❌ Plan creation failed: {result.get('error', 'Unknown error')}")
                return False
        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse response: {e}")
            print(f"   Raw text: {text[:200]}")
            return False
    else:
        print(f"\n❌ No text content in response")
        return False


def test_execute_plan(auto_execute: bool = True):
    """Test Step 2: Execute the plan with execute_plan tool."""
    print("\n" + "=" * 80)
    print(f"TEST 2: execute_plan Tool (auto_execute={auto_execute})")
    print("=" * 80)
    
    params = {
        "auto_execute": auto_execute
    }
    
    print(f"\n📤 Calling execute_plan...")
    print(f"   auto_execute: {auto_execute}")
    
    response = send_mcp_request("tools/call", {
        "name": "execute_plan",
        "arguments": params
    })
    
    if "error" in response:
        print(f"\n❌ Error: {response['error']}")
        return False
    
    text = extract_text_from_response(response)
    if text:
        try:
            result = json.loads(text)
            if result.get("success"):
                print(f"\n✅ Plan execution completed!")
                
                detailed_list = result.get('DETAILED_TODO_list', [])
                print(f"   Total items: {len(detailed_list)}")
                
                # Show summary of matched tools
                for i, item in enumerate(detailed_list, 1):
                    print(f"\n   Item {i}:")
                    print(f"      Action: {item.get('action', 'N/A')}")
                    print(f"      Matched Tool: {item.get('tool_name', 'None')}")
                    print(f"      Tool Type: {item.get('tool_type', 'N/A')}")
                    print(f"      Similarity: {item.get('similarity_score', 0):.3f}")
                    
                    if auto_execute:
                        print(f"      Executed: {item.get('executed', False)}")
                        if item.get('execution_result'):
                            exec_result = item['execution_result']
                            print(f"      Result: {exec_result.get('success', 'N/A')}")
                
                return True
            else:
                print(f"\n❌ Plan execution failed: {result.get('error', 'Unknown error')}")
                return False
        except json.JSONDecodeError:
            print(f"\n❌ Failed to parse response: {text[:200]}")
            return False
    else:
        print(f"\n❌ No text content in response")
        return False


def test_redis_persistence():
    """Test Step 3: Verify Redis persistence of TODO_list and DETAILED_TODO_list."""
    print("\n" + "=" * 80)
    print("TEST 3: Redis Persistence Check")
    print("=" * 80)
    
    try:
        redis_config = load_redis_config()
        print(f"\n📡 Connecting to Redis: {redis_config['host']}:{redis_config['port']}")
        
        redis_client = redis.Redis(
            host=redis_config['host'],
            port=redis_config['port'],
            password=redis_config['password'],
            decode_responses=True
        )
        
        # Test connection
        redis_client.ping()
        print("✅ Redis connection successful")
        
        # Check TODO_list
        todo_list_key = "mcp:mirror_vanisher:todo_list"
        todo_list_data = redis_client.get(todo_list_key)
        
        if todo_list_data and isinstance(todo_list_data, str):
            todo_list = json.loads(todo_list_data)
            print(f"\n✅ TODO_list found in Redis")
            print(f"   Items: {len(todo_list)}")
            for i, item in enumerate(todo_list, 1):
                print(f"   {i}. {item.get('action', 'N/A')}")
        else:
            print(f"\n❌ TODO_list not found in Redis (key: {todo_list_key})")
            return False
        
        # Check DETAILED_TODO_list
        detailed_list_key = "mcp:mirror_vanisher:detailed_todo_list"
        detailed_list_data = redis_client.get(detailed_list_key)
        
        if detailed_list_data and isinstance(detailed_list_data, str):
            detailed_list = json.loads(detailed_list_data)
            print(f"\n✅ DETAILED_TODO_list found in Redis")
            print(f"   Items: {len(detailed_list)}")
            for i, item in enumerate(detailed_list, 1):
                print(f"   {i}. {item.get('action', 'N/A')} -> {item.get('tool_name', 'None')}")
        else:
            print(f"\n❌ DETAILED_TODO_list not found in Redis (key: {detailed_list_key})")
            return False
        
        return True
        
    except redis.RedisError as e:
        print(f"\n❌ Redis error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


def main():
    """Run all integration tests."""
    print("🚀 Starting execute_plan Integration Tests\n")
    
    results = []
    
    # Test 1: Create plan
    results.append(("Create Plan", test_create_plan()))
    
    # Test 2: Execute plan without auto-execution
    results.append(("Execute Plan (no auto)", test_execute_plan(auto_execute=False)))
    
    # Test 3: Verify Redis persistence
    results.append(("Redis Persistence", test_redis_persistence()))
    
    # Test 4: Execute plan with auto-execution
    results.append(("Execute Plan (auto)", test_execute_plan(auto_execute=True)))
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
