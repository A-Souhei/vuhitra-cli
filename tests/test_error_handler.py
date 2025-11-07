import pytest
import sys
import os
from io import StringIO
from unittest.mock import patch, MagicMock

from src.errors_handler import ErrorHandler, get_error_handler, handle_exception, capture_message

# Check if sentry_sdk is available
try:
    import sentry_sdk
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False


@pytest.fixture(autouse=True)
def reset_error_handler():
    """Reset the ErrorHandler singleton before each test."""
    ErrorHandler._instance = None
    ErrorHandler._sentry_initialized = False
    yield
    ErrorHandler._instance = None
    ErrorHandler._sentry_initialized = False


class TestErrorHandler:
    """Test cases for the ErrorHandler class."""
    
    def test_singleton_pattern(self):
        """Test that ErrorHandler follows singleton pattern."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()
        assert handler1 is handler2
    
    def test_default_configuration(self):
        """Test default configuration values."""
        handler = ErrorHandler()
        assert handler.mode == 'DEV'
        assert handler.enable_logging is True
        assert handler.sentry_enabled is False
    
    def test_dev_mode_logging(self):
        """Test that logging is enabled in DEV mode."""
        handler = ErrorHandler()
        handler.configure(mode='DEV')
        assert handler.mode == 'DEV'
        assert handler.enable_logging is True
    
    def test_prod_mode_no_logging(self):
        """Test that logging is disabled in PROD mode."""
        handler = ErrorHandler()
        handler.configure(mode='PROD')
        assert handler.mode == 'PROD'
        assert handler.enable_logging is False
    
    def test_handle_exception_basic(self, capsys):
        """Test basic exception handling."""
        handler = ErrorHandler()
        handler.configure(mode='DEV')
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            handler.handle_exception(e, context={'test': 'value'})
        
        captured = capsys.readouterr()
        assert 'ValueError' in captured.err
        assert 'Test error' in captured.err
        assert 'test' in captured.err
    
    def test_handle_exception_without_context(self, capsys):
        """Test exception handling without context."""
        handler = ErrorHandler()
        handler.configure(mode='DEV')
        
        try:
            raise RuntimeError("Runtime test error")
        except RuntimeError as e:
            handler.handle_exception(e)
        
        captured = capsys.readouterr()
        assert 'RuntimeError' in captured.err
        assert 'Runtime test error' in captured.err
    
    def test_capture_message_dev_mode(self, capsys):
        """Test message capture in DEV mode."""
        handler = ErrorHandler()
        handler.configure(mode='DEV')
        
        handler.capture_message("Test message", level="info")
        
        captured = capsys.readouterr()
        assert 'INFO' in captured.err
        assert 'Test message' in captured.err
    
    def test_capture_message_with_context(self, capsys):
        """Test message capture with context."""
        handler = ErrorHandler()
        handler.configure(mode='DEV')
        
        handler.capture_message(
            "Test message with context",
            level="warning",
            context={'key': 'value', 'number': 42}
        )
        
        captured = capsys.readouterr()
        assert 'WARNING' in captured.err
        assert 'Test message with context' in captured.err
        assert 'key' in captured.err
        assert 'value' in captured.err
    
    def test_prod_mode_minimal_output(self, capsys):
        """Test that PROD mode produces minimal output."""
        handler = ErrorHandler()
        handler.configure(mode='PROD')
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            handler.handle_exception(e)
        
        captured = capsys.readouterr()
        # Should only have basic error output, not detailed logs
        assert 'ERROR:' in captured.err
        assert 'ValueError' in captured.err
    
    def test_breadcrumb_dev_mode(self, capsys):
        """Test breadcrumb addition in DEV mode."""
        handler = ErrorHandler()
        handler.configure(mode='DEV')
        
        handler.add_breadcrumb(
            message="User action",
            category="ui",
            level="info",
            data={'button': 'submit'}
        )
        
        captured = capsys.readouterr()
        assert 'DEBUG' in captured.err
        assert 'User action' in captured.err
        assert 'ui' in captured.err
    
    @pytest.mark.skipif(not SENTRY_AVAILABLE, reason="sentry-sdk not installed")
    def test_sentry_initialization(self):
        """Test Sentry initialization with DSN."""
        with patch('sentry_sdk.init') as mock_init:
            handler = ErrorHandler()
            handler.configure(
                sentry_dsn="https://test@sentry.io/123",
                mode='DEV'
            )
            
            # Verify Sentry was initialized
            mock_init.assert_called_once()
            assert handler.sentry_enabled is True
    
    @pytest.mark.skipif(not SENTRY_AVAILABLE, reason="sentry-sdk not installed")
    def test_sentry_exception_capture(self):
        """Test exception capture with Sentry enabled."""
        with patch('sentry_sdk.init'), patch('sentry_sdk.capture_exception') as mock_capture, \
             patch('sentry_sdk.push_scope'):
            handler = ErrorHandler()
            handler.configure(
                sentry_dsn="https://test@sentry.io/123",
                mode='DEV'
            )
            
            try:
                raise ValueError("Test sentry error")
            except ValueError as e:
                handler.handle_exception(e, context={'test': 'sentry'})
            
            # Verify Sentry captured the exception
            mock_capture.assert_called_once()
    
    def test_convenience_functions(self, capsys):
        """Test convenience functions work correctly."""
        handler = get_error_handler()
        handler.configure(mode='DEV')
        
        # Test handle_exception convenience function
        try:
            raise ValueError("Convenience test")
        except ValueError as e:
            handle_exception(e, context={'source': 'test'})
        
        # Test capture_message convenience function
        capture_message("Convenience message", level="info")
        
        captured = capsys.readouterr()
        assert 'ValueError' in captured.err
        assert 'Convenience test' in captured.err
        assert 'Convenience message' in captured.err
    
    def test_format_error_details(self):
        """Test error detail formatting."""
        handler = ErrorHandler()
        
        try:
            raise RuntimeError("Format test error")
        except RuntimeError as e:
            details = handler._format_error_details(
                e,
                context={'key1': 'value1', 'key2': 'value2'}
            )
            
            assert 'Error Type: RuntimeError' in details
            assert 'Error Message: Format test error' in details
            assert 'key1' in details
            assert 'value1' in details
            assert 'key2' in details
            assert 'value2' in details
    
    def test_environment_variable_override(self, monkeypatch):
        """Test that environment variable overrides default mode."""
        monkeypatch.setenv('VUHITRA_MODE', 'PROD')
        handler = ErrorHandler()
        assert handler.mode == 'PROD'
        assert handler.enable_logging is False


class TestErrorHandlerIntegration:
    """Integration tests for error handler with config loader."""
    
    def test_config_loader_integration(self):
        """Test integration with ConfigLoader."""
        # Create a mock config loader
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda *keys, default=None: {
            ('environment', 'mode'): 'DEV',
            ('environment', 'enable_logging'): True,
            ('sentry',): {'dsn': '', 'environment': 'test'}
        }.get(keys, default)
        
        handler = ErrorHandler()
        handler.configure(config_loader=mock_config)
        
        assert handler.mode == 'DEV'
        assert handler.enable_logging is True
        assert handler.sentry_enabled is False
