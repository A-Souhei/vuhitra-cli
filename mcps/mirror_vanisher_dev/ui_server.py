#!/usr/bin/env python3
"""
Web UI Server for Mirror+Vanisher Development MCP

Provides a user-friendly web interface for interacting with the MCP tools.
"""

import os
import sys
import json
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.exploration import ExplorationTools
from src.architecture import ArchitectureTools
from src.chunking import ChunkingTools
from src.planning import PlanningTools
from src.code_generation import CodeGenerationTools
from src.testing import TestingTools
from src.quality_checks import QualityCheckTools
from src.security import SecurityTools
from src.mirror_vanisher import MirrorVanisherManager
from src.errors_handler import handle_exception

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
