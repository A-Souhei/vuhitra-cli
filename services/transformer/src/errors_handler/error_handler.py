import sys
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
import os


class ErrorHandler:
    """
    Centralized error handler with Sentry.io integration and environment-aware logging.
    
    Features:
    - DEV/PROD mode support
    - Sentry.io integration for error tracking
    - Detailed error logging with context
    - Stack trace capture
    - Custom error metadata support
    """
    
    _instance = None
    _sentry_initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ErrorHandler, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            self.mode = os.environ.get('VUHITRA_MODE', 'DEV').upper()
            self.enable_logging = self.mode == 'DEV'
            self.sentry_dsn = None
            self.sentry_enabled = False
            # Initialize default Sentry config
            self.sentry_environment = 'development'
            self.traces_sample_rate = 1.0
            self.send_default_pii = False
            self.attach_stacktrace = True
            
    def configure(self, config_loader=None, sentry_dsn: str = None, 
                  mode: str = None, enable_logging: bool = None):
        """
        Configure the error handler with settings from config or parameters.
        
        Args:
            config_loader: ConfigLoader instance for loading settings
            sentry_dsn: Sentry DSN string (optional)
            mode: Environment mode ('DEV' or 'PROD')
            enable_logging: Whether to enable logging
        """
        if config_loader:
            self.mode = config_loader.get('environment', 'mode', default='DEV').upper()
            self.enable_logging = config_loader.get('environment', 'enable_logging', default=True)
            
            sentry_config = config_loader.get('sentry', default={})
            self.sentry_dsn = sentry_config.get('dsn', '')
            self.sentry_environment = sentry_config.get('environment', 'development')
            self.traces_sample_rate = sentry_config.get('traces_sample_rate', 1.0)
            self.send_default_pii = sentry_config.get('send_default_pii', False)
            self.attach_stacktrace = sentry_config.get('attach_stacktrace', True)
        
        if sentry_dsn is not None:
            self.sentry_dsn = sentry_dsn
        if mode is not None:
            self.mode = mode.upper()
        if enable_logging is not None:
            self.enable_logging = enable_logging
            
        # Logging only happens on DEV mode
        if self.mode != 'DEV':
            self.enable_logging = False
        
        # Initialize Sentry if DSN is provided
        if self.sentry_dsn and not ErrorHandler._sentry_initialized:
            self._initialize_sentry()
    
    def _initialize_sentry(self):
        """Initialize Sentry SDK with configuration."""
        try:
            import sentry_sdk
            
            sentry_sdk.init(
                dsn=self.sentry_dsn,
                environment=self.sentry_environment,
                traces_sample_rate=self.traces_sample_rate,
                send_default_pii=self.send_default_pii,
                attach_stacktrace=self.attach_stacktrace,
            )
            
            ErrorHandler._sentry_initialized = True
            self.sentry_enabled = True
            
            if self.enable_logging:
                self._log_message("INFO", "Sentry initialized successfully")
                
        except ImportError:
            if self.enable_logging:
                self._log_message("WARNING", 
                    "sentry-sdk not installed. Install with: pip install sentry-sdk")
            self.sentry_enabled = False
        except Exception as e:
            if self.enable_logging:
                self._log_message("ERROR", f"Failed to initialize Sentry: {str(e)}")
            self.sentry_enabled = False
    
    def _log_message(self, level: str, message: str):
        """Internal logging method."""
        if not self.enable_logging:
            return
            
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{level}] {message}", file=sys.stderr)
    
    def _format_error_details(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Format detailed error information for logging.
        
        Args:
            error: The exception object
            context: Additional context information
            
        Returns:
            Formatted error string
        """
        details = [
            f"Error Type: {type(error).__name__}",
            f"Error Message: {str(error)}",
            f"Mode: {self.mode}",
        ]
        
        if context:
            details.append("Context:")
            for key, value in context.items():
                details.append(f"  - {key}: {value}")
        
        # Add stack trace
        tb = traceback.format_exc()
        if tb and tb != "NoneType: None\n":
            details.append("\nStack Trace:")
            details.append(tb)
        
        return "\n".join(details)
    
    def handle_exception(self, error: Exception, context: Optional[Dict[str, Any]] = None,
                        reraise: bool = False):
        """
        Handle an exception with logging and optional Sentry reporting.
        
        Args:
            error: The exception to handle
            context: Additional context information (dict)
            reraise: Whether to reraise the exception after handling
        """
        error_details = self._format_error_details(error, context)
        
        # Log to console if logging is enabled (DEV mode only)
        if self.enable_logging:
            self._log_message("ERROR", error_details)
        
        # Send to Sentry if enabled
        if self.sentry_enabled:
            try:
                import sentry_sdk
                
                with sentry_sdk.push_scope() as scope:
                    # Add context to Sentry
                    if context:
                        for key, value in context.items():
                            scope.set_context(key, {"value": str(value)})
                    
                    scope.set_tag("mode", self.mode)
                    scope.set_level("error")
                    
                    sentry_sdk.capture_exception(error)
                    
                    if self.enable_logging:
                        self._log_message("INFO", "Error sent to Sentry")
                        
            except Exception as sentry_error:
                if self.enable_logging:
                    self._log_message("WARNING", 
                        f"Failed to send error to Sentry: {str(sentry_error)}")
        
        # If Sentry is not enabled, just print the error
        if not self.sentry_enabled and not self.enable_logging:
            print(f"ERROR: {type(error).__name__}: {str(error)}", file=sys.stderr)
        
        if reraise:
            raise error
    
    def capture_message(self, message: str, level: str = "info", 
                       context: Optional[Dict[str, Any]] = None):
        """
        Capture a message (non-exception) with optional Sentry reporting.
        
        Args:
            message: The message to capture
            level: Message level (debug, info, warning, error, fatal)
            context: Additional context information
        """
        if self.enable_logging:
            self._log_message(level.upper(), message)
            if context:
                for key, value in context.items():
                    self._log_message(level.upper(), f"  {key}: {value}")
        
        # Send to Sentry if enabled
        if self.sentry_enabled:
            try:
                import sentry_sdk
                
                with sentry_sdk.push_scope() as scope:
                    if context:
                        for key, value in context.items():
                            scope.set_context(key, {"value": str(value)})
                    
                    scope.set_tag("mode", self.mode)
                    scope.set_level(level)
                    
                    sentry_sdk.capture_message(message, level=level)
                    
            except Exception as e:
                if self.enable_logging:
                    self._log_message("WARNING", 
                        f"Failed to send message to Sentry: {str(e)}")
    
    def set_user_context(self, user_id: str = None, username: str = None, 
                        email: str = None, **kwargs):
        """
        Set user context for error tracking.
        
        Args:
            user_id: User ID
            username: Username
            email: User email
            **kwargs: Additional user attributes
        """
        if self.sentry_enabled:
            try:
                import sentry_sdk
                
                user_data = {}
                if user_id:
                    user_data['id'] = user_id
                if username:
                    user_data['username'] = username
                if email:
                    user_data['email'] = email
                user_data.update(kwargs)
                
                sentry_sdk.set_user(user_data)
                
                if self.enable_logging:
                    self._log_message("INFO", f"User context set: {user_data}")
                    
            except Exception as e:
                if self.enable_logging:
                    self._log_message("WARNING", 
                        f"Failed to set user context: {str(e)}")
    
    def add_breadcrumb(self, message: str, category: str = "default", 
                       level: str = "info", data: Optional[Dict[str, Any]] = None):
        """
        Add a breadcrumb for debugging context.
        
        Args:
            message: Breadcrumb message
            category: Category of the breadcrumb
            level: Level (debug, info, warning, error, fatal)
            data: Additional data dictionary
        """
        if self.enable_logging:
            breadcrumb_msg = f"[{category}] {message}"
            if data:
                breadcrumb_msg += f" | Data: {data}"
            self._log_message("DEBUG", breadcrumb_msg)
        
        if self.sentry_enabled:
            try:
                import sentry_sdk
                
                sentry_sdk.add_breadcrumb(
                    message=message,
                    category=category,
                    level=level,
                    data=data
                )
            except Exception as e:
                if self.enable_logging:
                    self._log_message("WARNING", 
                        f"Failed to add breadcrumb: {str(e)}")


# Global instance
_error_handler = ErrorHandler()


def get_error_handler() -> ErrorHandler:
    """Get the global ErrorHandler instance."""
    return _error_handler


def handle_exception(error: Exception, context: Optional[Dict[str, Any]] = None, 
                    reraise: bool = False):
    """
    Convenience function to handle exceptions.
    
    Args:
        error: The exception to handle
        context: Additional context information
        reraise: Whether to reraise the exception
    """
    _error_handler.handle_exception(error, context, reraise)


def capture_message(message: str, level: str = "info", 
                   context: Optional[Dict[str, Any]] = None):
    """
    Convenience function to capture messages.
    
    Args:
        message: The message to capture
        level: Message level
        context: Additional context information
    """
    _error_handler.capture_message(message, level, context)
