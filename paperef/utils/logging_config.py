"""
Enhanced Logging configuration module with error handling
"""

import sys
import time
import traceback
from pathlib import Path
from typing import Any

from loguru import logger

from .config import Config


class ErrorHandler:
    """Enhanced error handling and logging"""

    def __init__(self):
        self.error_counts = {}
        self.warning_counts = {}

    def log_error(self, error: Exception, context: str = "", extra_data: dict[str, Any] | None = None) -> None:
        """
        Log error with context and optional extra data

        Args:
            error: Exception object
            context: Context where error occurred
            extra_data: Additional data to log
        """
        error_type = type(error).__name__

        # Count errors by type
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

        # Log error with full context
        error_msg = f"[{error_type}] {error!s}"
        if context:
            error_msg = f"{context}: {error_msg}"

        logger.error(error_msg)

        # Log stack trace in debug mode
        logger.debug(f"Stack trace:\n{traceback.format_exc()}")

        # Log extra data if provided
        if extra_data:
            logger.debug(f"Extra data: {extra_data}")

    def log_warning(self, message: str, context: str = "", extra_data: dict[str, Any] | None = None) -> None:
        """
        Log warning with context

        Args:
            message: Warning message
            context: Context where warning occurred
            extra_data: Additional data to log
        """
        warning_type = "Warning"

        # Count warnings
        self.warning_counts[warning_type] = self.warning_counts.get(warning_type, 0) + 1

        warning_msg = message
        if context:
            warning_msg = f"{context}: {warning_msg}"

        logger.warning(warning_msg)

        if extra_data:
            logger.debug(f"Warning data: {extra_data}")

    def log_operation_start(self, operation: str, **kwargs) -> None:
        """
        Log operation start

        Args:
            operation: Operation name
            **kwargs: Additional context
        """
        msg = f"Starting operation: {operation}"
        if kwargs:
            msg += f" ({kwargs})"
        logger.info(msg)

    def log_operation_end(self, operation: str, success: bool = True, duration: float | None = None, **kwargs) -> None:
        """
        Log operation end

        Args:
            operation: Operation name
            success: Whether operation was successful
            duration: Operation duration in seconds
            **kwargs: Additional context
        """
        status = "completed successfully" if success else "failed"
        msg = f"Operation {operation} {status}"

        if duration is not None:
            msg += f" in {duration:.2f}s"

        if kwargs:
            msg += f" ({kwargs})"

        if success:
            logger.info(msg)
        else:
            logger.error(msg)

    def get_error_summary(self) -> dict[str, Any]:
        """
        Get error summary statistics

        Returns:
            Error statistics
        """
        return {
            "error_counts": self.error_counts.copy(),
            "warning_counts": self.warning_counts.copy(),
            "total_errors": sum(self.error_counts.values()),
            "total_warnings": sum(self.warning_counts.values())
        }

    def reset_counts(self) -> None:
        """Reset error and warning counts"""
        self.error_counts.clear()
        self.warning_counts.clear()


# Global error handler instance
error_handler = ErrorHandler()


def setup_logging(
    config: Config,
    log_file: Path | None = None,
    json_format: bool = False,
    max_file_size: str = "10 MB",
    retention: str = "1 week"
) -> None:
    """
    Setup enhanced logging configuration

    Args:
        config: Configuration object
        log_file: Path to log file (optional)
        json_format: Use JSON format for logs
        max_file_size: Maximum log file size
        retention: Log retention period
    """
    # Remove default handler
    logger.remove()

    level = "DEBUG" if config.verbose else "INFO"

    # Console handler
    if json_format:
        console_format = "{time} | {level} | {name}:{function}:{line} | {message}"
    else:
        console_format = (
            "<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )

    logger.add(
        sys.stderr,
        format=console_format,
        level=level,
        colorize=not json_format,
        backtrace=True,
        diagnose=True
    )

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

        if json_format:
            file_format = "{time} | {level} | {name}:{function}:{line} | {message}"
        else:
            file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"

        logger.add(
            log_file,
            format=file_format,
            level="DEBUG",  # Always debug level for files
            rotation=max_file_size,
            retention=retention,
            encoding="utf-8"
        )

    # Add context information
    logger.bind(config=config.__class__.__name__)


def get_logger(name: str):
    """
    Get logger instance with error handling

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logger.bind(name=name)


def log_function_call(func_name: str, args: dict[str, Any] | None = None, level: str = "DEBUG") -> None:
    """
    Log function call with arguments

    Args:
        func_name: Function name
        args: Function arguments
        level: Log level
    """
    msg = f"Calling {func_name}"
    if args:
        # Mask sensitive information
        safe_args = {}
        for key, value in args.items():
            if "password" in key.lower() or "token" in key.lower():
                safe_args[key] = "***masked***"
            else:
                safe_args[key] = str(value)[:100]  # Truncate long values
        msg += f" with args: {safe_args}"

    logger.log(level, msg)


def log_performance(func_name: str, duration: float, success: bool = True) -> None:
    """
    Log performance information

    Args:
        func_name: Function name
        duration: Execution duration in seconds
        success: Whether function succeeded
    """
    status = "success" if success else "failure"
    logger.info(f"Performance: {func_name} completed in {duration:.3f}s ({status})")


# Context manager for operation timing
class OperationTimer:
    """Context manager for timing operations"""

    def __init__(self, operation_name: str, logger_instance=None):
        self.operation_name = operation_name
        self.logger = logger_instance or logger
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting operation: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None

        if success:
            self.logger.debug(f"Operation {self.operation_name} completed in {duration:.3f}s")
        else:
            self.logger.error(f"Operation {self.operation_name} failed after {duration:.3f}s: {exc_val}")

        return False  # Don't suppress exceptions


# Decorator for function timing
def timed_operation(func):
    """Decorator to time function execution"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            logger.debug(f"Function {func.__name__} completed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {duration:.3f}s: {e}")
            raise
    return wrapper


# Enhanced exception handling
def handle_exceptions(func):
    """Decorator to handle exceptions with enhanced logging"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            context = f"Function {func.__name__}"
            error_handler.log_error(e, context, {"args": args, "kwargs": kwargs})
            raise
    return wrapper
