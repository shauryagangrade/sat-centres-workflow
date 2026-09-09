"""
SAT Centre Updater - Overpass Provider Tests

Covers the country-code lookup used when parsing Overpass results.
"""

from providers.overpass import OverpassProvider


class TestOverpassProvider:
    """Test cases for the Overpass provider."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.provider = OverpassProvider()

    def test_country_from_code_known(self) -> None:
        """Known country codes map to full country names."""
        assert self.provider._country_from_code("IN") == "India"
        assert self.provider._country_from_code("BR") == "Brazil"
        assert self.provider._country_from_code("US") == "United States"

    def test_country_from_code_lowercase(self) -> None:
        """Country codes are matched case-insensitively."""
        assert self.provider._country_from_code("br") == "Brazil"
        assert self.provider._country_from_code("sg") == "Singapore"

    def test_country_from_code_unknown(self) -> None:
        """Unknown codes fall through to the raw code."""
        assert self.provider._country_from_code("XX") == "XX"
        assert self.provider._country_from_code("") == ""

    def test_close_session(self) -> None:
        """Closing the session does not raise."""
        self.provider.close()
