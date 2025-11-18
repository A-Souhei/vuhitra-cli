import sys
import os
import logging
import requests
import time
import zipfile
import tempfile
import redis
import json
import yaml
from pathlib import Path
from src.agent import generate
from src.utils.arg_parser import ArgumentParser
from src.errors_handler import handle_exception, capture_message, get_error_handler
from src.utils.config_loader import ConfigLoader
from src.utils.feedback_collector import FeedbackCollector
from src.utils.input_with_timeout import input_with_timeout
from src.utils.ui_formatter import (
    set_verbose_mode, is_verbose, print_banner, print_response,
    print_context_verbose, print_context_content_verbose, print_elasticsearch_verbose,
    print_nlp_analysis_verbose, print_timing_verbose, print_error, print_warning,
    print_success, print_info, print_debug, print_user_prompt, console, spinner
)
from src.utils.prompt_history import PromptHistoryManager
from src.utils.conversation_history import ConversationHistoryManager
from src.utils.ephemeral_context import EphemeralContextManager
from src.utils.eternal_context import EternalContextManager
from src.utils.spark_context import SparkContextManager
from src.utils.pillar_context import PillarContextManager
from src.utils.vanisher_context import VanisherContextManager
from src.utils.command_handler import CommandHandler, CommandResult
from src.utils.token_limit_manager import get_token_limit_manager
from src.utils.path_resolver import get_path_resolver
from src.utils.redis_helper import get_redis_client

# Add sandbox service to path for heuristics config
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "sandbox" / "src"))
from heuristics_config_loader import HeuristicsConfigLoader

# Add MCP modules to path for direct tool calls
sys.path.insert(0, str(Path(__file__).parent.parent / "mcps" / "mirror_vanisher_dev" / "src"))
from mirror_vanisher import MirrorVanisherManager
from planning import PlanningTools
from execute_plan import ExecutePlan

# Maximum prompt length to prevent DoS through excessive payload sizes
# Note: This is now dynamic - will use discovered model limits from Redis
# If no limit discovered yet, defaults to infinity (user will discover it)
MAX_PROMPT_LENGTH = float('inf')

logger = logging.getLogger(__name__)

def wait_for_services(max_retries=30, retry_delay=1.0):
    """
    Wait for sandbox and transformer services to be ready.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        bool: True if services are ready, False otherwise
    """
    config = ConfigLoader()
    sandbox_url = config.get_sandbox_url()
    health_endpoint = f"{sandbox_url}/health"
    
    print_info("Waiting for services to be ready...")
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(health_endpoint, timeout=2)
            if response.status_code == 200:
                data = response.json()
                
                # Check if retriever health includes transformer service
                retriever_health = data.get('retriever', {})
                if retriever_health.get('overall', False):
                    print_success("✓ All services are ready (sandbox + transformer)")
                    return True
                elif retriever_health.get('elasticsearch', False):
                    print_warning(f"Elasticsearch ready, waiting for transformer service... (attempt {attempt}/{max_retries})")
                else:
                    print_warning(f"Services starting... (attempt {attempt}/{max_retries})")
            else:
                print_warning(f"Sandbox returned status {response.status_code}, retrying... (attempt {attempt}/{max_retries})")
        except requests.exceptions.ConnectionError:
            print_warning(f"Cannot connect to sandbox, retrying... (attempt {attempt}/{max_retries})")
        except requests.exceptions.Timeout:
            print_warning(f"Health check timeout, retrying... (attempt {attempt}/{max_retries})")
        except Exception as e:
            print_warning(f"Health check error: {str(e)}, retrying... (attempt {attempt}/{max_retries})")
        
        if attempt < max_retries:
            time.sleep(retry_delay)
    
    print_error("✗ Services did not become ready in time")
    print_info("Please ensure Docker containers are running:")
    print_info("  cd services && docker compose up -d")
    return False

def initialize_error_handler():
    """Initialize the error handler with configuration."""
    try:
        config = ConfigLoader()
        error_handler = get_error_handler()
        error_handler.configure(config_loader=config)
    except Exception as e:
        print(f"WARNING: Failed to initialize error handler: {str(e)}", file=sys.stderr)

def get_todo_list_from_redis():
    """Fetch TODO_list from Redis storage (used by Mirror+Vanisher MCP create_plan tool)."""
    try:
        # Get Redis client from connection pool
        redis_client = get_redis_client()
        
        if redis_client is None:
            print_error("Failed to connect to Redis. Is Redis running?")
            return None
        
        # Retrieve TODO_list
        TODO_LIST_KEY = "mcp:mirror_vanisher:todo_list"
        
        try:
            todo_list_json = redis_client.get(TODO_LIST_KEY)
        except Exception as e:
            print_error(f"Error retrieving TODO_list from Redis: {str(e)}")
            return None
        
        if todo_list_json:
            try:
                # Type hint: with decode_responses=True, Redis returns str
                todo_list = json.loads(str(todo_list_json))
                return todo_list
            except json.JSONDecodeError as e:
                print_error(f"Error parsing TODO_list JSON: {str(e)}")
                return None
        else:
            return None
            
    except Exception as e:
        print_error(f"Unexpected error retrieving TODO_list: {str(e)}")
        return None


def fetch_similar_heuristic(prompt, verbose=False, negative_weight_boost=0.0):
    """Fetch similar heuristic from sandbox to enhance LLM context."""
    endpoint = None  # Initialize before try block
    start_time = time.time()

    try:
        # Validate prompt length (now using dynamic limits if discovered)
        # MAX_PROMPT_LENGTH is inf by default, so this only triggers if we have a DoS limit
        if MAX_PROMPT_LENGTH != float('inf') and len(prompt) > MAX_PROMPT_LENGTH:
            logger.warning(f"Prompt length ({len(prompt)}) exceeds maximum ({MAX_PROMPT_LENGTH}), truncating")
            prompt = prompt[:int(MAX_PROMPT_LENGTH)]

        config = ConfigLoader()
        sandbox_url = config.get_sandbox_url()
        endpoint = f"{sandbox_url}/retrieve/similar"
        confidence_threshold = config.get_sandbox_confidence_threshold()

        if verbose:
            debug_info = {
                "endpoint": endpoint,
                "prompt_length": len(prompt),
                "confidence_threshold": confidence_threshold,
                "min_rating": 4
            }
            if negative_weight_boost > 0:
                debug_info["negative_weight_boost"] = negative_weight_boost
            print_debug("Heuristic Retrieval Request", debug_info)

        request_json = {"prompt": prompt, "min_rating": 4, "verbose": verbose}
        if negative_weight_boost > 0:
            request_json["negative_weight_boost"] = negative_weight_boost

        response = requests.post(
            endpoint,
            json=request_json,
            timeout=15  # Increased timeout for embedding generation and potential network latency
        )
        response.raise_for_status()
        data = response.json()

        duration_ms = (time.time() - start_time) * 1000
        print_timing_verbose("Heuristic retrieval", duration_ms)

        # Check if this is a negative heuristic (anti-pattern)
        is_negative = data.get('is_negative', False)

        # Return the formatted insight if available and confidence is good
        if (data.get('confidence_score', 0) > confidence_threshold and
            data.get('insights') and
            data['insights'].get('formatted_insight')):

            formatted_insight = data['insights']['formatted_insight']

            if verbose:
                # Print verbose context information only when match is accepted
                if data.get('matched_heuristic'):
                    print_context_verbose(data)

                if is_negative:
                    print_warning(f"⚠️  Negative heuristic (anti-pattern) found (confidence: {data.get('confidence_score', 0):.2%})")
                    print_info("This will inform the LLM about approaches to AVOID")
                else:
                    print_success(f"✓ Heuristic match found (confidence: {data.get('confidence_score', 0):.2%})")
                # Display the actual context content that will be used
                print_context_content_verbose(formatted_insight)

            return formatted_insight, data
        else:
            if verbose:
                print_info(f"ℹ️  No suitable heuristic match (confidence: {data.get('confidence_score', 0):.2%} < {confidence_threshold:.2%})")

            return None, data

    except Exception as e:
        # Use error handler to log the exception
        handle_exception(e, context={
            'function': 'fetch_similar_heuristic',
            'endpoint': endpoint if 'endpoint' in locals() else 'unknown',
            'prompt_length': len(prompt)
        })

        if verbose:
            print_warning(f"Failed to fetch heuristic: {str(e)}")

        return None, None


def send_feedback_to_sandbox(feedback_data, verbose=False):
    """Send feedback to sandbox for heuristics analysis."""
    start_time = time.time()

    try:
        config = ConfigLoader()
        sandbox_url = config.get_sandbox_url()
        endpoint = f"{sandbox_url}/analyze/feedback"

        if verbose:
            debug_info = {
                "endpoint": endpoint,
                "rating": feedback_data.get('rating'),
                "prompt_length": len(feedback_data.get('prompt', '')),
                "response_length": len(feedback_data.get('response', '')),
                "execution_time_ms": feedback_data.get('execution_time_ms')
            }
            # Show user feedback if provided
            if 'user_feedback' in feedback_data and feedback_data['user_feedback']:
                debug_info["user_feedback"] = feedback_data['user_feedback']
            print_debug("Feedback Submission", debug_info)

        # Add verbose flag to request payload
        request_payload = feedback_data.copy()
        request_payload['verbose'] = verbose

        response = requests.post(endpoint, json=request_payload, timeout=10)
        response.raise_for_status()

        result_data = response.json()
        duration_ms = (time.time() - start_time) * 1000
        print_timing_verbose("Feedback submission", duration_ms)

        # Print verbose Elasticsearch and NLP info
        if verbose and result_data:
            if 'nlp_analysis' in result_data:
                print_nlp_analysis_verbose(result_data['nlp_analysis'])

            if 'elasticsearch_doc' in result_data:
                print_elasticsearch_verbose("STORE FEEDBACK", result_data['elasticsearch_doc'])

        if verbose:
            print_success("✓ Feedback successfully sent to sandbox")

        return True

    except requests.exceptions.HTTPError as e:
        # Log HTTP-specific errors with more context
        error_msg = f"HTTP error sending feedback to sandbox: {e.response.status_code} - {str(e)}"
        if verbose:
            print_error(error_msg)
        else:
            print(f"WARNING: {error_msg}", file=sys.stderr)
        return False

    except requests.exceptions.RequestException as e:
        # Log other request errors (timeout, connection, etc.)
        error_msg = f"Request error sending feedback to sandbox: {str(e)}"
        if verbose:
            print_error(error_msg)
        else:
            print(f"WARNING: {error_msg}", file=sys.stderr)
        return False

    except Exception as e:
        # Log error but don't fail the CLI
        error_msg = f"Failed to send feedback to sandbox: {str(e)}"
        if verbose:
            print_error(error_msg)
        else:
            print(f"WARNING: {error_msg}", file=sys.stderr)
        return False

