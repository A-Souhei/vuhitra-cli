#!/usr/bin/env python3
"""
Web UI Server for Mirror+Vanisher Development MCP

Provides a user-friendly web interface for interacting with the MCP tools.
"""

import os
import sys
import json
import logging
from flask import Flask, render_template, request, jsonify

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from exploration import ExplorationTools
from architecture import ArchitectureTools
from chunking import ChunkingTools
from planning import PlanningTools
from code_generation import CodeGenerationTools
from testing import TestingTools
from quality_checks import QualityCheckTools
from security import SecurityTools
from mirror_vanisher import MirrorVanisherManager
from execute_plan import ExecutePlan
from errors_handler import handle_exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# Initialize manager and tools
manager = MirrorVanisherManager()
exploration = ExplorationTools(manager)
architecture = ArchitectureTools(manager)
chunking = ChunkingTools(manager)
planning = PlanningTools(manager)
code_generation = CodeGenerationTools(manager)
testing = TestingTools(manager)
quality = QualityCheckTools(manager)
security = SecurityTools(manager)

# Create a mock server instance for execute_plan
class MockServer:
    def __init__(self):
        self.tools = {
            'explore_structure': {'description': 'Explore and visualize the hierarchical directory structure'},
            'detect_tech_stack': {'description': 'Detect and identify the technology stack'},
            'find_entrypoints': {'description': 'Find and locate main entrypoints'},
            'analyze_architecture': {'description': 'Analyze and identify architectural patterns'},
            'map_dependencies': {'description': 'Map and analyze dependencies'},
            'identify_patterns': {'description': 'Identify and recognize design patterns'},
            'create_plan': {'description': 'Create detailed implementation plans'},
            'generate_diff': {'description': 'Generate safe, reviewable code diffs'},
            'apply_changes': {'description': 'Apply code changes with safety checks'},
            'run_tests': {'description': 'Execute and run automated tests'},
            'run_linter': {'description': 'Run static code analysis linters'},
            'security_audit': {'description': 'Complete security audit'},
        }

mock_server = MockServer()
execute_plan_tool = ExecutePlan(manager, server_instance=mock_server)


@app.route('/')
def index():
    """Main page."""
    return render_template('index.html')


