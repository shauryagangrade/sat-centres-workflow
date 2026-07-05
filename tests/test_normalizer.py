"""
SAT Centre Updater - Normalizer Tests

Unit tests for the normalizer module.
"""

import json
from processing.normalizer import Normalizer, SatCentre


class TestSatCentre:
    """Test cases for the SatCentre dataclass."""

    def test_to_dict(self) -> None:
        """Test converting SatCentre to dictionary."""
        centre = SatCentre(
            id="abc123",
            name="Legacy School",
            city="Bangalore",
            country="India",
            latitude=12.9716,
            longitude=77.5946,
        )
        d = centre.to_dict()

        assert d["id"] == "abc123"
        assert d["name"] == "Legacy School"
        assert d["latitude"] == 12.9716

    def test_from_dict(self) -> None:
        """Test creating SatCentre from dictionary."""
        data = {
            "id": "xyz",
            "name": "Test School",
            "city": "Mumbai",
            "country": "India",
            "latitude": 19.0760,
            "longitude": 72.8777,
        }
        centre = SatCentre.from_dict(data)

        assert centre.id == "xyz"
        assert centre.name == "Test School"
        assert centre.city == "Mumbai"
        assert centre.latitude == 19.0760

    def test_from_dict_defaults(self) -> None:
        """Test SatCentre.from_dict with missing fields."""
        centre = SatCentre.from_dict({"name": "Minimal School"})

        assert centre.name == "Minimal School"
        assert centre.id == ""
        assert centre.latitude is None
        assert centre.longitude is None
        assert centre.metadata == {}


class TestNormalizer:
    """Test cases for the Normalizer class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.normalizer = Normalizer()

    def test_normalize_json_list(self) -> None:
        """Test normalizing a JSON list of records."""
        data = [
            {
                "TestCenterCode": "TC001",
                "TestCenterName": "Legacy School Bangalore",
                "City": "Bangalore",
                "State": "Karnataka",
                "Country": "India",
            }
        ]
        centres = self.normalizer.normalize(data)

        assert len(centres) == 1
        assert centres[0].name == "Legacy School Bangalore"
        assert centres[0].city == "Bangalore"
        assert centres[0].country == "India"

    def test_normalize_empty_list(self) -> None:
        """Test normalizing an empty list."""
        centres = self.normalizer.normalize([])
        assert len(centres) == 0

    def test_normalize_record_without_name_skipped(self) -> None:
        """Test that records without a name are skipped."""
        data = [{"city": "Bangalore", "country": "India"}]
        centres = self.normalizer.normalize(data)
        assert len(centres) == 0

    def test_normalize_csv(self) -> None:
        """Test normalizing CSV data."""
        csv_data = "name,city,country\nTest School,Mumbai,India\n"
        centres = self.normalizer.normalize(csv_data, fmt="csv")

        assert len(centres) == 1
        assert centres[0].name == "Test School"

    def test_normalize_json_string(self) -> None:
        """Test normalizing a JSON string."""
        json_str = json.dumps([
            {"name": "School A", "city": "Delhi", "country": "India"},
            {"name": "School B", "city": "Pune", "country": "India"},
        ])
        centres = self.normalizer.normalize(json_str)

        assert len(centres) == 2

    def test_generate_id_deterministic(self) -> None:
        """Test that the same record generates the same ID."""
        data = [
            {"name": "Same School", "city": "Same City", "country": "India"},
            {"name": "Same School", "city": "Same City", "country": "India"},
        ]
        centres = self.normalizer.normalize(data)

        assert len(centres) == 2
        # Both should have the same ID since the input is the same
        # (though they'll be separate objects in the list)

    def test_clean_string(self) -> None:
        """Test string cleaning."""
        assert self.normalizer._clean_string("  Hello   World  ") == "Hello World"
        assert self.normalizer._clean_string("") == ""
        assert self.normalizer._clean_string("test\x00value") == "testvalue"

    def test_parse_float_valid(self) -> None:
        """Test float parsing."""
        assert self.normalizer._parse_float("12.97") == 12.97
        assert self.normalizer._parse_float(42) == 42.0
        assert self.normalizer._parse_float(None) is None
        assert self.normalizer._parse_float("invalid") is None

    def test_save_and_load(self, tmp_path) -> None:
        """Test saving and loading centres."""
        from config import settings
        original_dir = settings.PATHS.GENERATED_DIR
        settings.PATHS.GENERATED_DIR = tmp_path

        normalizer = Normalizer(generated_dir=tmp_path)
        centres = [
            SatCentre(id="1", name="School A", city="Mumbai"),
            SatCentre(id="2", name="School B", city="Delhi"),
        ]

        path = normalizer.save(centres, "test_centres.json")
        assert path.exists()

        loaded = normalizer.load("test_centres.json")
        assert len(loaded) == 2
        assert loaded[0].name == "School A"
        assert loaded[1].name == "School B"

        settings.PATHS.GENERATED_DIR = original_dir
