"""Logging configuration for structured logging across all agents."""

import logging
import sys
from typing import Any, Dict

from .settings import get_settings


class CorrelationIDFilter(logging.Filter):
    """Add correlation ID to log records for request tracing."""

    def __init__(self, correlation_id: str = "N/A"):
        super().__init__()
        self.correlation_id = correlation_id

    def filter(self, record: logging.LogRecord) -> bool:
        """Add correlation_id attribute to log record."""
        record.correlation_id = self.correlation_id
        return True


def setup_logging(correlation_id: str = "N/A") -> None:
    """Configure structured logging for the application.
    
    Args:
        correlation_id: Unique identifier for request tracing across agents.
    """
    settings = get_settings()
    
    # Create formatter
    log_format = (
        "[%(asctime)s] [%(correlation_id)s] [%(name)s] "
        "[%(levelname)s] %(message)s"
    )
    
    if settings.is_production:
        # In production, use JSON-like format for easier parsing
        log_format = (
            '{"timestamp": "%(asctime)s", "correlation_id": "%(correlation_id)s", '
            '"logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
        )
    
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(CorrelationIDFilter(correlation_id))
    root_logger.addHandler(console_handler)
    
    # Set levels for third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__ of the module).
        
    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)


def update_correlation_id(logger: logging.Logger, correlation_id: str) -> None:
    """Update correlation ID for all handlers of a logger.
    
    Args:
        logger: Logger instance to update.
        correlation_id: New correlation ID.
    """
    for handler in logger.handlers:
        for filter_obj in handler.filters:
            if isinstance(filter_obj, CorrelationIDFilter):
                filter_obj.correlation_id = correlation_id
