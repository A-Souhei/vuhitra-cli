import pytest
import sys
import os
import tempfile
import yaml
from unittest.mock import patch

from src.utils.config_loader import ConfigLoader


@pytest.fixture
def test_config():
    """Fixture providing test configuration."""
    return {
        'environment': {
            'mode': 'DEV',
            'enable_logging': True
        },
        'sentry': {
            'dsn': 'https://test@sentry.io/123',
            'environment': 'development',
            'traces_sample_rate': 1.0
        },
        'ollama': {
            'host': 'localhost',
            'port': 11434,
            'protocol': 'http'
        }
    }


@pytest.fixture
def temp_config_file(test_config):
    """Fixture providing a temporary config file."""
    temp_file = tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.yaml',
        delete=False
    )
    yaml.dump(test_config, temp_file)
    temp_file.close()
    
    yield temp_file.name
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


class TestConfigLoader:
    """Test cases for the ConfigLoader class."""
    
    def test_load_config(self, temp_config_file):
        """Test loading configuration file."""
        loader = ConfigLoader(config_path=temp_config_file)
        assert loader.config is not None
        assert isinstance(loader.config, dict)
    
    def test_get_nested_value(self, temp_config_file):
        """Test retrieving nested configuration values."""
        loader = ConfigLoader(config_path=temp_config_file)
        
        mode = loader.get('environment', 'mode')
        assert mode == 'DEV'
        
        dsn = loader.get('sentry', 'dsn')
        assert dsn == 'https://test@sentry.io/123'
    
    def test_get_with_default(self, temp_config_file):
        """Test retrieving values with defaults."""
        loader = ConfigLoader(config_path=temp_config_file)
        
        # Non-existent key should return default
        value = loader.get('nonexistent', 'key', default='default_value')
        assert value == 'default_value'
    
    def test_get_environment_mode(self, temp_config_file):
        """Test getting environment mode."""
        loader = ConfigLoader(config_path=temp_config_file)
        mode = loader.get_environment_mode()
        assert mode == 'DEV'
    
    def test_get_logging_enabled(self, temp_config_file):
        """Test getting logging enabled setting."""
        loader = ConfigLoader(config_path=temp_config_file)
        enabled = loader.get_logging_enabled()
        assert enabled is True
    
    def test_get_sentry_dsn(self, temp_config_file):
        """Test getting Sentry DSN."""
        loader = ConfigLoader(config_path=temp_config_file)
        dsn = loader.get_sentry_dsn()
        assert dsn == 'https://test@sentry.io/123'
    
    def test_get_sentry_config(self, temp_config_file):
        """Test getting full Sentry configuration."""
        loader = ConfigLoader(config_path=temp_config_file)
        sentry_config = loader.get_sentry_config()
        
        assert isinstance(sentry_config, dict)
        assert sentry_config['dsn'] == 'https://test@sentry.io/123'
        assert sentry_config['environment'] == 'development'
        assert sentry_config['traces_sample_rate'] == 1.0
    
    def test_get_ollama_settings(self, temp_config_file):
        """Test getting Ollama settings."""
        loader = ConfigLoader(config_path=temp_config_file)
        
        host = loader.get_ollama_host()
        assert host == 'localhost'
        
        port = loader.get_ollama_port()
        assert port == 11434
        
        protocol = loader.get_ollama_protocol()
        assert protocol == 'http'
    
    def test_missing_config_file(self, capsys):
        """Test handling of missing configuration file."""
        loader = ConfigLoader(config_path='nonexistent.yaml')
        # Should return empty dict on error
        assert loader.config == {}
    
    def test_invalid_yaml(self):
        """Test handling of invalid YAML file."""
        # Create file with invalid YAML
        invalid_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        )
        invalid_file.write('invalid: yaml: content: [')
        invalid_file.close()
        
        try:
            loader = ConfigLoader(config_path=invalid_file.name)
            # Should return empty dict on YAML error
            assert loader.config == {}
        finally:
            os.unlink(invalid_file.name)
    
    def test_defaults_for_missing_keys(self):
        """Test that default values are returned for missing keys."""
        # Create minimal config
        minimal_config = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        )
        yaml.dump({}, minimal_config)
        minimal_config.close()
        
        try:
            loader = ConfigLoader(config_path=minimal_config.name)
            
            # Test defaults
            assert loader.get_environment_mode() == 'DEV'
            assert loader.get_logging_enabled() is True
            assert loader.get_sentry_dsn() == ''
            assert loader.get_ollama_protocol() == 'http'
            assert loader.get_ollama_port() == 11434
        finally:
            os.unlink(minimal_config.name)
