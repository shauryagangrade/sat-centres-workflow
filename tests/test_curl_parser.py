"""
SAT Centre Updater - cURL Parser Tests

Unit tests for the cURL parser module.
"""

import pytest

from processing.curl_parser import CurlParser


class TestCurlParser:
    """Test cases for the CurlParser class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.parser = CurlParser()

    def test_parse_simple_get(self) -> None:
        """Test parsing a simple GET request."""
        curl = 'curl "https://example.com/api/data" -H "Accept: application/json"'
        result = self.parser.parse(curl)

        assert result.method == "GET"
        assert result.url == "https://example.com/api/data"
        assert result.headers.get("Accept") == "application/json"

    def test_parse_post_with_json(self) -> None:
        """Test parsing a POST request with JSON data."""
        curl = """curl 'https://api.example.com/search' \\
          -H 'Content-Type: application/json' \\
          -H 'Authorization: Bearer token123' \\
          --data '{"query": "test"}'"""
        result = self.parser.parse(curl)

        assert result.method == "POST"
        assert result.url == "https://api.example.com/search"
        assert result.json_data == {"query": "test"}
        assert result.headers.get("Authorization") == "Bearer token123"

    def test_parse_cookies(self) -> None:
        """Test parsing cookies from cURL command."""
        curl = """curl 'https://example.com' \\
          -b 'session=abc123; user=john'"""
        result = self.parser.parse(curl)

        assert result.cookies.get("session") == "abc123"
        assert result.cookies.get("user") == "john"

    def test_parse_auth(self) -> None:
        """Test parsing authentication credentials."""
        curl = """curl 'https://api.example.com' -u 'user:pass123'"""
        result = self.parser.parse(curl)

        assert result.auth == ("user", "pass123")

    def test_parse_compressed(self) -> None:
        """Test parsing compressed flag."""
        curl = 'curl "https://example.com" --compressed'
        result = self.parser.parse(curl)

        assert result.compressed is True

    def test_parse_insecure(self) -> None:
        """Test parsing insecure flag."""
        curl = 'curl -k "https://example.com"'
        result = self.parser.parse(curl)

        assert result.insecure is True

    def test_parse_post_method_explicit(self) -> None:
        """Test parsing explicit POST method."""
        curl = """curl -X POST 'https://api.example.com/data' \\
          --data 'key=value'"""
        result = self.parser.parse(curl)

        assert result.method == "POST"
        assert result.data == "key=value"

    def test_parse_query_params(self) -> None:
        """Test parsing query parameters from URL."""
        curl = 'curl "https://example.com/search?q=test&page=1"'
        result = self.parser.parse(curl)

        assert result.query_params.get("q") == "test"
        assert result.query_params.get("page") == "1"

    def test_parse_empty_raises(self) -> None:
        """Test that empty cURL raises ValueError."""
        with pytest.raises(ValueError, match="Empty cURL command"):
            self.parser.parse("")

    def test_parse_no_url_raises(self) -> None:
        """Test that cURL without URL raises ValueError."""
        with pytest.raises(ValueError, match="Could not extract URL"):
            self.parser.parse("curl -H 'Accept: application/json'")

    def test_parse_line_continuations(self) -> None:
        """Test parsing cURL with line continuations."""
        curl = """curl 'https://example.com' \\
          -H 'Accept: application/json' \\
          -H 'Authorization: Bearer token'"""
        result = self.parser.parse(curl)

        assert result.url == "https://example.com"
        assert "Accept" in result.headers
        assert "Authorization" in result.headers

    def test_to_dict(self) -> None:
        """Test CurlRequest.to_dict() conversion."""
        curl = 'curl "https://example.com" -H "Accept: text/html"'
        result = self.parser.parse(curl)
        d = result.to_dict()

        assert isinstance(d, dict)
        assert d["method"] == "GET"
        assert d["url"] == "https://example.com"

    def test_parse_put_method(self) -> None:
        """Test parsing PUT method."""
        curl = """curl -X PUT 'https://api.example.com/resource/1' \\
          --data '{"name": "updated"}'"""
        result = self.parser.parse(curl)

        assert result.method == "PUT"
        assert result.json_data == {"name": "updated"}

    def test_parse_delete_method(self) -> None:
        """Test parsing DELETE method."""
        curl = 'curl -X DELETE "https://api.example.com/resource/1"'
        result = self.parser.parse(curl)

        assert result.method == "DELETE"
