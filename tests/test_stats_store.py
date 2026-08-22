"""
SAT Centre Updater - Stats Store Tests

Unit tests for the persisted run stats store.
"""

import json
from pathlib import Path

from utils.stats_store import StatsStore


class TestStatsStore:
    """Test cases for the StatsStore class."""

    def setup_method(self) -> None:
        """Set up test fixtures with a temporary stats file."""
        self.stats_file = Path("datasets/sat/reports/run_stats.json")
        self.store = StatsStore(stats_file=self.stats_file)
        self.store.clear()

    def teardown_method(self) -> None:
        """Clean up the stats file after each test."""
        self.store.clear()

    def test_load_missing_file_returns_empty(self) -> None:
        """Test that loading a missing file returns an empty dict."""
        assert self.store.load() == {}

    def test_update_and_load_round_trip(self) -> None:
        """Test that updated fields are persisted and loaded back."""
        self.store.update({"total_centres": 42, "new_centres": 3})

        data = self.store.load()
        assert data["total_centres"] == 42
        assert data["new_centres"] == 3

    def test_update_merges_with_existing(self) -> None:
        """Test that update merges fields instead of replacing them."""
        self.store.update({"total_centres": 42})
        self.store.update({"failed_centres": 5})

        data = self.store.load()
        assert data["total_centres"] == 42
        assert data["failed_centres"] == 5

    def test_update_overwrites_matching_keys(self) -> None:
        """Test that re-recording a key overwrites the old value."""
        self.store.update({"total_centres": 42})
        self.store.update({"total_centres": 100})

        assert self.store.load()["total_centres"] == 100

    def test_clear_removes_all_stats(self) -> None:
        """Test that clear empties the store."""
        self.store.update({"total_centres": 42})
        self.store.clear()

        assert self.store.load() == {}
        assert not self.stats_file.exists()

    def test_corrupt_file_returns_empty(self) -> None:
        """Test that a corrupt stats file is treated as empty."""
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self.stats_file.write_text("{not valid json", encoding="utf-8")

        assert self.store.load() == {}

    def test_non_dict_json_returns_empty(self) -> None:
        """Test that a non-object JSON document is treated as empty."""
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        self.stats_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

        assert self.store.load() == {}

    def test_default_path_in_reports_dir(self) -> None:
        """Test the default file path points at the reports directory."""
        default_store = StatsStore()
        assert default_store.stats_file.parent.name == "reports"
