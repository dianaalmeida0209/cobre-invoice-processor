# src/utils/logger.py
"""
Structured logging configuration for invoice processing
"""
import logging
import sys
from typing import Optional

def setup_logger(
    name: str = "cobre_processor",
    level: str = "INFO",
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up structured logger with appropriate formatting
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set log level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)
    
    # Create formatter
    if format_string is None:
        format_string = (
            "%(asctime)s | %(name)s | %(levelname)s | "
            "%(filename)s:%(lineno)d | %(message)s"
        )
    
    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance for a specific module
    """
    return setup_logger(f"cobre_processor.{name}")

# Create root logger
root_logger = setup_logger()