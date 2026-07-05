"""
SAT Centre Updater - Geocoder Module (Evidence-Based Pipeline)

Orchestrates the full pipeline:
    Normalization -> Candidate Retrieval -> Evidence Verification -> Decision -> Output

Uses the evidence-based verification system instead of simple fuzzy scoring.
Each candidate accumulates independent evidence signals.
The final confidence emerges from the combination of evidence.

Usage:
    from processing.geocoder import CentreGeocoder
    from processing.normalizer import SatCentre

    geocoder = CentreGeocoder()
    geocoded = geocoder.geocode_all(centres)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from cache.cache_manager import CacheManager
from processing.normalizer import SatCentre
from processing.query_generator import QueryGenerator
from providers.provider_manager import ProviderManager
from verification.confidence import ConfidenceCalculator, ConfidenceResult
from verification.decision_engine import Decision, DecisionEngine, VerificationState
from verification.fusion import EvidenceFusion, FusionScore
from verification.models import CandidateEvidence, VerificationResult
from verification.report import AuditEntry, AuditReport, AuditReportGenerator
from verification.verifier import LocationVerifier

logger = logging.getLogger(__name__)


@dataclass
class GeocodeResult:
    """Result of geocoding a single centre."""

    centre: SatCentre
    geocoded: bool = False
    best_candidate: Optional[CandidateEvidence] = None
    best_decision: Optional[Decision] = None
    verification_result: Optional[VerificationResult] = None
    audit_entries: List[AuditEntry] = field(default_factory=list)
    all_candidates: List[CandidateEvidence] = field(default_factory=list)
    queries_tried: List[str] = field(default_factory=list)
    provider_used: str = ""
    error: Optional[str] = None


class CentreGeocoder:
    """
    Orchestrates the evidence-based geocoding pipeline.

    Pipeline stages:
    1. Check if centre already has coordinates (skip unless force)
    2. Generate multiple search queries
    3. Query ALL providers for candidate retrieval
    4. Collect independent evidence for each candidate
    5. Fuse evidence into unified scores
    6. Calculate calibrated confidence
    7. Decision engine classifies and selects best
    8. Update centre with geocoded coordinates
    9. Generate audit trail
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
        self.provider_manager = ProviderManager(cache=self.cache)
        self.force = force

        # Evidence-based verification components
        self.verifier = LocationVerifier()
        self.decision_engine = DecisionEngine()
        self.fusion = EvidenceFusion()
        self.confidence_calc = ConfidenceCalculator()
        self.report_generator = AuditReportGenerator()

        # Stats
        self._total = 0
        self._geocoded = 0
        self._cached = 0
        self._failed = 0
        self._needs_review = 0

    def geocode_all(self, centres: List[SatCentre]) -> List[GeocodeResult]:
        """
        Geocode a list of centres using the evidence-based pipeline.

        Args:
            centres: List of SatCentre objects (may have existing coordinates).

        Returns:
            List of GeocodeResult objects.
        """
        self._total = len(centres)
        self._geocoded = 0
        self._cached = 0
        self._failed = 0
        self._needs_review = 0

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
        Geocode a single centre through the full evidence-based pipeline.

        Args:
            centre: SatCentre to geocode.

        Returns:
            GeocodeResult with full verification evidence.
        """
        result = GeocodeResult(centre=centre)

        # Skip if already geocoded (unless force)
        if (
            not self.force
            and centre.latitude is not None
            and centre.longitude is not None
        ):
            result.error = "cached: already has coordinates"
            return result

        # Stage 1: Generate queries
        queries = self.query_generator.generate(centre)
        result.queries_tried = queries

        if not queries:
            result.error = "no_queries_generated"
            return result

        # Stage 2: Retrieve candidates from ALL providers
        provider_results: Dict[str, List[Dict[str, Any]]] = {}
        all_candidate_dicts: List[Dict[str, Any]] = []

        for query in queries:
            provider_raw = self.provider_manager.geocode_all_providers(
                query, limit=5
            )
            for provider_name, candidates in provider_raw.items():
                if provider_name not in provider_results:
                    provider_results[provider_name] = []
                for c in candidates:
                    cand_dict = {
                        "name": c.name,
                        "address": c.address,
                        "city": c.city,
                        "state": c.state,
                        "country": c.country,
                        "latitude": c.latitude,
                        "longitude": c.longitude,
                        "confidence": c.confidence,
                        "provider": c.provider,
                        "raw": c.raw,
                    }
                    provider_results[provider_name].append(cand_dict)
                    all_candidate_dicts.append(cand_dict)

            if all_candidate_dicts:
                break  # Stop at first query that yields results

        if not all_candidate_dicts:
            result.error = "no_candidates_found"
            return result

        # Stage 3: Evidence-based verification
        reference = {
            "id": centre.id,
            "name": centre.name,
            "address": centre.address,
            "city": centre.city,
            "state": centre.state,
            "country": centre.country,
            "postal_code": centre.postal_code,
        }

        # Build previous data from existing metadata
        previous_data = None
        if centre.metadata.get("latitude") is not None:
            previous_data = {
                "latitude": centre.metadata.get("latitude"),
                "longitude": centre.metadata.get("longitude"),
                "name": centre.metadata.get("name", centre.name),
                "address": centre.metadata.get("address", centre.address),
            }

        verification = self.verifier.verify(
            reference=reference,
            candidates=all_candidate_dicts,
            provider_results=provider_results,
            previous_data=previous_data,
        )

        result.verification_result = verification
        result.all_candidates = verification.candidates

        # Stage 4: Decision engine
        decision_result = self.decision_engine.decide(
            evidence_list=verification.candidates,
            reference_id=centre.id,
            reference_name=centre.name,
        )

        if decision_result.best_candidate is None:
            result.error = "below_confidence_threshold"
            return result

        result.best_candidate = decision_result.best_candidate
        result.best_decision = decision_result.best_decision
        result.provider_used = decision_result.best_candidate.provider

        # Stage 5: Generate audit report
        for evidence, decision in decision_result.all_decisions:
            fusion_score = self.fusion.fuse(evidence)
            confidence = self.confidence_calc.calculate(fusion_score, evidence)
            entry = self.report_generator.generate_for_candidate(
                evidence, fusion_score, confidence, decision.state.value
            )
            result.audit_entries.append(entry)

        # Stage 6: Update centre with best match
        best = decision_result.best_candidate
        result.geocoded = True

        centre.latitude = best.latitude
        centre.longitude = best.longitude
        centre.metadata["confidence"] = (
            decision_result.best_decision.confidence
            if decision_result.best_decision
            else 0.0
        )
        centre.metadata["verification_state"] = (
            decision_result.selected_state.value
            if decision_result.selected_state
            else "unknown"
        )
        centre.metadata["geocode_provider"] = best.provider
        centre.metadata["evidence_summary"] = {
            "positive_signals": best.positive_signals(),
            "negative_signals": best.negative_signals(),
            "provider": best.provider,
        }

        return result

    @property
    def stats(self) -> Dict[str, Any]:
        """Get geocoding statistics."""
        return {
            "total": self._total,
            "geocoded": self._geocoded,
            "cached": self._cached,
            "failed": self._failed,
            "needs_review": self._needs_review,
            "cache_hits": self.provider_manager.cache_hits,
            "provider_usage": self.provider_manager.stats,
        }

    def close(self) -> None:
        """Close all provider sessions."""
        self.provider_manager.close()
