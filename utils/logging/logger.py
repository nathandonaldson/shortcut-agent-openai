"""
Core logging implementation for Shortcut Enhancement System.
Provides structured logging with context and trace correlation.
"""

import os
import sys
import json
import time
import logging
import uuid
import threading
import functools
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Union, TypeVar, cast
from contextlib import contextmanager

from openai import OpenAI
from agents import RunContextWrapper
try:
    from agents.tracing import add_trace_processor
    # Import TraceProcessor directly
    try:
        from agents.tracing.processor_interface import ProcessorInterface as TraceProcessor
    except ImportError:
        # Fallback to base class if available
        from agents.tracing.base import TraceProcessor
    
    # Create a simple processor class with required methods
    class SimpleTraceProcessor(TraceProcessor):
        async def process_trace(self, trace_obj):
            # Simple implementation that logs trace information
            print(f"Processing trace: {getattr(trace_obj, 'workflow_name', 'unknown')}")
        
        async def process_span(self, span):
            # Simple implementation that logs span information
            print(f"Processing span: {getattr(span, 'span_id', 'unknown')}")
    
    TRACING_AVAILABLE = True
except ImportError:
    # Tracing not available
    print("Warning: OpenAI Agents SDK tracing not available")
    TRACING_AVAILABLE = False

# Check if OpenAI SDK is available
try:
    from agents import __version__ as agents_version
    OPENAI_SDK_AVAILABLE = True and TRACING_AVAILABLE
except ImportError:
    OPENAI_SDK_AVAILABLE = False

# Store trace context in thread-local storage
_thread_local = threading.local()

# Log levels
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# Default log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Type variable for function return types
T = TypeVar('T')

class JsonFormatter(logging.Formatter):
    """Format log records as JSON strings."""
    
    def __init__(self, include_timestamp: bool = True):
        super().__init__()
        self.include_timestamp = include_timestamp
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        # Start with basic log data
        log_data = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add timestamp if requested
        if self.include_timestamp:
            log_data["timestamp"] = datetime.fromtimestamp(record.created).isoformat()
        
        # Add traceback info for exceptions
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any extra attributes set on the record
        for key, value in record.__dict__.items():
            if key not in {"args", "asctime", "created", "exc_info", "exc_text", 
                          "filename", "funcName", "id", "levelname", "levelno",
                          "lineno", "module", "msecs", "message", "msg", 
                          "name", "pathname", "process", "processName", 
                          "relativeCreated", "stack_info", "thread", "threadName"}:
                log_data[key] = value
        
        # Serialize to JSON
        return json.dumps(log_data)

