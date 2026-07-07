"""
Place type evidence collector.

Determines whether a geocoding candidate actually resembles an SAT venue.
Positive signals: school, university, college, educational campus, testing center.
Negative signals: residential building, farm, forest, industrial site, etc.
"""

import re
from typing import Dict, Optional

from verification.models import PlaceTypeEvidence


# Positive place types for SAT centres
POSITIVE_TYPES = {
    "school",
    "university",
    "college",
    "academy",
    "institute",
    "education",
    "campus",
    "testing_center",
    "test_center",
    "examination_center",
    "examination_centre",
    "lyceum",
    "gymnasium",
    "seminary",
    "polytechnic",
    "technical_institute",
}

# Negative place types (clearly not SAT venues)
NEGATIVE_TYPES = {
    "residential": "Residential building",
    "house": "House",
    "apartment": "Apartment building",
    "farm": "Farm",
    "forest": "Forest",
    "wood": "Woodland",
    "industrial": "Industrial site",
    "factory": "Factory",
    "mall": "Shopping mall",
    "shop": "Shop",
    "store": "Store",
    "parking": "Parking lot",
    "car_park": "Car park",
    "empty": "Empty land",
    "bare": "Bare land",
    "water": "Water body",
    "river": "River",
    "lake": "Lake",
    "ocean": "Ocean",
    "beach": "Beach",
    "mountain": "Mountain",
    "peak": "Mountain peak",
    "valley": "Valley",
    "desert": "Desert",
    "wetland": "Wetland",
    "cemetery": "Cemetery",
    "graveyard": "Graveyard",
    "prison": "Prison",
    "jail": "Jail",
    "hospital": "Hospital",
    "clinic": "Clinic",
    "pharmacy": "Pharmacy",
    "restaurant": "Restaurant",
    "hotel": "Hotel",
    "motel": "Motel",
    "bar": "Bar",
    "pub": "Pub",
    "nightclub": "Nightclub",
    "gas_station": "Gas station",
    "petrol_station": "Petrol station",
    "park": "Park",
    "garden": "Garden",
    "playground": "Playground",
    "stadium": "Stadium",
    "arena": "Arena",
    "cinema": "Cinema",
    "theater": "Theater",
    "theatre": "Theatre",
    "museum": "Museum",
    "gallery": "Gallery",
    "library": "Library",
    "church": "Church",
    "mosque": "Mosque",
    "temple": "Temple",
    "synagogue": "Synagogue",
    "shrine": "Shrine",
    "station": "Station (transport)",
    "stop": "Stop (transport)",
    "airport": "Airport",
    "port": "Port",
    "harbour": "Harbour",
    "harbor": "Harbor",
    "bridge": "Bridge",
    "tunnel": "Tunnel",
    "dam": "Dam",
    "power_station": "Power station",
    "substation": "Substation",
    "tower": "Tower",
    "mast": "Mast",
    "lighthouse": "Lighthouse",
}

# Educational keywords that can appear in names
EDUCATIONAL_KEYWORDS = {
    "school",
    "academy",
    "college",
    "university",
    "institute",
    "lyceum",
    "gymnasium",
    "seminary",
    "polytechnic",
    "campus",
    "education",
    "learning",
    "tutor",
    "tuition",
    "coaching",
    "center",
    "centre",
    "exam",
    "test",
    "sat",
    "gre",
    "gmat",
    "toefl",
    "ielts",
}


class PlaceTypeEvidenceCollector:
    """
    Collects place type evidence for a candidate.

    Determines if the candidate resembles an educational institution
    or testing center.
    """

    def collect(
        self,
        candidate_name: str,
        candidate_address: str,
        raw_data: Optional[Dict] = None,
    ) -> PlaceTypeEvidence:
        """
        Collect place type evidence.

        Args:
            candidate_name: Name of the candidate place.
            candidate_address: Address of the candidate.
            raw_data: Raw provider response data (may contain OSM tags, etc.).

        Returns:
            PlaceTypeEvidence with place type signals.
        """
        evidence = PlaceTypeEvidence()

        # Extract place type from raw data
        place_type = self._extract_place_type(raw_data) if raw_data else ""

        # Check if it's a positive type
        if place_type in POSITIVE_TYPES:
            evidence.category = place_type
            evidence.is_educational = True
            evidence.confidence = 0.9
            return evidence

        # Check if it's a negative type
        if place_type in NEGATIVE_TYPES:
            evidence.category = place_type
            evidence.is_negative_type = True
            evidence.negative_type_detail = NEGATIVE_TYPES[place_type]
            evidence.confidence = 0.8
            return evidence

        # Check name for educational keywords
        name_lower = candidate_name.lower()
        for keyword in EDUCATIONAL_KEYWORDS:
            if keyword in name_lower:
                evidence.category = "educational_keyword_match"
                evidence.is_educational = True
                evidence.confidence = 0.7
                return evidence

        # Check OSM tags if available
        if raw_data:
            tags = raw_data.get("tags", {})
            amenity = tags.get("amenity", "")
            if amenity in ("school", "university", "college", "library"):
                evidence.category = amenity
                evidence.is_educational = True
                evidence.confidence = 0.85
                return evidence

            building = tags.get("building", "")
            if building in ("school", "university", "college", "education"):
                evidence.category = f"building:{building}"
                evidence.is_educational = True
                evidence.confidence = 0.8
                return evidence

        # Default: unknown type, slightly negative
        evidence.category = "unknown"
        evidence.confidence = 0.3
        return evidence

    def _extract_place_type(self, raw_data: Dict) -> str:
        """Extract place type from raw provider data."""
        # Try Geoapify format
        if "properties" in raw_data:
            props = raw_data["properties"]
            return props.get("category", props.get("type", "")).lower()

        # Try Nominatim/OSM format
        if "type" in raw_data:
            return raw_data["type"].lower()

        if "class" in raw_data:
            return raw_data["class"].lower()

        # Try Overpass format
        tags = raw_data.get("tags", {})
        if "amenity" in tags:
            return tags["amenity"].lower()
        if "building" in tags:
            return tags["building"].lower()
        if "landuse" in tags:
            return tags["landuse"].lower()

        return ""
