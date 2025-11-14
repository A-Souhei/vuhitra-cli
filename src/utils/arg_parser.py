import argparse
from src.utils.config_loader import ConfigLoader

class ArgumentParser:
    def __init__(self):
        self.config = ConfigLoader()
        self.default_model = self.config.get_default_model()
        self.parser = self._create_parser()
    
    def _create_parser(self):
        p = argparse.ArgumentParser(description='vuhitra-cli: LLM CLI application')
        p.add_argument('-m', '--model', default=self.default_model, help='Model to use')
        p.add_argument('-p', '--prompt', help='Prompt to send (omit for interactive mode)')
        p.add_argument('-v', '--verbose', action='store_true', help='Enable verbose mode with detailed debugging output')
        return p
    
    def parse_args(self):
        return self.parser.parse_args()
