"""
SAT Centre Updater - Stats Store

Persists per-step pipeline statistics to a JSON file so that the
reports step can hydrate summary.md / summary.html even when steps
run as separate CLI invocations.

Usage:
    from utils.stats_store import StatsStore

    store = StatsStore()
    store.clear()                       # start of a new run (download step)
    store.update({"total_centres": 42}) # any pipeline step
    data = store.load()                 # reports step
"""

import json
import logging
from pathlib import Path
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


class StatsStore:
    """Read/merge/write access to the persisted run stats JSON."""

    def __init__(self, stats_file: Path | None = None) -> None:
        """
        Initialize the stats store.

        Args:
            stats_file: Path to the stats JSON file.
                Defaults to REPORTS_DIR / run_stats.json.
        """
        self.stats_file = stats_file or (settings.PATHS.REPORTS_DIR / "run_stats.json")
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        """
        Load all recorded stats.

        Returns:
            Dictionary of recorded stats, or an empty dict if the
            file is missing or corrupt.
        """
        if not self.stats_file.exists():
            return {}

        try:
            with open(self.stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Could not read stats file {self.stats_file}: {e}")
            return {}

    def update(self, fields: dict[str, Any]) -> None:
        """
        Merge fields into the stored stats.

        Args:
            fields: Key/value pairs to record.
        """
        data = self.load()
        data.update(fields)

        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.warning(f"Could not write stats file {self.stats_file}: {e}")

    def clear(self) -> None:
        """Remove all recorded stats (start of a new pipeline run)."""
        try:
            if self.stats_file.exists():
                self.stats_file.unlink()
        except OSError as e:
            logger.warning(f"Could not remove stats file {self.stats_file}: {e}")
