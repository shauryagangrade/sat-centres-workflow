"""
SAT Centre Updater - Nominatim Geocoding Provider

Uses OpenStreetMap Nominatim for geocoding. Free, no API key required.
Respects the 1 request/second rate limit.

Usage:
    from providers.nominatim import NominatimProvider

    provider = NominatimProvider()
    results = provider.geocode("Legacy School Bangalore India")
"""

import time
from typing import Any, Dict, List

import requests

from config import settings
from processing.scorer import GeocodeCandidate


class NominatimProvider:
    """
    Nominatim geocoding provider using OpenStreetMap data.

    Rate limit: 1 request per second ( enforced via _last_request_time ).
    Endpoint: https://nominatim.openstreetmap.org/search
    """

    BASE_URL = "https://nominatim.openstreetmap.org/search"

    def __init__(self) -> None:
        """Initialize the Nominatim provider."""
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": settings.HTTP.USER_AGENT,
                "Accept": "application/json",
            }
        )
        self._last_request_time: float = 0.0
        self._min_interval: float = settings.GEOCODING.RATE_LIMIT_DELAY

    def _respect_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def geocode(self, query: str, limit: int = 5) -> List[GeocodeCandidate]:
        """
        Geocode a query string.

        Args:
            query: Search string.
            limit: Maximum number of results.

        Returns:
            List of GeocodeCandidate objects.
        """
        self._respect_rate_limit()

        params: Dict[str, Any] = {
            "q": query,
            "format": "jsonv2",
            "limit": limit,
            "addressdetails": 1,
        }

        try:
            response = self.session.get(
                self.BASE_URL, params=params, timeout=settings.HTTP.TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            return []

        return [self._parse_result(item) for item in data]

    def _parse_result(self, item: Dict[str, Any]) -> GeocodeCandidate:
        """Parse a Nominatim result into a GeocodeCandidate."""
        address = item.get("address", {})

        return GeocodeCandidate(
            name=item.get("display_name", "").split(",")[0].strip(),
            address=self._build_address(address),
            city=address.get("city", address.get("town", address.get("village", ""))),
            state=address.get("state", ""),
            country=address.get("country", ""),
            latitude=float(item.get("lat", 0)),
            longitude=float(item.get("lon", 0)),
            confidence=min(1.0, float(item.get("importance", 0.5)) + 0.2),
            provider="nominatim",
            raw=item,
        )

    def _build_address(self, address: Dict[str, Any]) -> str:
        """Build a human-readable address from Nominatim address components."""
        parts = [
            address.get("house_number", ""),
            address.get("road", ""),
            address.get("suburb", address.get("neighbourhood", "")),
        ]
        return ", ".join(p for p in parts if p).strip(", ")

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
