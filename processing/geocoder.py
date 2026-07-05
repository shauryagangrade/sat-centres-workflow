"""
SAT Centre Updater - Geocoder Module

Main geocoding orchestrator that ties together providers, scorer, query generator, and cache.
Iterates through centres, generates queries, geocodes candidates, scores them, and picks the best match.

Usage:
    from processing.geocoder import CentreGeocoder
    from processing.normalizer import SatCentre

    geocoder = CentreGeocoder()
    geocoded = geocoder.geocode_all(centres)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cache.cache_manager import CacheManager
from processing.normalizer import SatCentre
from processing.query_generator import QueryGenerator
from processing.scorer import CandidateScorer, GeocodeCandidate, ScoredCandidate
from providers.provider_manager import ProviderManager

logger = logging.getLogger(__name__)


@dataclass
class GeocodeResult:
    """Result of geocoding a single centre."""

    centre: SatCentre
    geocoded: bool = False
    best_match: Optional[ScoredCandidate] = None
    all_candidates: List[GeocodeCandidate] = field(default_factory=list)
    queries_tried: List[str] = field(default_factory=list)
    provider_used: str = ""
    error: Optional[str] = None


class CentreGeocoder:
    """
    Orchestrates the geocoding pipeline for SAT centres.

    Steps:
    1. Check if centre already has coordinates and is cached
    2. Generate multiple search queries
    3. Try each query against the provider chain
    4. Score all candidates
    5. Pick the best match if above confidence threshold
    6. Update the centre with geocoded coordinates
    """

    def __init__(
        self,
        cache: Optional[CacheManager] = None,
        force: bool = False,
    ) -> None:
        """
        Initialize the geocoder.

        Args:
            cache: Optional CacheManager instance.
            force: If True, re-geocode centres that already have coordinates.
        """
        self.cache = cache or CacheManager()
        self.query_generator = QueryGenerator()
        self.scorer = CandidateScorer()
        self.provider_manager = ProviderManager(cache=self.cache)
        self.force = force

        # Stats
        self._total = 0
        self._geocoded = 0
        self._cached = 0
        self._failed = 0

    def geocode_all(self, centres: List[SatCentre]) -> List[GeocodeResult]:
        """
        Geocode a list of centres.

        Args:
            centres: List of SatCentre objects (may have existing coordinates).

        Returns:
            List of GeocodeResult objects.
        """
        self._total = len(centres)
        self._geocoded = 0
        self._cached = 0
        self._failed = 0

        results: List[GeocodeResult] = []
        for i, centre in enumerate(centres):
            logger.info(f"Geocoding [{i + 1}/{self._total}] {centre.name}")
            result = self.geocode_single(centre)
            results.append(result)

            if result.geocoded:
                self._geocoded += 1
            elif result.error and "cached" in str(result.error):
                self._cached += 1
            else:
                self._failed += 1

        return results

    def geocode_single(self, centre: SatCentre) -> GeocodeResult:
        """
        Geocode a single centre.

        Args:
            centre: SatCentre to geocode.

        Returns:
            GeocodeResult with geocoding outcome.
        """
        result = GeocodeResult(centre=centre)

        # Skip if already geocoded (unless force)
        if (
            not self.force
            and centre.latitude is not None
            and centre.longitude is not None
        ):
            result.geocoded = False
            result.error = "cached: already has coordinates"
            return result

        # Generate queries
        queries = self.query_generator.generate(centre)
        result.queries_tried = queries

        if not queries:
            result.error = "no_queries_generated"
            return result

        # Try each query
        all_candidates: List[GeocodeCandidate] = []
        for query in queries:
            candidates = self.provider_manager.geocode(query, limit=5)
            all_candidates.extend(candidates)

            if candidates:
                break  # Stop at first successful query

        if not all_candidates:
            result.error = "no_candidates_found"
            return result

        result.all_candidates = all_candidates

        # Build reference for scoring
        reference = {
            "name": centre.name,
            "address": centre.address,
            "city": centre.city,
            "state": centre.state,
            "country": centre.country,
        }

        # Score and pick best
        best = self.scorer.best_candidate(reference, all_candidates)

        if best is None:
            result.error = "below_confidence_threshold"
            return result

        result.best_match = best
        result.provider_used = best.candidate.provider
        result.geocoded = True

        # Update centre coordinates
        centre.latitude = best.candidate.latitude
        centre.longitude = best.candidate.longitude
        centre.metadata["confidence"] = best.score
        centre.metadata["geocode_provider"] = best.candidate.provider
        centre.metadata["geocode_breakdown"] = best.breakdown

        return result

    @property
    def stats(self) -> Dict[str, int]:
        """Get geocoding statistics."""
        return {
            "total": self._total,
            "geocoded": self._geocoded,
            "cached": self._cached,
            "failed": self._failed,
            "cache_hits": self.provider_manager.cache_hits,
            "provider_usage": self.provider_manager.stats,
        }

    def close(self) -> None:
        """Close all provider sessions."""
        self.provider_manager.close()
