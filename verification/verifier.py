"""
Location verifier - main orchestrator.

Coordinates all evidence collectors and produces structured evidence
for each candidate. This is the primary entry point for verification.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from verification.evidence.geography import GeographyEvidenceCollector
from verification.evidence.history import HistoricalEvidenceCollector
from verification.evidence.place_type import PlaceTypeEvidenceCollector
from verification.evidence.providers import ProviderEvidenceCollector
from verification.evidence.text import TextEvidenceCollector
from verification.models import CandidateEvidence, VerificationResult

logger = logging.getLogger(__name__)


class LocationVerifier:
    """
    Main verification orchestrator.

    For every candidate, collects independent pieces of evidence
    from multiple collectors. The verification stage never returns
    a single score — it produces structured evidence.

    Usage:
        verifier = LocationVerifier()
        result = verifier.verify(reference, candidates, provider_results)
    """

    def __init__(self) -> None:
        """Initialize all evidence collectors."""
        self.text_collector = TextEvidenceCollector()
        self.geography_collector = GeographyEvidenceCollector()
        self.provider_collector = ProviderEvidenceCollector()
        self.place_type_collector = PlaceTypeEvidenceCollector()
        self.history_collector = HistoricalEvidenceCollector()

    def verify(
        self,
        reference: Dict[str, str],
        candidates: List[Dict[str, Any]],
        provider_results: Optional[Dict[str, List[Dict]]] = None,
        previous_data: Optional[Dict] = None,
    ) -> VerificationResult:
        """
        Verify all candidates for a reference location.

        Args:
            reference: Reference location data (name, address, city, state, country).
            candidates: List of candidate dicts from geocoding providers.
            provider_results: Dict mapping provider name to its candidate list.
            previous_data: Optional historical data for this location.

        Returns:
            VerificationResult with evidence for all candidates.
        """
        result = VerificationResult(
            reference_id=reference.get("id", ""),
            reference_name=reference.get("name", ""),
        )

        for i, candidate in enumerate(candidates):
            candidate_id = candidate.get(
                "id", f"candidate_{i}_{candidate.get('provider', 'unknown')}"
            )

            evidence = self._collect_evidence(
                reference=reference,
                candidate=candidate,
                candidate_id=candidate_id,
                all_candidates=candidates,
                provider_results=provider_results,
                previous_data=previous_data,
            )

            result.candidates.append(evidence)

        # Determine best candidate based on evidence strength
        if result.candidates:
            best = max(
                result.candidates,
                key=lambda c: len(c.positive_signals()) - len(c.negative_signals()),
            )
            result.best_candidate_id = best.candidate_id

        return result

    def _collect_evidence(
        self,
        reference: Dict[str, str],
        candidate: Dict[str, Any],
        candidate_id: str,
        all_candidates: List[Dict],
        provider_results: Optional[Dict[str, List[Dict]]],
        previous_data: Optional[Dict],
    ) -> CandidateEvidence:
        """
        Collect all evidence for a single candidate.

        Runs each evidence collector independently.
        If a collector fails, it's recorded in skipped_collectors.
        """
        evidence = CandidateEvidence(
            candidate_id=candidate_id,
            provider=candidate.get("provider", "unknown"),
            latitude=candidate.get("latitude", 0.0),
            longitude=candidate.get("longitude", 0.0),
        )

        # 1. Textual evidence
        try:
            evidence.text = self.text_collector.collect(
                reference=reference,
                candidate_name=candidate.get("name", ""),
                candidate_address=candidate.get("address", ""),
                candidate_city=candidate.get("city", ""),
                candidate_state=candidate.get("state", ""),
                candidate_country=candidate.get("country", ""),
                candidate_postal=candidate.get("postal_code", ""),
                candidate_street=candidate.get("street", ""),
            )
        except Exception as e:
            logger.warning(f"Text evidence collection failed: {e}")
            evidence.skipped_collectors.append("text")

        # 2. Geographic evidence
        try:
            reverse_data = candidate.get("raw", {})
            evidence.geography = self.geography_collector.collect(
                reference=reference,
                candidate_lat=evidence.latitude,
                candidate_lon=evidence.longitude,
                reverse_geocode_data=reverse_data,
                previous_coords=(
                    (previous_data["latitude"], previous_data["longitude"])
                    if previous_data
                    and previous_data.get("latitude") is not None
                    and previous_data.get("longitude") is not None
                    else None
                ),
            )
        except Exception as e:
            logger.warning(f"Geography evidence collection failed: {e}")
            evidence.skipped_collectors.append("geography")

        # 3. Provider consensus evidence
        try:
            evidence.provider_evidence = self.provider_collector.collect(
                candidate_provider=evidence.provider,
                all_candidates=all_candidates,
                provider_results=provider_results,
            )
        except Exception as e:
            logger.warning(f"Provider evidence collection failed: {e}")
            evidence.skipped_collectors.append("provider")

        # 4. Place type evidence
        try:
            evidence.place_type = self.place_type_collector.collect(
                candidate_name=candidate.get("name", ""),
                candidate_address=candidate.get("address", ""),
                raw_data=candidate.get("raw"),
            )
        except Exception as e:
            logger.warning(f"Place type evidence collection failed: {e}")
            evidence.skipped_collectors.append("place_type")

        # 5. Historical evidence
        try:
            evidence.historical = self.history_collector.collect(
                candidate_lat=evidence.latitude,
                candidate_lon=evidence.longitude,
                candidate_name=candidate.get("name", ""),
                candidate_address=candidate.get("address", ""),
                previous_data=previous_data,
            )
        except Exception as e:
            logger.warning(f"Historical evidence collection failed: {e}")
            evidence.skipped_collectors.append("history")

        return evidence
