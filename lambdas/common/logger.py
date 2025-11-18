"""
Structured logging utilities for Lambda functions.

Provides JSON-formatted logging with correlation IDs for request tracing.
"""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional
import uuid


class StructuredLogger:
    """
    JSON structured logger for Lambda functions.

    Automatically includes correlation_id, timestamp, function name, and log level.
    """

    def __init__(self, name: str, level: Optional[str] = None):
        """
        Initialize structured logger.

        Args:
            name: Logger name (typically Lambda function name)
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                  Defaults to LOG_LEVEL environment variable or INFO.
        """
        self.name = name
        self.correlation_id = str(uuid.uuid4())

        # Set log level from environment or parameter
        log_level = level or os.environ.get('LOG_LEVEL', 'INFO')
        self.level = getattr(logging, log_level.upper(), logging.INFO)

        # Configure Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers = []

        # Add console handler with JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self.level)
        self.logger.addHandler(handler)

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracing."""
        self.correlation_id = correlation_id

    def _format_message(self, level: str, message: str, **kwargs) -> str:
        """
        Format log message as JSON.

        Args:
            level: Log level string
            message: Log message
            **kwargs: Additional context fields

        Returns:
            JSON-formatted log string
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': level,
            'correlation_id': self.correlation_id,
            'function': self.name,
            'message': message,
        }

        # Add any additional context
        if kwargs:
            log_entry['context'] = kwargs

        return json.dumps(log_entry)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        if self.level <= logging.DEBUG:
            print(self._format_message('DEBUG', message, **kwargs))

    def info(self, message: str, **kwargs):
        """Log info message."""
        if self.level <= logging.INFO:
            print(self._format_message('INFO', message, **kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        if self.level <= logging.WARNING:
            print(self._format_message('WARNING', message, **kwargs))

    def error(self, message: str, **kwargs):
        """Log error message."""
        if self.level <= logging.ERROR:
            print(self._format_message('ERROR', message, **kwargs))

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        if self.level <= logging.CRITICAL:
            print(self._format_message('CRITICAL', message, **kwargs))

    def log_exception(self, exception: Exception, message: str = "Exception occurred", **kwargs):
        """
        Log exception with stack trace.

        Args:
            exception: Exception to log
            message: Context message
            **kwargs: Additional context
        """
        import traceback

        context = {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
            **kwargs
        }

        self.error(message, **context)


def get_logger(name: str, level: Optional[str] = None) -> StructuredLogger:
    """
    Factory function to create a structured logger.

    Args:
        name: Logger name
        level: Optional log level override

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name, level)
