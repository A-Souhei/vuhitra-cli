#!/usr/bin/env python3
"""
Manual test for the updated create_plan tool in Mirror+Vanisher Development MCP.
Tests:
1. create_plan returns TODO_list
2. Beautiful formatted plan output
3. TODO_list storage in memory
4. get_todo_list retrieval
5. Special character handling (code with quotes)
"""

import sys
import json
from pathlib import Path

# Add MCP to path
mcp_path = Path(__file__).parent.parent / "mcps" / "mirror_vanisher_dev"
sys.path.insert(0, str(mcp_path))
sys.path.insert(0, str(mcp_path / "src"))

from mirror_vanisher import MirrorVanisherManager
from planning import PlanningTools

# Colors
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
RED = '\033[0;31m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def print_header(test_name):
    """Print test header."""
    print("=" * 80)
    print(test_name)
    print("=" * 80)

def print_success(message):
    """Print success message."""
    print(f"{GREEN}✓ {message}{NC}")

def print_error(message):
    """Print error message."""
    print(f"{RED}✗ {message}{NC}")

def print_info(message):
    """Print info message."""
    print(f"{BLUE}ℹ {message}{NC}")

def main():
    """Run create_plan tool tests."""

    print("=" * 80)
    print("CREATE_PLAN TOOL TEST - Updated Features")
    print("=" * 80)
    print()

    # Initialize manager and tools
    print(f"{YELLOW}Initializing planning tools...{NC}")
    manager = MirrorVanisherManager()
    planning = PlanningTools(manager)
    print_success("Planning tools initialized")
    print()

    # Test 1: Create plan for a feature implementation
    print_header("TEST 1: Create Plan - Feature Implementation")
    # Use current directory as test path
    test_path = str(Path(__file__).parent.parent)
    task = 'Add user authentication with JWT tokens and implement login/logout functionality with "secure" password hashing'

    result = planning.create_plan(test_path, task)

    if result.get('success'):
        print_success("Plan created successfully")

        # Check for TODO_list in response
        if 'TODO_list' in result:
            print_success(f"TODO_list present with {len(result['TODO_list'])} items")
            print_info("TODO_list items:")
            for item in result['TODO_list']:
                print(f"  Step {item['step_number']}: {item['action']}")
                print(f"    Details: {item['details']}")
                print(f"    Status: {item['status']}")
        else:
            print_error("TODO_list not found in response")

        # Check for formatted_plan in response
        if 'formatted_plan' in result:
            print_success("Formatted plan present")
            print_info("Formatted Plan Output:")
            print(result['formatted_plan'])
        else:
            print_error("Formatted plan not found in response")
    else:
        print_error(f"Failed to create plan: {result.get('error')}")
    print()

    # Test 2: Get TODO_list from memory
    print_header("TEST 2: Get TODO_list from Memory")
    todo_result = planning.get_todo_list()

    if todo_result.get('success'):
        print_success(f"Retrieved TODO_list with {todo_result.get('count')} items")
        print_info("Stored TODO_list:")
        print(json.dumps(todo_result['TODO_list'], indent=2))
    else:
        print_error(f"Failed to retrieve TODO_list: {todo_result.get('error')}")
    print()

    # Test 3: Create another plan (should overwrite)
    print_header("TEST 3: Create New Plan - Bug Fix (Should Overwrite TODO_list)")
    task2 = 'Fix memory leak in database connection pool with proper cleanup'

    result2 = planning.create_plan(test_path, task2)

    if result2.get('success'):
        print_success("New plan created successfully")
        print_info(f"New plan has {len(result2['TODO_list'])} steps")
    else:
        print_error(f"Failed to create plan: {result2.get('error')}")
    print()

    # Test 4: Verify TODO_list was overwritten
    print_header("TEST 4: Verify TODO_list Was Overwritten")
    todo_result2 = planning.get_todo_list()

    if todo_result2.get('success'):
        print_success(f"Retrieved TODO_list with {todo_result2.get('count')} items")

        if todo_result2.get('count') > 0:
            # Check if it's the new plan
            first_item = todo_result2['TODO_list'][0]
            if 'root cause' in first_item['action'].lower() or 'bug' in first_item['details'].lower():
                print_success("TODO_list correctly overwritten with bug fix plan")
            else:
                print_error("TODO_list may not have been overwritten correctly")

            print_info("Current TODO_list:")
            for item in todo_result2['TODO_list']:
                print(f"  Step {item['step_number']}: {item['action']}")
        else:
            print_error("TODO_list is empty - previous test may have failed")
    else:
        print_error(f"Failed to retrieve TODO_list: {todo_result2.get('error')}")
    print()

    # Test 5: Test with complex task containing code and special characters
    print_header("TEST 5: Create Plan with Code and Special Characters")
    task3 = '''Implement API endpoint: POST /api/users with JSON body {"name": "John", "email": "john@example.com"} and return {"status": "success", "user_id": 123}'''

    result3 = planning.create_plan(test_path, task3)

    if result3.get('success'):
        print_success("Plan with special characters created successfully")

        # Verify JSON serialization works
        try:
            json_str = json.dumps(result3['TODO_list'])
            # Verify it can be parsed back
            json.loads(json_str)
            print_success("JSON serialization/deserialization successful")
            print_info(f"Serialized TODO_list length: {len(json_str)} characters")
        except Exception as e:
            print_error(f"JSON serialization failed: {e}")
    else:
        print_error(f"Failed to create plan: {result3.get('error')}")
    print()

    print("=" * 80)
    print("All tests completed!")
    print("=" * 80)

if __name__ == "__main__":
    main()
