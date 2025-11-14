import yaml
import os
from src.errors_handler import handle_exception

class ConfigLoader:
    def __init__(self, config_path='config.yaml', secrets_path='secrets.yaml'):
        self.config_path = config_path
        self.secrets_path = secrets_path
        self.config = self._load()
        self.secrets = self._load_secrets()
    
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
    
    def _load_secrets(self):
        """Load secrets from secrets.yaml file"""
        try:
            if os.path.exists(self.secrets_path):
                with open(self.secrets_path) as f:
                    return yaml.safe_load(f) or {}
            else:
                # Secrets file is optional, return empty dict if not found
                return {}
        except yaml.YAMLError as e:
            handle_exception(e, context={
                'secrets_path': self.secrets_path,
                'error': 'Invalid YAML format in secrets file'
            })
            return {}
        except Exception as e:
            handle_exception(e, context={
                'secrets_path': self.secrets_path,
                'error': 'Failed to load secrets'
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
    
    def get_secret(self, *keys, default=None):
        """Get nested secret value using dot notation"""
        value = self.secrets
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default
            if value is None:
                return default
        return value
    
    def _get_ollama_mode(self):
        """Get the active Ollama mode (local or remote)"""
        return self.get('ollama', 'use', default='local')

    def get_ollama_host(self):
        config_key = self._get_ollama_mode()
        return self.get('ollama', config_key, 'host')

    def get_ollama_protocol(self):
        config_key = self._get_ollama_mode()
        return self.get('ollama', config_key, 'protocol', default='http')

    def get_ollama_port(self):
        config_key = self._get_ollama_mode()
        return self.get('ollama', config_key, 'port', default=11434)

    def get_ollama_api_path(self):
        config_key = self._get_ollama_mode()
        return self.get('ollama', config_key, 'api_path', default='/api/generate')
    
    def get_default_model(self):
        """Get default model based on the active Ollama configuration (local/remote)"""
        config_key = self._get_ollama_config_key()
        # Try to get model.default.local or model.default.remote
        default_model = self.get('model', 'default', config_key)
        
        # Fallback: if model.default is a string (old config format)
        if default_model is None:
            default_model = self.get('model', 'default')
            # If still None or it's a dict without the key, use tinyllama as ultimate fallback
            if default_model is None or isinstance(default_model, dict):
                default_model = 'tinyllama'
        
        return default_model
    
    def get_available_models(self):
        return self.get('model', 'available', default=[])
    
    def get_cli_timeout(self):
        return self.get('cli', 'default_timeout', default=30)

    def get_feedback_enabled(self):
        return self.get('cli', 'enable_feedback', default=False)

    def get_environment_mode(self):
        return self.get('environment', 'mode', default='DEV')
    
    def get_logging_enabled(self):
        return self.get('environment', 'enable_logging', default=True)
    
    def get_sentry_dsn(self):
        return self.get('sentry', 'dsn', default='')
    
    def get_sentry_config(self):
        return self.get('sentry', default={})
    
    def get_redis_password(self):
        """Get Redis password from secrets file"""
        password = self.get_secret('redis', 'password')
        if not password:
            raise ValueError(
                "Redis password is required! Set it in secrets.yaml. "
                "See docs/SECRETS.md for setup instructions."
            )
        return password

    def get_sandbox_host(self):
        return self.get('sandbox', 'host', default='localhost')
    
    def get_sandbox_port(self):
        return self.get('sandbox', 'port', default=8000)
    
    def get_sandbox_protocol(self):
        return self.get('sandbox', 'protocol', default='http')
    
    def get_sandbox_url(self):
        protocol = self.get_sandbox_protocol()
        host = self.get_sandbox_host()
        port = self.get_sandbox_port()
        return f"{protocol}://{host}:{port}"

    def get_sandbox_confidence_threshold(self):
        return self.get('sandbox', 'confidence_threshold', default=0.75)
