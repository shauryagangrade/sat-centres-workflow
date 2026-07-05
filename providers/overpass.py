"""
SAT Centre Updater - Overpass Geocoding Provider

Uses the Overpass API to search for schools/educational institutions by name.
This is a fallback provider that searches for nodes tagged as schools.

Usage:
    from providers.overpass import OverpassProvider

    provider = OverpassProvider()
    results = provider.geocode("Legacy School Bangalore India")
"""

import time
from typing import Any, Dict, List, Optional

import requests

from config import settings
from processing.scorer import GeocodeCandidate


class OverpassProvider:
    """
    Overpass API geocoding provider.

    Searches for educational institutions using Overpass QL queries.
    Uses the default Overpass API endpoint (or a custom one).
    """

    DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    def __init__(self, overpass_url: Optional[str] = None) -> None:
        """
        Initialize the Overpass provider.

        Args:
            overpass_url: Custom Overpass API URL.
        """
        self.overpass_url = overpass_url or self.DEFAULT_OVERPASS_URL

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.HTTP.USER_AGENT,
        })
        self._last_request_time: float = 0.0
        self._min_interval: float = 5.0  # Overpass rate limits are stricter

    def _respect_rate_limit(self) -> None:
        """Enforce rate limiting."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def geocode(self, query: str, limit: int = 5) -> List[GeocodeCandidate]:
        """
        Search for educational institutions matching the query.

        Args:
            query: Search string (school name + location).
            limit: Maximum number of results.

        Returns:
            List of GeocodeCandidate objects.
        """
        self._respect_rate_limit()

        # Build Overpass QL query
        overpass_query = self._build_query(query, limit)

        try:
            response = self.session.post(
                self.overpass_url,
                data={"data": overpass_query},
                timeout=settings.HTTP.TIMEOUT * 2,  # Overpass can be slow
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            return []

        elements = data.get("elements", [])
        return [self._parse_element(el) for el in elements[:limit]]

    def _build_query(self, query: str, limit: int) -> str:
        """
        Build an Overpass QL query for school search.

        Searches for nodes and ways tagged as educational institutions
        whose name matches (fuzzy) the query.
        """
        # Extract name from query (first significant words)
        name_part = query.split()[0:3] if query else []
        name_search = " ".join(name_part)

        # Escape for Overpass
        name_search = name_search.replace('"', '\\"')

        return f"""
        [out:json][timeout:30];
        (
          node["amenity"="school"]["name"~"{name_search}",i](global);
          way["amenity"="school"]["name"~"{name_search}",i](global);
        );
        out center body;
        """

    def _parse_element(self, element: Dict[str, Any]) -> GeocodeCandidate:
        """Parse an Overpass element into a GeocodeCandidate."""
        tags = element.get("tags", {})

        # Get coordinates
        lat = element.get("lat") or element.get("center", {}).get("lat", 0)
        lon = element.get("lon") or element.get("center", {}).get("lon", 0)

        return GeocodeCandidate(
            name=tags.get("name", ""),
            address=self._build_address(tags),
            city=tags.get("addr:city", ""),
            state=tags.get("addr:state", ""),
            country=self._country_from_code(tags.get("addr:country", "")),
            latitude=float(lat),
            longitude=float(lon),
            confidence=0.4,  # Lower base confidence for Overpass
            provider="overpass",
            raw=element,
        )

    def _build_address(self, tags: Dict[str, Any]) -> str:
        """Build address from OSM addr:* tags."""
        parts = [
            tags.get("addr:housenumber", ""),
            tags.get("addr:street", ""),
            tags.get("addr:suburb", tags.get("addr:neighbourhood", "")),
        ]
        return ", ".join(p for p in parts if p).strip(", ")

    def _country_from_code(self, code: str) -> str:
        """Convert ISO 3166-1 alpha-2 country code to full name."""
        code_map = {
            "IN": "India", "US": "United States", "GB": "United Kingdom",
            "CA": "Canada", "AE": "United Arab Emirates", "SG": "Singapore",
            "AU": "Australia", "DE": "Germany", "FR": "France",
            "JP": "Japan", "KR": "South Korea", "CN": "China",
        }
        return code_map.get(code.upper(), code)

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
