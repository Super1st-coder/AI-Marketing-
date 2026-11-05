"""Logging configuration"""
import logging
import sys
from typing import Optional
from loguru import logger


def setup_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """
    Setup logging configuration
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to output logs in JSON format
    """
    logger.remove()
    
    if json_logs:
        logger.add(
            sys.stdout,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
            level=level,
            serialize=True
        )
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=level,
            colorize=True
        )
    
    # Add file handler
    logger.add(
        "logs/fury_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="30 days",
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    )


def get_logger(name: Optional[str] = None):
    """Get logger instance"""
    if name:
        return logger.bind(name=name)
    return logger

