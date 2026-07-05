"""
SAT Centre Updater - Provider Manager

Orchestrates multiple geocoding providers with automatic fallback,
caching integration, and rate-limit-aware parallel execution.

Usage:
    from providers.provider_manager import ProviderManager

    manager = ProviderManager()
    results = manager.geocode("Legacy School Bangalore India")
"""

from typing import Dict, List, Optional

from cache.cache_manager import CacheManager
from config import settings
from processing.scorer import GeocodeCandidate
from providers.nominatim import NominatimProvider
from providers.photon import PhotonProvider
from providers.geoapify import GeoapifyProvider
from providers.overpass import OverpassProvider


class ProviderManager:
    """
    Manages multiple geocoding providers with fallback and caching.

    Provider execution order:
    1. Check cache
    2. Nominatim
    3. Photon
    4. Geoapify
    5. Overpass (fallback)

    Stops at the first provider that returns results.
    """

    def __init__(self, cache: Optional[CacheManager] = None) -> None:
        """
        Initialize the provider manager.

        Args:
            cache: Optional CacheManager for caching results.
        """
        self.cache = cache or CacheManager()

        # Initialize providers in order
        self._providers = {
            "nominatim": NominatimProvider(),
            "photon": PhotonProvider(),
            "geoapify": GeoapifyProvider(),
            "overpass": OverpassProvider(),
        }

        # Provider order from config
        self._provider_order = settings.GEOCODING.PROVIDER_ORDER

        # Stats
        self._stats: Dict[str, int] = {name: 0 for name in self._provider_order}
        self._cache_hits: int = 0

    def geocode(self, query: str, limit: int = 5) -> List[GeocodeCandidate]:
        """
        Geocode a query using the provider chain with caching.

        Args:
            query: Search string.
            limit: Maximum results per provider.

        Returns:
            List of GeocodeCandidate objects from the first successful provider.
        """
        cache_key = f"geocode:{query.lower().strip()}:{limit}"

        # Check cache first
        cached = self.cache.get("geocode", cache_key)
        if cached is not None:
            self._cache_hits += 1
            return [GeocodeCandidate(**item) for item in cached]

        # Try each provider in order
        for provider_name in self._provider_order:
            provider = self._providers.get(provider_name)
            if provider is None:
                continue

            try:
                results = provider.geocode(query, limit=limit)
                if results:
                    self._stats[provider_name] += 1

                    # Cache results
                    serializable = []
                    for r in results:
                        serializable.append(
                            {
                                "name": r.name,
                                "address": r.address,
                                "city": r.city,
                                "state": r.state,
                                "country": r.country,
                                "latitude": r.latitude,
                                "longitude": r.longitude,
                                "confidence": r.confidence,
                                "provider": r.provider,
                                "raw": r.raw,
                            }
                        )
                    self.cache.set("geocode", cache_key, serializable)

                    return results
            except Exception:
                # Provider failed, try next
                continue

        return []

    def geocode_batch(
        self, queries: Dict[str, List[str]], limit: int = 5
    ) -> Dict[str, List[GeocodeCandidate]]:
        """
        Geocode multiple queries with caching.

        Args:
            queries: Dictionary mapping IDs to query lists.
            limit: Maximum results per query.

        Returns:
            Dictionary mapping IDs to geocode results.
        """
        results: Dict[str, List[GeocodeCandidate]] = {}

        for item_id, query_list in queries.items():
            for query in query_list:
                candidates = self.geocode(query, limit=limit)
                if candidates:
                    if item_id not in results:
                        results[item_id] = candidates
                    break  # Use first successful query

        return results

    @property
    def stats(self) -> Dict[str, int]:
        """Get provider usage statistics."""
        return self._stats.copy()

    @property
    def cache_hits(self) -> int:
        """Get cache hit count."""
        return self._cache_hits

    def close(self) -> None:
        """Close all provider sessions."""
        for provider in self._providers.values():
            provider.close()
