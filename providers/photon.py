"""
SAT Centre Updater - Photon Geocoding Provider

Uses the Photon geocoding service (powered by OpenStreetMap/Komoot).
Free, no API key required. Faster than Nominatim.

Usage:
    from providers.photon import PhotonProvider

    provider = PhotonProvider()
    results = provider.geocode("Legacy School Bangalore India")
"""

import time
from typing import Any, Dict, List

import requests

from config import settings
from processing.scorer import GeocodeCandidate


class PhotonProvider:
    """
    Photon geocoding provider.

    Endpoint: https://photon.komoot.io/api
    Rate limit: More generous than Nominatim, but still polite.
    """

    BASE_URL = "https://photon.komoot.io/api/"

    def __init__(self) -> None:
        """Initialize the Photon provider."""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.HTTP.USER_AGENT,
            "Accept": "application/json",
        })
        self._last_request_time: float = 0.0
        self._min_interval: float = 0.5

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
            List of GeocodeCandidate objects.
        """
        self._respect_rate_limit()

        params: Dict[str, Any] = {
            "q": query,
            "limit": limit,
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
        """Parse a Photon GeoJSON feature into a GeocodeCandidate."""
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [0, 0])

        return GeocodeCandidate(
            name=props.get("name", ""),
            address=self._build_address(props),
            city=props.get("city", props.get("town", props.get("village", ""))),
            state=props.get("state", ""),
            country=props.get("country", ""),
            latitude=float(coords[1]) if len(coords) > 1 else 0.0,
            longitude=float(coords[0]) if len(coords) > 0 else 0.0,
            confidence=min(1.0, props.get("score", 0.5)),
            provider="photon",
            raw=props,
        )

    def _build_address(self, props: Dict[str, Any]) -> str:
        """Build a human-readable address from Photon properties."""
        parts = [
            props.get("housenumber", ""),
            props.get("street", ""),
            props.get("district", props.get("suburb", "")),
        ]
        return ", ".join(p for p in parts if p).strip(", ")

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()
