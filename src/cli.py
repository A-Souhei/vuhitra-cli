import sys
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
                response = generate(model, prompt)
                print(response)
                print()

                # Collect feedback if enabled
                feedback_data = feedback_collector.collect_feedback(prompt, response)

                # TODO: Send feedback_data to ElasticSearch service when implemented
                # For now, feedback is collected and can be logged/stored as needed
                if feedback_data:
                    # Placeholder for future ElasticSearch integration
                    # This is where we'll send: prompt, response, rating, timestamp
                    # along with prompt_keywords and prompt_sentiment
                    pass

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
        response = generate(model, prompt)
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
