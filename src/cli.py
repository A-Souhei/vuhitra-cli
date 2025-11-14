import sys
import logging
import requests
import time
from src.agent import generate
from src.utils.arg_parser import ArgumentParser
from src.errors_handler import handle_exception, capture_message, get_error_handler
from src.utils.config_loader import ConfigLoader
from src.utils.feedback_collector import FeedbackCollector
from src.utils.ui_formatter import (
    set_verbose_mode, is_verbose, print_banner, print_response,
    print_context_verbose, print_context_content_verbose, print_elasticsearch_verbose,
    print_nlp_analysis_verbose, print_timing_verbose, print_error, print_warning,
    print_success, print_info, print_debug, print_user_prompt, console
)
from src.utils.prompt_history import PromptHistoryManager

# Maximum prompt length to prevent DoS through excessive payload sizes
MAX_PROMPT_LENGTH = 10000

logger = logging.getLogger(__name__)

def initialize_error_handler():
    """Initialize the error handler with configuration."""
    try:
        config = ConfigLoader()
        error_handler = get_error_handler()
        error_handler.configure(config_loader=config)
    except Exception as e:
        print(f"WARNING: Failed to initialize error handler: {str(e)}", file=sys.stderr)

def fetch_similar_heuristic(prompt, verbose=False):
    """Fetch similar heuristic from sandbox to enhance LLM context."""
    endpoint = None  # Initialize before try block
    start_time = time.time()

    try:
        # Validate prompt length
        if len(prompt) > MAX_PROMPT_LENGTH:
            logger.warning(f"Prompt length ({len(prompt)}) exceeds maximum ({MAX_PROMPT_LENGTH}), truncating")
            prompt = prompt[:MAX_PROMPT_LENGTH]

        config = ConfigLoader()
        sandbox_url = config.get_sandbox_url()
        endpoint = f"{sandbox_url}/retrieve/similar"
        confidence_threshold = config.get_sandbox_confidence_threshold()

        if verbose:
            print_debug("Heuristic Retrieval Request", {
                "endpoint": endpoint,
                "prompt_length": len(prompt),
                "confidence_threshold": confidence_threshold,
                "min_rating": 4
            })

        response = requests.post(
            endpoint,
            json={"prompt": prompt, "min_rating": 4, "verbose": verbose},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        duration_ms = (time.time() - start_time) * 1000
        print_timing_verbose("Heuristic retrieval", duration_ms)

        # Print verbose context information
        if verbose and data.get('matched_heuristic'):
            print_context_verbose(data)

        # Check if this is a negative heuristic (anti-pattern)
        is_negative = data.get('is_negative', False)

        # Return the formatted insight if available and confidence is good
        if (data.get('confidence_score', 0) > confidence_threshold and
            data.get('insights') and
            data['insights'].get('formatted_insight')):

            formatted_insight = data['insights']['formatted_insight']

            if verbose:
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
                print_info(f"No suitable heuristic match (confidence: {data.get('confidence_score', 0):.2%} < {confidence_threshold:.2%})")

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
            print_debug("Feedback Submission", {
                "endpoint": endpoint,
                "rating": feedback_data.get('rating'),
                "prompt_length": len(feedback_data.get('prompt', '')),
                "response_length": len(feedback_data.get('response', '')),
                "execution_time_ms": feedback_data.get('execution_time_ms')
            })

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

def interactive_mode(model, verbose=False):
    """Run interactive mode with enhanced UI and verbose logging."""
    # Set global verbose mode
    set_verbose_mode(verbose)

    # Print styled banner
    print_banner(model)

    # Initialize feedback collector
    feedback_collector = FeedbackCollector()

    # Initialize prompt history manager
    prompt_manager = PromptHistoryManager()

    if verbose:
        history_count = prompt_manager.get_history_count()
        print_info(f"Prompt history loaded: {history_count} previous prompts available")
        print_info(f"Auto-complete enabled: Press ↑/↓ to navigate history, → to accept suggestion")
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

            # Print user prompt in verbose mode
            if verbose:
                print_user_prompt(prompt)

            # Timing for overall request
            request_start = time.time()

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
            llm_start = time.time()
            response, execution_time_ms = generate(model, enhanced_prompt)
            llm_duration = (time.time() - llm_start) * 1000

            if verbose:
                print_timing_verbose("LLM generation", llm_duration)

            # Print response with markdown formatting
            print_response(response)

            # Collect feedback if enabled
            feedback_data = feedback_collector.collect_feedback(prompt, response)

            if feedback_data:
                # Add execution time and metadata to feedback
                feedback_data['execution_time_ms'] = execution_time_ms

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
                send_feedback_to_sandbox(feedback_data, verbose=verbose)

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

def non_interactive_mode(model, prompt, verbose=False):
    """Run non-interactive mode with a single prompt."""
    # Set global verbose mode
    set_verbose_mode(verbose)

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

        capture_message("CLI started", level="info", context={
            'mode': 'interactive' if not args.prompt else 'non_interactive',
            'model': args.model,
            'verbose': verbose
        })

        if args.prompt:
            non_interactive_mode(args.model, args.prompt, verbose=verbose)
        else:
            interactive_mode(args.model, verbose=verbose)

    except Exception as e:
        handle_exception(e, context={'function': 'main'})
        sys.exit(1)

if __name__ == '__main__':
    main()
