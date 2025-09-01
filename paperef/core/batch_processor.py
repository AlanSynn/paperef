"""
Batch processing has been removed from the project.

This module is kept as a stub to maintain import compatibility, but all
previous batch-related classes and functions have been deprecated and removed
to simplify the codebase and reduce flaky/slow test behavior.
"""

from __future__ import annotations

from typing import Any


class RemovedFeatureError(RuntimeError):
    """Raised when removed batch processing functionality is accessed."""


def __getattr__(name: str) -> Any:  # type: ignore[override]
    msg = "Batch processing has been removed. Please process files individually via the CLI or API."
    raise RemovedFeatureError(
        msg
    )
