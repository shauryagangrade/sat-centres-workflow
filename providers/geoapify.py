"""
SAT Centre Updater - Geoapify Geocoding Provider

Uses the Geoapify geocoding API. Requires an API key.
Generous free tier: 3000 requests/day.

Usage:
    from providers.geoapify import GeoapifyProvider

    provider = GeoapifyProvider(api_key="your-key")
    results = provider.geocode("Legacy School Bangalore India")
"""

import time
from typing import Any, Dict, List, Optional

import requests

from config import settings
from processing.scorer import GeocodeCandidate


class GeoapifyProvider:
    """
    Geoapify geocoding provider.

    Endpoint: https://api.geoapify.com/v1/geocode/search
    Requires API key.
    """

    BASE_URL = "https://api.geoapify.com/v1/geocode/search"

    def __init__(self, api_key: Optional[str] = None) -> None:
        """
        Initialize the Geoapify provider.

        Args:
            api_key: Geoapify API key. Falls back to config setting.
        """
        self.api_key = api_key or settings.GEOCODING.GEOAPIFY_API_KEY

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.HTTP.USER_AGENT,
            "Accept": "application/json",
        })
        self._last_request_time: float = 0.0
        self._min_interval: float = 0.3

    def _respect_rate_limit(self) -> None:
        """Enforce rate limiting."""
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
            List of GeocodeCandidate objects. Empty if no API key or on error.
        """
        if not self.api_key:
            return []

        self._respect_rate_limit()

        params: Dict[str, Any] = {
            "text": query,
            "limit": limit,
            "apiKey": self.api_key,
            "format": "json",
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=settings.HTTP.TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except (requests.RequestException, ValueError):
            return []

        features = data.get("features", [])
        return [self._parse_feature(f) for f in features]

    def _parse_feature(self, feature: Dict[str, Any]) -> GeocodeCandidate:
        """Parse a Geoapify GeoJSON feature into a GeocodeCandidate."""
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])

        return GeocodeCandidate(
            name=props.get("name", ""),
            address=props.get("formatted", ""),
            city=props.get("city", props.get("town", props.get("village", ""))),
            state=props.get("state", ""),
            country=props.get("country", ""),
            latitude=float(coords[1]) if len(coords) > 1 else 0.0,
            longitude=float(coords[0]) if len(coords) > 0 else 0.0,
            confidence=min(1.0, props.get("rank", {}).get("confidence", 0.5)),
            provider="geoapify",
            raw=props,
        )

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
