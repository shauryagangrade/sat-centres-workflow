"""
Evidence fusion engine.

Combines independent evidence signals into a unified assessment.
Uses weighted aggregation with configurable importance weights.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from verification.models import CandidateEvidence


# Default weights for each evidence category
DEFAULT_CATEGORY_WEIGHTS: Dict[str, float] = {
    "text": 0.30,
    "geography": 0.25,
    "provider": 0.20,
    "place_type": 0.15,
    "historical": 0.10,
}


@dataclass
class FusionScore:
    """Result of fusing evidence for a single candidate."""

    total_score: float = 0.0
    category_scores: Dict[str, float] = field(default_factory=dict)
    positive_count: int = 0
    negative_count: int = 0
    evidence_strength: float = 0.0  # How much evidence we have (0-1)

    def to_dict(self) -> Dict:
        return {
            "total_score": self.total_score,
            "category_scores": self.category_scores,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "evidence_strength": self.evidence_strength,
        }


class EvidenceFusion:
    """
    Fuses multiple evidence categories into a unified score.

    Each evidence category contributes a score weighted by its importance.
    The fusion considers both the scores and the strength of available evidence.
    """

    def __init__(
        self, category_weights: Optional[Dict[str, float]] = None
    ) -> None:
        """
        Initialize the fusion engine.

        Args:
            category_weights: Custom weights for evidence categories.
        """
        self.weights = category_weights or DEFAULT_CATEGORY_WEIGHTS.copy()
        # Normalize weights to sum to 1.0
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    def fuse(self, evidence: CandidateEvidence) -> FusionScore:
        """
        Fuse all evidence for a candidate into a single score.

        Args:
            evidence: Complete evidence bundle for a candidate.

        Returns:
            FusionScore with total score and breakdown.
        """
        result = FusionScore()

        # Score each category
        result.category_scores["text"] = self._score_text(evidence)
        result.category_scores["geography"] = self._score_geography(evidence)
        result.category_scores["provider"] = self._score_provider(evidence)
        result.category_scores["place_type"] = self._score_place_type(evidence)
        result.category_scores["historical"] = self._score_historical(evidence)

        # Weighted total
        total = 0.0
        categories_with_data = 0
        for cat, weight in self.weights.items():
            score = result.category_scores.get(cat, 0.0)
            total += score * weight
            if score > 0:
                categories_with_data += 1

        result.total_score = round(total, 4)

        # Count positive and negative signals
        result.positive_count = len(evidence.positive_signals())
        result.negative_count = len(evidence.negative_signals())

        # Evidence strength: how many categories contributed
        result.evidence_strength = (
            categories_with_data / len(self.weights) if self.weights else 0.0
        )

        return result

    def rank(
        self, candidates: List[CandidateEvidence]
    ) -> List[tuple]:
        """
        Rank candidates by fused score.

        Args:
            candidates: List of evidence bundles.

        Returns:
            List of (CandidateEvidence, FusionScore) tuples, sorted descending.
        """
        scored = [(c, self.fuse(c)) for c in candidates]
        scored.sort(key=lambda x: x[1].total_score, reverse=True)
        return scored

    def _score_text(self, evidence: CandidateEvidence) -> float:
        """Score textual evidence (0.0-1.0)."""
        t = evidence.text
        # Weighted combination of text fields
        fields = {
            "name": 0.35,
            "city": 0.20,
            "country": 0.20,
            "state": 0.10,
            "address": 0.10,
            "postal": 0.05,
        }

        score = 0.0
        for field_name, weight in fields.items():
            value = getattr(t, f"{field_name}_similarity", 0.0)
            score += value * weight

        # Bonus for alias/transliteration detection
        if t.alias_detected:
            score = min(1.0, score + 0.05)
        if t.transliteration_match:
            score = min(1.0, score + 0.03)

        return score

    def _score_geography(self, evidence: CandidateEvidence) -> float:
        """Score geographic evidence (0.0-1.0)."""
        g = evidence.geography
        score = 0.0

        # On land is fundamental
        if not g.on_land:
            return 0.0

        # Distance from city center (closer = better)
        if g.distance_from_city_center is not None:
            if g.distance_from_city_center <= 1.0:
                score += 0.30
            elif g.distance_from_city_center <= 5.0:
                score += 0.25
            elif g.distance_from_city_center <= 20.0:
                score += 0.15
            elif g.distance_from_city_center <= 50.0:
                score += 0.05
            # > 50km adds nothing

        # Reverse geocode match
        if g.reverse_geocode_match:
            score += 0.25

        # Admin hierarchy valid
        if g.admin_hierarchy_valid:
            score += 0.15

        # Urban area
        if g.urban_area:
            score += 0.05

        # Nearby educational
        if g.nearby_educational:
            score += 0.10

        # Nearby roads
        if g.nearby_roads:
            score += 0.05

        # Coordinate precision
        score += g.coordinate_precision * 0.10

        return min(1.0, score)

    def _score_provider(self, evidence: CandidateEvidence) -> float:
        """Score provider consensus evidence (0.0-1.0)."""
        p = evidence.provider_evidence

        if p.providers_total == 0:
            return 0.0

        # Base score from consensus ratio
        score = p.consensus_ratio * 0.6

        # Bonus for multiple providers agreeing
        if p.providers_agreeing >= 3:
            score += 0.3
        elif p.providers_agreeing >= 2:
            score += 0.2
        elif p.providers_agreeing >= 1:
            score += 0.1

        # Provider weight contribution
        if p.provider_weights:
            avg_weight = sum(p.provider_weights.values()) / len(p.provider_weights)
            score += avg_weight * 0.1

        # Penalty for disagreement
        if p.disagreement:
            score *= 0.5

        # Penalty for high coordinate variance
        if p.coordinate_variance > 0.1:  # ~11km variance
            score *= 0.7
        elif p.coordinate_variance > 0.01:  # ~1.1km variance
            score *= 0.9

        return min(1.0, score)

    def _score_place_type(self, evidence: CandidateEvidence) -> float:
        """Score place type evidence (0.0-1.0)."""
        pt = evidence.place_type

        if pt.is_negative_type:
            return 0.0

        if pt.is_educational:
            return pt.confidence

        # Unknown type gets a neutral score
        return 0.3

    def _score_historical(self, evidence: CandidateEvidence) -> float:
        """Score historical evidence (0.0-1.0)."""
        h = evidence.historical

        if not h.has_previous_data:
            # No historical data = neutral
            return 0.5

        score = 0.0

        # Matches previous location
        if h.matches_previous:
            score += 0.5

        # Distance from previous
        if h.distance_from_previous is not None:
            if h.distance_from_previous <= 1.0:
                score += 0.3
            elif h.distance_from_previous <= 5.0:
                score += 0.2
            elif h.distance_from_previous <= 20.0:
                score += 0.1
            elif h.distance_from_previous > LARGE_MOVEMENT_THRESHOLD_KM:
                score -= 0.2

        # Name/address changes reduce score
        if h.name_changed:
            score -= 0.1
        if h.address_changed:
            score -= 0.05

        # Large movement penalty
        if h.large_movement:
            score -= 0.3

        return max(0.0, min(1.0, score))


# Import constant from history module
from verification.evidence.history import LARGE_MOVEMENT_THRESHOLD_KM