def interactive_mode(model, verbose=False, coding=False):
    """Run interactive mode with enhanced UI and verbose logging.

    Args:
        model: The LLM model to use
        verbose: Enable verbose debugging output
        coding: Enable coding mode (disables eternals/ephemerals/auto-iteration, enables pillars/vanishers)
    """
    # Set global verbose mode
    set_verbose_mode(verbose)

    # Print styled banner
    print_banner(model)

    # Show coding mode status
    if coding:
        console.print("[bold green]🔧 Coding mode enabled[/bold green] - Using Pillars & Vanishers, auto-iteration disabled")

    # Initialize feedback collector
    feedback_collector = FeedbackCollector()

    # Get working directory for @ prefix resolution
    working_dir = os.getcwd()

    # Initialize path resolver for @ prefix paths
    path_resolver = get_path_resolver(working_dir=working_dir)

    # Initialize prompt history manager with working directory for file completion
    prompt_manager = PromptHistoryManager(working_dir=working_dir)

    # Initialize conversation history manager
    conversation_history = ConversationHistoryManager()

    # Initialize context managers based on mode
    if coding:
        # Coding mode: disable eternals/ephemerals, enable pillars/vanishers
        ephemeral_context = EphemeralContextManager(enabled=False)
        eternal_context = EternalContextManager(enabled=False)
        pillar_context = PillarContextManager(enabled=True)
        vanisher_context = VanisherContextManager(enabled=True)

        # Auto-load pillars from pillars/ directory with spinner
        with spinner("🔧 Initializing coding mode, loading pillars..."):
            loaded_count, loaded_files = pillar_context.auto_load_from_pillars_directory(verbose=verbose)
        if loaded_count > 0:
            print_success(f"✓ Auto-loaded {loaded_count} pillar(s) from pillars/ directory")
            if verbose:
                for filename in loaded_files:
                    print_info(f"  - {filename}")
    else:
        # Normal mode: enable eternals/ephemerals, disable pillars/vanishers
        ephemeral_context = EphemeralContextManager()
        eternal_context = EternalContextManager()
        pillar_context = PillarContextManager(enabled=False)
        vanisher_context = VanisherContextManager(enabled=False)

    # Initialize Spark context manager (in-memory ephemeral, always enabled)
    spark_context = SparkContextManager()

    # Initialize heuristics config (used for conversation history settings)
    heuristics_config = HeuristicsConfigLoader()

    # Initialize command handler
    command_handler = CommandHandler()

    # Register /clear command
    def clear_command_handler(args):
        """Handle /clear command."""
        if not args:
            return CommandResult(
                success=False,
                message="Usage: /clear context - Clear conversation history and Sparks\n"
                        "       /clear tokenlimit - Clear discovered token limit for current model\n"
                        "       /clear ephemeral [label|--all] - Clear ephemeral context\n"
                        "       /clear eternal [label|--all] - Clear eternal context\n"
                        "       /clear pillar [label|--all] - Clear pillar context (coding mode)\n"
                        "       /clear vanisher [label|--all] - Clear vanisher context (coding mode)\n"
                        "       /clear spark [label|--all] - Clear Spark context"
            )

        subcommand = args[0].lower()

        if subcommand == "context":
            messages = []

            # Clear conversation history
            if conversation_history.is_enabled():
                count = conversation_history.get_history_count()
                conversation_history.clear_history()
                messages.append(f"✓ Cleared {count} conversation turns from history")
            else:
                messages.append("Conversation history is disabled")

            # Also clear all Sparks (as per requirements - Sparks die with /clear context)
            if spark_context.is_enabled():
                spark_count = spark_context.get_count()
                if spark_count > 0:
                    spark_context.clear_all()
                    messages.append(f"✓ Cleared {spark_count} Spark(s)")

            return CommandResult(
                success=True,
                message="\n".join(messages)
            )
        elif subcommand == "tokenlimit":
            token_manager = get_token_limit_manager()
            if token_manager.clear_limit(model):
                return CommandResult(
                    success=True,
                    message=f"✓ Cleared discovered token limit for {model}\n"
                            f"The limit will be re-discovered on next error"
                )
            else:
                return CommandResult(
                    success=False,
                    message="Failed to clear token limit (Redis not available or error occurred)"
                )
        elif subcommand == "ephemeral":
            if not ephemeral_context.is_enabled():
                return CommandResult(
                    success=False,
                    message="Ephemeral context is disabled"
                )

            if len(args) < 2:
                return CommandResult(
                    success=False,
                    message="Usage: /clear ephemeral <label> - Clear specific ephemeral context\n"
                            "       /clear ephemeral --all - Clear all ephemeral contexts"
                )

            target = args[1]

            if target == "--all":
                count = ephemeral_context.clear_all()
                return CommandResult(
                    success=True,
                    message=f"✓ Cleared all ephemeral contexts ({count} contexts removed)"
                )
            else:
                if ephemeral_context.remove_by_label(target):
                    return CommandResult(
                        success=True,
                        message=f"✓ Removed ephemeral context '{target}'"
                    )
                else:
                    return CommandResult(
                        success=False,
                        message=f"Context '{target}' not found. Use '/show ephemeral' to see loaded contexts."
                    )
        elif subcommand == "eternal":
            if not eternal_context.is_enabled():
                return CommandResult(
                    success=False,
                    message="Eternal context is disabled"
                )

            if len(args) < 2:
                return CommandResult(
                    success=False,
                    message="Usage: /clear eternal <label> - Clear specific eternal context\n"
                            "       /clear eternal --all - Clear all eternal contexts"
                )

            target = args[1]

            if target == "--all":
                count = eternal_context.clear_all()
                return CommandResult(
                    success=True,
                    message=f"✓ Cleared all eternal contexts ({count} contexts removed from storage)"
                )
            else:
                if eternal_context.remove_by_label(target):
                    return CommandResult(
                        success=True,
                        message=f"✓ Removed eternal context '{target}' from storage"
                    )
                else:
                    return CommandResult(
                        success=False,
                        message=f"Eternal context '{target}' not found. Use '/show eternal' to see loaded contexts."
                    )
        elif subcommand == "pillar":
            if not pillar_context.is_enabled():
                return CommandResult(
                    success=False,
                    message="Pillar context is disabled. Enable coding mode with --coding flag."
                )

            if len(args) < 2:
                return CommandResult(
                    success=False,
                    message="Usage: /clear pillar <label> - Clear specific pillar context\n"
                            "       /clear pillar --all - Clear all pillar contexts"
                )

            target = args[1]

            if target == "--all":
                count = pillar_context.clear_all()
                return CommandResult(
                    success=True,
                    message=f"✓ Cleared all pillar contexts ({count} contexts removed from storage)"
                )
            else:
                if pillar_context.remove_by_label(target):
                    return CommandResult(
                        success=True,
                        message=f"✓ Removed pillar context '{target}' from storage"
                    )
                else:
                    return CommandResult(
                        success=False,
                        message=f"Pillar context '{target}' not found. Use '/show pillar' to see loaded contexts."
                    )
        elif subcommand == "vanisher":
            if not vanisher_context.is_enabled():
                return CommandResult(
                    success=False,
                    message="Vanisher context is disabled. Enable coding mode with --coding flag."
                )

            if len(args) < 2:
                return CommandResult(
                    success=False,
                    message="Usage: /clear vanisher <label> - Clear specific vanisher context\n"
                            "       /clear vanisher --all - Clear all vanisher contexts"
                )

            target = args[1]

            if target == "--all":
                count = vanisher_context.clear_all()
                return CommandResult(
                    success=True,
                    message=f"✓ Cleared all vanisher contexts ({count} contexts removed)"
                )
            else:
                if vanisher_context.remove_by_label(target):
                    return CommandResult(
                        success=True,
                        message=f"✓ Removed vanisher context '{target}'"
                    )
                else:
                    return CommandResult(
                        success=False,
                        message=f"Vanisher context '{target}' not found. Use '/show vanisher' to see loaded contexts."
                    )
        elif subcommand == "spark":
            if not spark_context.is_enabled():
                return CommandResult(
                    success=False,
                    message="Spark context is disabled"
                )

            if len(args) < 2:
                return CommandResult(
                    success=False,
                    message="Usage: /clear spark <label> - Clear specific Spark context\n"
                            "       /clear spark --all - Clear all Spark contexts"
                )

            target = args[1]

            if target == "--all":
                success, message = spark_context.clear_all()
                return CommandResult(success=success, message=message)
            else:
                success, message = spark_context.clear_by_label(target)
                if not success:
                    message += "\nUse '/show spark' to see loaded Spark contexts."
                return CommandResult(success=success, message=message)
        else:
            return CommandResult(
                success=False,
                message=f"Unknown subcommand: {subcommand}\n"
                        f"Use: /clear context, /clear tokenlimit, /clear ephemeral, /clear eternal, /clear pillar, /clear vanisher, or /clear spark"
            )

    command_handler.register_command("clear", clear_command_handler)

    # Register /limit command to show current token limit
    def limit_command_handler(args):
        """Handle /limit command to show discovered token limit."""
        token_manager = get_token_limit_manager()
        limit = token_manager.get_limit(model)

        if limit == float('inf'):
            return CommandResult(
                success=True,
                message=f"Model: {model}\n"
                        f"Token limit: Not yet discovered (unlimited until error occurs)\n"
                        f"The system will automatically learn the limit when it's exceeded."
            )
        else:
            estimated_chars = int(limit * 4)  # Rough estimate
            return CommandResult(
                success=True,
                message=f"Model: {model}\n"
                        f"Discovered token limit: {int(limit)} tokens (~{estimated_chars} characters)\n"
                        f"Use '/clear tokenlimit' to reset and re-discover"
            )

    command_handler.register_command("limit", limit_command_handler)

    # Register /load command to load ephemeral context from file
    def load_command_handler(args):
        """Handle /load command to load ephemeral context from file."""
        if not ephemeral_context.is_enabled():
            return CommandResult(
                success=False,
                message="Ephemeral context is disabled. Enable it in config.yaml"
            )

        if not args:
            return CommandResult(
                success=False,
                message="Usage: /load <file_path> [label] [description]\n"
                        "       /load ./docs/api_spec.md\n"
                        "       /load @docs/api_spec.md api \"REST API specification\"\n"
                        "       /load @docs/ (loads all files in directory)\n"
                        "       /load ./docs/coding_standards.md standards \"Python coding standards\"\n"
                        "\n"
                        "Note: For descriptions with spaces, use quotes (handled by shell)"
            )

        file_path = args[0]
        label = args[1] if len(args) > 1 else None
        description = args[2] if len(args) > 2 else None

        # Resolve @ prefix path if present
        success, resolved_path, error = path_resolver.resolve_path(file_path)
        if not success:
            return CommandResult(success=False, message=error)

        # Check if it's a directory
        if path_resolver.is_directory(file_path):
            # Load all files in directory
            success, files, error = path_resolver.get_directory_files(file_path)
            if not success:
                return CommandResult(success=False, message=error)

            # Load each file with spinner
            loaded = []
            failed = []

            with spinner(f"📄 Loading ephemerals from {file_path}..."):
                for file in files:
                    file_label = label if label else None
                    file_success, file_message = ephemeral_context.load_file(file, file_label, description)
                    if file_success:
                        loaded.append(os.path.basename(file))
                    else:
                        failed.append((os.path.basename(file), file_message))

            # Build result message
            messages = []
            if loaded:
                messages.append(f"✓ Loaded {len(loaded)} ephemeral context(s) from {file_path}")
                messages.append(f"  Files: {', '.join(loaded)}")

            if failed:
                messages.append(f"✗ Failed to load {len(failed)} file(s):")
                for filename, error_msg in failed:
                    messages.append(f"  - {filename}: {error_msg}")

            if not loaded and failed:
                return CommandResult(success=False, message="\n".join(messages))

            return CommandResult(success=True, message="\n".join(messages))
        else:
            # Load single file
            success, message = ephemeral_context.load_file(resolved_path, label, description)
            return CommandResult(success=success, message=message)

    command_handler.register_command("load", load_command_handler)

    # Register /load-eternal command to load eternal context from file
    def load_eternal_command_handler(args):
        """Handle /load-eternal command to load eternal context from file."""
        if not eternal_context.is_enabled():
            return CommandResult(
                success=False,
                message="Eternal context is disabled. Enable it in config.yaml"
            )

        if not args:
            return CommandResult(
                success=False,
                message="Usage: /load-eternal <file_path> [label] [description]\n"
                        "       /load-eternal ./docs/api_spec.md\n"
                        "       /load-eternal @docs/api_spec.md api \"REST API specification\"\n"
                        "       /load-eternal @docs/ (loads all files in directory)\n"
                        "       /load-eternal ./docs/coding_standards.md standards \"Python coding standards\""
            )

        file_path = args[0]
        label = args[1] if len(args) > 1 else None
        description = args[2] if len(args) > 2 else None

        # Resolve @ prefix path if present
        success, resolved_path, error = path_resolver.resolve_path(file_path)
        if not success:
            return CommandResult(success=False, message=error)

        # Check if it's a directory
        if path_resolver.is_directory(file_path):
            # Load all files in directory
            success, files, error = path_resolver.get_directory_files(file_path)
            if not success:
                return CommandResult(success=False, message=error)

            # Load each file with spinner
            loaded = []
            failed = []

            with spinner(f"💾 Loading eternals from {file_path}..."):
                for file in files:
                    # Generate unique labels for each file in directory
                    # Use provided label as prefix, or filename if no label
                    if label:
                        # Use label as prefix with filename
                        file_label = f"{label}-{Path(file).stem}"
                    else:
                        # Use filename (without extension) as label
                        file_label = Path(file).stem

                    file_success, file_message = eternal_context.load_file(file, file_label, description)
                    if file_success:
                        loaded.append(os.path.basename(file))
                    else:
                        failed.append((os.path.basename(file), file_message))

            # Build result message
            messages = []
            if loaded:
                messages.append(f"✓ Loaded {len(loaded)} eternal context(s) from {file_path}")
                messages.append(f"  Files: {', '.join(loaded)}")

            if failed:
                messages.append(f"✗ Failed to load {len(failed)} file(s):")
                for filename, error_msg in failed:
                    messages.append(f"  - {filename}: {error_msg}")

            if not loaded and failed:
                return CommandResult(success=False, message="\n".join(messages))

            return CommandResult(success=True, message="\n".join(messages))
        else:
            # Load single file
            success, message = eternal_context.load_file(resolved_path, label, description)
            return CommandResult(success=success, message=message)

    command_handler.register_command("load-eternal", load_eternal_command_handler)

    # Register /pillar command to load pillar context from file (coding mode only)
    def pillar_command_handler(args):
        """Handle /pillar command to load pillar context from file (coding mode only)."""
        if not pillar_context.is_enabled():
            return CommandResult(
                success=False,
                message="Pillar context is disabled. Enable coding mode with --coding flag."
            )

        if not args:
            return CommandResult(
                success=False,
                message="Usage: /pillar load <file_path> [label] [description]\n"
                        "       /pillar load ./docs/api_spec.md\n"
                        "       /pillar load @docs/api_spec.md api \"REST API specification\"\n"
                        "       /pillar load @docs/ (loads all files in directory)\n"
                        "       /pillar load ./docs/coding_standards.md standards \"Python coding standards\""
            )

        subcommand = args[0].lower()

        if subcommand == "load":
            if len(args) < 2:
                return CommandResult(
                    success=False,
                    message="Usage: /pillar load <file_path> [label] [description]"
                )

            file_path = args[1]
            label = args[2] if len(args) > 2 else None
            description = args[3] if len(args) > 3 else None

            # Resolve @ prefix path if present
            success, resolved_path, error = path_resolver.resolve_path(file_path)
            if not success:
                return CommandResult(success=False, message=error)

            # Check if it's a directory
            if path_resolver.is_directory(file_path):
                # Load all files in directory
                success, files, error = path_resolver.get_directory_files(file_path)
                if not success:
                    return CommandResult(success=False, message=error)

                # Load each file with spinner
                loaded = []
                failed = []

                with spinner(f"📚 Loading pillars from {file_path}..."):
                    for file in files:
                        # Generate unique labels for each file in directory
                        # Use provided label as prefix, or filename if no label
                        if label:
                            # Use label as prefix with filename
                            file_label = f"{label}-{Path(file).stem}"
                        else:
                            # Use filename (without extension) as label
                            file_label = Path(file).stem

                        file_success, file_message = pillar_context.load_file(file, file_label, description)
                        if file_success:
                            loaded.append(os.path.basename(file))
                        else:
                            failed.append((os.path.basename(file), file_message))

                # Build result message
                messages = []
                if loaded:
                    messages.append(f"✓ Loaded {len(loaded)} pillar(s) from {file_path}")
                    messages.append(f"  Files: {', '.join(loaded)}")

                if failed:
                    messages.append(f"✗ Failed to load {len(failed)} file(s):")
                    for filename, error_msg in failed:
                        messages.append(f"  - {filename}: {error_msg}")

                if not loaded and failed:
                    return CommandResult(success=False, message="\n".join(messages))

                return CommandResult(success=True, message="\n".join(messages))
            else:
                # Load single file
                success, message = pillar_context.load_file(resolved_path, label, description)
                return CommandResult(success=success, message=message)
        else:
            return CommandResult(
                success=False,
                message=f"Unknown pillar subcommand: {subcommand}\n"
                        "Available: /pillar load <file_path> [label] [description]"
            )

    command_handler.register_command("pillar", pillar_command_handler)

    # Register /vanisher command to load vanisher context from mirrored file (coding mode only)
    def vanisher_command_handler(args):
        """Handle /vanisher command to load vanisher context from mirrored file (coding mode only)."""
        if not vanisher_context.is_enabled():
            return CommandResult(
                success=False,
                message="Vanisher context is disabled. Enable coding mode with --coding flag."
            )

        if not args:
            return CommandResult(
                success=False,
                message="Usage: /vanisher load <directory_path> [label] [description]\n"
                        "       /vanisher load @testing/\n"
                        "       /vanisher load @src/ mycode \"Source code directory\"\n"
                        "\n"
                        "NOTE: Vanishers only accept directory-type mirrors.\n"
                        "      Mirror a directory first using '/mirror do @directory/'"
            )

        subcommand = args[0].lower()

        if subcommand == "load":
            if len(args) < 2:
                return CommandResult(
                    success=False,
                    message="Usage: /vanisher load <directory_path> [label] [description]\n"
                            "NOTE: Vanishers only accept directory-type mirrors"
                )

            file_path = args[1]
            label = args[2] if len(args) > 2 else None
            description = args[3] if len(args) > 3 else None

            # Resolve @ prefix path if present
            success, resolved_path, error = path_resolver.resolve_path(file_path)
            if not success:
                return CommandResult(success=False, message=error)

            # Vanishers load individual files from mirrored directories
            # The directory itself must be mirrored first, then we load each file separately
            if not path_resolver.is_directory(file_path):
                return CommandResult(
                    success=False,
                    message=f"Vanishers load files from mirrored directories. '{file_path}' is not a directory.\n"
                            "Use '/mirror do @directory/' to mirror a directory first."
                )

            # Get all files in the mirrored directory
            success, files, error = path_resolver.get_directory_files(file_path)
            if not success:
                return CommandResult(success=False, message=error)

            # Load each file individually with spinner
            loaded = []
            failed = []

            with spinner(f"📦 Loading files from mirrored directory {file_path}..."):
                for file in files:
                    # Generate unique labels for each file in directory
                    # Use provided label as prefix, or filename if no label
                    if label:
                        # Use label as prefix with filename
                        file_label = f"{label}-{Path(file).stem}"
                    else:
                        # Use filename (without extension) as label
                        file_label = Path(file).stem

                    file_success, file_message = vanisher_context.load_file(file, file_label, description)
                    if file_success:
                        loaded.append(os.path.basename(file))
                    else:
                        failed.append((os.path.basename(file), file_message))

            # Build result message
            messages = []
            if loaded:
                messages.append(f"✓ Loaded {len(loaded)} vanisher(s) from {file_path}")
                messages.append(f"  Files: {', '.join(loaded)}")

            if failed:
                messages.append(f"✗ Failed to load {len(failed)} file(s):")
                for filename, error_msg in failed:
                    messages.append(f"  - {filename}: {error_msg}")

            if not loaded and failed:
                return CommandResult(success=False, message="\n".join(messages))

            return CommandResult(success=True, message="\n".join(messages))
        else:
            return CommandResult(
                success=False,
                message=f"Unknown vanisher subcommand: {subcommand}\n"
                        "Available: /vanisher load <file_path> [label] [description]"
            )

    command_handler.register_command("vanisher", vanisher_command_handler)

    # Register /show command to show information
    def show_command_handler(args):
        """Handle /show command to display information."""
        if not args:
            return CommandResult(
                success=False,
                message="Usage: /show ephemeral - Show loaded ephemeral contexts\n"
                        "       /show eternal - Show loaded eternal contexts\n"
                        "       /show pillar - Show loaded pillar contexts (coding mode)\n"
                        "       /show vanisher - Show loaded vanisher contexts (coding mode)\n"
                        "       /show spark - Show loaded Spark contexts\n"
                        "       /show TODO_list - Show current TODO list from MCP create_plan"
            )

        subcommand = args[0].lower()

        if subcommand == "ephemeral":
            if not ephemeral_context.is_enabled():
                return CommandResult(
                    success=False,
                    message="Ephemeral context is disabled"
                )

            summary = ephemeral_context.get_summary()
            return CommandResult(success=True, message=summary)
        elif subcommand == "eternal":
            if not eternal_context.is_enabled():
                return CommandResult(
                    success=False,
                    message="Eternal context is disabled"
                )

            summary = eternal_context.get_summary()
            return CommandResult(success=True, message=summary)
        elif subcommand == "pillar":
            if not pillar_context.is_enabled():
                return CommandResult(
                    success=False,
                    message="Pillar context is disabled. Enable coding mode with --coding flag."
                )

            summary = pillar_context.get_summary()
            return CommandResult(success=True, message=summary)
        elif subcommand == "vanisher":
            if not vanisher_context.is_enabled():
                return CommandResult(
                    success=False,
                    message="Vanisher context is disabled. Enable coding mode with --coding flag."
                )

            summary = vanisher_context.get_summary()
            return CommandResult(success=True, message=summary)
        elif subcommand == "spark":
            if not spark_context.is_enabled():
                return CommandResult(
                    success=False,
                    message="Spark context is disabled"
                )

            summary = spark_context.get_summary()
            return CommandResult(success=True, message=summary)
        elif subcommand == "todo_list":
            # Fetch TODO_list from Redis
            todo_list = get_todo_list_from_redis()
            
            if todo_list is None:
                return CommandResult(
                    success=False,
                    message="No TODO_list found. Create a plan using the Mirror+Vanisher MCP create_plan tool first."
                )
            
            if not todo_list:
                return CommandResult(
                    success=False,
                    message="TODO_list is empty."
                )
            
            # Format the TODO_list nicely
            output = []
            output.append("=" * 80)
            output.append("📋 TODO LIST")
            output.append("=" * 80)
            output.append(f"\nTotal items: {len(todo_list)}\n")
            
            for item in todo_list:
                status_emoji = "⏳" if item['status'] == 'pending' else "✅"
                output.append(f"{status_emoji} {item['step_number']}. {item['action']}")
                output.append(f"   ➤ {item['details']}")
                output.append(f"   Status: [{item['status'].upper()}]")
                output.append("")
            
            output.append("=" * 80)
            
            return CommandResult(success=True, message="\n".join(output))
        else:
            return CommandResult(
                success=False,
                message=f"Unknown subcommand: {subcommand}\n"
                        f"Use: /show ephemeral, /show eternal, /show pillar, /show vanisher, /show spark, or /show TODO_list"
            )

    command_handler.register_command("show", show_command_handler)

    # Register /mirror command to mirror files/directories to sandbox
    def mirror_command_handler(args):
        """Handle /mirror command to sync files with sandbox mirrors volume."""
        if not args:
            return CommandResult(
                success=False,
                message="Usage: /mirror do @<path> - Copy file/directory to sandbox mirror\n"
                        "       /mirror destroy @<path> - Remove mirror from sandbox\n"
                        "       /mirror sync @<path> - Sync changes from host to sandbox mirror\n"
                        "       /mirror revert+sync @<path> - Sync changes from sandbox mirror back to host\n"
                        "       /mirror exists @<path> - Check if mirror exists in sandbox\n"
                        "       /mirror synced @<path> - Check if host and sandbox mirror are in sync\n"
                        "       /mirror list - List all registered mirrors\n"
                        "\n"
                        "Examples:\n"
                        "  /mirror do @data - Copy data/ directory to sandbox\n"
                        "  /mirror sync @data - Update sandbox mirror with host changes\n"
                        "  /mirror exists @data - Check if data/ is mirrored\n"
                        "  /mirror synced @data - Check if data/ is in sync with mirror\n"
                        "  /mirror revert+sync @data - Apply sandbox changes back to host\n"
                        "  /mirror list - List all mirrors\n"
                        "  /mirror destroy @data - Remove data/ mirror from sandbox"
            )

        subcommand = args[0].lower()

        if subcommand not in ["do", "destroy", "sync", "revert+sync", "exists", "synced", "list"]:
            return CommandResult(
                success=False,
                message=f"Unknown subcommand: {subcommand}\n"
                        f"Use: /mirror do, /mirror destroy, /mirror sync, /mirror revert+sync, /mirror exists, /mirror synced, or /mirror list"
            )

        # Special handling for list subcommand (doesn't require path)
        if subcommand == "list":
            config = ConfigLoader()
            sandbox_url = config.get_sandbox_url()

            try:
                response = requests.get(
                    f"{sandbox_url}/mirror-list",
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    mirrors = result.get('mirrors', [])

                    if not mirrors:
                        return CommandResult(
                            success=True,
                            message="No mirrors registered"
                        )

                    messages = ["Registered mirrors:"]
                    for mirror in mirrors:
                        name = mirror.get('name', 'unknown')
                        mirror_type = mirror.get('type', 'unknown')
                        file_count = mirror.get('file_count', 0)
                        created_at = mirror.get('created_at', 'unknown')
                        sync_status = mirror.get('sync_status', 'unknown')
                        last_checked = mirror.get('last_checked', 'never')

                        # Format creation time
                        try:
                            from datetime import datetime
                            created_dt = datetime.fromisoformat(created_at)
                            created_str = created_dt.strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            created_str = created_at

                        # Format last checked time
                        try:
                            checked_dt = datetime.fromisoformat(last_checked)
                            checked_str = checked_dt.strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            checked_str = last_checked

                        sync_indicator = "✓" if sync_status == "synced" else "✗"
                        messages.append(f"\n  {sync_indicator} {name} ({mirror_type})")
                        messages.append(f"    Files: {file_count}")
                        messages.append(f"    Created: {created_str}")
                        messages.append(f"    Status: {sync_status}")
                        messages.append(f"    Last checked: {checked_str}")

                    return CommandResult(
                        success=True,
                        message="\n".join(messages)
                    )
                else:
                    error_msg = response.json().get('error', 'Unknown error')
                    return CommandResult(
                        success=False,
                        message=f"Failed to list mirrors: {error_msg}"
                    )

            except requests.exceptions.ConnectionError:
                return CommandResult(
                    success=False,
                    message="Cannot connect to sandbox service. Ensure Docker containers are running."
                )
            except requests.exceptions.Timeout:
                return CommandResult(
                    success=False,
                    message="Sandbox request timed out. The operation may still be in progress."
                )
            except Exception as e:
                handle_exception(e, context={
                    'command': 'mirror',
                    'subcommand': 'list'
                })
                return CommandResult(
                    success=False,
                    message=f"Error listing mirrors: {str(e)}"
                )

        # All other subcommands require a path argument
        if len(args) < 2:
            return CommandResult(
                success=False,
                message=f"Usage: /mirror {subcommand} @<path>"
            )

        path_arg = args[1]
        if not path_arg.startswith('@'):
            return CommandResult(
                success=False,
                message=f"Path must start with @ prefix. Example: /mirror {subcommand} @data"
            )

        # Resolve the @ path
        success, resolved_path, error = path_resolver.resolve_path(path_arg)
        if not success:
            return CommandResult(
                success=False,
                message=f"Failed to resolve path {path_arg}: {error}"
            )

        # Extract target name from path (remove @ prefix)
        target_name = path_arg[1:]  # Remove @

        config = ConfigLoader()
        sandbox_url = config.get_sandbox_url()

        try:
            if subcommand == "do":
                # Copy file/directory to sandbox mirror
                resolved = Path(resolved_path)

                if not resolved.exists():
                    return CommandResult(
                        success=False,
                        message=f"Path not found: {resolved_path}"
                    )

                if resolved.is_file():
                    # Upload single file
                    with open(resolved, 'rb') as f:
                        files = [('files', (resolved.name, f, 'application/octet-stream'))]
                        data = {'target_name': target_name}
                        response = requests.post(
                            f"{sandbox_url}/upload-directory",
                            files=files,
                            data=data,
                            timeout=30
                        )
                else:
                    # Upload directory
                    # Collect file paths first
                    file_paths = [(fp, fp.relative_to(resolved)) for fp in resolved.rglob('*') if fp.is_file()]

                    if not file_paths:
                        return CommandResult(
                            success=False,
                            message=f"No files found in directory: {resolved_path}"
                        )

                    # Open all files for streaming (requests library will read them lazily)
                    files_to_upload = []
                    file_handles = []
                    try:
                        for file_path, rel_path in file_paths:
                            fh = open(file_path, 'rb')
                            file_handles.append(fh)
                            files_to_upload.append(
                                ('files', (str(rel_path), fh, 'application/octet-stream'))
                            )

                        data = {'target_name': target_name}
                        response = requests.post(
                            f"{sandbox_url}/sync",
                            files=files_to_upload,
                            data=data,
                            timeout=60
                        )
                    finally:
                        # Close all file handles
                        for fh in file_handles:
                            try:
                                fh.close()
                            except Exception:
                                pass

                if response.status_code in [200, 207]:
                    result = response.json()
                    messages = [f"✓ Mirrored '{target_name}' to sandbox"]
                    if 'synced' in result:
                        messages.append(f"  Files synced: {len(result['synced'])}")
                    if 'failed' in result:
                        messages.append(f"  Files failed: {len(result['failed'])}")
                    return CommandResult(success=True, message="\n".join(messages))
                else:
                    error_msg = response.json().get('error', 'Unknown error')
                    return CommandResult(
                        success=False,
                        message=f"Failed to mirror to sandbox: {error_msg}"
                    )

            elif subcommand == "destroy":
                # Remove mirror from sandbox
                response = requests.delete(
                    f"{sandbox_url}/mirrors/remove/{target_name}",
                    timeout=30
                )

                if response.status_code == 200:
                    return CommandResult(
                        success=True,
                        message=f"✓ Removed mirror '{target_name}' from sandbox"
                    )
                elif response.status_code == 404:
                    return CommandResult(
                        success=False,
                        message=f"Mirror '{target_name}' not found in sandbox"
                    )
                else:
                    error_msg = response.json().get('error', 'Unknown error')
                    return CommandResult(
                        success=False,
                        message=f"Failed to remove mirror: {error_msg}"
                    )

            elif subcommand == "sync":
                # Sync changes from host to sandbox mirror
                resolved = Path(resolved_path)

                if not resolved.exists():
                    return CommandResult(
                        success=False,
                        message=f"Path not found: {resolved_path}"
                    )

                if resolved.is_file():
                    # Sync single file
                    with open(resolved, 'rb') as f:
                        files = [('files', (resolved.name, f, 'application/octet-stream'))]
                        data = {'target_name': target_name}
                        response = requests.post(
                            f"{sandbox_url}/sync",
                            files=files,
                            data=data,
                            timeout=30
                        )
                else:
                    # Sync directory
                    # Collect file paths first
                    file_paths = [(fp, fp.relative_to(resolved)) for fp in resolved.rglob('*') if fp.is_file()]

                    if not file_paths:
                        return CommandResult(
                            success=False,
                            message=f"No files found in directory: {resolved_path}"
                        )

                    # Open all files for streaming (requests library will read them lazily)
                    files_to_upload = []
                    file_handles = []
                    try:
                        for file_path, rel_path in file_paths:
                            fh = open(file_path, 'rb')
                            file_handles.append(fh)
                            files_to_upload.append(
                                ('files', (str(rel_path), fh, 'application/octet-stream'))
                            )

                        data = {'target_name': target_name}
                        response = requests.post(
                            f"{sandbox_url}/sync",
                            files=files_to_upload,
                            data=data,
                            timeout=60
                        )
                    finally:
                        # Close all file handles
                        for fh in file_handles:
                            try:
                                fh.close()
                            except Exception:
                                pass

                if response.status_code in [200, 207]:
                    result = response.json()
                    messages = [f"✓ Synced '{target_name}' to sandbox"]
                    if 'synced' in result:
                        messages.append(f"  Files synced: {len(result['synced'])}")
                    if 'deleted' in result and result['deleted']:
                        messages.append(f"  Files deleted: {len(result['deleted'])}")
                    if 'failed' in result:
                        messages.append(f"  Files failed: {len(result['failed'])}")
                    return CommandResult(success=True, message="\n".join(messages))
                else:
                    error_msg = response.json().get('error', 'Unknown error')
                    return CommandResult(
                        success=False,
                        message=f"Failed to sync to sandbox: {error_msg}"
                    )

            elif subcommand == "revert+sync":
                # Sync changes from sandbox mirror back to host
                # First, get the file list to understand what we're downloading
                metadata_response = requests.post(
                    f"{sandbox_url}/revert-sync",
                    json={'target_name': target_name},
                    timeout=30
                )

                if metadata_response.status_code == 404:
                    return CommandResult(
                        success=False,
                        message=f"Mirror '{target_name}' not found in sandbox"
                    )
                elif metadata_response.status_code != 200:
                    error_msg = metadata_response.json().get('error', 'Unknown error')
                    return CommandResult(
                        success=False,
                        message=f"Failed to get mirror info: {error_msg}"
                    )

                result = metadata_response.json()
                files_info = result.get('files', [])

                if not files_info:
                    return CommandResult(
                        success=True,
                        message=f"No files to sync from sandbox mirror '{target_name}'"
                    )

                # Download the mirror content
                download_response = requests.get(
                    f"{sandbox_url}/download-mirror/{target_name}",
                    timeout=60
                )

                if download_response.status_code != 200:
                    return CommandResult(
                        success=False,
                        message=f"Failed to download mirror from sandbox"
                    )

                # Prepare the host directory
                resolved = Path(resolved_path)

                # Track which files we're downloading from the mirror
                mirror_files = {file_info['name'] for file_info in files_info}

                try:
                    # Check if it's a zip file (directory) or single file
                    content_type = download_response.headers.get('content-type', '')

                    if 'application/zip' in content_type:
                        # Handle directory as zip archive
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
                            temp_zip.write(download_response.content)
                            temp_zip_path = temp_zip.name

                        try:
                            # Extract zip to host directory
                            resolved.mkdir(parents=True, exist_ok=True)

                            with zipfile.ZipFile(temp_zip_path, 'r') as zf:
                                zf.extractall(resolved)

                            updated_files = list(mirror_files)

                            # Delete files on host that don't exist in the mirror (true sync)
                            deleted_files = []
                            if resolved.is_dir():
                                for host_file in resolved.rglob('*'):
                                    if host_file.is_file():
                                        rel_path = str(host_file.relative_to(resolved))
                                        # Normalize path separators for comparison
                                        rel_path_normalized = rel_path.replace('\\', '/')
                                        mirror_files_normalized = {f.replace('\\', '/') for f in mirror_files}

                                        if rel_path_normalized not in mirror_files_normalized:
                                            try:
                                                host_file.unlink()
                                                deleted_files.append(rel_path)
                                            except Exception as e:
                                                handle_exception(e, context={
                                                    'command': 'mirror',
                                                    'subcommand': 'revert+sync',
                                                    'operation': 'delete_orphaned',
                                                    'file': rel_path
                                                })

                            messages = [
                                f"✓ Synced {len(updated_files)} file(s) from sandbox to host '{resolved_path}'"
                            ]
                            if deleted_files:
                                messages.append(f"  Files deleted from host: {len(deleted_files)}")

                            return CommandResult(success=True, message="\n".join(messages))
                        finally:
                            # Clean up temp file
                            try:
                                os.unlink(temp_zip_path)
                            except OSError:
                                # Ignore cleanup errors (file may not exist or already deleted)
                                pass

                    else:
                        # Handle single file
                        resolved.parent.mkdir(parents=True, exist_ok=True)
                        with open(resolved, 'wb') as f:
                            f.write(download_response.content)

                        return CommandResult(
                            success=True,
                            message=f"✓ Downloaded file from sandbox to '{resolved_path}'"
                        )

                except zipfile.BadZipFile:
                    return CommandResult(
                        success=False,
                        message="Failed to extract mirror archive (corrupted zip file)"
                    )
                except Exception as e:
                    handle_exception(e, context={
                        'command': 'mirror',
                        'subcommand': 'revert+sync',
                        'target': target_name
                    })
                    return CommandResult(
                        success=False,
                        message=f"Error downloading/extracting mirror: {str(e)}"
                    )

            elif subcommand == "exists":
                # Check if mirror exists in sandbox
                response = requests.get(
                    f"{sandbox_url}/mirror-exists/{target_name}",
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get('exists'):
                        is_file = result.get('is_file', False)
                        file_count = result.get('file_count', 0)
                        type_str = "file" if is_file else "directory"

                        messages = [f"✓ Mirror '{target_name}' exists in sandbox ({type_str})"]
                        if not is_file:
                            messages.append(f"  Contains {file_count} file(s)")

                        return CommandResult(success=True, message="\n".join(messages))
                    else:
                        return CommandResult(
                            success=True,
                            message=f"Mirror '{target_name}' does not exist in sandbox"
                        )
                else:
                    error_msg = response.json().get('error', 'Unknown error')
                    return CommandResult(
                        success=False,
                        message=f"Failed to check mirror existence: {error_msg}"
                    )

            elif subcommand == "synced":
                # Check if host and sandbox mirror are in sync
                resolved = Path(resolved_path)

                if not resolved.exists():
                    return CommandResult(
                        success=False,
                        message=f"Path not found: {resolved_path}"
                    )

                # Build file list from host
                host_files = []
                if resolved.is_file():
                    host_files.append({
                        'name': resolved.name,
                        'size': resolved.stat().st_size,
                        'modified': resolved.stat().st_mtime
                    })
                else:
                    for file_path in resolved.rglob('*'):
                        if file_path.is_file():
                            rel_path = file_path.relative_to(resolved)
                            host_files.append({
                                'name': str(rel_path),
                                'size': file_path.stat().st_size,
                                'modified': file_path.stat().st_mtime
                            })

                response = requests.post(
                    f"{sandbox_url}/mirror-synced",
                    json={
                        'target_name': target_name,
                        'files': host_files
                    },
                    timeout=30
                )

                if response.status_code == 404:
                    return CommandResult(
                        success=False,
                        message=f"Mirror '{target_name}' not found in sandbox"
                    )
                elif response.status_code == 200:
                    result = response.json()
                    if result.get('synced'):
                        return CommandResult(
                            success=True,
                            message=f"✓ Host and sandbox mirror '{target_name}' are in sync"
                        )
                    else:
                        differences = result.get('differences', {})
                        messages = [f"✗ Host and sandbox mirror '{target_name}' are NOT in sync:"]

                        only_in_host = differences.get('only_in_host', [])
                        only_in_mirror = differences.get('only_in_mirror', [])
                        different_size = differences.get('different_size', [])
                        different_modified = differences.get('different_modified', [])

                        if only_in_host:
                            messages.append(f"  Files only in host: {len(only_in_host)}")
                            for f in only_in_host[:5]:
                                messages.append(f"    - {f}")
                            if len(only_in_host) > 5:
                                messages.append(f"    ... and {len(only_in_host) - 5} more")

                        if only_in_mirror:
                            messages.append(f"  Files only in mirror: {len(only_in_mirror)}")
                            for f in only_in_mirror[:5]:
                                messages.append(f"    - {f}")
                            if len(only_in_mirror) > 5:
                                messages.append(f"    ... and {len(only_in_mirror) - 5} more")

                        if different_size:
                            messages.append(f"  Files with different sizes: {len(different_size)}")
                            for diff in different_size[:5]:
                                messages.append(f"    - {diff['name']} (host: {diff['host_size']}, mirror: {diff['mirror_size']})")
                            if len(different_size) > 5:
                                messages.append(f"    ... and {len(different_size) - 5} more")

                        if different_modified:
                            messages.append(f"  Files with different timestamps: {len(different_modified)}")

                        return CommandResult(success=False, message="\n".join(messages))
                else:
                    error_msg = response.json().get('error', 'Unknown error')
                    return CommandResult(
                        success=False,
                        message=f"Failed to check sync status: {error_msg}"
                    )

        except requests.exceptions.ConnectionError:
            return CommandResult(
                success=False,
                message="Cannot connect to sandbox service. Ensure Docker containers are running."
            )
        except requests.exceptions.Timeout:
            return CommandResult(
                success=False,
                message="Sandbox request timed out. The operation may still be in progress."
            )
        except Exception as e:
            handle_exception(e, context={
                'command': 'mirror',
                'subcommand': subcommand,
                'target': target_name
            })
            return CommandResult(
                success=False,
                message=f"Error executing mirror command: {str(e)}"
            )

    command_handler.register_command("mirror", mirror_command_handler)

    # Register /code command for combined coding workflow operations
    def code_command_handler(args):
        """Handle /code command for combined coding workflow operations.

        /code init @<path> - Initialize coding session (mirror + pillar load)
        /code session exit @<path> - End coding session (revert+sync + exit)
        """
        if not args:
            return CommandResult(
                success=False,
                message="Usage: /code init @<path> <task> - Initialize coding session\n"
                        "       /code session exit @<path> - End coding session\n"
                        "\n"
                        "Examples:\n"
                        "  /code init @myproject Add user authentication with JWT\n"
                        "  /code session exit @myproject - Sync changes back and exit"
            )

        subcommand = args[0].lower()

        # Handle 'session exit' as a two-word subcommand
        if subcommand == "session" and len(args) > 1 and args[1].lower() == "exit":
            # /code session exit @<path>
            if len(args) < 3:
                return CommandResult(
                    success=False,
                    message="Usage: /code session exit @<path>"
                )

            path_arg = args[2]
            if not path_arg.startswith('@'):
                return CommandResult(
                    success=False,
                    message=f"Path must start with @ prefix. Example: /code session exit @myproject"
                )

            # Execute revert+sync
            revert_result = mirror_command_handler(["revert+sync", path_arg])

            if not revert_result.success:
                return CommandResult(
                    success=False,
                    message=f"Failed to sync changes back:\n{revert_result.message}"
                )

            # Return success with exit signal
            return CommandResult(
                success=True,
                message=f"{revert_result.message}\n\n"
                        f"Coding session ended. Changes synced back to host.\n"
                        f"Type 'exit' to leave the CLI.",
                data={'should_exit': True}
            )

        elif subcommand == "init":
            # /code init @<path> <task description>
            if len(args) < 2:
                return CommandResult(
                    success=False,
                    message="Usage: /code init @<path> <task description>"
                )

            path_arg = args[1]
            if not path_arg.startswith('@'):
                return CommandResult(
                    success=False,
                    message=f"Path must start with @ prefix. Example: /code init @myproject Add authentication"
                )

            # Task is everything after the path
            if len(args) < 3:
                return CommandResult(
                    success=False,
                    message="Task description is required.\n"
                            "Usage: /code init @<path> <task description>\n"
                            "Example: /code init @myproject Add user authentication with JWT"
                )

            task = " ".join(args[2:])

            # Check if vanisher context is enabled
            if not vanisher_context.is_enabled():
                return CommandResult(
                    success=False,
                    message="Vanisher context is disabled. Enable coding mode with --coding flag to use /code init."
                )

            messages = []

            # Step 1: Execute mirror do
            mirror_result = mirror_command_handler(["do", path_arg])

            if not mirror_result.success:
                return CommandResult(
                    success=False,
                    message=f"Failed to mirror folder:\n{mirror_result.message}"
                )

            messages.append(f"[1/2] Mirror: {mirror_result.message}")

            # Step 2: Execute vanisher load
            # Extract the path without @ for label generation
            target_name = path_arg[1:]  # Remove @

            vanisher_result = vanisher_command_handler(["load", path_arg])

            if not vanisher_result.success:
                messages.append(f"[2/2] Vanisher load failed: {vanisher_result.message}")
                return CommandResult(
                    success=False,
                    message="\n\n".join(messages)
                )

            messages.append(f"[2/2] Vanisher: {vanisher_result.message}")

            messages.append(f"\nCoding session initialized for '{target_name}'.")
            messages.append(f"Task: {task}")

            # Direct MCP tool calls instead of auto-prompt
            try:
                # Initialize MCP manager and tools
                mcp_manager = MirrorVanisherManager()
                planning_tools = PlanningTools(mcp_manager)

                # Step 3: Create plan
                messages.append("\n[3/4] Creating implementation plan...")
                plan_result = planning_tools.create_plan(target_name, task)

                if not plan_result.get('success', False):
                    error_msg = plan_result.get('error', 'Unknown error creating plan')
                    messages.append(f"[3/4] Plan creation failed: {error_msg}")
                    return CommandResult(
                        success=False,
                        message="\n\n".join(messages)
                    )

                # Show plan summary
                todo_list = plan_result.get('TODO_list', [])
                plan_type = plan_result.get('type', 'feature')
                messages.append(f"[3/4] Plan created: {len(todo_list)} steps ({plan_type})")

                # Step 4: Execute plan with Ouroboros
                messages.append("\n[4/4] Executing plan with Ouroboros auto-executor...")

                executor = ExecutePlan(mcp_manager)
                exec_result = executor.execute_plan(auto_execute=True)

                if not exec_result.get('success', False):
                    error_msg = exec_result.get('error', 'Unknown error executing plan')
                    messages.append(f"[4/4] Execution failed: {error_msg}")
                    return CommandResult(
                        success=False,
                        message="\n\n".join(messages)
                    )

                # Show execution summary
                completed = exec_result.get('completed_count', 0)
                failed = exec_result.get('failed_count', 0)
                total = exec_result.get('detailed_todo_list_count', 0)
                cancelled = exec_result.get('cancelled', False)

                if cancelled:
                    messages.append(f"[4/4] Execution cancelled: {completed}/{total} steps completed")
                else:
                    messages.append(f"[4/4] Execution complete: {completed}/{total} steps completed, {failed} failed")

                # Include execution output if available
                output = exec_result.get('output', '')
                if output:
                    messages.append(f"\n{output}")

                return CommandResult(
                    success=True,
                    message="\n\n".join(messages),
                    data={
                        'plan_result': plan_result,
                        'exec_result': exec_result
                    }
                )

            except Exception as e:
                handle_exception(e, context={
                    'function': 'code_command_handler',
                    'operation': 'direct MCP tool calls',
                    'target': target_name,
                    'task': task
                })
                messages.append(f"\nError during MCP execution: {str(e)}")
                return CommandResult(
                    success=False,
                    message="\n\n".join(messages)
                )

        else:
            return CommandResult(
                success=False,
                message=f"Unknown subcommand: {subcommand}\n"
                        f"Available: /code init @<path>, /code session exit @<path>"
            )

    command_handler.register_command("code", code_command_handler)

    def detect_and_load_spark_references(prompt_text: str) -> tuple:
        """Detect and load @ references in prompt as Sparks.

        Args:
            prompt_text: The user's prompt text

        Returns:
            Tuple of (modified_prompt, loaded_sparks_list, errors_list)
        """
        import re

        # Find all @ references in the prompt (pattern: @path/to/file or @filename)
        # Match @ followed by non-whitespace characters
        pattern = r'@([^\s]+)'
        matches = re.findall(pattern, prompt_text)

        if not matches:
            return prompt_text, [], []

        loaded_sparks = []
        errors = []

        for match in matches:
            path = f"@{match}"

            # Check if this path is already loaded as Spark, ephemeral, or eternal
            # If so, skip it (avoid duplicate loading)
            path_without_at = match
            existing_spark = spark_context.get_context_by_label(path_without_at)
            existing_ephemeral = ephemeral_context.get_context_by_label(path_without_at)
            existing_eternal = eternal_context.get_context_by_label(path_without_at)

            if existing_spark or existing_ephemeral or existing_eternal:
                continue  # Already loaded, skip

            # Try to load as Spark
            success, resolved_path, error = path_resolver.resolve_path(path)
            if not success:
                errors.append(f"Failed to resolve {path}: {error}")
                continue

            # Check if it's a directory or file
            if path_resolver.is_directory(path):
                # Load directory as Spark
                dir_success, dir_message = spark_context.load_directory(resolved_path, label_prefix=path_without_at)
                if dir_success:
                    loaded_sparks.append(f"{path} (directory)")
                else:
                    errors.append(f"Failed to load directory {path}: {dir_message}")
            else:
                # Load file as Spark
                file_success, file_message = spark_context.load_file(resolved_path, label=path_without_at)
                if file_success:
                    loaded_sparks.append(path)
                else:
                    errors.append(f"Failed to load {path}: {file_message}")

        # Return original prompt (keep @ references in the text), loaded sparks, and errors
        return prompt_text, loaded_sparks, errors

    def process_prompt_injections(prompt_text: str) -> str:
        """Process :category shortcuts and replace with random phrases.

        Args:
            prompt_text: The user's prompt text

        Returns:
            Modified prompt with :category replaced by random phrases with emojis
        """
        import re
        from src.utils.prompt_injection_completer import PromptInjectionCompleter

        # Check if there are any :category patterns
        pattern = r':(\w+)'
        if not re.search(pattern, prompt_text):
            return prompt_text

        # Initialize the completer to get phrases
        completer = PromptInjectionCompleter()

        def replace_with_phrase(match):
            """Replace :category with random phrase from that category."""
            category = match.group(1)
            phrase = completer.get_random_phrase(category)
            emoji = completer.get_category_emoji(category)

            if phrase:
                # Add emoji before the phrase
                return f"{emoji} {phrase}"
            else:
                # Keep original if category not found
                return match.group(0)

        # Replace all :category with phrases
        modified_prompt = re.sub(pattern, replace_with_phrase, prompt_text)

        return modified_prompt

    if verbose:
        history_count = prompt_manager.get_history_count()
        print_info(f"Prompt history loaded: {history_count} previous prompts available")
        print_info(f"Auto-complete enabled: Press ↑/↓ to navigate history, → to accept suggestion")

        if conversation_history.is_enabled():
            conv_count = conversation_history.get_history_count()
            print_info(f"Conversation history enabled: {conv_count} previous conversations")
            print_info(f"Commands available: {', '.join(['/' + cmd for cmd in command_handler.get_available_commands()])}")

        console.print()

    while True:
        try:
            # Get prompt with history and auto-complete
            prompt = prompt_manager.get_prompt()

            if prompt.lower() in ['exit', 'quit']:
                console.print("\n[bold cyan]👋 Goodbye![/bold cyan]\n")
                break

            if not prompt.strip():
                continue

            # Replace :category shortcuts with random phrases
            prompt = process_prompt_injections(prompt)

            # Check if this is a command
            if command_handler.is_command(prompt):
                result = command_handler.execute(prompt)
                if result:
                    if result.success:
                        print_success(result.message)
                    else:
                        print_error(result.message)

                    # Check if command returned an auto-prompt to execute
                    if result.data and isinstance(result.data, dict) and result.data.get('auto_prompt'):
                        # Use auto_prompt as the next prompt instead of continuing
                        prompt = result.data['auto_prompt']
                        if verbose:
                            print_info("Auto-executing prompt from command...")
                        # Don't continue - fall through to process the prompt
                    else:
                        continue
                else:
                    continue

            # Detect and load @ references as Sparks (if not already loaded)
            prompt, loaded_sparks, spark_errors = detect_and_load_spark_references(prompt)

            # Show loaded Sparks
            if loaded_sparks and verbose:
                print_info(f"Loaded {len(loaded_sparks)} Spark(s): {', '.join(loaded_sparks)}")

            # Show Spark loading errors
            if spark_errors:
                for error in spark_errors:
                    print_warning(error)

            # Print user prompt in verbose mode
            if verbose:
                print_user_prompt(prompt)

            # Timing for overall request
            request_start = time.time()

            # Load auto-iteration config with safe defaults
            config = ConfigLoader()
            max_iterations_config = config.get_auto_iteration_max_iterations()
            max_iterations = max_iterations_config if isinstance(max_iterations_config, int) else 5
            
            timeout_config = config.get_auto_iteration_timeout()
            timeout_seconds = timeout_config if isinstance(timeout_config, int) else 3
            
            increment_config = config.get_auto_iteration_negative_weight_increment()
            negative_weight_increment = increment_config if isinstance(increment_config, (int, float)) else 0.1

            # Auto-iteration loop
            iteration_number = 0
            negative_weight_boost = 0.0
            rating = None

            while iteration_number < max_iterations:
                # Get eternal context (filtered by semantic relevance to prompt)
                eternal_context_str = ""
                if eternal_context.is_enabled():
                    eternal_context_str = eternal_context.get_context_string(prompt=prompt, verbose=verbose)

                    if eternal_context_str and verbose:
                        # Get relevant contexts to show count
                        relevant = eternal_context.get_relevant_contexts(prompt, verbose=verbose)
                        loaded_labels = [label for label, ctx, score in relevant]
                        print_debug("Eternal Context", {
                            "contexts_loaded": len(relevant),
                            "loaded": loaded_labels if loaded_labels else "none",
                            "total_contexts": eternal_context.get_context_count(),
                            "relevance_filtered": eternal_context.semantic_filtering_enabled
                        })

                # Get pillar context (coding mode - filtered by semantic relevance to prompt)
                pillar_context_str = ""
                if pillar_context.is_enabled():
                    pillar_context_str = pillar_context.get_context_string(prompt=prompt, verbose=verbose)

                    if pillar_context_str and verbose:
                        # Get relevant contexts to show count
                        relevant = pillar_context.get_relevant_contexts(prompt, verbose=verbose)
                        loaded_labels = [label for label, ctx, score in relevant]
                        print_debug("Pillar Context", {
                            "contexts_loaded": len(relevant),
                            "loaded": loaded_labels if loaded_labels else "none",
                            "total_contexts": pillar_context.get_context_count(),
                            "relevance_filtered": pillar_context.semantic_filtering_enabled
                        })

                # Get ephemeral context (filtered by semantic relevance to prompt)
                ephemeral_context_str = ""
                if ephemeral_context.is_enabled():
                    ephemeral_context_str = ephemeral_context.get_context_string(prompt=prompt, verbose=verbose)

                    if ephemeral_context_str and verbose:
                        # Get relevant contexts to show count
                        relevant = ephemeral_context.get_relevant_contexts(prompt, verbose=verbose)
                        loaded_labels = [ctx.label for ctx, score in relevant]
                        print_debug("Ephemeral Context", {
                            "contexts_loaded": len(relevant),
                            "loaded": loaded_labels if loaded_labels else "none",
                            "total_contexts": ephemeral_context.get_context_count(),
                            "relevance_filtered": ephemeral_context.semantic_filtering_enabled
                        })

                # Get vanisher context (coding mode - filtered by semantic relevance to prompt)
                vanisher_context_str = ""
                if vanisher_context.is_enabled():
                    vanisher_context_str = vanisher_context.get_context_string(prompt=prompt, verbose=verbose)

                    if vanisher_context_str and verbose:
                        # Get relevant contexts to show count
                        relevant = vanisher_context.get_relevant_contexts(prompt, verbose=verbose)
                        loaded_labels = [ctx.label for ctx, score in relevant]
                        print_debug("Vanisher Context", {
                            "contexts_loaded": len(relevant),
                            "loaded": loaded_labels if loaded_labels else "none",
                            "total_contexts": vanisher_context.get_context_count(),
                            "relevance_filtered": vanisher_context.semantic_filtering_enabled
                        })

                # Get Spark context (in-memory ephemeral, dies with /clear context)
                spark_context_str = ""
                if spark_context.is_enabled():
                    spark_context_str = spark_context.get_context_string()

                    if spark_context_str and verbose:
                        print_debug("Spark Context", {
                            "contexts_loaded": spark_context.get_count()
                        })

                # Retrieve relevant conversation history if enabled
                # SKIP during auto-iteration retries to avoid corrupting heuristic learning
                conversation_context = ""
                if conversation_history.is_enabled() and iteration_number == 0:
                    top_k = heuristics_config.get_conversation_history_top_k()
                    min_similarity = heuristics_config.get_conversation_history_min_similarity()
                    include_in_context = heuristics_config.get_conversation_history_include_in_context()

                    if include_in_context:
                        relevant_history = conversation_history.retrieve_relevant_history(
                            prompt,
                            top_k=top_k,
                            min_similarity=min_similarity
                        )

                        if relevant_history and verbose:
                            print_debug("Conversation History", {
                                "relevant_turns": len(relevant_history),
                                "top_similarity": f"{relevant_history[0][1]:.2%}" if relevant_history else "N/A"
                            })

                        conversation_context = conversation_history.format_history_for_context(relevant_history)
                elif conversation_history.is_enabled() and iteration_number > 0 and verbose:
                    print_info("🔇 Conversation history disabled during auto-iteration (heuristics-only mode)")

                # Fetch similar heuristic to enhance context (with boost if iterating)
                heuristic_context, heuristic_data = fetch_similar_heuristic(
                    prompt,
                    verbose=verbose,
                    negative_weight_boost=negative_weight_boost
                )

                # Enhance prompt with contexts: eternal/pillar, ephemeral/vanisher, spark, conversation history, and heuristic context
                enhanced_prompt = prompt
                context_parts = []

                # Order: Eternal/Pillar (first, permanent), Ephemeral/Vanisher (session), Spark (in-memory), Conversation, Heuristics
                if eternal_context_str:
                    context_parts.append(eternal_context_str)

                if pillar_context_str:
                    context_parts.append(pillar_context_str)

                if ephemeral_context_str:
                    context_parts.append(ephemeral_context_str)

                if vanisher_context_str:
                    context_parts.append(vanisher_context_str)

                if spark_context_str:
                    context_parts.append(spark_context_str)

                if conversation_context:
                    context_parts.append(conversation_context)

                if heuristic_context:
                    context_parts.append(heuristic_context)

                if context_parts:
                    enhanced_prompt = "\n\n".join(context_parts) + f"\n\nUser query: {prompt}"

                    if verbose:
                        print_debug("Enhanced Prompt", {
                            "original_length": len(prompt),
                            "enhanced_length": len(enhanced_prompt),
                            "eternal_context": len(eternal_context_str) if eternal_context_str else 0,
                            "pillar_context": len(pillar_context_str) if pillar_context_str else 0,
                            "ephemeral_context": len(ephemeral_context_str) if ephemeral_context_str else 0,
                            "vanisher_context": len(vanisher_context_str) if vanisher_context_str else 0,
                            "spark_context": len(spark_context_str) if spark_context_str else 0,
                            "conversation_context": len(conversation_context) if conversation_context else 0,
                            "heuristic_context": len(heuristic_context) if heuristic_context else 0,
                            "iteration": iteration_number,
                            "negative_weight_boost": negative_weight_boost
                        })

                # Inject reasoning prompt for auto-iteration retries (the cherry on top!)
                # When iteration_number > 0, it means we got rating=0 and are retrying
                # SKIP if we have user_feedback - we want LLM to follow the correction, not overthink it
                if heuristic_data and heuristic_data.get('matched_heuristic'):
                    user_feedback_value = heuristic_data.get('matched_heuristic', {}).get('user_feedback', '')
                else:
                    user_feedback_value = ''
                has_user_feedback = bool(user_feedback_value and user_feedback_value.strip())

                if iteration_number > 0 and not has_user_feedback:
                    from src.utils.prompt_injection_completer import PromptInjectionCompleter
                    completer = PromptInjectionCompleter()
                    reasoning_phrase = completer.get_random_phrase('reasoning')
                    reasoning_emoji = completer.get_category_emoji('reasoning')

                    if reasoning_phrase:
                        # Inject the reasoning instruction into the prompt
                        reasoning_injection = f"{reasoning_emoji} {reasoning_phrase}"
                        enhanced_prompt = f"{enhanced_prompt}\n\n{reasoning_injection}"

                        if verbose:
                            print_info(f"🍒 Auto-iteration boost: Added reasoning prompt - '{reasoning_phrase}'")
                elif iteration_number > 0 and has_user_feedback and verbose:
                    print_info("🎯 Skipping reasoning boost - user correction provided (follow directive, don't overthink)")

                # Check token limit before generating (proactive warning)
                token_manager = get_token_limit_manager()
                is_within_limit, limit_warning = token_manager.check_limit(model, enhanced_prompt)

                if not is_within_limit and verbose:
                    print_warning(limit_warning)
                    # Continue anyway - the actual error will be caught and limit stored if it fails

                # Generate response
                llm_start = time.time()
                response, execution_time_ms = generate(model, enhanced_prompt)
                llm_duration = (time.time() - llm_start) * 1000

                if verbose:
                    print_timing_verbose("LLM generation", llm_duration)

                # Print response with markdown formatting
                print_response(response)

                # Store conversation turn in history (do this before feedback to ensure it's captured)
                if conversation_history.is_enabled():
                    stored = conversation_history.add_turn(prompt, response)
                    if verbose and stored:
                        conv_count = conversation_history.get_history_count()
                        print_debug("Conversation History", {
                            "stored": True,
                            "total_turns": conv_count
                        })

                # Collect feedback if enabled
                feedback_data = feedback_collector.collect_feedback(prompt, response)

                if feedback_data:
                    rating = feedback_data.get('rating')

                    # Add execution time and metadata to feedback
                    feedback_data['execution_time_ms'] = execution_time_ms

                    # Add auto-iteration metadata
                    # is_auto_iteration is True in two cases:
                    # 1. iteration_number > 0: This is a subsequent retry attempt (not the first)
                    # 2. could_retry: This is the first attempt (iteration 0) BUT got rating=0 and we can retry
                    #    - This flags the first failed attempt so we know it's part of an auto-iteration cycle
                    # is_auto_iteration is False only when:
                    # - First attempt (iteration 0) with any rating other than 0
                    # - OR at max iterations (no more retries possible)
                    could_retry = (rating == 0 and iteration_number + 1 < max_iterations)
                    feedback_data['iteration_number'] = iteration_number
                    feedback_data['is_auto_iteration'] = (iteration_number > 0 or could_retry)
                    feedback_data['negative_weight_boost'] = negative_weight_boost

                    # Add heuristic context metadata if available
                    if heuristic_data and heuristic_data.get('matched_heuristic'):
                        feedback_data['parent_heuristic_id'] = heuristic_data['matched_heuristic'].get('_id')

                        # Add chain information
                        chain = heuristic_data.get('chain', [])
                        if chain:
                            feedback_data['chain_ids'] = [doc.get('_id') for doc in chain if doc.get('_id')]
                            feedback_data['chain_depth'] = len(chain) + 1
                        else:
                            feedback_data['chain_depth'] = 1

                        # Add contexted heuristic IDs
                        feedback_data['contexted_heuristic_ids'] = [heuristic_data['matched_heuristic'].get('_id')]

                    if verbose:
                        console.print()

                    # Send to sandbox for heuristics processing
                    # Force synchronous processing during auto-iteration to ensure
                    # the heuristic is stored before the next retry
                    force_sync = (iteration_number > 0 or rating == 0)  # Sync for iterations and potential retries

                    if verbose and could_retry:
                        print_info("📝 Storing failed attempt as negative heuristic for next iteration...")

                    send_feedback_to_sandbox(feedback_data, verbose=(verbose or force_sync))

                    # Check if we should auto-iterate (rating == 0)
                    # SKIP auto-iteration in coding mode
                    if rating == 0:
                        if coding:
                            # Coding mode: auto-iteration disabled, just break
                            if verbose:
                                print_info("⚠️  Rating 0 received, but auto-iteration is disabled in coding mode")
                            break
                        elif iteration_number + 1 < max_iterations:
                            # Ask user if they want to retry with timeout
                            console.print(f"\n[yellow]⚠️  Response out of context (attempt {iteration_number + 1}/{max_iterations})[/yellow]")

                            retry_response = input_with_timeout(
                                f"Retry with increased anti-pattern learning? (Y/n) [auto in {timeout_seconds}s]: ",
                                timeout_seconds,
                                'Y'
                            )

                            if retry_response.lower() == 'n':
                                if verbose:
                                    print_info("User declined auto-iteration, moving to next prompt")
                                break  # Exit iteration loop

                            # User agreed or timeout - continue iteration
                            iteration_number += 1
                            negative_weight_boost += negative_weight_increment
                            negative_weight_boost = min(1.0, negative_weight_boost)  # Cap at 1.0

                            if verbose:
                                print_info(f"🔄 Retrying (iteration {iteration_number + 1}/{max_iterations}) with negative_weight_boost={negative_weight_boost:.2f}")

                            continue  # Retry with increased boost

                        else:
                            # Max iterations exceeded
                            console.print(f"\n[red]❌ Max iterations ({max_iterations}) exceeded[/red]")
                            console.print("\n[bold yellow]💡 Help us learn![/bold yellow]")
                            console.print("Would you like to provide the correct response? This will help improve future answers.")

                            try:
                                provide_response = input("\nProvide correct response? (y/N): ").strip().lower()

                                if provide_response == 'y':
                                    console.print("\n[bold]Please enter the correct response (or what you think is correct):[/bold]")
                                    console.print("[dim]Press Enter twice when done (two consecutive empty lines to finish)[/dim]\n")

                                    # Collect multi-line response
                                    correct_response_lines = []
                                    consecutive_empty_lines = 0
                                    while True:
                                        try:
                                            line = input()
                                            if line == "":
                                                consecutive_empty_lines += 1
                                                # Break on two consecutive empty lines
                                                if consecutive_empty_lines >= 2:
                                                    # Remove the first trailing empty line that was appended
                                                    if correct_response_lines and correct_response_lines[-1] == "":
                                                        correct_response_lines.pop()
                                                    break
                                            else:
                                                consecutive_empty_lines = 0
                                            correct_response_lines.append(line)
                                        except (EOFError, KeyboardInterrupt):
                                            # User cancelled input (Ctrl+C or Ctrl+D)
                                            break

                                    correct_response = "\n".join(correct_response_lines).strip()

                                    if correct_response:
                                        # Store this as a high-quality heuristic
                                        correct_feedback_data = {
                                            'prompt': prompt,
                                            'response': correct_response,
                                            'rating': 5,  # Mark as highest quality
                                            'timestamp': feedback_data.get('timestamp') if feedback_data else time.strftime('%Y-%m-%dT%H:%M:%S'),
                                            'execution_time_ms': 0,  # User-provided
                                            'iteration_number': max_iterations,
                                            'is_auto_iteration': False,  # This is the final correct answer
                                            'negative_weight_boost': 0.0,
                                            'user_provided_correction': True  # Flag to identify user corrections
                                        }

                                        # Add heuristic context if available
                                        if heuristic_data and heuristic_data.get('matched_heuristic'):
                                            correct_feedback_data['parent_heuristic_id'] = heuristic_data['matched_heuristic'].get('_id')
                                            correct_feedback_data['contexted_heuristic_ids'] = [heuristic_data['matched_heuristic'].get('_id')]

                                        if verbose:
                                            console.print()
                                            print_info("📝 Storing user-provided correct response as high-quality heuristic...")

                                        send_feedback_to_sandbox(correct_feedback_data, verbose=verbose)
                                        console.print("\n[green]✓ Thank you! Your response has been stored to improve future answers.[/green]")
                                    else:
                                        console.print("\n[yellow]No response provided, skipping.[/yellow]")

                            except (EOFError, KeyboardInterrupt):
                                # User interrupted during "provide correct response" flow (Ctrl+C or Ctrl+D)
                                # Silently continue to options menu - this is intentional UX
                                pass

                            # Now show the options menu
                            console.print("\n[bold]What would you like to do next?[/bold]")
                            console.print("1) Rephrase your prompt")
                            console.print("2) Continue to next prompt")
                            console.print("3) Exit interactive mode")

                            try:
                                choice = input("\nChoice (1/2/3): ").strip()

                                if choice == '1':
                                    # Let user rephrase - break iteration loop to get new prompt
                                    break
                                elif choice == '3':
                                    # Exit interactive mode
                                    console.print("\n[bold cyan]👋 Goodbye![/bold cyan]\n")
                                    return
                                # else: choice == '2' or any other - continue to next prompt
                            except (EOFError, KeyboardInterrupt):
                                # User interrupted during options menu selection (Ctrl+C or Ctrl+D)
                                # Silently exit iteration loop and continue - this is intentional UX
                                pass

                            break  # Exit iteration loop
                    else:
                        # Rating > 0, success! Exit iteration loop
                        if iteration_number > 0 and verbose:
                            print_success(f"✓ Positive rating received after {iteration_number + 1} attempts")
                        break

                else:
                    # No feedback collected (user skipped) - exit iteration loop
                    break

            # Print total request timing
            total_duration = (time.time() - request_start) * 1000
            if verbose:
                print_timing_verbose("Total request", total_duration)
                console.print()

        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold cyan]👋 Goodbye![/bold cyan]\n")
            break

        except Exception as e:
            handle_exception(e, context={
                'mode': 'interactive',
                'model': model,
                'verbose': verbose
            })
            print_error(str(e))

def non_interactive_mode(model, prompt, verbose=False, coding=False):
    """Run non-interactive mode with a single prompt.

    Args:
        model: The LLM model to use
        prompt: The prompt to process
        verbose: Enable verbose debugging output
        coding: Coding mode flag (ignored in non-interactive mode)
    """
    # Set global verbose mode
    set_verbose_mode(verbose)

    # Show warning if coding mode was requested
    if coding:
        print_warning("⚠️  Coding mode is only available in interactive mode. Use ./start.sh --coding without -p flag.")

    try:
        if verbose:
            print_user_prompt(prompt)

        # Fetch similar heuristic to enhance context
        heuristic_context, heuristic_data = fetch_similar_heuristic(prompt, verbose=verbose)
        
        # Enhance prompt with heuristic context if available
        enhanced_prompt = prompt
        if heuristic_context:
            enhanced_prompt = f"{heuristic_context}\n\nUser query: {prompt}"

            if verbose:
                print_debug("Enhanced Prompt", {
                    "original_length": len(prompt),
                    "enhanced_length": len(enhanced_prompt),
                    "context_added": len(heuristic_context)
                })

        # Generate response
        response, execution_time_ms = generate(model, enhanced_prompt)

        if verbose:
            print_timing_verbose("LLM generation", execution_time_ms)
            print_response(response)
        else:
            # Non-verbose: just print plain response
            print(response)

    except Exception as e:
        handle_exception(e, context={
            'mode': 'non_interactive',
            'model': model,
            'prompt_length': len(prompt),
            'verbose': verbose
        })
        print_error(str(e))

def main():
    initialize_error_handler()

    try:
        parser = ArgumentParser()
        args = parser.parse_args()

        # Set verbose mode from args
        verbose = args.verbose
        coding = args.coding

        # Wait for services to be ready before proceeding
        if not wait_for_services():
            print_error("Cannot proceed without services. Exiting.")
            sys.exit(1)

        capture_message("CLI started", level="info", context={
            'mode': 'interactive' if not args.prompt else 'non_interactive',
            'model': args.model,
            'verbose': verbose,
            'coding': coding
        })

        if args.prompt:
            non_interactive_mode(args.model, args.prompt, verbose=verbose, coding=coding)
        else:
            interactive_mode(args.model, verbose=verbose, coding=coding)

    except Exception as e:
        handle_exception(e, context={'function': 'main'})
        sys.exit(1)

if __name__ == '__main__':
    main()
