"""
Verification data models.

Defines structured evidence output, candidate representation,
and verification results used across the pipeline.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TextEvidence:
    """Textual similarity evidence for a candidate."""

    name_similarity: float = 0.0
    address_similarity: float = 0.0
    city_similarity: float = 0.0
    state_similarity: float = 0.0
    country_similarity: float = 0.0
    postal_similarity: float = 0.0
    street_similarity: float = 0.0
    admin_area_similarity: float = 0.0
    alias_detected: bool = False
    transliteration_match: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name_similarity": self.name_similarity,
            "address_similarity": self.address_similarity,
            "city_similarity": self.city_similarity,
            "state_similarity": self.state_similarity,
            "country_similarity": self.country_similarity,
            "postal_similarity": self.postal_similarity,
            "street_similarity": self.street_similarity,
            "admin_area_similarity": self.admin_area_similarity,
            "alias_detected": self.alias_detected,
            "transliteration_match": self.transliteration_match,
        }


@dataclass
class GeographyEvidence:
    """Geographic evidence for a candidate."""

    distance_from_city_center: Optional[float] = None
    distance_from_admin_boundary: Optional[float] = None
    distance_from_previous: Optional[float] = None
    reverse_geocode_match: bool = False
    admin_hierarchy_valid: bool = False
    coordinate_precision: float = 0.0
    on_land: bool = True
    urban_area: Optional[bool] = None
    nearby_roads: bool = False
    nearby_educational: bool = False
    nearby_landmarks: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "distance_from_city_center": self.distance_from_city_center,
            "distance_from_admin_boundary": self.distance_from_admin_boundary,
            "distance_from_previous": self.distance_from_previous,
            "reverse_geocode_match": self.reverse_geocode_match,
            "admin_hierarchy_valid": self.admin_hierarchy_valid,
            "coordinate_precision": self.coordinate_precision,
            "on_land": self.on_land,
            "urban_area": self.urban_area,
            "nearby_roads": self.nearby_roads,
            "nearby_educational": self.nearby_educational,
            "nearby_landmarks": self.nearby_landmarks,
        }


@dataclass
class ProviderEvidence:
    """Provider consensus evidence for a candidate."""

    providers_agreeing: int = 0
    providers_total: int = 0
    consensus_ratio: float = 0.0
    coordinate_variance: float = 0.0
    provider_weights: Dict[str, float] = field(default_factory=dict)
    disagreement: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "providers_agreeing": self.providers_agreeing,
            "providers_total": self.providers_total,
            "consensus_ratio": self.consensus_ratio,
            "coordinate_variance": self.coordinate_variance,
            "provider_weights": self.provider_weights,
            "disagreement": self.disagreement,
        }


@dataclass
class PlaceTypeEvidence:
    """Place type evidence for a candidate."""

    category: str = "unknown"
    confidence: float = 0.0
    is_educational: bool = False
    is_negative_type: bool = False
    negative_type_detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "confidence": self.confidence,
            "is_educational": self.is_educational,
            "is_negative_type": self.is_negative_type,
            "negative_type_detail": self.negative_type_detail,
        }


@dataclass
class HistoricalEvidence:
    """Historical evidence for a candidate."""

    has_previous_data: bool = False
    matches_previous: bool = False
    distance_from_previous: Optional[float] = None
    address_changed: bool = False
    name_changed: bool = False
    large_movement: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_previous_data": self.has_previous_data,
            "matches_previous": self.matches_previous,
            "distance_from_previous": self.distance_from_previous,
            "address_changed": self.address_changed,
            "name_changed": self.name_changed,
            "large_movement": self.large_movement,
        }


@dataclass
class CandidateEvidence:
    """
    Complete evidence bundle for a single candidate.

    Aggregates all evidence types collected during verification.
    This is the primary output of the verification stage.
    """

    candidate_id: str = ""
    provider: str = ""
    latitude: float = 0.0
    longitude: float = 0.0

    text: TextEvidence = field(default_factory=TextEvidence)
    geography: GeographyEvidence = field(default_factory=GeographyEvidence)
    provider_evidence: ProviderEvidence = field(default_factory=ProviderEvidence)
    place_type: PlaceTypeEvidence = field(default_factory=PlaceTypeEvidence)
    historical: HistoricalEvidence = field(default_factory=HistoricalEvidence)

    # Collectors that failed or were skipped
    skipped_collectors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "provider": self.provider,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "text": self.text.to_dict(),
            "geography": self.geography.to_dict(),
            "provider_evidence": self.provider_evidence.to_dict(),
            "place_type": self.place_type.to_dict(),
            "historical": self.historical.to_dict(),
            "skipped_collectors": self.skipped_collectors,
        }

    def positive_signals(self) -> List[str]:
        """Return human-readable list of positive evidence signals."""
        signals: List[str] = []

        if self.text.name_similarity >= 0.8:
            signals.append(f"Name similarity: {self.text.name_similarity:.0%}")
        if self.text.city_similarity >= 0.8:
            signals.append("City matched")
        if self.text.country_similarity >= 0.9:
            signals.append("Country matched")
        if self.text.state_similarity >= 0.8:
            signals.append("State matched")
        if self.geography.reverse_geocode_match:
            signals.append("Reverse geocode matched")
        if self.geography.on_land:
            signals.append("On land")
        if self.geography.nearby_educational:
            signals.append("Nearby educational institutions")
        if self.provider_evidence.providers_agreeing >= 2:
            signals.append(
                f"{self.provider_evidence.providers_agreeing} providers agreed"
            )
        if self.place_type.is_educational:
            signals.append(f"Educational institution ({self.place_type.category})")
        if self.historical.matches_previous:
            signals.append("Historical location matched")
        if (
            self.historical.distance_from_previous is not None
            and self.historical.distance_from_previous < 1.0
        ):
            signals.append(
                f"{self.historical.distance_from_previous * 1000:.0f}m from previous location"
            )

        return signals

    def negative_signals(self) -> List[str]:
        """Return human-readable list of negative evidence signals."""
        signals: List[str] = []

        if self.text.name_similarity < 0.4:
            signals.append(f"Low name similarity: {self.text.name_similarity:.0%}")
        if self.text.country_similarity < 0.5:
            signals.append("Country mismatch")
        if self.text.city_similarity < 0.5:
            signals.append("City mismatch")
        if not self.geography.on_land:
            signals.append("Coordinates in ocean")
        if self.geography.reverse_geocode_match is False and self.geography.distance_from_city_center is not None and self.geography.distance_from_city_center > 50:
            signals.append(
                f"{self.geography.distance_from_city_center:.0f} km from expected city"
            )
        if self.provider_evidence.disagreement:
            signals.append("Provider disagreement")
        if self.place_type.is_negative_type:
            signals.append(f"Inappropriate place type: {self.place_type.negative_type_detail}")
        if self.historical.large_movement:
            signals.append("Large unexpected movement from previous location")
        if not self.text.alias_detected and self.text.name_similarity < 0.3:
            signals.append("No external evidence")

        return signals


@dataclass
class VerificationResult:
    """
    Result of verifying a single reference against multiple candidates.

    Contains all candidate evidence bundles for comparison
    by the DecisionEngine.
    """

    reference_id: str = ""
    reference_name: str = ""
    candidates: List[CandidateEvidence] = field(default_factory=list)
    best_candidate_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_id": self.reference_id,
            "reference_name": self.reference_name,
            "candidates": [c.to_dict() for c in self.candidates],
            "best_candidate_id": self.best_candidate_id,
        }
