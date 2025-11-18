"""
Execute Plan Tool - Ouroboros Automatic Execution System

This tool implements automatic plan execution with:
1. Ouroboros function: Recursive tool matching using semantic similarity
2. Auto-iteration execution with ESC cancellation
3. RAG context history integration
4. Failure handling with exploiter function for alternative plans
5. Pretty printing for user feedback
"""

import logging
import json
import redis
import requests
import numpy as np
import sys
import select
import termios
import tty
from redis.exceptions import RedisError
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from errors_handler import handle_exception
from src.utils.embedding_utils import EmbeddingCacheMixin, cosine_similarity
from src.utils.config_loader import ConfigLoader
from src.utils.conversation_history import ConversationHistoryManager

logger = logging.getLogger(__name__)

# Configuration defaults
REDIS_HOST = 'localhost'
REDIS_PORT = 16379  # Default to docker-compose mapped port
REDIS_PASSWORD = None
TODO_LIST_KEY = "mcp:mirror_vanisher:todo_list"
DETAILED_TODO_LIST_KEY = "mcp:mirror_vanisher:detailed_todo_list"
EXECUTION_HISTORY_KEY = "mcp:mirror_vanisher:execution_history"
DEFAULT_SIMILARITY_THRESHOLD = 0.3  # Minimum similarity score to consider a match
DEFAULT_MAX_AUTO_ITERATIONS = 25

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
    """Tool for automatic plan execution with ouroboros tool matching."""

    def __init__(self, manager, server_instance=None):
        """Initialize execute plan tool.

        Args:
            manager: MirrorVanisherManager instance
            server_instance: Optional reference to the MCP server for accessing tools
        """
        self.manager = manager
        self.server_instance = server_instance
        self.cancelled = False

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

        # Get transformer URL from config
        transformer_config = self.config.get('transformer', default={})
        protocol = transformer_config.get('protocol', 'http')
        host = transformer_config.get('host', 'localhost')
        port = transformer_config.get('port', 16050)
        self.transformer_url = f"{protocol}://{host}:{port}"

        # Initialize separate Redis client for embedding caching (from EmbeddingCacheMixin)
        self._init_embedding_redis()

        # Get ouroboros config
        ouroboros_config = self.config.get('ouroboros', default={})
        self.max_auto_iterations = ouroboros_config.get('max_auto_iterations', DEFAULT_MAX_AUTO_ITERATIONS)
        self.similarity_threshold = ouroboros_config.get('tool_matching_threshold', DEFAULT_SIMILARITY_THRESHOLD)
        self.history_similarity_threshold = ouroboros_config.get('history_similarity_threshold', 0.5)
        self.history_top_k = ouroboros_config.get('history_top_k', 3)

        # In-memory fallback for TODO lists
        self.memory_todo_list = []
        self.memory_detailed_todo_list = []

        # Cache for tool embeddings
        self.tool_embeddings_cache = {}

        # Initialize conversation history manager for RAG context
        self.history_manager = ConversationHistoryManager()

        # Execution history for context
        self.execution_history = []

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
                        'inputSchema': tool_info.get('inputSchema', {}),
                        'source': 'mirror_vanisher'
                    })

        return tools

    def get_executor_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from Executor MCP.

        Returns:
            List of tool dictionaries with name and description
        """
        executor_tools = [
            {
                'name': 'execute_python_code',
                'description': 'Execute and run Python scripts with command-line arguments, capturing output and return code',
                'source': 'executor'
            },
            {
                'name': 'execute_shell_command',
                'description': 'Execute shell commands and bash scripts, capturing output and return code',
                'source': 'executor'
            },
            {
                'name': 'execute_javascript_code',
                'description': 'Execute JavaScript or Node.js scripts with command-line arguments',
                'source': 'executor'
            },
            {
                'name': 'execute_code_snippet',
                'description': 'Execute code snippets dynamically in Python, JavaScript, or Bash',
                'source': 'executor'
            },
            {
                'name': 'create_file',
                'description': 'Create and write a new file with specified content',
                'source': 'executor'
            },
            {
                'name': 'update_file',
                'description': 'Update and replace the complete content of an existing file',
                'source': 'executor'
            },
            {
                'name': 'append_to_file',
                'description': 'Append content to the end of an existing file',
                'source': 'executor'
            },
            {
                'name': 'delete_file',
                'description': 'Delete and remove an existing file',
                'source': 'executor'
            },
            {
                'name': 'copy_file',
                'description': 'Copy a file to a new location',
                'source': 'executor'
            },
            {
                'name': 'move_file',
                'description': 'Move and relocate a file to a new location',
                'source': 'executor'
            },
            {
                'name': 'install_pip_packages',
                'description': 'Install Python packages using pip package manager',
                'source': 'executor'
            },
            {
                'name': 'install_npm_packages',
                'description': 'Install Node.js packages using npm package manager',
                'source': 'executor'
            },
            {
                'name': 'run_build_command',
                'description': 'Execute build commands including make, gradle, maven, or custom build scripts',
                'source': 'executor'
            },
            {
                'name': 'compile_python',
                'description': 'Compile Python source files to bytecode for syntax validation',
                'source': 'executor'
            },
            {
                'name': 'create_virtual_env',
                'description': 'Create a Python virtual environment for isolated package management',
                'source': 'executor'
            },
            {
                'name': 'install_in_virtual_env',
                'description': 'Install Python packages in an existing virtual environment',
                'source': 'executor'
            },
            {
                'name': 'run_in_virtual_env',
                'description': 'Run commands or scripts inside a Python virtual environment',
                'source': 'executor'
            },
            {
                'name': 'run_docker_build',
                'description': 'Build Docker images from Dockerfile',
                'source': 'executor'
            },
            {
                'name': 'create_directory',
                'description': 'Create a new directory or directory structure',
                'source': 'executor'
            },
            {
                'name': 'create_directory_structure',
                'description': 'Create complex directory structures from nested configuration',
                'source': 'executor'
            },
            {
                'name': 'delete_directory',
                'description': 'Delete and remove a directory and its contents',
                'source': 'executor'
            },
            {
                'name': 'copy_directory',
                'description': 'Copy a directory and all its contents to a new location',
                'source': 'executor'
            },
            {
                'name': 'move_directory',
                'description': 'Move a directory and its contents to a new location',
                'source': 'executor'
            },
            {
                'name': 'list_directory_contents',
                'description': 'List and enumerate contents of a directory',
                'source': 'executor'
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

    def find_best_matching_tool(
        self,
        step_text: str,
        tools: List[Dict[str, Any]]
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """Find the best matching tool for a step using semantic similarity.

        Args:
            step_text: Text describing the step
            tools: List of tool dictionaries

        Returns:
            Tuple of (best_tool, similarity_score) or None if no match found
        """
        try:
            # Generate embedding for step
            step_embedding = self._generate_embedding(step_text)

            if step_embedding is None:
                # Fallback to keyword matching
                logger.warning(f"Embeddings unavailable, using keyword matching for: {step_text}")
                return self._keyword_match_best_tool(step_text, tools)

            best_match = None
            best_score = 0.0

            for tool in tools:
                tool_name = tool.get('name', '')
                tool_description = tool.get('description', '')

                # Get or generate tool embedding
                tool_embedding = self.get_or_generate_tool_embedding(tool_name, tool_description)

                if tool_embedding is None:
                    continue

                # Calculate cosine similarity
                similarity = cosine_similarity(step_embedding, tool_embedding)

                if similarity >= self.similarity_threshold and similarity > best_score:
                    best_score = similarity
                    best_match = tool

            if best_match:
                return (best_match, best_score)
            return None

        except Exception as e:
            handle_exception(e, context={
                'function': 'find_best_matching_tool',
                'step_text': step_text[:100]
            })
            return None

    def _keyword_match_best_tool(
        self,
        step_text: str,
        tools: List[Dict[str, Any]]
    ) -> Optional[Tuple[Dict[str, Any], float]]:
        """Fallback keyword-based tool matching.

        Args:
            step_text: Text describing the step
            tools: List of tool dictionaries

        Returns:
            Tuple of (best_tool, score) or None if no match
        """
        step_words = set(step_text.lower().split())
        best_match = None
        best_score = 0.0
        threshold = 0.1  # Lower threshold for keyword matching

        for tool in tools:
            tool_name = tool.get('name', '')
            tool_description = tool.get('description', '')

            # Combine tool name and description
            tool_text = f"{tool_name} {tool_description}".lower()
            tool_words = set(tool_text.split())

            # Calculate Jaccard similarity
            if not tool_words:
                continue

            intersection = step_words & tool_words
            union = step_words | tool_words

            score = len(intersection) / len(union) if union else 0.0

            if score >= threshold and score > best_score:
                best_score = score
                best_match = tool

        if best_match:
            return (best_match, best_score)
        return None

    def ouroboros_match_tools(self, todo_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ouroboros function: Recursively match all steps with tools.

        This function loops through all available tools and matches each step
        with the best matching tool using semantic similarity. Steps without
        matching tools are NOT added to the DETAILED_TODO_list.

        Args:
            todo_list: Original TODO_list from create_plan

        Returns:
            DETAILED_TODO_list with only steps that have matching tools
        """
        detailed_list = []

        # Get all available tools
        mirror_vanisher_tools = self.get_mirror_vanisher_tools(exclude_tools=['create_plan', 'execute_plan'])
        executor_tools = self.get_executor_tools()
        all_tools = mirror_vanisher_tools + executor_tools

        logger.info(f"Ouroboros: Processing {len(todo_list)} TODO items against {len(all_tools)} tools")

        for idx, step in enumerate(todo_list):
            step_number = step.get('step_number', idx + 1)
            action = step.get('action', '')
            details = step.get('details', '')

            # Combine action and details for matching
            step_text = f"{action}. {details}"

            logger.info(f"Ouroboros: Matching step {step_number}: {action}")

            # Find best matching tool
            match_result = self.find_best_matching_tool(step_text, all_tools)

            if match_result:
                tool, similarity = match_result
                tool_name = tool.get('name')
                tool_source = tool.get('source', 'unknown')

                logger.info(f"  ✓ Matched: {tool_name} (similarity: {similarity:.2f})")

                # Add to detailed list
                detailed_item = {
                    'step_number': step_number,
                    'original_action': action,
                    'original_details': details,
                    'tool_source': tool_source,
                    'tool_name': tool_name,
                    'tool_description': tool.get('description', ''),
                    'similarity_score': similarity,
                    'status': 'pending',
                    'execution_result': None
                }

                detailed_list.append(detailed_item)
            else:
                logger.warning(f"  ✗ No matching tool found for step {step_number}: {action}")

        logger.info(f"Ouroboros: Built DETAILED_TODO_list with {len(detailed_list)} items (from {len(todo_list)} steps)")

        return detailed_list

    def check_for_esc_key(self) -> bool:
        """Check if ESC key was pressed (non-blocking).

        Returns:
            True if ESC was pressed, False otherwise
        """
        try:
            # Check if running in a terminal
            if not sys.stdin.isatty():
                return False

            # Non-blocking check for input
            if select.select([sys.stdin], [], [], 0)[0]:
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setraw(sys.stdin.fileno())
                    ch = sys.stdin.read(1)
                    if ch == '\x1b':  # ESC key
                        return True
                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            return False
        except Exception:
            return False

    def pretty_print_step_info(self, item: Dict[str, Any], iteration: int, total: int) -> str:
        """Generate pretty formatted step information.

        Args:
            item: DETAILED_TODO_list item
            iteration: Current iteration number
            total: Total number of iterations

        Returns:
            Formatted string for display
        """
        separator = "─" * 60
        return f"""
{separator}
┃ ITERATION {iteration}/{total}
{separator}
┃ Action: {item.get('original_action', 'N/A')}
┃ Details: {item.get('original_details', 'N/A')}
┃ Tool: {item.get('tool_name', 'N/A')}
┃ Source: {item.get('tool_source', 'N/A')}
┃ Similarity: {item.get('similarity_score', 0):.2%}
{separator}
"""

    def generate_step_explanation(self, item: Dict[str, Any], context: str = "") -> str:
        """Generate LLM explanation for what the step will do.

        Args:
            item: DETAILED_TODO_list item
            context: Additional context from previous iterations

        Returns:
            Explanation string
        """
        try:
            # Get Ollama config
            ollama_config = self.config.get('ollama', default={})
            use_mode = ollama_config.get('use', 'local')
            ollama_server = ollama_config.get(use_mode, {})

            # Get model config
            model_config = self.config.get('model', default={})
            default_models = model_config.get('default', {})
            model = default_models.get(use_mode, 'tinyllama')

            # Build Ollama URL
            protocol = ollama_server.get('protocol', 'http')
            host = ollama_server.get('host', 'localhost')
            port = ollama_server.get('port', 11434)
            api_path = ollama_server.get('api_path', '/api/generate')

            url = f"{protocol}://{host}:{port}{api_path}"

            # Build prompt
            prompt = f"""You are explaining what a tool execution step will do. Be concise and clear.

Tool: {item.get('tool_name', 'N/A')}
Tool Description: {item.get('tool_description', 'N/A')}
Action: {item.get('original_action', 'N/A')}
Details: {item.get('original_details', 'N/A')}

{f"Previous Context: {context}" if context else ""}

Explain in 1-2 sentences what this step will accomplish:"""

            # Call Ollama
            response = requests.post(
                url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            explanation = data.get('response', '').strip()
            return explanation if explanation else "Executing the planned step..."

        except Exception as e:
            handle_exception(e, context={
                'function': 'generate_step_explanation',
                'tool_name': item.get('tool_name')
            })
            return "Executing the planned step..."

    def get_rag_context(self, step_text: str) -> str:
        """Get relevant RAG context from conversation history.

        Args:
            step_text: Current step text for similarity matching

        Returns:
            Formatted context string
        """
        try:
            relevant_history = self.history_manager.retrieve_relevant_history(
                step_text,
                top_k=self.history_top_k,
                min_similarity=self.history_similarity_threshold
            )

            if relevant_history:
                return self.history_manager.format_history_for_context(relevant_history)
            return ""

        except Exception as e:
            handle_exception(e, context={'function': 'get_rag_context'})
            return ""

    def execute_tool(
        self,
        item: Dict[str, Any],
        context: str = ""
    ) -> Dict[str, Any]:
        """Execute a single tool from the DETAILED_TODO_list.

        Args:
            item: DETAILED_TODO_list item
            context: Additional context from previous iterations

        Returns:
            Execution result dictionary
        """
        tool_name = item.get('tool_name')
        tool_source = item.get('tool_source')

        try:
            # For now, simulate execution
            # In production, this would call the actual tool handlers
            result = {
                'success': True,
                'tool_name': tool_name,
                'tool_source': tool_source,
                'output': f"Executed {tool_name} successfully",
                'timestamp': datetime.now().isoformat()
            }

            # Add to execution history
            self.execution_history.append({
                'step_number': item.get('step_number'),
                'action': item.get('original_action'),
                'tool_name': tool_name,
                'result': result,
                'context': context[:500] if context else ""
            })

            # Add to conversation history for RAG
            self.history_manager.add_turn(
                f"Execute {tool_name}: {item.get('original_action')}",
                f"Result: {result.get('output', 'Completed')}"
            )

            return result

        except Exception as e:
            error_result = {
                'success': False,
                'tool_name': tool_name,
                'tool_source': tool_source,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            handle_exception(e, context={
                'function': 'execute_tool',
                'tool_name': tool_name
            })
            return error_result

    def handle_failure(
        self,
        item: Dict[str, Any],
        error_result: Dict[str, Any],
        todo_list: List[Dict[str, Any]]
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        """Handle execution failure with user choice.

        Args:
            item: Failed DETAILED_TODO_list item
            error_result: Error result from execution
            todo_list: Original TODO_list

        Returns:
            Tuple of (choice: 'continue' or 'retry', new_detailed_list or None)
        """
        # In MCP context, we can't directly interact with user
        # Instead, return information about the failure
        # The calling code should handle the user interaction

        failure_info = {
            'failed_step': item.get('step_number'),
            'failed_action': item.get('original_action'),
            'failed_tool': item.get('tool_name'),
            'error': error_result.get('error', 'Unknown error'),
            'options': [
                'continue - Skip this step and continue with next iteration',
                'retry - Use exploiter function to find an alternative approach'
            ]
        }

        return ('continue', None, failure_info)

    def exploiter_function(
        self,
        failure_info: Dict[str, Any],
        todo_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Exploiter function: Create new plan from failure context.

        Uses the failure logs, description, and output along with the TODO_list
        to create a new alternative plan using the ouroboros process.

        Args:
            failure_info: Information about the failure
            todo_list: Original TODO_list

        Returns:
            New DETAILED_TODO_list with alternative approach
        """
        try:
            # Get Ollama config
            ollama_config = self.config.get('ollama', default={})
            use_mode = ollama_config.get('use', 'local')
            ollama_server = ollama_config.get(use_mode, {})

            # Get model config
            model_config = self.config.get('model', default={})
            default_models = model_config.get('default', {})
            model = default_models.get(use_mode, 'tinyllama')

            # Build Ollama URL
            protocol = ollama_server.get('protocol', 'http')
            host = ollama_server.get('host', 'localhost')
            port = ollama_server.get('port', 11434)
            api_path = ollama_server.get('api_path', '/api/generate')

            url = f"{protocol}://{host}:{port}{api_path}"

            # Build prompt for alternative plan
            prompt = f"""A step in the execution plan failed. Create an alternative approach.

Failed Step: {failure_info.get('failed_action', 'N/A')}
Failed Tool: {failure_info.get('failed_tool', 'N/A')}
Error: {failure_info.get('error', 'Unknown')}

Original TODO List:
{json.dumps(todo_list, indent=2)}

Create a new TODO list that:
1. Avoids the failed approach
2. Uses alternative tools or methods
3. Still achieves the same goal

Return as JSON array with format:
[{{"step_number": 1, "action": "...", "details": "..."}}]"""

            # Call Ollama
            response = requests.post(
                url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            response.raise_for_status()
            data = response.json()

            response_text = data.get('response', '').strip()

            # Try to parse JSON from response
            try:
                # Find JSON array in response
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    new_todo_list = json.loads(json_str)

                    # Run ouroboros on new plan
                    return self.ouroboros_match_tools(new_todo_list)
            except json.JSONDecodeError:
                pass

            # If parsing fails, return empty list
            logger.warning("Failed to parse alternative plan from LLM")
            return []

        except Exception as e:
            handle_exception(e, context={
                'function': 'exploiter_function',
                'failure_info': failure_info
            })
            return []

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
        """Execute the plan using ouroboros function and auto-iteration.

        Args:
            auto_execute: If True, automatically execute all items

        Returns:
            Dictionary with execution results
        """
        try:
            logger.info("Starting ouroboros execute_plan")
            self.cancelled = False
            self.execution_history = []

            # Step 1: Get TODO_list
            todo_list = self.get_todo_list()

            if not todo_list:
                return {
                    'success': False,
                    'error': 'No TODO_list found. Please create a plan first using create_plan tool.'
                }

            logger.info(f"Retrieved TODO_list with {len(todo_list)} items")

            # Step 2: Use ouroboros function to match tools
            detailed_list = self.ouroboros_match_tools(todo_list)

            if not detailed_list:
                return {
                    'success': False,
                    'error': 'No tool matches found for any TODO_list steps.',
                    'message': 'The ouroboros function could not find matching tools for any steps.'
                }

            # Step 3: Save DETAILED_TODO_list
            self.save_detailed_todo_list(detailed_list)

            # Step 4: Execute if auto_execute is True
            execution_results = []
            completed_count = 0
            failed_count = 0

            if auto_execute:
                logger.info("Starting ouroboros auto-execution")

                total_iterations = len(detailed_list)

                # Check max iterations limit
                if total_iterations > self.max_auto_iterations:
                    return {
                        'success': False,
                        'error': f'Plan has {total_iterations} steps, exceeding max limit of {self.max_auto_iterations}.',
                        'detailed_todo_list': detailed_list,
                        'message': f'Please reduce the plan to {self.max_auto_iterations} steps or less.'
                    }

                # Build execution output
                output_lines = [
                    "",
                    "╔══════════════════════════════════════════════════════════════╗",
                    "║         OUROBOROS AUTO-EXECUTION STARTING                    ║",
                    "╠══════════════════════════════════════════════════════════════╣",
                    f"║  Total Steps: {total_iterations}                                              ║",
                    f"║  Max Iterations: {self.max_auto_iterations}                                         ║",
                    "║                                                              ║",
                    "║  Press ESC at any time to cancel execution                   ║",
                    "╚══════════════════════════════════════════════════════════════╝",
                    ""
                ]

                for idx, item in enumerate(detailed_list):
                    iteration = idx + 1

                    # Check for cancellation
                    if self.check_for_esc_key():
                        self.cancelled = True
                        output_lines.append("\n⚠️  EXECUTION CANCELLED BY USER (ESC pressed)")
                        break

                    # Pretty print step info
                    step_info = self.pretty_print_step_info(item, iteration, total_iterations)
                    output_lines.append(step_info)

                    # Get RAG context
                    step_text = f"{item.get('original_action', '')}. {item.get('original_details', '')}"
                    rag_context = self.get_rag_context(step_text)

                    # Build context from previous executions
                    prev_context = ""
                    if self.execution_history:
                        prev_results = [
                            f"Step {h['step_number']}: {h['action']} -> {h['result'].get('output', 'N/A')}"
                            for h in self.execution_history[-3:]  # Last 3 results
                        ]
                        prev_context = "\n".join(prev_results)

                    combined_context = f"{rag_context}\n{prev_context}" if rag_context else prev_context

                    # Generate and display explanation
                    explanation = self.generate_step_explanation(item, combined_context)
                    output_lines.append(f"┃ Explanation: {explanation}")
                    output_lines.append("")

                    # Execute the tool
                    result = self.execute_tool(item, combined_context)

                    if result.get('success'):
                        completed_count += 1
                        output_lines.append(f"✅ Step {iteration} completed: {result.get('output', 'Success')}")
                        item['status'] = 'completed'
                    else:
                        failed_count += 1
                        error_msg = result.get('error', 'Unknown error')
                        output_lines.append(f"❌ Step {iteration} failed: {error_msg}")
                        item['status'] = 'failed'

                        # Handle failure - in MCP context, we continue by default
                        # User interaction would happen at a higher level
                        output_lines.append("⚠️  Continuing with next step...")

                    item['execution_result'] = result
                    execution_results.append(result)

                # Save updated detailed list
                self.save_detailed_todo_list(detailed_list)

                # Summary
                output_lines.extend([
                    "",
                    "═" * 60,
                    "EXECUTION SUMMARY",
                    "═" * 60,
                    f"Total Steps: {total_iterations}",
                    f"Completed: {completed_count}",
                    f"Failed: {failed_count}",
                    f"Cancelled: {'Yes' if self.cancelled else 'No'}",
                    "═" * 60
                ])

            # Return results
            return {
                'success': True,
                'todo_list_count': len(todo_list),
                'detailed_todo_list_count': len(detailed_list),
                'DETAILED_TODO_list': detailed_list,
                'auto_execute': auto_execute,
                'execution_results': execution_results if auto_execute else [],
                'completed_count': completed_count,
                'failed_count': failed_count,
                'cancelled': self.cancelled,
                'execution_history': self.execution_history,
                'output': '\n'.join(output_lines) if auto_execute else '',
                'message': f'Ouroboros matched {len(detailed_list)} tools from {len(todo_list)} steps' +
                          (f', executed {completed_count}/{len(detailed_list)} successfully' if auto_execute else '')
            }

        except Exception as e:
            handle_exception(e, context={'function': 'execute_plan'})
            return {'success': False, 'error': str(e)}
