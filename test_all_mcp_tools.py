#!/usr/bin/env python3
"""
Comprehensive MCP Tools Test Script
Tests all tools inside the sandbox container
"""

import sys
import json
sys.path.insert(0, 'src')

from src.mirror_vanisher import MirrorVanisherManager
from src.exploration import ExplorationTools
from src.architecture import ArchitectureTools
from src.chunking import ChunkingTools
from src.planning import PlanningTools
from src.testing import TestingTools
from src.quality_checks import QualityCheckTools
from src.security import SecurityTools

def test_tool(name, func, *args, **kwargs):
    """Test a tool and print results"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print('='*60)
    try:
        result = func(*args, **kwargs)
        success = result.get('success', False)
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"Status: {status}")

        # Print relevant info
        if success:
            # Print a summary based on the result
            if 'structure' in result:
                print(f"Files found: {result['structure'].get('statistics', {}).get('total_files', 0)}")
            if 'tech_stack' in result:
                print(f"Primary language: {result['tech_stack'].get('primary_language', 'Unknown')}")
            if 'entrypoints' in result:
                print(f"Entrypoints: {len(result.get('entrypoints', []))}")
            if 'structure_type' in result:
                print(f"Architecture: {result.get('structure_type', 'Unknown')}")
            if 'plan' in result:
                print(f"Plan type: {result['plan'].get('type', 'Unknown')}")
                print(f"Steps: {len(result['plan'].get('steps', []))}")
            if 'all_checks_passed' in result:
                print(f"All checks passed: {result.get('all_checks_passed', False)}")
            if 'has_security_issues' in result:
                print(f"Security issues found: {result.get('has_security_issues', False)}")
        else:
            print(f"Error: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"Status: ❌ EXCEPTION")
        print(f"Error: {str(e)}")

# Initialize all tools
print("Initializing MCP Tools...")
manager = MirrorVanisherManager()
manager.sandbox_url = 'http://localhost:8000'

exploration = ExplorationTools(manager)
architecture = ArchitectureTools(manager)
chunking = ChunkingTools(manager)
planning = PlanningTools(manager)
testing_tools = TestingTools(manager)
quality = QualityCheckTools(manager)
security = SecurityTools(manager)

print("\n" + "="*60)
print("MCP TOOLS COMPREHENSIVE TEST")
print("="*60)

# Step 0: Verification
test_tool("list_mirror_vanishers", manager.list_mirror_vanishers)
test_tool("verify_mirror_vanisher", manager.verify_mirror_vanisher, "test-project")

# Step 1: Exploration
test_tool("explore_structure", exploration.explore_structure, "test-project", max_depth=3)
test_tool("detect_tech_stack", exploration.detect_tech_stack, "test-project")
test_tool("find_entrypoints", exploration.find_entrypoints, "test-project")
test_tool("full_exploration", exploration.full_exploration, "test-project", max_depth=3)

# Step 2: Architecture
test_tool("analyze_architecture", architecture.analyze_architecture, "test-project")
test_tool("map_dependencies", architecture.map_dependencies, "test-project")
test_tool("identify_patterns", architecture.identify_patterns, "test-project")

# Step 3: Chunking
test_tool("chunk_file", chunking.chunk_file, "test-project/calculator.py", chunk_size=50, overlap=10)
test_tool("chunk_directory", chunking.chunk_directory, "test-project", chunk_size=100)

# Step 4: Planning
test_tool("create_plan", planning.create_plan, "test-project", "Add input validation to calculator", {})

# Step 6: Testing
test_tool("run_tests", testing_tools.run_tests, "test-project")

# Step 7: Quality Checks
test_tool("run_linter", quality.run_linter, "test-project", fix=False)
test_tool("run_formatter", quality.run_formatter, "test-project", check_only=True)
test_tool("full_quality_check", quality.full_quality_check, "test-project", fix=False)

# Step 8: Security
test_tool("scan_secrets", security.scan_secrets, "test-project")
test_tool("security_audit", security.security_audit, "test-project")

print("\n" + "="*60)
print("TEST SUITE COMPLETE")
print("="*60)
