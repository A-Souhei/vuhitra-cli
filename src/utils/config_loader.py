import yaml
from src.errors_handler import handle_exception

class ConfigLoader:
    def __init__(self, config_path='config.yaml'):
        self.config_path = config_path
        self.config = self._load()
    
    def _load(self):
        try:
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        except FileNotFoundError as e:
            handle_exception(e, context={
                'config_path': self.config_path,
                'error': 'Config file not found'
            })
            return {}
        except yaml.YAMLError as e:
            handle_exception(e, context={
                'config_path': self.config_path,
                'error': 'Invalid YAML format'
            })
            return {}
        except Exception as e:
            handle_exception(e, context={
                'config_path': self.config_path,
                'error': 'Failed to load config'
            })
            return {}

    def get(self, *keys, default=None):
        """Get nested config value using dot notation"""
        value = self.config
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value
    
    def get_ollama_host(self):
        return self.get('ollama', 'host')
    
    def get_ollama_protocol(self):
        return self.get('ollama', 'protocol', default='http')
    
    def get_ollama_port(self):
        return self.get('ollama', 'port', default=11434)
    
    def get_ollama_api_path(self):
        return self.get('ollama', 'api_path', default='/api/generate')
    
    def get_default_model(self):
        return self.get('model', 'default', default='llama3.1:8b')
    
    def get_available_models(self):
        return self.get('model', 'available', default=[])
    
    def get_cli_timeout(self):
        return self.get('cli', 'default_timeout', default=30)
    
    def get_environment_mode(self):
        return self.get('environment', 'mode', default='DEV')
    
    def get_logging_enabled(self):
        return self.get('environment', 'enable_logging', default=True)
    
    def get_sentry_dsn(self):
        return self.get('sentry', 'dsn', default='')
    
    def get_sentry_config(self):
        return self.get('sentry', default={})
