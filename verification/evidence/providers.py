"""
Provider consensus evidence collector.

Evaluates agreement across multiple geocoding providers.
Consensus increases confidence; disagreement reduces it.
Tracks coordinate variance and provider reliability weights.
"""

import math
from typing import Dict, List, Optional, Tuple

from verification.models import ProviderEvidence


# Provider reliability weights (0.0-1.0)
# Based on data quality, freshness, and educational institution coverage
PROVIDER_WEIGHTS: Dict[str, float] = {
    "nominatim": 0.85,
    "photon": 0.80,
    "geoapify": 0.90,
    "overpass": 0.75,
    "pelias": 0.85,
    "mapbox": 0.92,
    "google": 0.95,
    "here": 0.88,
}


def _coordinate_variance(coords: List[Tuple[float, float]]) -> float:
    """
    Calculate variance of a set of coordinates.
    Returns variance in degrees (lower = more agreement).
    """
    if len(coords) < 2:
        return 0.0

    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]

    lat_var = sum((x - sum(lats) / len(lats)) ** 2 for x in lats) / len(lats)
    lon_var = sum((x - sum(lons) / len(lons)) ** 2 for x in lons) / len(lons)

    return math.sqrt(lat_var + lon_var)


def _find_cluster_center(
    coords: List[Tuple[float, float]], threshold_km: float = 5.0
) -> Optional[Tuple[float, float]]:
    """
    Find the center of the largest cluster of coordinates within threshold_km.
    Uses simple iterative clustering.
    """
    if not coords:
        return None

    if len(coords) == 1:
        return coords[0]

    # Simple approach: find the point that has the most neighbors within threshold
    best_center = coords[0]
    best_count = 0

    for i, (lat1, lon1) in enumerate(coords):
        count = 0
        for j, (lat2, lon2) in enumerate(coords):
            if i == j:
                continue
            dist = _haversine_km(lat1, lon1, lat2, lon2)
            if dist <= threshold_km:
                count += 1

        if count > best_count:
            best_count = count
            best_center = (lat1, lon1)

    return best_center


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km."""
    R = 6371.0
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class ProviderEvidenceCollector:
    """
    Collects provider consensus evidence for a candidate.

    Evaluates how many providers agree on a location,
    the variance of their coordinates, and provider reliability.
    """

    def collect(
        self,
        candidate_provider: str,
        all_candidates: List[Dict],
        provider_results: Optional[Dict[str, List[Dict]]] = None,
    ) -> ProviderEvidence:
        """
        Collect provider consensus evidence.

        Args:
            candidate_provider: The provider that returned this candidate.
            all_candidates: All candidates from all providers for this reference.
            provider_results: Dict mapping provider name to its candidate list.

        Returns:
            ProviderEvidence with consensus signals.
        """
        evidence = ProviderEvidence()

        if provider_results is None:
            # Single provider case
            evidence.providers_agreeing = 1
            evidence.providers_total = 1
            evidence.consensus_ratio = 1.0
            evidence.provider_weights = {
                candidate_provider: PROVIDER_WEIGHTS.get(candidate_provider, 0.5)
            }
            return evidence

        # Count unique providers
        providers_with_results = {
            name: cands for name, cands in provider_results.items() if cands
        }
        evidence.providers_total = len(providers_with_results)

        if evidence.providers_total == 0:
            return evidence

        # Find which providers agree (have candidates within 5km of the best)
        if not all_candidates:
            return evidence

        # Use the first candidate's coordinates as reference
        ref_lat = all_candidates[0].get("latitude", 0)
        ref_lon = all_candidates[0].get("longitude", 0)

        agreeing_providers = set()
        provider_coords: Dict[str, List[Tuple[float, float]]] = {}

        for name, candidates in providers_with_results.items():
            for cand in candidates:
                cand_lat = cand.get("latitude", 0)
                cand_lon = cand.get("longitude", 0)
                dist = _haversine_km(ref_lat, ref_lon, cand_lat, cand_lon)

                if name not in provider_coords:
                    provider_coords[name] = []
                provider_coords[name].append((cand_lat, cand_lon))

                if dist <= 5.0:  # Within 5km = agreement
                    agreeing_providers.add(name)
                    break

        evidence.providers_agreeing = len(agreeing_providers)
        evidence.consensus_ratio = (
            evidence.providers_agreeing / evidence.providers_total
            if evidence.providers_total > 0
            else 0.0
        )

        # Calculate coordinate variance
        all_coords = []
        for coords in provider_coords.values():
            all_coords.extend(coords)
        evidence.coordinate_variance = _coordinate_variance(all_coords)

        # Provider weights
        evidence.provider_weights = {
            name: PROVIDER_WEIGHTS.get(name, 0.5)
            for name in providers_with_results
        }

        # Disagreement flag
        evidence.disagreement = (
            evidence.providers_total >= 2 and evidence.consensus_ratio < 0.5
        )

        return evidence
