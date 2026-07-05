"""
SAT Centre Updater - Logging Configuration

Configures structured logging with daily log files and multiple handlers.

Usage:
    from utils.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Processing started")
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import settings


_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(
    name: str,
    level: Optional[str] = None,
) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__).
        level: Log level override. Uses config default if None.

    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        _configure_logger(logger, level or "INFO")

    return logger


def _configure_logger(logger: logging.Logger, level: str) -> None:
    """Attach handlers to a logger."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(console)

    # File handler (daily log)
    log_dir = settings.PATHS.LOGS_DIR
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"sat_updater_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    logger.addHandler(file_handler)
