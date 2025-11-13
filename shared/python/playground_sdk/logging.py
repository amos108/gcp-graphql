"""Structured logging setup for Cloud Logging"""

import logging
import json
import sys
from typing import Optional, Dict, Any
from datetime import datetime
from .context import get_run_id


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs as JSON with run_id and other structured fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'severity': record.levelname,
            'message': record.getMessage(),
            'logger': record.name,
            'run_id': get_run_id(),
        }

        # Add extra fields if present
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add source location
        log_data['source'] = {
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName
        }

        return json.dumps(log_data)


def setup_logging(
    service_name: str,
    level: str = 'INFO',
    structured: bool = True
) -> logging.Logger:
    """
    Setup structured logging for a service.

    Args:
        service_name: Name of the service
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Whether to use structured (JSON) logging

    Returns:
        Configured logger instance

    Example:
        ```python
        from playground_sdk import setup_logging

        logger = setup_logging('payment-service')
        logger.info('Payment processed', extra={'amount': 99.99, 'user_id': 123})
        ```
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)

    if structured:
        # Use JSON formatter
        handler.setFormatter(StructuredFormatter())
    else:
        # Use simple formatter for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name, defaults to calling module

    Returns:
        Logger instance

    Example:
        ```python
        from playground_sdk import get_logger

        logger = get_logger(__name__)
        logger.info('Something happened')
        ```
    """
    return logging.getLogger(name or __name__)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically adds run_id to all log messages.

    Example:
        ```python
        from playground_sdk.logging import LoggerAdapter, get_logger

        logger = LoggerAdapter(get_logger(__name__))
        logger.info('Payment processed', amount=99.99)
        # Automatically includes run_id in output
        ```
    """

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add run_id to log extra data"""
        extra = kwargs.get('extra', {})
        extra['run_id'] = get_run_id()
        kwargs['extra'] = extra
        return msg, kwargs


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **kwargs
):
    """
    Log a message with automatic run_id and context.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **kwargs: Additional fields to include in log

    Example:
        ```python
        from playground_sdk.logging import log_with_context, get_logger

        logger = get_logger(__name__)
        log_with_context(logger, 'info', 'Payment processed',
                        amount=99.99, user_id=123)
        ```
    """
    extra = {'run_id': get_run_id()}
    extra.update(kwargs)

    log_method = getattr(logger, level.lower())
    log_method(message, extra=extra)
