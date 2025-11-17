"""
Planning Tools - Step 4 of the Pillars Methodology

Tools for creating atomic, file-specific implementation plans.
"""

import logging
import json
import redis
from redis.exceptions import RedisError
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional

from errors_handler import handle_exception

logger = logging.getLogger(__name__)

# Configuration defaults
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_PASSWORD = None
TODO_LIST_KEY = "mcp:mirror_vanisher:todo_list"

# Load configuration with error handling
try:
    config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"
    secrets_path = Path(__file__).parent.parent.parent.parent / "secrets.yaml"
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if config and 'redis' in config:
                REDIS_HOST = config['redis'].get('host', REDIS_HOST)
                REDIS_PORT = config['redis'].get('port', REDIS_PORT)
    else:
        logger.warning(f"Configuration file not found: {config_path}, using defaults")
    
    # Try to load secrets, fallback to no password if not available
    if secrets_path.exists():
        with open(secrets_path, 'r') as f:
            secrets = yaml.safe_load(f)
            if secrets and 'redis' in secrets:
                REDIS_PASSWORD = secrets['redis'].get('password')
    else:
        logger.info(f"Secrets file not found: {secrets_path}, using no password")
        
except (yaml.YAMLError, IOError) as e:
    logger.error(f"Error loading configuration: {e}, using defaults")
    handle_exception(e, context={'function': 'load_configuration', 'module': 'planning'})


