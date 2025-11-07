import yaml

class ConfigLoader:
    def __init__(self, config_path='config.yaml'):
        self.config_path = config_path
        self.config = self._load()
    
    def _load(self):
        with open(self.config_path) as f:
            return yaml.safe_load(f)
        return None

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
