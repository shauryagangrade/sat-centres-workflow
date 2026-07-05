"""
SAT Centre Updater - Validator Tests

Unit tests for the centre validator module.
"""

from processing.normalizer import SatCentre
from processing.validator import CentreValidator


class TestCentreValidator:
    """Test cases for the CentreValidator class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.validator = CentreValidator()

    def test_valid_centre_passes(self) -> None:
        """Test that a valid centre passes validation."""
        centre = SatCentre(
            id="1",
            name="Legacy School",
            city="Bangalore",
            state="Karnataka",
            country="India",
            latitude=12.9716,
            longitude=77.5946,
        )
        valid, failed = self.validator.validate([centre])

        assert len(valid) == 1
        assert len(failed) == 0

    def test_missing_coords_fails(self) -> None:
        """Test that missing coordinates causes failure."""
        centre = SatCentre(
            id="1",
            name="Test School",
            country="India",
            latitude=None,
            longitude=None,
        )
        valid, failed = self.validator.validate([centre])

        assert len(valid) == 0
        assert len(failed) == 1
        assert "missing_coordinates" in failed[0].failure_reasons

    def test_wrong_country_fails(self) -> None:
        """Test that wrong country causes failure."""
        centre = SatCentre(
            id="1",
            name="Test School",
            country="Atlantis",
            latitude=12.97,
            longitude=77.59,
        )
        valid, failed = self.validator.validate([centre])

        assert len(valid) == 0
        assert len(failed) == 1
        assert any("wrong_country" in r for r in failed[0].failure_reasons)

    def test_duplicate_id_fails(self) -> None:
        """Test that duplicate IDs cause failure."""
        centres = [
            SatCentre(id="1", name="School A", country="India", latitude=12.97, longitude=77.59),
            SatCentre(id="1", name="School B", country="India", latitude=19.07, longitude=72.87),
        ]
        valid, failed = self.validator.validate(centres)

        assert len(valid) == 1
        assert len(failed) == 1
        assert any("duplicate_id" in r for r in failed[0].failure_reasons)

    def test_duplicate_coords_fails(self) -> None:
        """Test that duplicate coordinates cause failure."""
        centres = [
            SatCentre(id="1", name="School A", country="India", latitude=12.97, longitude=77.59),
            SatCentre(id="2", name="School B", country="India", latitude=12.97, longitude=77.59),
        ]
        valid, failed = self.validator.validate(centres)

        assert len(valid) == 1
        assert len(failed) == 1
        assert any("duplicate_coords" in r for r in failed[0].failure_reasons)

    def test_is_on_land_india(self) -> None:
        """Test that Indian coordinates are detected as land."""
        assert self.validator._is_on_land(12.9716, 77.5946) is True

    def test_is_on_land_ocean(self) -> None:
        """Test that ocean coordinates are detected."""
        # (-10.0, 60.0) is in the Southern Indian Ocean, outside all continent bounding boxes
        assert self.validator._is_on_land(-10.0, 60.0) is False

    def test_get_summary(self) -> None:
        """Test summary generation."""
        centres = [
            SatCentre(id="1", name="A", country="India", latitude=12.97, longitude=77.59),
            SatCentre(id="2", name="B", country="India", latitude=19.07, longitude=72.87),
            SatCentre(id="3", name="C", country="Atlantis", latitude=10.0, longitude=10.0),
        ]
        valid, failed = self.validator.validate(centres)
        summary = self.validator.get_summary(3, valid, failed)

        assert summary.total == 3
        assert summary.valid == 2
        assert summary.failed == 1
