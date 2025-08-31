"""
Performance monitoring utilities
"""

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations"""
    operation_count: int = 0
    total_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    avg_time: float = 0.0
    operations: dict[str, int] = field(default_factory=lambda: defaultdict(int))


class PerformanceMonitor:
    """Monitor performance of operations"""

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self._operation_stack = []

    @contextmanager
    def measure(self, operation_name: str):
        """Context manager to measure operation duration"""
        start_time = time.perf_counter()
        self._operation_stack.append(operation_name)

        try:
            yield
        finally:
            duration = time.perf_counter() - start_time
            operation = self._operation_stack.pop()

            # Update metrics
            self.metrics.operation_count += 1
            self.metrics.total_time += duration
            self.metrics.min_time = min(self.metrics.min_time, duration)
            self.metrics.max_time = max(self.metrics.max_time, duration)
            self.metrics.avg_time = self.metrics.total_time / self.metrics.operation_count
            self.metrics.operations[operation] += 1

            logger.debug(
                f"Operation '{operation}' completed in {duration:.3f}s"
            )

    def get_summary(self) -> dict[str, Any]:
        """Get performance summary"""
        return {
            "total_operations": self.metrics.operation_count,
            "total_time": self.metrics.total_time,
            "average_time": self.metrics.avg_time,
            "min_time": self.metrics.min_time,
            "max_time": self.metrics.max_time,
            "operations_breakdown": dict(self.metrics.operations),
        }

    def reset(self):
        """Reset all metrics"""
        self.metrics = PerformanceMetrics()
        self._operation_stack.clear()


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def measure_performance(operation_name: str):
    """Decorator to measure function performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with performance_monitor.measure(operation_name or func.__name__):
                return func(*args, **kwargs)
        return wrapper
    return decorator
