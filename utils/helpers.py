"""
SAT Centre Updater - Utility Helpers

Shared utility functions used across the project.

Usage:
    from utils.helpers import setup_directories, format_bytes
"""

import os
from pathlib import Path
from typing import Any, Dict

from config import settings


def setup_directories() -> None:
    """Create all required project directories."""
    dirs = [
        settings.PATHS.RAW_DIR,
        settings.PATHS.GENERATED_DIR,
        settings.PATHS.OUTPUT_DIR,
        settings.PATHS.REPORTS_DIR,
        settings.PATHS.LOGS_DIR,
        settings.PATHS.CACHE_DIR,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def format_bytes(size: int) -> str:
    """Format byte count to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def format_duration(seconds: float) -> str:
    """Format seconds to human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.1f}s"


def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely navigate nested dictionaries."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current
