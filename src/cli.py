import sys
from src.agent import generate
from src.utils.arg_parser import ArgumentParser

def interactive_mode(model):
    print(f"vuhitra-cli interactive mode (model: {model})")
    print("Type 'exit' or 'quit' to leave, Ctrl+C to interrupt\n")
    
    while True:
        try:
            prompt = input(">>> ")
            if prompt.lower() in ['exit', 'quit']:
                break
            if prompt.strip():
                response = generate(model, prompt)
                print(response)
                print()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

def non_interactive_mode(model, prompt):
    response = generate(model, prompt)
    print(response)

def main():
    parser = ArgumentParser()
    args = parser.parse_args()
    
    if args.prompt:
        non_interactive_mode(args.model, args.prompt)
    else:
        interactive_mode(args.model)

if __name__ == '__main__':
    main()
