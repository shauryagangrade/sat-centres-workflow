"""
SAT Centre Updater - Candidate Scorer Module

Scores geocoding candidates using RapidFuzz fuzzy string matching.
Selects the best match based on weighted fields: name, address, city, state, country, provider confidence, distance.

Usage:
    from processing.scorer import CandidateScorer
    from processing.normalizer import SatCentre

    scorer = CandidateScorer()
    best = scorer.best_candidate(centre, candidates)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

from config import settings


@dataclass
class GeocodeCandidate:
    """A single geocoding candidate returned by a provider."""

    name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    confidence: float = 0.0
    provider: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoredCandidate:
    """A candidate with its computed score."""

    candidate: GeocodeCandidate
    score: float = 0.0
    breakdown: Dict[str, float] = field(default_factory=dict)


# Weighted field importance
DEFAULT_WEIGHTS: Dict[str, float] = {
    "name": 0.25,
    "address": 0.10,
    "city": 0.20,
    "state": 0.10,
    "country": 0.20,
    "confidence": 0.10,
    "distance_penalty": 0.05,
}


class CandidateScorer:
    """
    Scores geocoding candidates against a reference SatCentre.

    Uses RapidFuzz's token_set_ratio and partial_ratio for fuzzy matching,
    combined with provider confidence and optional distance penalty.
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None) -> None:
        """
        Initialize the scorer.

        Args:
            weights: Optional custom weights dictionary.
        """
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.confidence_threshold = settings.GEOCODING.CONFIDENCE_THRESHOLD

    def score(self, reference: Dict[str, str], candidate: GeocodeCandidate) -> ScoredCandidate:
        """
        Score a single candidate against a reference dictionary.

        Args:
            reference: Dictionary with keys: name, address, city, state, country.
            candidate: The geocode candidate to score.

        Returns:
            ScoredCandidate with score and breakdown.
        """
        breakdown: Dict[str, float] = {}

        # Name match
        ref_name = reference.get("name", "")
        breakdown["name"] = self._fuzzy_score(ref_name, candidate.name) / 100.0

        # Address match
        ref_addr = reference.get("address", "")
        breakdown["address"] = self._fuzzy_score(ref_addr, candidate.address) / 100.0

        # City match
        ref_city = reference.get("city", "")
        breakdown["city"] = self._fuzzy_score(ref_city, candidate.city) / 100.0

        # State match
        ref_state = reference.get("state", "")
        breakdown["state"] = self._fuzzy_score(ref_state, candidate.state) / 100.0

        # Country match (exact match is critical)
        ref_country = reference.get("country", "")
        country_score = self._exact_or_close_score(ref_country, candidate.country)
        breakdown["country"] = country_score

        # Provider confidence
        breakdown["confidence"] = candidate.confidence

        # Distance penalty (if available in raw data)
        distance = candidate.raw.get("distance_km", 0.0)
        breakdown["distance_penalty"] = max(0.0, 1.0 - min(distance / 100.0, 1.0))

        # Weighted sum
        total = 0.0
        for field_name, weight in self.weights.items():
            total += breakdown.get(field_name, 0.0) * weight

        return ScoredCandidate(
            candidate=candidate,
            score=round(total, 4),
            breakdown=breakdown,
        )

    def best_candidate(
        self, reference: Dict[str, str], candidates: List[GeocodeCandidate]
    ) -> Optional[ScoredCandidate]:
        """
        Find the best matching candidate from a list.

        Args:
            reference: Dictionary with keys: name, address, city, state, country.
            candidates: List of geocode candidates.

        Returns:
            Best ScoredCandidate or None if no candidates or none meets threshold.
        """
        if not candidates:
            return None

        scored = [self.score(reference, c) for c in candidates]
        scored.sort(key=lambda s: s.score, reverse=True)

        best = scored[0]
        if best.score < self.confidence_threshold:
            return None

        return best

    def rank_candidates(
        self, reference: Dict[str, str], candidates: List[GeocodeCandidate]
    ) -> List[ScoredCandidate]:
        """
        Rank all candidates by score (highest first).

        Args:
            reference: Dictionary with keys: name, address, city, state, country.
            candidates: List of geocode candidates.

        Returns:
            List of ScoredCandidate objects sorted by score descending.
        """
        scored = [self.score(reference, c) for c in candidates]
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored

    def _fuzzy_score(self, query: str, target: str) -> float:
        """
        Compute a fuzzy match score between two strings.

        Uses token_set_ratio for better handling of word order differences.

        Args:
            query: Reference string.
            target: Candidate string.

        Returns:
            Score between 0 and 100.
        """
        if not query or not target:
            return 0.0

        # Use token_set_ratio which handles word reordering well
        return fuzz.token_set_ratio(query.lower(), target.lower())

    def _exact_or_close_score(self, query: str, target: str) -> float:
        """
        Score country match with tolerance for common variations.

        Args:
            query: Reference country name.
            target: Candidate country name.

        Returns:
            Score between 0.0 and 1.0.
        """
        if not query or not target:
            return 0.0

        q = query.strip().lower()
        t = target.strip().lower()

        # Exact match
        if q == t:
            return 1.0

        # Common country name mappings
        aliases = {
            "india": ["in", "republic of india", "bharat"],
            "us": ["usa", "united states", "united states of america", "u.s.", "u.s.a.", "us"],
            "usa": ["us", "united states", "united states of america", "u.s.", "u.s.a.", "us"],
            "uk": ["united kingdom", "gb", "great britain", "u.k.", "england"],
            "canada": ["ca", "dominion of canada"],
            "uae": ["united arab emirates", "ae", "dubai", "abu dhabi"],
            "singapore": ["sg", "republic of singapore"],
        }

        for canonical, variants in aliases.items():
            all_forms = [canonical] + variants
            if q in all_forms and t in all_forms:
                return 1.0

        # Fuzzy fallback — clearly different countries score 0
        score = fuzz.ratio(q, t)
        if score < 50:
            return 0.0
        return score / 100.0
