"""
SAT Centre Updater - Schema Transformer Tests

Tests for URL template detection, schema inference, and transformation.
"""

import json

from processing.normalizer import SatCentre
from processing.schema_transformer import SchemaTransformer


class TestSchemaTransformer:
    """Test cases for the SchemaTransformer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = SchemaTransformer()
        self.centres = [
            SatCentre(
                id="1",
                name="Legacy School",
                address="12 MG Road",
                city="Bangalore",
                state="Karnataka",
                country="India",
                postal_code="560001",
                latitude=12.9716,
                longitude=77.5946,
            ),
            SatCentre(
                id="2",
                name="Delhi Public School",
                address="45 Mathura Road",
                city="Delhi",
                state="Delhi",
                country="India",
                postal_code="110001",
                latitude=28.6139,
                longitude=77.2090,
            ),
        ]

    def test_literal_string_preserved(self):
        """Test that non-URL literal strings are preserved as-is."""
        sample = {"name": "Test", "type": "school"}
        schema = self.transformer.infer_schema(sample, self.centres)
        assert schema["type"] == "literal:school"

    def test_url_template_detection_google_maps(self):
        """Test detection of Google Maps URL with coordinates."""
        sample = {
            "gmaps_link": "https://maps.google.com/?q=12.9716,77.5946"
        }
        schema = self.transformer.infer_schema(sample, self.centres)
        assert "url_template:" in schema["gmaps_link"]
        assert "https://maps.google.com/?q={lat},{lng}" in schema["gmaps_link"]
        # Original URL stored as fallback
        assert "|||" in schema["gmaps_link"]

    def test_url_template_detection_separate_params(self):
        """Test detection of URL with lat/lng as separate query params."""
        sample = {
            "link": "https://example.com/place?lat=12.9716&lon=77.5946"
        }
        schema = self.transformer.infer_schema(sample, self.centres)
        assert "url_template:" in schema["link"]
        assert "{lat}" in schema["link"]
        assert "{lng}" in schema["link"]

    def test_url_template_substitution(self):
        """Test that URL templates are substituted with actual coordinates."""
        sample = {
            "gmaps_link": "https://maps.google.com/?q=12.9716,77.5946"
        }
        results = self.transformer.transform(self.centres, sample)

        assert len(results) == 2
        # First centre: Bangalore
        assert results[0]["gmaps_link"] == "https://maps.google.com/?q=12.9716,77.5946"
        # Second centre: Delhi
        assert results[1]["gmaps_link"] == "https://maps.google.com/?q=28.6139,77.209"

    def test_url_template_with_encoded_comma(self):
        """Test URL with %2C encoded comma."""
        sample = {
            "link": "https://maps.google.com/?q=12.9716%2C77.5946"
        }
        schema = self.transformer.infer_schema(sample, self.centres)
        assert "url_template:" in schema["link"]
        assert "{lat}" in schema["link"]
        assert "{lng}" in schema["link"]

    def test_non_url_string_not_templated(self):
        """Test that non-URL strings are not treated as templates."""
        sample = {"note": "This is a school in Bangalore"}
        schema = self.transformer.infer_schema(sample, self.centres)
        assert schema["note"] == "literal:This is a school in Bangalore"

    def test_url_without_coords_not_templated(self):
        """Test that URLs without coordinates are treated as literals."""
        sample = {"website": "https://example.com/school"}
        schema = self.transformer.infer_schema(sample, self.centres)
        assert schema["website"] == "literal:https://example.com/school"

    def test_url_template_without_coords_uses_original(self):
        """Test that URL template without available coords returns original."""
        sample = {
            "gmaps_link": "https://maps.google.com/?q=12.9716,77.5946"
        }
        # Centre with no coordinates
        no_coord_centres = [
            SatCentre(id="1", name="Test", latitude=None, longitude=None)
        ]
        results = self.transformer.transform(no_coord_centres, sample)
        assert results[0]["gmaps_link"] == "https://maps.google.com/?q=12.9716,77.5946"

    def test_nested_url_template(self):
        """Test URL template in nested object."""
        sample = {
            "links": {
                "google_maps": "https://maps.google.com/?q=12.9716,77.5946"
            }
        }
        results = self.transformer.transform(self.centres, sample)
        assert results[0]["links"]["google_maps"] == "https://maps.google.com/?q=12.9716,77.5946"
        assert results[1]["links"]["google_maps"] == "https://maps.google.com/?q=28.6139,77.209"

    def test_direct_field_mapping(self):
        """Test that direct field matches are found correctly."""
        sample = {"name": "", "city": "", "latitude": 0.0}
        schema = self.transformer.infer_schema(sample, self.centres)
        assert schema["name"] == "name"
        assert schema["city"] == "city"
        assert schema["latitude"] == "latitude"

    def test_detect_url_template_method(self):
        """Test the _detect_url_template method directly."""
        # Valid coordinate URL
        result = self.transformer._detect_url_template(
            "https://maps.google.com/?q=12.9716,77.5946"
        )
        assert result is not None
        assert "{lat}" in result
        assert "{lng}" in result

        # Non-URL
        assert self.transformer._detect_url_template("just text") is None

        # URL without coords
        assert self.transformer._detect_url_template("https://example.com") is None

        # Empty
        assert self.transformer._detect_url_template("") is None
        assert self.transformer._detect_url_template(None) is None
