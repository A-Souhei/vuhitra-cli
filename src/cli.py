import sys
import requests
from src.agent import generate
from src.utils.arg_parser import ArgumentParser
from src.errors_handler import handle_exception, capture_message, get_error_handler
from src.utils.config_loader import ConfigLoader
from src.utils.feedback_collector import FeedbackCollector

def initialize_error_handler():
    """Initialize the error handler with configuration."""
    try:
        config = ConfigLoader()
        error_handler = get_error_handler()
        error_handler.configure(config_loader=config)
    except Exception as e:
        print(f"WARNING: Failed to initialize error handler: {str(e)}", file=sys.stderr)

def fetch_similar_heuristic(prompt):
    """Fetch similar heuristic from sandbox to enhance LLM context."""
    try:
        config = ConfigLoader()
        sandbox_url = config.get_sandbox_url()
        endpoint = f"{sandbox_url}/retrieve/similar"
        confidence_threshold = config.get_sandbox_confidence_threshold()

        response = requests.post(
            endpoint,
            json={"prompt": prompt, "min_rating": 3},
            timeout=5
        )
        response.raise_for_status()
        data = response.json()

        # Return the formatted insight if available and confidence is good
        if (data.get('confidence_score', 0) > confidence_threshold and
            data.get('insights') and
            data['insights'].get('formatted_insight')):
            return data['insights']['formatted_insight']

        return None
    except Exception as e:
        # Use error handler to log the exception
        handle_exception(e, context={
            'function': 'fetch_similar_heuristic',
            'endpoint': endpoint if 'endpoint' in locals() else 'unknown',
            'prompt_length': len(prompt)
        })
        return None


def send_feedback_to_sandbox(feedback_data):
    """Send feedback to sandbox for heuristics analysis."""
    try:
        config = ConfigLoader()
        sandbox_url = config.get_sandbox_url()
        endpoint = f"{sandbox_url}/analyze/feedback"

        response = requests.post(endpoint, json=feedback_data, timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.HTTPError as e:
        # Log HTTP-specific errors with more context
        print(f"WARNING: HTTP error sending feedback to sandbox: {e.response.status_code} - {str(e)}", file=sys.stderr)
        return False
    except requests.exceptions.RequestException as e:
        # Log other request errors (timeout, connection, etc.)
        print(f"WARNING: Request error sending feedback to sandbox: {str(e)}", file=sys.stderr)
        return False
    except Exception as e:
        # Log error but don't fail the CLI
        print(f"WARNING: Failed to send feedback to sandbox: {str(e)}", file=sys.stderr)
        return False

def interactive_mode(model):
    print(f"vuhitra-cli interactive mode (model: {model})")
    print("Type 'exit' or 'quit' to leave, Ctrl+C to interrupt\n")

    # Initialize feedback collector
    feedback_collector = FeedbackCollector()

    while True:
        try:
            prompt = input(">>> ")
            if prompt.lower() in ['exit', 'quit']:
                break
            if prompt.strip():
                # Fetch similar heuristic to enhance context
                heuristic_context = fetch_similar_heuristic(prompt)

                # Enhance prompt with heuristic context if available
                enhanced_prompt = prompt
                if heuristic_context:
                    enhanced_prompt = f"{heuristic_context}\n\nUser query: {prompt}"

                response, execution_time_ms = generate(model, enhanced_prompt)
                print(response)
                print()

                # Collect feedback if enabled
                feedback_data = feedback_collector.collect_feedback(prompt, response)

                if feedback_data:
                    # Add execution time to feedback
                    feedback_data['execution_time_ms'] = execution_time_ms

                    # Send to sandbox for heuristics processing
                    send_feedback_to_sandbox(feedback_data)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
        except Exception as e:
            handle_exception(e, context={
                'mode': 'interactive',
                'model': model
            })
            print(f"ERROR: {str(e)}")

def non_interactive_mode(model, prompt):
    try:
        # Fetch similar heuristic to enhance context
        heuristic_context = fetch_similar_heuristic(prompt)

        # Enhance prompt with heuristic context if available
        enhanced_prompt = prompt
        if heuristic_context:
            enhanced_prompt = f"{heuristic_context}\n\nUser query: {prompt}"

        response, execution_time_ms = generate(model, enhanced_prompt)
        print(response)
    except Exception as e:
        handle_exception(e, context={
            'mode': 'non_interactive',
            'model': model,
            'prompt_length': len(prompt)
        })
        print(f"ERROR: {str(e)}")

def main():
    initialize_error_handler()
    
    try:
        parser = ArgumentParser()
        args = parser.parse_args()
        
        capture_message("CLI started", level="info", context={
            'mode': 'interactive' if not args.prompt else 'non_interactive',
            'model': args.model
        })
        
        if args.prompt:
            non_interactive_mode(args.model, args.prompt)
        else:
            interactive_mode(args.model)
    except Exception as e:
        handle_exception(e, context={'function': 'main'})
        sys.exit(1)

if __name__ == '__main__':
    main()
