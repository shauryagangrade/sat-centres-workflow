"""
Geographic evidence collector.

Evaluates spatial properties of a candidate: distance from expected locations,
reverse geocoding consistency, land/ocean detection, urban/rural classification,
and nearby point-of-interest signals.
"""

import math
from typing import Dict, Optional, Tuple

from verification.models import GeographyEvidence


# Simplified bounding boxes for continents (rough ocean detection)
CONTINENT_BBOXES: Dict[str, Tuple[float, float, float, float]] = {
    "asia": (-10.0, -170.0, 55.0, 180.0),
    "europe": (35.0, -25.0, 72.0, 45.0),
    "north_america": (7.0, -170.0, 85.0, -50.0),
    "south_america": (-60.0, -90.0, 15.0, -30.0),
    "africa": (-40.0, -20.0, 38.0, 55.0),
    "oceania": (-55.0, 100.0, 0.0, 180.0),
}

# Rough city center coordinates for distance calculation
# In production, this would come from a geocoding service
_CITY_CENTERS: Dict[str, Tuple[float, float]] = {
    "bangalore": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "chennai": (13.0827, 80.2707),
    "hyderabad": (17.3850, 78.4867),
    "pune": (18.5204, 73.8567),
    "kolkata": (22.5726, 88.3639),
    "agra": (27.1767, 78.0081),
    "jaipur": (26.9124, 75.7873),
    "lucknow": (26.8467, 80.9462),
    # US cities
    "new york": (40.7128, -74.0060),
    "los angeles": (34.0522, -118.2437),
    "chicago": (41.8781, -87.6298),
    "houston": (29.7604, -95.3698),
    "phoenix": (33.4484, -112.0740),
    # UK cities
    "london": (51.5074, -0.1278),
    "manchester": (53.4808, -2.2426),
    "birmingham": (52.4862, -1.8904),
    # Canada
    "toronto": (43.6532, -79.3832),
    "vancouver": (49.2827, -123.1207),
    # UAE
    "dubai": (25.2048, 55.2708),
    "abu dhabi": (24.4539, 54.3773),
    # Singapore
    "singapore": (1.3521, 103.8198),
}


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth.
    Returns distance in kilometers.
    """
    R = 6371.0  # Earth's radius in km

    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def is_on_land(lat: float, lon: float) -> bool:
    """
    Rough check if coordinates are on land using continent bounding boxes.
    """
    for _name, (min_lat, min_lon, max_lat, max_lon) in CONTINENT_BBOXES.items():
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return True
    return False


def estimate_coordinate_precision(lat: float, lon: float) -> float:
    """
    Estimate coordinate precision based on decimal places.
    More decimals = higher precision.
    Returns 0.0-1.0.
    """
    # Count meaningful decimal places
    lat_str = f"{lat:.6f}".rstrip("0")
    lon_str = f"{lon:.6f}".rstrip("0")

    lat_decimals = len(lat_str.split(".")[-1]) if "." in lat_str else 0
    lon_decimals = len(lon_str.split(".")[-1]) if "." in lon_str else 0

    avg_decimals = (lat_decimals + lon_decimals) / 2
    # 6 decimals ≈ 11cm precision, 4 decimals ≈ 11m, 2 decimals ≈ 1.1km
    return min(1.0, avg_decimals / 6.0)


class GeographyEvidenceCollector:
    """
    Collects geographic evidence for a candidate.

    Evaluates spatial relationships, land/ocean status, and proximity signals.
    """

    def collect(
        self,
        reference: Dict[str, str],
        candidate_lat: float,
        candidate_lon: float,
        reverse_geocode_data: Optional[Dict] = None,
        previous_coords: Optional[Tuple[float, float]] = None,
    ) -> GeographyEvidence:
        """
        Collect geographic evidence for a candidate.

        Args:
            reference: Dict with keys: city, state, country.
            candidate_lat: Candidate latitude.
            candidate_lon: Candidate longitude.
            reverse_geocode_data: Optional reverse geocode response.
            previous_coords: Optional (lat, lon) from historical data.

        Returns:
            GeographyEvidence with geographic signals.
        """
        evidence = GeographyEvidence()

        # Distance from expected city center
        city = reference.get("city", "").lower()
        if city in _CITY_CENTERS:
            city_lat, city_lon = _CITY_CENTERS[city]
            evidence.distance_from_city_center = _haversine_distance(
                candidate_lat, candidate_lon, city_lat, city_lon
            )

        # Land vs ocean check
        evidence.on_land = is_on_land(candidate_lat, candidate_lon)

        # Coordinate precision
        evidence.coordinate_precision = estimate_coordinate_precision(
            candidate_lat, candidate_lon
        )

        # Reverse geocode consistency
        if reverse_geocode_data:
            evidence.reverse_geocode_match = self._check_reverse_consistency(
                reference, reverse_geocode_data
            )
            evidence.admin_hierarchy_valid = self._check_admin_hierarchy(
                reference, reverse_geocode_data
            )
            evidence.urban_area = self._estimate_urban(reverse_geocode_data)
            evidence.nearby_educational = self._check_nearby_educational(
                reverse_geocode_data
            )
            evidence.nearby_roads = self._check_nearby_roads(reverse_geocode_data)
            evidence.nearby_landmarks = self._check_nearby_landmarks(reverse_geocode_data)

        # Distance from previous location
        if previous_coords:
            prev_lat, prev_lon = previous_coords
            evidence.distance_from_previous = _haversine_distance(
                candidate_lat, candidate_lon, prev_lat, prev_lon
            )

        return evidence

    def _check_reverse_consistency(
        self, reference: Dict[str, str], reverse_data: Dict
    ) -> bool:
        """Check if reverse geocode matches expected location."""
        rev_city = reverse_data.get("city", "").lower()
        ref_city = reference.get("city", "").lower()

        if ref_city and rev_city:
            if ref_city in rev_city or rev_city in ref_city:
                return True
            # Fuzzy check
            from rapidfuzz import fuzz

            if fuzz.ratio(ref_city, rev_city) > 70:
                return True

        rev_country = reverse_data.get("country", "").lower()
        ref_country = reference.get("country", "").lower()

        if ref_country and rev_country:
            if ref_country in rev_country or rev_country in ref_country:
                return True

        return False

    def _check_admin_hierarchy(
        self, reference: Dict[str, str], reverse_data: Dict
    ) -> bool:
        """Validate administrative hierarchy consistency."""
        # Check that city is within state, state is within country
        ref_state = reference.get("state", "").lower()
        ref_country = reference.get("country", "").lower()
        rev_state = reverse_data.get("state", "").lower()
        rev_country = reverse_data.get("country", "").lower()

        if ref_country and rev_country:
            if ref_country not in rev_country and rev_country not in ref_country:
                return False

        if ref_state and rev_state:
            if ref_state not in rev_state and rev_state not in ref_state:
                # Allow fuzzy match
                from rapidfuzz import fuzz

                if fuzz.ratio(ref_state, rev_state) < 60:
                    return False

        return True

    def _estimate_urban(self, reverse_data: Dict) -> bool:
        """Estimate if location is in an urban area."""
        # Heuristic: if reverse data has a city field, likely urban
        return bool(reverse_data.get("city"))

    def _check_nearby_educational(self, reverse_data: Dict) -> bool:
        """Check if there are nearby educational institutions."""
        # Check if the place itself or nearby places are educational
        place_type = reverse_data.get("type", "").lower()
        category = reverse_data.get("category", "").lower()

        educational_types = {"school", "university", "college", "academy", "education"}
        if place_type in educational_types or category in educational_types:
            return True

        # Check OSM tags if available
        tags = reverse_data.get("tags", {})
        if tags.get("amenity") in ("school", "university", "college"):
            return True

        return False

    def _check_nearby_roads(self, reverse_data: Dict) -> bool:
        """Check if there are nearby roads."""
        # If address has a street component, likely near roads
        return bool(
            reverse_data.get("road") or reverse_data.get("street")
        )

    def _check_nearby_landmarks(self, reverse_data: Dict) -> bool:
        """Check for nearby landmarks."""
        # Heuristic: if place has a name and is not residential
        place_type = reverse_data.get("type", "").lower()
        negative_types = {"residential", "house", "apartment", "building"}
        return bool(reverse_data.get("name")) and place_type not in negative_types
