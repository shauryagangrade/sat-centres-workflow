"""
SAT Centre Updater - Configuration Tests

Verifies the config defaults added/changed this session (schema template
directory, all-countries validation) and directory setup.
"""

from pathlib import Path

from config import settings
from utils.helpers import setup_directories


class TestPathDefaults:
    """Tests for path configuration defaults."""

    def test_templates_dir_default(self) -> None:
        assert settings.PATHS.TEMPLATES_DIR == Path("templates")

    def test_generated_dir_default(self) -> None:
        assert settings.PATHS.GENERATED_DIR == Path("datasets/sat/generated")


class TestValidationDefaults:
    """Tests for validation configuration defaults."""

    def test_valid_countries_empty_means_all(self) -> None:
        assert settings.VALIDATION.VALID_COUNTRIES == []


class TestSetupDirectories:
    """Tests for utils.helpers.setup_directories."""

    def test_creates_templates_dir(self, monkeypatch, tmp_path) -> None:
        targets: dict[str, Path] = {}
        for name in (
            "RAW_DIR",
            "GENERATED_DIR",
            "OUTPUT_DIR",
            "REPORTS_DIR",
            "LOGS_DIR",
            "CACHE_DIR",
            "TEMPLATES_DIR",
        ):
            target = tmp_path / name.lower()
            targets[name] = target
            monkeypatch.setattr(settings.PATHS, name, target)

        setup_directories()

        for name, target in targets.items():
            assert target.is_dir(), f"{name} directory not created: {target}"
