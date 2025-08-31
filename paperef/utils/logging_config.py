"""
Logging configuration for PaperRef
"""

import sys
from pathlib import Path

from loguru import logger

from .config import Config


def setup_logging(config: Config, log_file: Path | None = None) -> None:
    """Set up logging configuration"""

    # Remove default handler
    logger.remove()

    # Console handler with rich formatting
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        level="INFO" if not config.verbose else "DEBUG",
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    # File handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            level="DEBUG",
            rotation="10 MB",
            retention="1 week",
            encoding="utf-8"
        )

    # Add context information
    logger.bind(config=config.__class__.__name__)


def get_logger(name: str):
    """Get a logger instance with the specified name"""
    return logger.bind(name=name)