class LoggerContext:
    """
    Context manager for adding context to logs.
    Temporarily adds context fields to all logs produced by the logger.
    """
    
    def __init__(self, logger: 'StructuredLogger', **context):
        self.logger = logger
        self.context = context
        self.previous_context = {}
    
    def __enter__(self):
        # Save current context and update with new values
        self.previous_context = self.logger.context.copy()
        self.logger.context.update(self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context
        self.logger.context = self.previous_context

class StructuredLogger:
    """
    Enhanced logger that produces structured, contextual logs.
    Supports adding context fields, trace correlation, and operation tracking.
    """
    
    def __init__(self, name: str, context: Optional[Dict[str, Any]] = None):
        self.name = name
        self.logger = logging.getLogger(name)
        self.context = context or {}
    
    def _add_context_to_record(self, record: logging.LogRecord) -> None:
        """Add context fields to a log record."""
        # Add current trace context
        trace_context = get_current_trace_context()
        if trace_context:
            for key, value in trace_context.items():
                setattr(record, key, value)
        
        # Add logger context
        for key, value in self.context.items():
            setattr(record, key, value)
    
    def with_context(self, **context) -> LoggerContext:
        """Create a context manager that adds context to all logs."""
        return LoggerContext(self, **context)
    
    def debug(self, msg: str, **kwargs) -> None:
        """Log a debug message with context."""
        extra = kwargs.copy()
        for key, value in extra.items():
            # Store complex values as JSON strings
            if not isinstance(value, (str, int, float, bool, type(None))):
                extra[key] = json.dumps(value)
                
        record = self.logger.makeRecord(
            self.name, logging.DEBUG, "", 0, msg, (), None, 
            extra=extra
        )
        self._add_context_to_record(record)
        self.logger.handle(record)
    
    def info(self, msg: str, **kwargs) -> None:
        """Log an info message with context."""
        extra = kwargs.copy()
        for key, value in extra.items():
            # Store complex values as JSON strings
            if not isinstance(value, (str, int, float, bool, type(None))):
                extra[key] = json.dumps(value)
                
        record = self.logger.makeRecord(
            self.name, logging.INFO, "", 0, msg, (), None, 
            extra=extra
        )
        self._add_context_to_record(record)
        self.logger.handle(record)
    
    def warning(self, msg: str, **kwargs) -> None:
        """Log a warning message with context."""
        extra = kwargs.copy()
        for key, value in extra.items():
            # Store complex values as JSON strings
            if not isinstance(value, (str, int, float, bool, type(None))):
                extra[key] = json.dumps(value)
                
        record = self.logger.makeRecord(
            self.name, logging.WARNING, "", 0, msg, (), None, 
            extra=extra
        )
        self._add_context_to_record(record)
        self.logger.handle(record)
    
    def error(self, msg: str, **kwargs) -> None:
        """Log an error message with context."""
        extra = kwargs.copy()
        for key, value in extra.items():
            # Store complex values as JSON strings
            if not isinstance(value, (str, int, float, bool, type(None))):
                extra[key] = json.dumps(value)
                
        record = self.logger.makeRecord(
            self.name, logging.ERROR, "", 0, msg, (), None, 
            extra=extra
        )
        self._add_context_to_record(record)
        self.logger.handle(record)
    
    def exception(self, msg: str, exc_info=True, **kwargs) -> None:
        """Log an exception message with traceback and context."""
        extra = kwargs.copy()
        for key, value in extra.items():
            # Store complex values as JSON strings
            if not isinstance(value, (str, int, float, bool, type(None))):
                extra[key] = json.dumps(value)
                
        record = self.logger.makeRecord(
            self.name, logging.ERROR, "", 0, msg, (), exc_info, 
            extra=extra
        )
        self._add_context_to_record(record)
        self.logger.handle(record)
    
    def critical(self, msg: str, **kwargs) -> None:
        """Log a critical message with context."""
        extra = kwargs.copy()
        for key, value in extra.items():
            # Store complex values as JSON strings
            if not isinstance(value, (str, int, float, bool, type(None))):
                extra[key] = json.dumps(value)
                
        record = self.logger.makeRecord(
            self.name, logging.CRITICAL, "", 0, msg, (), None, 
            extra=extra
        )
        self._add_context_to_record(record)
        self.logger.handle(record)
    
    @contextmanager
    def operation(self, operation_name: str, **kwargs):
        """
        Context manager to log an operation's start and end with timing.
        
        Args:
            operation_name: Name of the operation being performed
            **kwargs: Additional context fields to include in logs
            
        Yields:
            operation_id: A unique ID for the operation
        """
        operation_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Log operation start
        self.info(f"Starting operation: {operation_name}", 
                operation_id=operation_id, 
                event="operation_start", 
                **kwargs)
        
        try:
            # Execute the operation
            yield operation_id
            
            # Log successful completion
            duration = time.time() - start_time
            self.info(f"Completed operation: {operation_name}", 
                    operation_id=operation_id, 
                    event="operation_end",
                    duration_ms=int(duration * 1000),
                    status="success", 
                    **kwargs)
                     
        except Exception as e:
            # Log operation failure
            duration = time.time() - start_time
            self.error(f"Failed operation: {operation_name}", 
                    operation_id=operation_id, 
                    event="operation_end",
                    duration_ms=int(duration * 1000),
                    status="error",
                    error=str(e),
                    **kwargs)
            # Re-raise the exception
            raise

# Dictionary to store loggers by name
_loggers: Dict[str, StructuredLogger] = {}

def get_logger(name: str) -> StructuredLogger:
    """
    Get or create a structured logger by name.
    
    Args:
        name: Name of the logger
        
    Returns:
        StructuredLogger instance
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    
    return _loggers[name]

def set_trace_context(trace_id: Optional[str] = None, **context) -> None:
    """
    Set the current trace context for this thread.
    
    Args:
        trace_id: Trace ID (optional)
        **context: Additional context fields
    """
    current_context = getattr(_thread_local, 'trace_context', {}).copy()
    
    if trace_id is not None:
        current_context['trace_id'] = trace_id
    
    # Update with new context
    current_context.update(context)
    
    # Store updated context
    _thread_local.trace_context = current_context

def get_current_trace_context() -> Dict[str, Any]:
    """
    Get the current trace context for this thread.
    
    Returns:
        Dictionary with trace context or empty dict if none
    """
    return getattr(_thread_local, 'trace_context', {}).copy()

def clear_trace_context() -> None:
    """Clear the current trace context for this thread."""
    if hasattr(_thread_local, 'trace_context'):
        delattr(_thread_local, 'trace_context')

@contextmanager
def trace_context(trace_id: Optional[str] = None, **context):
    """
    Context manager for setting trace context within a block.
    
    Args:
        trace_id: Trace ID (optional)
        **context: Additional context fields
        
    Yields:
        None
    """
    # Save previous context
    previous_context = get_current_trace_context()
    
    # Set new context
    set_trace_context(trace_id, **context)
    
    try:
        yield
    finally:
        # Restore previous context
        if previous_context:
            _thread_local.trace_context = previous_context
        else:
            clear_trace_context()

def logged_operation(logger_name: str, operation_name: Optional[str] = None, **context):
    """
    Decorator to log function execution as an operation.
    
    Args:
        logger_name: Name of the logger to use
        operation_name: Name of the operation (defaults to function name)
        **context: Additional context fields
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Get the logger
            logger = get_logger(logger_name)
            
            # Use function name if operation name not provided
            op_name = operation_name or func.__name__
            
            # Execute within operation context
            with logger.operation(op_name, **context):
                return func(*args, **kwargs)
        
        return wrapper
    
    return decorator

def configure_file_logging(log_dir: str = LOG_DIR, 
                          log_filename: str = "application.log",
                          log_level: str = "INFO",
                          log_format: str = "json") -> None:
    """
    Configure file-based logging for the application.
    
    Args:
        log_dir: Directory to store log files
        log_filename: Name of the log file
        log_level: Minimum log level to capture (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format for logs ("json" or "text")
    """
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Create the file handler
    log_file_path = os.path.join(log_dir, log_filename)
    file_handler = logging.FileHandler(log_file_path)
    
    # Set log level
    level = LOG_LEVELS.get(log_level.upper(), logging.INFO)
    file_handler.setLevel(level)
    
    # Create formatter based on format type
    if log_format.lower() == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    file_handler.setFormatter(formatter)
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

def configure_console_logging(log_level: str = "INFO",
                             log_format: str = "text") -> None:
    """
    Configure console logging for the application.
    
    Args:
        log_level: Minimum log level to capture (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Format for logs ("json" or "text")
    """
    # Create the console handler
    console_handler = logging.StreamHandler(sys.stdout)
    
    # Set log level
    level = LOG_LEVELS.get(log_level.upper(), logging.INFO)
    console_handler.setLevel(level)
    
    # Create formatter based on format type
    if log_format.lower() == "json":
        formatter = JsonFormatter(include_timestamp=False)
    else:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console_handler.setFormatter(formatter)
    
    # Add to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)

def configure_global_logging(log_dir: str = LOG_DIR,
                            log_filename: str = "application.log",
                            console_level: str = "INFO",
                            file_level: str = "DEBUG",
                            console_format: str = "text",
                            file_format: str = "json") -> None:
    """
    Configure global logging settings for the application.
    
    Args:
        log_dir: Directory to store log files
        log_filename: Name of the log file
        console_level: Log level for console output
        file_level: Log level for file output
        console_format: Format for console logs ("json" or "text")
        file_format: Format for file logs ("json" or "text")
    """
    # Reset root logger
    root_logger = logging.getLogger()
    root_logger.handlers = []
    
    # Set root logger level to the most verbose requested
    console_level_value = LOG_LEVELS.get(console_level.upper(), logging.INFO)
    file_level_value = LOG_LEVELS.get(file_level.upper(), logging.DEBUG)
    root_logger.setLevel(min(console_level_value, file_level_value))
    
    # Configure console logging
    configure_console_logging(console_level, console_format)
    
    # Configure file logging
    configure_file_logging(log_dir, log_filename, file_level, file_format)
    
    # Configure OpenAI SDK logging if available
    if OPENAI_SDK_AVAILABLE:
        configure_openai_sdk_logging()

def configure_openai_sdk_logging() -> None:
    """Configure OpenAI Agent SDK logging integration."""
    # Skip if tracing not available
    if not TRACING_AVAILABLE:
        print("Skipping OpenAI SDK logging configuration - tracing not available")
        return
        
    # Configure SDK loggers
    agent_logger = logging.getLogger("openai.agents")
    tracing_logger = logging.getLogger("openai.agents.tracing")
    
    # Set appropriate levels
    agent_logger.setLevel(logging.INFO)
    tracing_logger.setLevel(logging.INFO)
    
    # Add our simple trace processor to the SDK
    add_trace_processor(SimpleTraceProcessor())

# Initialize with default settings
def init_logging() -> None:
    """Initialize logging with default settings."""
    # Configure logging only if handlers aren't already set up
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        configure_global_logging()

# Initialize logging when module is imported
init_logging()