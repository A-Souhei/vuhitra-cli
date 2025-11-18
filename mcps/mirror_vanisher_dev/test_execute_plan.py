#!/usr/bin/env python3
"""
Test script for execute_plan tool

This script tests the execute_plan functionality by:
1. Creating a sample TODO_list
2. Testing semantic matching with tools
3. Building DETAILED_TODO_list
4. Verifying storage in Redis/memory
"""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from execute_plan import ExecutePlan
from mirror_vanisher import MirrorVanisherManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockServer:
    """Mock MCP server for testing."""

    def __init__(self):
        """Initialize mock server with sample tools."""
        self.tools = {
            'explore_structure': {
                'description': 'Explore and visualize directory structure and file organization',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string', 'description': 'Path to explore'},
                        'max_depth': {'type': 'integer', 'description': 'Maximum depth'}
                    },
                    'required': ['path']
                }
            },
            'detect_tech_stack': {
                'description': 'Detect technology stack, programming languages, and frameworks',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string', 'description': 'Path to analyze'}
                    },
                    'required': ['path']
                }
            },
            'generate_tests': {
                'description': 'Generate test templates and testing recommendations for source code files',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'file_path': {'type': 'string', 'description': 'File to test'},
                        'test_type': {'type': 'string', 'enum': ['unit', 'integration', 'edge']}
                    },
                    'required': ['file_path']
                }
            },
            'run_linter': {
                'description': 'Run static code analysis linters to detect code quality issues',
                'inputSchema': {
                    'type': 'object',
                    'properties': {
                        'path': {'type': 'string', 'description': 'Path to lint'},
                        'fix': {'type': 'boolean', 'description': 'Auto-fix issues'}
                    },
                    'required': ['path']
                }
            }
        }


def test_execute_plan():
    """Test execute_plan functionality."""

    logger.info("=" * 80)
    logger.info("TESTING EXECUTE_PLAN TOOL")
    logger.info("=" * 80)

    # Initialize components
    logger.info("\n1. Initializing components...")
    manager = MirrorVanisherManager()

    # Create mock server
    mock_server = MockServer()
    execute_plan_tool = ExecutePlan(manager, server_instance=mock_server)

    logger.info("✓ Components initialized successfully")

    # Create a sample TODO_list
    logger.info("\n2. Creating sample TODO_list...")
    sample_todo_list = [
        {
            'step_number': 1,
            'action': 'Explore project structure',
            'details': 'Understand the directory layout and file organization',
            'status': 'pending'
        },
        {
            'step_number': 2,
            'action': 'Detect technology stack',
            'details': 'Identify programming languages and frameworks used',
            'status': 'pending'
        },
        {
            'step_number': 3,
            'action': 'Generate unit tests',
            'details': 'Create test templates for the main module',
            'status': 'pending'
        },
        {
            'step_number': 4,
            'action': 'Run code quality checks',
            'details': 'Execute linter to find code quality issues',
            'status': 'pending'
        }
    ]

    # Store TODO_list in memory fallback for testing
    execute_plan_tool.memory_todo_list = sample_todo_list

    logger.info(f"✓ Created TODO_list with {len(sample_todo_list)} items:")
    for item in sample_todo_list:
        logger.info(f"  - Step {item['step_number']}: {item['action']}")

    # Test getting Mirror+Vanisher tools
    logger.info("\n3. Testing tool retrieval...")
    mv_tools = execute_plan_tool.get_mirror_vanisher_tools(exclude_tools=['create_plan'])
    executor_tools = execute_plan_tool.get_executor_tools()

    logger.info(f"✓ Retrieved {len(mv_tools)} Mirror+Vanisher tools")
    logger.info(f"✓ Retrieved {len(executor_tools)} Executor tools")

    # Test semantic matching
    logger.info("\n4. Testing semantic matching...")
    logger.info("Note: This requires transformer service to be running")
    logger.info("If transformer service is not available, matching will be skipped")

    try:
        # Test with first TODO item
        test_step = sample_todo_list[0]
        step_text = f"{test_step['action']}. {test_step['details']}"

        matches = execute_plan_tool.find_matching_tools(step_text, mv_tools)

        if matches:
            logger.info(f"✓ Found {len(matches)} matching tools for step 1:")
            for tool, similarity in matches[:3]:  # Show top 3
                logger.info(f"  - {tool['name']} (similarity: {similarity:.3f})")
        else:
            logger.warning("⚠ No matches found (transformer service may be unavailable)")

    except Exception as e:
        logger.warning(f"⚠ Semantic matching test skipped: {e}")

    # Test building DETAILED_TODO_list
    logger.info("\n5. Testing DETAILED_TODO_list generation...")

    try:
        detailed_list = execute_plan_tool.build_detailed_todo_list(sample_todo_list)

        logger.info(f"✓ Built DETAILED_TODO_list with {len(detailed_list)} items")

        if detailed_list:
            logger.info("\nSample detailed items:")
            for item in detailed_list[:3]:  # Show first 3
                logger.info(f"  - Step {item['step_number']}: {item['tool_name']} ({item['tool_type']})")
                logger.info(f"    Similarity: {item['similarity_score']:.3f}")
        else:
            logger.warning("⚠ No detailed items generated (transformer service may be unavailable)")

    except Exception as e:
        logger.error(f"✗ Error building DETAILED_TODO_list: {e}")
        import traceback
        traceback.print_exc()

    # Test saving DETAILED_TODO_list
    logger.info("\n6. Testing DETAILED_TODO_list storage...")

    try:
        # Create a sample detailed list for testing
        test_detailed_list = [
            {
                'step_number': 1,
                'original_action': 'Explore project structure',
                'original_details': 'Understand the directory layout',
                'tool_type': 'mirror_vanisher',
                'tool_name': 'explore_structure',
                'parameters': {'path': '.'},
                'similarity_score': 0.85,
                'status': 'pending'
            }
        ]

        success = execute_plan_tool.save_detailed_todo_list(test_detailed_list)

        if success:
            logger.info("✓ DETAILED_TODO_list saved successfully")

            # Verify it's in memory
            if execute_plan_tool.memory_detailed_todo_list:
                logger.info("✓ DETAILED_TODO_list stored in memory fallback")
        else:
            logger.warning("⚠ Failed to save DETAILED_TODO_list")

    except Exception as e:
        logger.error(f"✗ Error saving DETAILED_TODO_list: {e}")

    # Test execute_plan method
    logger.info("\n7. Testing execute_plan method (without auto-execution)...")

    try:
        result = execute_plan_tool.execute_plan(auto_execute=False)

        if result.get('success'):
            logger.info("✓ execute_plan completed successfully")
            logger.info(f"  - TODO_list items: {result.get('todo_list_count', 0)}")
            logger.info(f"  - DETAILED_TODO_list items: {result.get('detailed_todo_list_count', 0)}")
            logger.info(f"  - Message: {result.get('message', '')}")
        else:
            logger.warning(f"⚠ execute_plan returned error: {result.get('error', 'Unknown')}")

    except Exception as e:
        logger.error(f"✗ Error executing plan: {e}")
        import traceback
        traceback.print_exc()

    logger.info("\n" + "=" * 80)
    logger.info("TEST COMPLETED")
    logger.info("=" * 80)
    logger.info("\nNote: Some tests may fail if:")
    logger.info("  - Transformer service is not running")
    logger.info("  - Redis is not available (memory fallback will be used)")
    logger.info("  - Configuration files are missing")


if __name__ == '__main__':
    test_execute_plan()
