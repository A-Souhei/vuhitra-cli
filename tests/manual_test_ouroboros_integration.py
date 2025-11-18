#!/usr/bin/env python3
"""
Integration test for Ouroboros Execute Plan functionality.

This test validates the end-to-end workflow with actual services.
"""

import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "mcps" / "mirror_vanisher_dev" / "src"))

import yaml
import redis
from unittest.mock import Mock

from execute_plan import ExecutePlan


def get_redis_client():
    """Create Redis client with authentication."""
    secrets_path = project_root / "secrets.yaml"
    password = ''

    if secrets_path.exists():
        with open(secrets_path, 'r') as f:
            secrets = yaml.safe_load(f)
        password = secrets.get('redis', {}).get('password', '')

    return redis.Redis(
        host='localhost',
        port=16379,
        password=password if password else None,
        decode_responses=True
    )


def test_ouroboros_tool_matching_integration():
    """Test ouroboros tool matching with actual embeddings service."""
    print("\n" + "=" * 60)
    print("TEST: Ouroboros Tool Matching Integration")
    print("=" * 60)

    # Create mock manager and server
    manager = Mock()
    server = Mock()

    # Set up server tools (same as the main MCP)
    server.tools = {
        'analyze_code': {
            'description': 'Analyze code for patterns, bugs, and improvements',
            'inputSchema': {'properties': {'code': {'type': 'string'}}}
        },
        'generate_code': {
            'description': 'Generate code based on requirements',
            'inputSchema': {'properties': {'task': {'type': 'string'}}}
        },
        'explore_codebase': {
            'description': 'Explore and analyze codebase structure',
            'inputSchema': {'properties': {'path': {'type': 'string'}}}
        },
        'run_tests': {
            'description': 'Run test suite and report results',
            'inputSchema': {'properties': {'path': {'type': 'string'}}}
        }
    }

    # Create ExecutePlan instance
    executor = ExecutePlan(manager, server)

    # Create test TODO_list
    todo_list = [
        {'step_number': 1, 'action': 'Explore the project structure', 'details': 'Analyze the codebase to understand organization'},
        {'step_number': 2, 'action': 'Generate a utility function', 'details': 'Create a helper function for data processing'},
        {'step_number': 3, 'action': 'Analyze existing code', 'details': 'Review code for potential improvements'}
    ]

    print("\nInput TODO_list:")
    for item in todo_list:
        print(f"  {item['step_number']}. {item['action']}")

    # Run ouroboros matching
    print("\nRunning ouroboros tool matching...")
    detailed_list = executor.ouroboros_match_tools(todo_list)

    print(f"\nMatched {len(detailed_list)}/{len(todo_list)} steps")
    print("\nDETAILED_TODO_list:")

    for item in detailed_list:
        print(f"\n  Step {item['step_number']}:")
        print(f"    Action: {item['original_action']}")
        print(f"    Tool: {item['tool_name']} (from {item['tool_source']})")
        print(f"    Similarity: {item['similarity_score']:.2%}")

    # Verify results
    assert len(detailed_list) > 0, "Should have matched at least one step"

    for item in detailed_list:
        assert 'tool_name' in item
        assert 'similarity_score' in item
        assert item['similarity_score'] >= 0.1  # Should be above keyword threshold

    print("\n✅ Tool matching integration test PASSED")
    return True


def test_execute_plan_build_only():
    """Test execute_plan with auto_execute=False (build list only)."""
    print("\n" + "=" * 60)
    print("TEST: Execute Plan - Build DETAILED_TODO_list Only")
    print("=" * 60)

    # Create mock manager and server
    manager = Mock()
    server = Mock()
    server.tools = {
        'analyze_code': {
            'description': 'Analyze code for patterns, bugs, and improvements',
            'inputSchema': {'properties': {'code': {'type': 'string'}}}
        }
    }

    # Create ExecutePlan instance
    executor = ExecutePlan(manager, server)

    # Set up TODO_list in memory
    executor.memory_todo_list = [
        {'step_number': 1, 'action': 'Analyze code', 'details': 'Review for issues'}
    ]

    print("\nCalling execute_plan(auto_execute=False)...")
    result = executor.execute_plan(auto_execute=False)

    print(f"\nResult:")
    print(f"  Success: {result['success']}")
    print(f"  TODO_list count: {result['todo_list_count']}")
    print(f"  DETAILED_TODO_list count: {result['detailed_todo_list_count']}")
    print(f"  Auto-execute: {result['auto_execute']}")

    # Verify results
    assert result['success'] is True, "Should succeed"
    assert result['auto_execute'] is False, "auto_execute should be False"
    assert len(result['execution_results']) == 0, "Should have no execution results"

    print("\n✅ Build-only test PASSED")
    return True


def test_redis_integration():
    """Test Redis storage for TODO_list and DETAILED_TODO_list."""
    print("\n" + "=" * 60)
    print("TEST: Redis Storage Integration")
    print("=" * 60)

    redis_client = get_redis_client()

    # Test connection
    print("\nTesting Redis connection...")
    try:
        redis_client.ping()
    except redis.ConnectionError:
        print("  ⚠ Redis not available - skipping test")
        return True  # Return True to not fail the test suite
    print("  ✓ Redis connection successful")

    # Create test data
    test_todo_list = [
        {'step_number': 1, 'action': 'Test action', 'details': 'Test details'}
    ]

    # Store in Redis
    print("\nStoring TODO_list in Redis...")
    redis_client.set('vuhitra:TODO_list', json.dumps(test_todo_list))
    print("  ✓ TODO_list stored")

    # Retrieve and verify
    stored = redis_client.get('vuhitra:TODO_list')
    retrieved = json.loads(stored)

    assert retrieved == test_todo_list, "Retrieved should match stored"
    print("  ✓ TODO_list retrieved and verified")

    # Clean up
    redis_client.delete('vuhitra:TODO_list')
    print("  ✓ Cleaned up test data")

    print("\n✅ Redis integration test PASSED")
    return True


def test_pretty_print_output():
    """Test pretty printing functionality."""
    print("\n" + "=" * 60)
    print("TEST: Pretty Print Output")
    print("=" * 60)

    # Create mock instance
    manager = Mock()
    server = Mock()
    server.tools = {}

    executor = ExecutePlan(manager, server)

    # Test item
    item = {
        'original_action': 'Create utility function',
        'original_details': 'Add factorial calculation helper',
        'tool_name': 'create_file',
        'tool_source': 'executor',
        'similarity_score': 0.8530
    }

    print("\nGenerating pretty print output...")
    output = executor.pretty_print_step_info(item, 3, 10)

    print("\nOutput:")
    print(output)

    # Verify output contains expected elements
    assert 'ITERATION 3/10' in output
    assert 'Create utility function' in output
    assert 'create_file' in output
    assert 'executor' in output
    assert '85.30%' in output

    print("\n✅ Pretty print test PASSED")
    return True


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("OUROBOROS AUTO-EXECUTION INTEGRATION TESTS")
    print("=" * 60)

    tests = [
        ("Tool Matching", test_ouroboros_tool_matching_integration),
        ("Build Only", test_execute_plan_build_only),
        ("Redis Storage", test_redis_integration),
        ("Pretty Print", test_pretty_print_output)
    ]

    results = []

    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"\n❌ {name} test FAILED: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, r, _ in results if r)
    total = len(results)

    for name, result, error in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")
        if error:
            print(f"         Error: {error}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
