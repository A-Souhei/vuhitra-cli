"""
Execute Plan Tool - Automatic execution of TODO_list plans

This tool implements automatic plan execution by:
1. Retrieving TODO_list from Redis/memory
2. Using semantic similarity to match steps with available tools
3. Building DETAILED_TODO_list with tool mappings
4. Automatically executing all items without ratings/heuristics
"""

import logging
import json
import redis
import numpy as np
from redis.exceptions import RedisError
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import sys
import os
from pathlib import Path as PathLib

# Add project root to path for imports
project_root = PathLib(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from errors_handler import handle_exception
from src.utils.embedding_utils import EmbeddingCacheMixin, cosine_similarity
from src.utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)

# Configuration defaults
REDIS_HOST = 'localhost'
REDIS_PORT = 16379  # Default to docker-compose mapped port
REDIS_PASSWORD = None
TODO_LIST_KEY = "mcp:mirror_vanisher:todo_list"
DETAILED_TODO_LIST_KEY = "mcp:mirror_vanisher:detailed_todo_list"
SIMILARITY_THRESHOLD = 0.3  # Minimum similarity score to consider a match

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
    handle_exception(e, context={'function': 'load_configuration', 'module': 'execute_plan'})


class ExecutePlan(EmbeddingCacheMixin):
    """Tool for automatic plan execution with semantic tool matching."""

    def __init__(self, manager, server_instance=None):
        """Initialize execute plan tool.

        Args:
            manager: MirrorVanisherManager instance
            server_instance: Optional reference to the MCP server for accessing tools
        """
        self.manager = manager
        self.server_instance = server_instance

        # Initialize config loader
        self.config = ConfigLoader()

        # Initialize Redis connection
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
            logger.info("Redis connection established successfully for execute_plan")
        except RedisError as e:
            logger.warning(f"Redis not available: {e}. Execute plan will use memory fallback.")
            handle_exception(e, context={'function': '__init__', 'class': 'ExecutePlan'})

        # Don't call _init_redis from EmbeddingCacheMixin as we're using our own Redis connection
        # The mixin will use self.redis_client if it's set

        # Get transformer URL from config
        transformer_config = self.config.get('transformer', default={})
        protocol = transformer_config.get('protocol', 'http')
        host = transformer_config.get('host', 'localhost')
        port = transformer_config.get('port', 16050)
        self.transformer_url = f"{protocol}://{host}:{port}"

        # In-memory fallback for TODO lists
        self.memory_todo_list = []
        self.memory_detailed_todo_list = []

        # Cache for tool embeddings
        self.tool_embeddings_cache = {}

    def get_mirror_vanisher_tools(self, exclude_tools: List[str] = None) -> List[Dict[str, Any]]:
        """Get all tools from Mirror+Vanisher Development MCP.

        Args:
            exclude_tools: List of tool names to exclude

        Returns:
            List of tool dictionaries with name and description
        """
        exclude_tools = exclude_tools or []
        tools = []

        if self.server_instance and hasattr(self.server_instance, 'tools'):
            for tool_name, tool_info in self.server_instance.tools.items():
                if tool_name not in exclude_tools:
                    tools.append({
                        'name': tool_name,
                        'description': tool_info.get('description', ''),
                        'inputSchema': tool_info.get('inputSchema', {})
                    })

        return tools

    def get_executor_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from Executor MCP.

        This method would ideally connect to the Executor MCP server.
        For now, we'll return a predefined list based on known tools.

        Returns:
            List of tool dictionaries with name and description
        """
        # TODO: In production, this should dynamically fetch from Executor MCP
        # For now, we'll use a static list based on the Executor MCP tools we know
        executor_tools = [
            {
                'name': 'execute_python_code',
                'description': 'Execute and run Python scripts with command-line arguments, capturing output and return code'
            },
            {
                'name': 'execute_shell_command',
                'description': 'Execute shell commands and bash scripts, capturing output and return code'
            },
            {
                'name': 'execute_javascript_code',
                'description': 'Execute JavaScript or Node.js scripts with command-line arguments'
            },
            {
                'name': 'execute_code_snippet',
                'description': 'Execute code snippets dynamically in Python, JavaScript, or Bash'
            },
            {
                'name': 'create_file',
                'description': 'Create and write a new file with specified content'
            },
            {
                'name': 'update_file',
                'description': 'Update and replace the complete content of an existing file'
            },
            {
                'name': 'append_to_file',
                'description': 'Append content to the end of an existing file'
            },
            {
                'name': 'delete_file',
                'description': 'Delete and remove an existing file'
            },
            {
                'name': 'copy_file',
                'description': 'Copy a file to a new location'
            },
            {
                'name': 'move_file',
                'description': 'Move and relocate a file to a new location'
            },
            {
                'name': 'install_pip_packages',
                'description': 'Install Python packages using pip package manager'
            },
            {
                'name': 'install_npm_packages',
                'description': 'Install Node.js packages using npm package manager'
            },
            {
                'name': 'run_build_command',
                'description': 'Execute build commands including make, gradle, maven, or custom build scripts'
            },
            {
                'name': 'compile_python',
                'description': 'Compile Python source files to bytecode for syntax validation'
            },
            {
                'name': 'create_virtual_env',
                'description': 'Create a Python virtual environment for isolated package management'
            },
            {
                'name': 'install_in_virtual_env',
                'description': 'Install Python packages in an existing virtual environment'
            },
            {
                'name': 'run_in_virtual_env',
                'description': 'Run commands or scripts inside a Python virtual environment'
            },
            {
                'name': 'run_docker_build',
                'description': 'Build Docker images from Dockerfile'
            },
            {
                'name': 'create_directory',
                'description': 'Create a new directory or directory structure'
            },
            {
                'name': 'create_directory_structure',
                'description': 'Create complex directory structures from nested configuration'
            },
            {
                'name': 'delete_directory',
                'description': 'Delete and remove a directory and its contents'
            },
            {
                'name': 'copy_directory',
                'description': 'Copy a directory and all its contents to a new location'
            },
            {
                'name': 'move_directory',
                'description': 'Move a directory and its contents to a new location'
            },
            {
                'name': 'list_directory_contents',
                'description': 'List and enumerate contents of a directory'
            }
        ]

        return executor_tools

    def get_or_generate_tool_embedding(self, tool_name: str, tool_description: str) -> Optional[np.ndarray]:
        """Get or generate embedding for a tool description.

        Args:
            tool_name: Name of the tool
            tool_description: Description of the tool

        Returns:
            Embedding vector or None if generation fails
        """
        # Check cache first
        if tool_name in self.tool_embeddings_cache:
            return self.tool_embeddings_cache[tool_name]

        # Generate embedding for tool description
        embedding = self._generate_embedding(tool_description)

        if embedding is not None:
            self.tool_embeddings_cache[tool_name] = embedding

        return embedding

    def find_matching_tools(
        self,
        step_text: str,
        tools: List[Dict[str, Any]],
        threshold: float = SIMILARITY_THRESHOLD
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Find tools that match a step using semantic similarity or keyword matching.

        Args:
            step_text: Text describing the step
            tools: List of tool dictionaries
            threshold: Minimum similarity score

        Returns:
            List of (tool, similarity_score) tuples, sorted by score descending
        """
        try:
            # Try semantic similarity first
            step_embedding = self._generate_embedding(step_text)
            
            if step_embedding is not None:
                # Use semantic matching
                matches = []

                for tool in tools:
                    tool_name = tool.get('name', '')
                    tool_description = tool.get('description', '')

                    # Get or generate tool embedding
                    tool_embedding = self.get_or_generate_tool_embedding(tool_name, tool_description)

                    if tool_embedding is None:
                        continue

                    # Calculate cosine similarity
                    similarity = cosine_similarity(step_embedding, tool_embedding)

                    if similarity >= threshold:
                        matches.append((tool, similarity))

                # Sort by similarity score descending
                matches.sort(key=lambda x: x[1], reverse=True)
                return matches
            else:
                # Fallback to keyword matching when embeddings are unavailable
                logger.warning(f"Embeddings unavailable, using keyword matching for: {step_text}")
                return self._keyword_match_tools(step_text, tools, threshold)

        except Exception as e:
            handle_exception(e, context={
                'function': 'find_matching_tools',
                'step_text': step_text[:100]
            })
            return []

    def _keyword_match_tools(
        self,
        step_text: str,
        tools: List[Dict[str, Any]],
        threshold: float = 0.1  # Lower threshold for keyword matching
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Fallback keyword-based tool matching when embeddings are unavailable.

        Args:
            step_text: Text describing the step
            tools: List of tool dictionaries
            threshold: Minimum score threshold (0.0-1.0), default 0.1 for keyword matching

        Returns:
            List of (tool, score) tuples, sorted by score descending
        """
        step_words = set(step_text.lower().split())
        matches = []

        for tool in tools:
            tool_name = tool.get('name', '')
            tool_description = tool.get('description', '')
            
            # Combine tool name and description
            tool_text = f"{tool_name} {tool_description}".lower()
            tool_words = set(tool_text.split())

            # Calculate Jaccard similarity (intersection over union)
            if not tool_words:
                continue

            intersection = step_words & tool_words
            union = step_words | tool_words
            
            score = len(intersection) / len(union) if union else 0.0

            if score >= threshold:
                matches.append((tool, score))

        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f"Keyword matching found {len(matches)} matches (threshold={threshold}) for: {step_text[:50]}")
        
        return matches

    def extract_parameters_from_step(
        self,
        step: Dict[str, Any],
        tool_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract parameters from a step based on tool schema.

        Args:
            step: TODO_list step item
            tool_schema: Tool's inputSchema

        Returns:
            Dictionary of parameters
        """
        # This is a simplified parameter extraction
        # In a production system, this would be more sophisticated
        params = {}

        required_params = tool_schema.get('required', [])
        properties = tool_schema.get('properties', {})

        # Extract common parameters from step details
        step_details = step.get('details', '')
        step_action = step.get('action', '')

        # Try to extract path (common in many tools)
        if 'path' in properties:
            # Use a default path or extract from context
            params['path'] = '.'  # Default to current directory

        # Try to extract other parameters from step text
        # This is a placeholder - a real implementation would use NLP/LLM
        combined_text = f"{step_action} {step_details}"

        return params

    def build_detailed_todo_list(
        self,
        todo_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build DETAILED_TODO_list by matching steps with tools.

        Args:
            todo_list: Original TODO_list from create_plan

        Returns:
            DETAILED_TODO_list with tool mappings
        """
        detailed_list = []

        # Get available tools (exclude create_plan)
        mirror_vanisher_tools = self.get_mirror_vanisher_tools(exclude_tools=['create_plan'])
        executor_tools = self.get_executor_tools()

        logger.info(f"Processing {len(todo_list)} TODO items")
        logger.info(f"Available Mirror+Vanisher tools: {len(mirror_vanisher_tools)}")
        logger.info(f"Available Executor tools: {len(executor_tools)}")

        for idx, step in enumerate(todo_list):
            step_number = step.get('step_number', idx + 1)
            action = step.get('action', '')
            details = step.get('details', '')

            # Combine action and details for matching
            step_text = f"{action}. {details}"

            logger.info(f"Processing step {step_number}: {action}")

            # Find matching Mirror+Vanisher tools
            mv_matches = self.find_matching_tools(step_text, mirror_vanisher_tools)

            # Process each matched tool
            for tool, similarity in mv_matches:
                tool_name = tool.get('name')
                tool_schema = tool.get('inputSchema', {})

                logger.info(f"  Matched Mirror+Vanisher tool: {tool_name} (similarity: {similarity:.2f})")

                # Extract parameters
                parameters = self.extract_parameters_from_step(step, tool_schema)

                # Add to detailed list
                detailed_item = {
                    'step_number': step_number,
                    'original_action': action,
                    'original_details': details,
                    'tool_type': 'mirror_vanisher',
                    'tool_name': tool_name,
                    'tool_description': tool.get('description', ''),
                    'parameters': parameters,
                    'similarity_score': similarity,
                    'status': 'pending',
                    'execution_result': None
                }

                detailed_list.append(detailed_item)

                # Also check if we should use an Executor tool
                executor_matches = self.find_matching_tools(step_text, executor_tools)

                for exec_tool, exec_similarity in executor_matches:
                    exec_tool_name = exec_tool.get('name')

                    logger.info(f"    Also matched Executor tool: {exec_tool_name} (similarity: {exec_similarity:.2f})")

                    # Add executor tool to detailed list
                    exec_detailed_item = {
                        'step_number': step_number,
                        'original_action': action,
                        'original_details': details,
                        'tool_type': 'executor',
                        'tool_name': exec_tool_name,
                        'tool_description': exec_tool.get('description', ''),
                        'parameters': {},  # Would need to extract executor-specific params
                        'similarity_score': exec_similarity,
                        'status': 'pending',
                        'execution_result': None
                    }

                    detailed_list.append(exec_detailed_item)

        logger.info(f"Built DETAILED_TODO_list with {len(detailed_list)} items")

        return detailed_list

    def save_detailed_todo_list(self, detailed_list: List[Dict[str, Any]]) -> bool:
        """Save DETAILED_TODO_list to Redis with memory fallback.

        Args:
            detailed_list: DETAILED_TODO_list to save

        Returns:
            True if saved successfully
        """
        try:
            # Always save to memory fallback
            self.memory_detailed_todo_list = detailed_list

            # Try to save to Redis if available
            if self.redis_available and self.redis_client:
                try:
                    self.redis_client.set(DETAILED_TODO_LIST_KEY, json.dumps(detailed_list))
                    logger.info("DETAILED_TODO_list saved to Redis")
                    return True
                except RedisError as e:
                    logger.warning(f"Failed to save DETAILED_TODO_list to Redis: {e}")
                    handle_exception(e, context={'function': 'save_detailed_todo_list'})
            else:
                logger.info("DETAILED_TODO_list saved to memory (Redis not available)")

            return True

        except Exception as e:
            handle_exception(e, context={'function': 'save_detailed_todo_list'})
            return False

    def get_todo_list(self) -> List[Dict[str, Any]]:
        """Get TODO_list from Redis with memory fallback.

        Returns:
            TODO_list or empty list if not found
        """
        try:
            # Try Redis first
            if self.redis_available and self.redis_client:
                try:
                    todo_list_json = self.redis_client.get(TODO_LIST_KEY)
                    if todo_list_json:
                        # Redis client has decode_responses=True, so todo_list_json is already a string
                        return json.loads(todo_list_json)
                except RedisError as e:
                    logger.warning(f"Failed to get TODO_list from Redis: {e}")
                    handle_exception(e, context={'function': 'get_todo_list'})

            # Fallback to memory
            if self.memory_todo_list:
                return self.memory_todo_list

            return []

        except Exception as e:
            handle_exception(e, context={'function': 'get_todo_list'})
            return []

    def execute_plan(self, auto_execute: bool = True) -> Dict[str, Any]:
        """Execute the plan by building and optionally running DETAILED_TODO_list.

        Args:
            auto_execute: If True, automatically execute all items. If False, only build the list.

        Returns:
            Dictionary with execution results
        """
        try:
            logger.info("Starting execute_plan")

            # Step 1: Get TODO_list
            todo_list = self.get_todo_list()

            if not todo_list:
                return {
                    'success': False,
                    'error': 'No TODO_list found. Please create a plan first using create_plan tool.'
                }

            logger.info(f"Retrieved TODO_list with {len(todo_list)} items")

            # Step 2: Build DETAILED_TODO_list with semantic matching
            detailed_list = self.build_detailed_todo_list(todo_list)

            if not detailed_list:
                return {
                    'success': False,
                    'error': 'No tool matches found for TODO_list steps. Check if steps are specific enough.'
                }

            # Step 3: Save DETAILED_TODO_list
            save_success = self.save_detailed_todo_list(detailed_list)

            if not save_success:
                logger.warning("Failed to save DETAILED_TODO_list, but continuing")

            # Step 4: Execute if auto_execute is True
            execution_results = []

            if auto_execute:
                logger.info("Starting automatic execution of DETAILED_TODO_list")

                for idx, item in enumerate(detailed_list):
                    logger.info(f"Executing item {idx + 1}/{len(detailed_list)}: {item['tool_name']}")

                    # TODO: Implement actual tool execution
                    # This would call the actual tool handlers with parameters
                    # For now, we'll mark it as ready for execution

                    execution_result = {
                        'item_index': idx,
                        'tool_name': item['tool_name'],
                        'tool_type': item['tool_type'],
                        'status': 'ready_for_execution',
                        'message': 'Tool execution would happen here in full implementation'
                    }

                    execution_results.append(execution_result)

                    # Update item status
                    item['status'] = 'ready_for_execution'
                    item['execution_result'] = execution_result

                # Save updated detailed list
                self.save_detailed_todo_list(detailed_list)

            # Return results
            return {
                'success': True,
                'todo_list_count': len(todo_list),
                'detailed_todo_list_count': len(detailed_list),
                'detailed_todo_list': detailed_list,
                'auto_execute': auto_execute,
                'execution_results': execution_results if auto_execute else [],
                'message': f'Successfully built DETAILED_TODO_list with {len(detailed_list)} items' +
                          (f' and executed {len(execution_results)} items' if auto_execute else '')
            }

        except Exception as e:
            handle_exception(e, context={'function': 'execute_plan'})
            return {'success': False, 'error': str(e)}
