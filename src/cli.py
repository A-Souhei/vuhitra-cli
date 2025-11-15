import sys
import logging
import requests
import time
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
    print_success, print_info, print_debug, print_user_prompt, console
)
from src.utils.prompt_history import PromptHistoryManager

# Maximum prompt length to prevent DoS through excessive payload sizes
MAX_PROMPT_LENGTH = 10000

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

def fetch_similar_heuristic(prompt, verbose=False, negative_weight_boost=0.0):
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
                # Fetch similar heuristic to enhance context (with boost if iterating)
                heuristic_context, heuristic_data = fetch_similar_heuristic(
                    prompt,
                    verbose=verbose,
                    negative_weight_boost=negative_weight_boost
                )
                
                # Enhance prompt with heuristic context if available
                enhanced_prompt = prompt
                if heuristic_context:
                    enhanced_prompt = f"{heuristic_context}\n\nUser query: {prompt}"

                    if verbose:
                        print_debug("Enhanced Prompt", {
                            "original_length": len(prompt),
                            "enhanced_length": len(enhanced_prompt),
                            "context_added": len(heuristic_context),
                            "iteration": iteration_number,
                            "negative_weight_boost": negative_weight_boost
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
                    if rating == 0:
                        if iteration_number + 1 < max_iterations:
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
        
        # Wait for services to be ready before proceeding
        if not wait_for_services():
            print_error("Cannot proceed without services. Exiting.")
            sys.exit(1)

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
