"""
Logging configuration for the application.

This module sets up the logging system and provides logging utilities
for consistent logging across the application.
"""
import logging
import sys
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

from fastapi import Depends
from loguru import logger


def setup_logging() -> None:
    """Configure Loguru logger."""
    # Remove default handlers
    logger.remove()
    
    # Configure a handler to stderr with a nice format
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True,
        level="DEBUG",
    )
    
    # Configure a file handler for permanent logs
    logger.add(
        "logs/app.log",
        rotation="500 MB",
        retention="10 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
    )
    
    # Intercept standard library logging
    intercept_stdlib_logging()
    
    logger.info("Logging configured")


def intercept_stdlib_logging() -> None:
    """
    Intercept standard library logging and redirect to loguru.
    
    This is useful for libraries that use the standard logging module.
    """
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            # Get corresponding Loguru level if possible
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
                
            # Find caller from record
            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
                
            # Log using logger
            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )
    
    # Setup handlers
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Update existing loggers
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


def with_log_context(**context_params: Any) -> Callable:
    """
    Decorator that adds context to all log messages in the decorated function.
    
    Args:
        **context_params: Context parameters to add to log messages
        
    Returns:
        Callable: Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with logger.contextualize(**context_params):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def get_logger_dependency() -> logger:
    """
    Get logger as a FastAPI dependency.
    
    Returns:
        Logger: Loguru logger instance
    """
    return logger