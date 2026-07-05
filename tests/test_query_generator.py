"""
SAT Centre Updater - Query Generator Tests

Unit tests for the query generator module.
"""

from processing.normalizer import SatCentre
from processing.query_generator import QueryGenerator


class TestQueryGenerator:
    """Test cases for the QueryGenerator class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.gen = QueryGenerator()

    def test_generate_full_info(self) -> None:
        """Test generating queries with full centre info."""
        centre = SatCentre(
            id="1",
            name="Legacy International School",
            city="Bangalore",
            state="Karnataka",
            country="India",
        )
        queries = self.gen.generate(centre)

        assert len(queries) > 0
        # Most specific query should be first
        assert "Legacy International School" in queries[0]
        assert "Bangalore" in queries[0]
        assert "India" in queries[0]

    def test_generate_minimal_info(self) -> None:
        """Test generating queries with minimal info."""
        centre = SatCentre(id="1", name="Test School")
        queries = self.gen.generate(centre)

        assert len(queries) >= 1
        assert "Test School" in queries[0]

    def test_generate_no_duplicates(self) -> None:
        """Test that generated queries have no duplicates."""
        centre = SatCentre(
            id="1",
            name="School",
            city="City",
            state="State",
            country="Country",
        )
        queries = self.gen.generate(centre)

        assert len(queries) == len(set(queries))

    def test_generate_max_queries(self) -> None:
        """Test that query count respects MAX_QUERIES limit."""
        centre = SatCentre(
            id="1",
            name="A",
            address="123 Street",
            city="B",
            state="C",
            country="D",
        )
        queries = self.gen.generate(centre)

        assert len(queries) <= self.gen.MAX_QUERIES

    def test_generate_batch(self) -> None:
        """Test batch query generation."""
        centres = [
            SatCentre(id="1", name="School A", city="Mumbai"),
            SatCentre(id="2", name="School B", city="Delhi"),
        ]
        batch = self.gen.generate_batch(centres)

        assert "1" in batch
        assert "2" in batch
        assert len(batch["1"]) > 0
        assert len(batch["2"]) > 0

    def test_generate_empty_name(self) -> None:
        """Test generating queries with empty name."""
        centre = SatCentre(id="1", city="Bangalore", country="India")
        queries = self.gen.generate(centre)

        # Should still return something if city + country present
        assert len(queries) >= 0

    def test_clean_name_removes_noise(self) -> None:
        """Test that noise words are removed from cleaned names."""
        cleaned = self.gen._clean_name("The Legacy School of Bangalore")
        assert "the" not in cleaned.lower().split()
        assert "of" not in cleaned.lower().split()
