"""
Historical evidence collector.

Evaluates consistency with previously verified coordinates.
Large unexpected movements reduce confidence.
Address and name changes are tracked.
"""

import math
from typing import Dict, Optional, Tuple

from verification.models import HistoricalEvidence

# Threshold for "large movement" in km
LARGE_MOVEMENT_THRESHOLD_KM = 50.0

# Threshold for "small movement" in km (still notable but acceptable)
SMALL_MOVEMENT_THRESHOLD_KM = 5.0


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


class HistoricalEvidenceCollector:
    """
    Collects historical evidence by comparing against previously verified data.

    Checks for consistency in coordinates, address, and name.
    """

    def collect(
        self,
        candidate_lat: float,
        candidate_lon: float,
        candidate_name: str,
        candidate_address: str,
        previous_data: Optional[Dict] = None,
    ) -> HistoricalEvidence:
        """
        Collect historical evidence.

        Args:
            candidate_lat: Candidate latitude.
            candidate_lon: Candidate longitude.
            candidate_name: Candidate name.
            candidate_address: Candidate address.
            previous_data: Dict with keys: latitude, longitude, name, address.

        Returns:
            HistoricalEvidence with historical signals.
        """
        evidence = HistoricalEvidence()

        if not previous_data:
            return evidence

        evidence.has_previous_data = True

        prev_lat = previous_data.get("latitude")
        prev_lon = previous_data.get("longitude")
        prev_name = previous_data.get("name", "")
        prev_address = previous_data.get("address", "")

        # Check coordinate match
        if prev_lat is not None and prev_lon is not None:
            distance = _haversine_km(candidate_lat, candidate_lon, prev_lat, prev_lon)
            evidence.distance_from_previous = distance

            # Matches if within 1km
            evidence.matches_previous = distance <= 1.0

            # Large movement detection
            evidence.large_movement = distance > LARGE_MOVEMENT_THRESHOLD_KM

        # Check name change
        if prev_name:
            from rapidfuzz import fuzz

            name_sim = fuzz.ratio(candidate_name.lower(), prev_name.lower())
            evidence.name_changed = name_sim < 70

        # Check address change
        if prev_address:
            from rapidfuzz import fuzz

            addr_sim = fuzz.ratio(candidate_address.lower(), prev_address.lower())
            evidence.address_changed = addr_sim < 60

        return evidence