@app.route('/api/mirror-vanishers')
def api_list_mirror_vanishers():
    """API: List all mirror+vanisher directories."""
    try:
        result = manager.list_mirror_vanishers()
        return jsonify(result)
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/mirror-vanishers'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/verify', methods=['POST'])
def api_verify():
    """API: Verify a path is a valid mirror+vanisher."""
    try:
        data = request.get_json()
        path = data.get('path')

        if not path:
            return jsonify({'success': False, 'error': 'Path required'}), 400

        result = manager.verify_mirror_vanisher(path)
        return jsonify(result)
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/verify'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/explore', methods=['POST'])
def api_explore():
    """API: Full exploration."""
    try:
        data = request.get_json()
        path = data.get('path')
        max_depth = data.get('max_depth', 3)

        if not path:
            return jsonify({'success': False, 'error': 'Path required'}), 400

        result = exploration.full_exploration(path, max_depth)
        return jsonify(result)
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/explore'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/architecture', methods=['POST'])
def api_architecture():
    """API: Analyze architecture."""
    try:
        data = request.get_json()
        path = data.get('path')

        if not path:
            return jsonify({'success': False, 'error': 'Path required'}), 400

        result = architecture.analyze_architecture(path)
        return jsonify(result)
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/architecture'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/plan', methods=['POST'])
def api_plan():
    """API: Create implementation plan."""
    try:
        data = request.get_json()
        path = data.get('path')
        task = data.get('task')
        context = data.get('context', {})

        if not path or not task:
            return jsonify({'success': False, 'error': 'Path and task required'}), 400

        result = planning.create_plan(path, task, context)
        return jsonify(result)
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/plan'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/test', methods=['POST'])
def api_test():
    """API: Run tests."""
    try:
        data = request.get_json()
        path = data.get('path')

        if not path:
            return jsonify({'success': False, 'error': 'Path required'}), 400

        result = testing.run_tests(path)
        return jsonify(result)
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/test'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/quality-check', methods=['POST'])
def api_quality_check():
    """API: Run quality checks."""
    try:
        data = request.get_json()
        path = data.get('path')
        fix = data.get('fix', False)

        if not path:
            return jsonify({'success': False, 'error': 'Path required'}), 400

        result = quality.full_quality_check(path, fix)
        return jsonify(result)
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/quality-check'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/security-audit', methods=['POST'])
def api_security_audit():
    """API: Run security audit."""
    try:
        data = request.get_json()
        path = data.get('path')

        if not path:
            return jsonify({'success': False, 'error': 'Path required'}), 400

        result = security.security_audit(path)
        return jsonify(result)
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/security-audit'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/workflow/feature', methods=['POST'])
def api_feature_workflow():
    """API: Complete feature workflow."""
    try:
        data = request.get_json()
        path = data.get('path')
        feature_description = data.get('feature_description')

        if not path or not feature_description:
            return jsonify({'success': False, 'error': 'Path and feature_description required'}), 400

        # Import workflow methods from server
        from server import MCPServer
        mcp_server = MCPServer()
        result = mcp_server.complete_feature_workflow(path, feature_description)
        return jsonify(result)
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/workflow/feature'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/workflow/bugfix', methods=['POST'])
def api_bugfix_workflow():
    """API: Bugfix workflow."""
    try:
        data = request.get_json()
        path = data.get('path')
        bug_description = data.get('bug_description')

        if not path or not bug_description:
            return jsonify({'success': False, 'error': 'Path and bug_description required'}), 400

        from server import MCPServer
        mcp_server = MCPServer()
        result = mcp_server.bugfix_workflow(path, bug_description)
        return jsonify(result)
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/workflow/bugfix'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/set-todo-list', methods=['POST'])
def api_set_todo_list():
    """API: Set TODO_list for testing execute_plan."""
    try:
        data = request.get_json()
        todo_list = data.get('todo_list', [])

        if not todo_list:
            return jsonify({'success': False, 'error': 'todo_list required'}), 400

        # Store in execute_plan_tool's memory
        execute_plan_tool.memory_todo_list = todo_list

        return jsonify({
            'success': True,
            'message': f'TODO_list set with {len(todo_list)} items',
            'todo_list_count': len(todo_list)
        })
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/set-todo-list'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/execute-plan', methods=['POST'])
def api_execute_plan():
    """API: Execute plan with ouroboros tool matching.

    This endpoint:
    1. Takes an optional TODO_list (or uses existing one)
    2. Runs ouroboros tool matching to create DETAILED_TODO_list
    3. Optionally auto-executes the matched steps
    """
    try:
        data = request.get_json() or {}

        # Optional: set TODO_list from request
        todo_list = data.get('todo_list')
        if todo_list:
            execute_plan_tool.memory_todo_list = todo_list

        # Get auto_execute flag (default True)
        auto_execute = data.get('auto_execute', True)

        # Execute the plan
        result = execute_plan_tool.execute_plan(auto_execute=auto_execute)

        return jsonify(result)
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/execute-plan'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ouroboros-match', methods=['POST'])
def api_ouroboros_match():
    """API: Run only ouroboros tool matching without execution.

    This is useful for testing the tool matching algorithm.
    """
    try:
        data = request.get_json() or {}

        # Get TODO_list from request
        todo_list = data.get('todo_list')
        if not todo_list:
            return jsonify({'success': False, 'error': 'todo_list required'}), 400

        # Run ouroboros matching
        detailed_list = execute_plan_tool.ouroboros_match_tools(todo_list)

        return jsonify({
            'success': True,
            'todo_list_count': len(todo_list),
            'detailed_todo_list_count': len(detailed_list),
            'DETAILED_TODO_list': detailed_list,
            'message': f'Ouroboros matched {len(detailed_list)} tools from {len(todo_list)} steps'
        })
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/ouroboros-match'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/exploiter', methods=['POST'])
def api_exploiter():
    """API: Run exploiter function to generate alternative plan.

    When a step fails, the exploiter generates an alternative approach.
    """
    try:
        data = request.get_json() or {}

        # Get required parameters
        failure_info = data.get('failure_info')
        todo_list = data.get('todo_list')

        if not failure_info or not todo_list:
            return jsonify({
                'success': False,
                'error': 'failure_info and todo_list required'
            }), 400

        # Run exploiter function
        new_detailed_list = execute_plan_tool.exploiter_function(failure_info, todo_list)

        return jsonify({
            'success': True,
            'original_todo_list_count': len(todo_list),
            'new_detailed_list_count': len(new_detailed_list),
            'DETAILED_TODO_list': new_detailed_list,
            'message': f'Exploiter generated alternative plan with {len(new_detailed_list)} steps'
        })
    except Exception as e:
        handle_exception(e, context={'endpoint': '/api/exploiter'})
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'mirror-vanisher-dev-mcp-ui',
        'version': '1.0.0'
    })


def main():
    """Run the UI server."""
    port = int(os.getenv('UI_PORT', 5100))
    host = os.getenv('UI_HOST', '0.0.0.0')

    logger.info(f"Starting Mirror+Vanisher Development MCP UI Server on {host}:{port}")
    app.run(host=host, port=port, debug=True)


if __name__ == '__main__':
    main()