class PlanningTools:
    """Tools for creating and validating implementation plans."""

    def __init__(self, manager):
        """Initialize planning tools."""
        self.manager = manager
        # Initialize Redis connection with validation (optional for testing)
        self.redis_client = None
        self.redis_available = False
        
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=0,
                password=REDIS_PASSWORD,
                decode_responses=True
            )
            # Test the connection
            self.redis_client.ping()
            self.redis_available = True
            logger.info("Redis connection established successfully")
        except RedisError as e:
            logger.warning(f"Redis not available: {e}. TODO_list persistence disabled.")
            handle_exception(e, context={'function': '__init__', 'class': 'PlanningTools'})
            # Don't raise - allow initialization to continue without Redis

    def create_plan(self, path: str, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create atomic, file-specific implementation plan.

        Args:
            path: Working directory
            task: Task description
            context: Additional context (exploration, architecture, etc.)

        Returns:
            Dictionary with implementation plan
        """
        try:
            resolved_path = self.manager.resolve_path(path)
            if not resolved_path:
                return {'success': False, 'error': f'Path not found: {path}'}

            context = context or {}

            # Generate plan structure
            plan = {
                'task': task,
                'path': str(resolved_path),
                'steps': [],
                'estimated_files_to_modify': [],
                'potential_risks': [],
                'testing_requirements': []
            }

            # Analyze task type
            task_lower = task.lower()

            if 'fix' in task_lower or 'bug' in task_lower:
                plan['type'] = 'bugfix'
                plan['steps'] = [
                    {'step': 1, 'action': 'Identify root cause', 'details': 'Locate the source of the bug'},
                    {'step': 2, 'action': 'Create test case', 'details': 'Write test that reproduces the bug'},
                    {'step': 3, 'action': 'Implement fix', 'details': 'Apply minimal changes to fix the bug'},
                    {'step': 4, 'action': 'Verify fix', 'details': 'Ensure test passes and no regressions'}
                ]
                plan['testing_requirements'] = ['Unit test for bug reproduction', 'Regression tests']

            elif 'refactor' in task_lower:
                plan['type'] = 'refactoring'
                plan['steps'] = [
                    {'step': 1, 'action': 'Document current behavior', 'details': 'Write tests for existing functionality'},
                    {'step': 2, 'action': 'Create refactoring plan', 'details': 'Identify code to change'},
                    {'step': 3, 'action': 'Apply refactoring', 'details': 'Make incremental changes'},
                    {'step': 4, 'action': 'Verify behavior unchanged', 'details': 'Run all tests'}
                ]
                plan['testing_requirements'] = ['All existing tests must pass']
                plan['potential_risks'] = ['Behavior changes', 'Performance regression']

            elif 'add' in task_lower or 'implement' in task_lower or 'feature' in task_lower:
                plan['type'] = 'feature_implementation'
                plan['steps'] = [
                    {'step': 1, 'action': 'Design API/interface', 'details': 'Define function signatures and data structures'},
                    {'step': 2, 'action': 'Implement core logic', 'details': 'Write main functionality'},
                    {'step': 3, 'action': 'Add error handling', 'details': 'Handle edge cases and errors'},
                    {'step': 4, 'action': 'Write tests', 'details': 'Unit and integration tests'},
                    {'step': 5, 'action': 'Update documentation', 'details': 'Add docstrings and comments'}
                ]
                plan['testing_requirements'] = ['Unit tests', 'Integration tests', 'Edge case tests']

            else:
                plan['type'] = 'general'
                plan['steps'] = [
                    {'step': 1, 'action': 'Analyze requirements', 'details': 'Understand what needs to be done'},
                    {'step': 2, 'action': 'Plan changes', 'details': 'Identify files to modify'},
                    {'step': 3, 'action': 'Implement changes', 'details': 'Make code changes'},
                    {'step': 4, 'action': 'Test changes', 'details': 'Verify functionality'}
                ]

            # Add context-aware recommendations
            if context.get('exploration'):
                tech_stack = context['exploration'].get('tech_stack', {})
                plan['detected_tech_stack'] = tech_stack.get('primary_language', 'Unknown')

            if context.get('architecture'):
                plan['architecture_pattern'] = context['architecture'].get('structure_type', 'Unknown')

            # Generate TODO_list from plan steps
            todo_list = []
            for step in plan['steps']:
                todo_item = {
                    'step_number': step['step'],
                    'action': step['action'],
                    'details': step['details'],
                    'status': 'pending'
                }
                todo_list.append(todo_item)

            # Store TODO_list in Redis (overwrite previous) with error handling
            if self.redis_available and self.redis_client:
                try:
                    self.redis_client.set(TODO_LIST_KEY, json.dumps(todo_list))
                except RedisError as e:
                    logger.warning(f"Failed to store TODO_list in Redis: {e}")
                    # Continue even if Redis storage fails - plan is still returned
            else:
                logger.debug("Redis not available, skipping TODO_list storage")

            # Create beautiful formatted plan output
            formatted_plan = self._format_plan_beautifully(plan, todo_list)

            # Log the beautiful plan
            logger.info(f"\n{formatted_plan}")

            return {
                'success': True,
                'plan': plan,
                'TODO_list': todo_list,
                'formatted_plan': formatted_plan,
                'message': f'Created {plan["type"]} plan with {len(plan["steps"])} steps'
            }

        except Exception as e:
            handle_exception(e, context={'function': 'create_plan', 'path': path, 'task': task})
            return {'success': False, 'error': str(e)}

    def _format_plan_beautifully(self, plan: Dict[str, Any], todo_list: List[Dict[str, Any]]) -> str:
        """Format plan in a beautiful, readable way.

        Args:
            plan: The plan dictionary
            todo_list: The TODO list items

        Returns:
            Beautifully formatted plan string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("📋 IMPLEMENTATION PLAN")
        lines.append("=" * 80)
        lines.append("")

        # Task information
        lines.append(f"📌 Task: {plan['task']}")
        lines.append(f"📂 Path: {plan['path']}")
        lines.append(f"🏷️  Type: {plan['type'].upper().replace('_', ' ')}")
        lines.append("")

        # Tech stack if available
        if 'detected_tech_stack' in plan:
            lines.append(f"💻 Tech Stack: {plan['detected_tech_stack']}")

        # Architecture pattern if available
        if 'architecture_pattern' in plan:
            lines.append(f"🏗️  Architecture: {plan['architecture_pattern']}")

        if 'detected_tech_stack' in plan or 'architecture_pattern' in plan:
            lines.append("")

        # Steps
        lines.append("📝 STEPS:")
        lines.append("-" * 80)
        for item in todo_list:
            lines.append(f"  • {item['action']}")
            lines.append(f"    ◦ {item['details']}")
            lines.append("")

        # Testing requirements
        if plan.get('testing_requirements'):
            lines.append("🧪 TESTING REQUIREMENTS:")
            lines.append("-" * 80)
            for req in plan['testing_requirements']:
                lines.append(f"  • {req}")
            lines.append("")

        # Potential risks
        if plan.get('potential_risks'):
            lines.append("⚠️  POTENTIAL RISKS:")
            lines.append("-" * 80)
            for risk in plan['potential_risks']:
                lines.append(f"  • {risk}")
            lines.append("")

        # Files to modify
        if plan.get('estimated_files_to_modify'):
            lines.append("📄 ESTIMATED FILES TO MODIFY:")
            lines.append("-" * 80)
            for file_path in plan['estimated_files_to_modify']:
                lines.append(f"  • {file_path}")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)

    def get_todo_list(self) -> Dict[str, Any]:
        """Get the current TODO_list from Redis storage.

        Returns:
            Dictionary containing the TODO_list
        """
        try:
            # Check if Redis is available
            if not self.redis_available or not self.redis_client:
                logger.warning("Redis not available, returning empty TODO_list")
                return {
                    'success': True,
                    'TODO_list': [],
                    'count': 0,
                    'message': 'Redis not available'
                }
            
            # Retrieve TODO_list from Redis with proper error handling
            try:
                todo_list_json = self.redis_client.get(TODO_LIST_KEY)
            except RedisError as e:
                logger.error(f"Redis connection error when retrieving TODO_list: {e}")
                return {
                    'success': False,
                    'error': f'Redis connection error: {str(e)}'
                }
            
            if todo_list_json:
                try:
                    # Type hint: with decode_responses=True, Redis returns str
                    todo_list = json.loads(str(todo_list_json))
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing error for TODO_list: {e}")
                    return {
                        'success': False,
                        'error': f'JSON parsing error: {str(e)}'
                    }
            else:
                todo_list = []
            
            return {
                'success': True,
                'TODO_list': todo_list,
                'count': len(todo_list)
            }
        except Exception as e:
            handle_exception(e, context={'function': 'get_todo_list'})
            return {'success': False, 'error': str(e)}

    def validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a plan for feasibility and completeness.

        Args:
            plan: Plan to validate

        Returns:
            Dictionary with validation results
        """
        try:
            issues = []
            warnings = []

            # Check required fields
            if 'steps' not in plan or not plan['steps']:
                issues.append('Plan has no steps defined')

            if 'task' not in plan or not plan['task']:
                issues.append('Plan has no task description')

            # Check step structure
            if 'steps' in plan:
                for i, step in enumerate(plan['steps'], 1):
                    if 'action' not in step:
                        issues.append(f'Step {i} missing action')
                    if 'details' not in step:
                        warnings.append(f'Step {i} missing details')

            # Check for testing
            if 'testing_requirements' not in plan or not plan['testing_requirements']:
                warnings.append('No testing requirements specified')

            is_valid = len(issues) == 0

            return {
                'success': True,
                'is_valid': is_valid,
                'issues': issues,
                'warnings': warnings,
                'message': 'Plan is valid' if is_valid else 'Plan has issues'
            }

        except Exception as e:
            handle_exception(e, context={'function': 'validate_plan'})
            return {'success': False, 'error': str(e)}
