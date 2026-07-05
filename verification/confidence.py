"""
Calibrated confidence calculator.

Converts raw fusion scores into calibrated confidence values
that reflect actual probability of correctness.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from verification.fusion import FusionScore
from verification.models import CandidateEvidence


@dataclass
class ConfidenceResult:
    """Calibrated confidence result for a candidate."""

    raw_score: float = 0.0
    calibrated_confidence: float = 0.0
    evidence_quality: float = 0.0
    uncertainty: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "raw_score": self.raw_score,
            "calibrated_confidence": self.calibrated_confidence,
            "evidence_quality": self.evidence_quality,
            "uncertainty": self.uncertainty,
        }


class ConfidenceCalculator:
    """
    Calculates calibrated confidence from fused evidence scores.

    Uses sigmoid-based calibration to map raw scores to probabilities.
    Accounts for evidence quality and quantity.
    """

    # Sigmoid parameters for calibration
    # Steepness: higher = sharper transition
    # Midpoint: the raw score at which confidence = 0.5
    SIGMOID_STEEPNESS: float = 10.0
    SIGMOID_MIDPOINT: float = 0.5

    def __init__(
        self,
        sigmoid_steepness: Optional[float] = None,
        sigmoid_midpoint: Optional[float] = None,
    ) -> None:
        """
        Initialize the confidence calculator.

        Args:
            sigmoid_steepness: Steepness of the sigmoid calibration curve.
            sigmoid_midpoint: Raw score at which confidence = 0.5.
        """
        self.steepness = sigmoid_steepness or self.SIGMOID_STEEPNESS
        self.midpoint = sigmoid_midpoint or self.SIGMOID_MIDPOINT

    def calculate(
        self,
        fusion_score: FusionScore,
        evidence: CandidateEvidence,
    ) -> ConfidenceResult:
        """
        Calculate calibrated confidence.

        Args:
            fusion_score: Fused evidence score.
            evidence: Original evidence bundle.

        Returns:
            ConfidenceResult with calibrated confidence.
        """
        result = ConfidenceResult()
        result.raw_score = fusion_score.total_score

        # Apply sigmoid calibration
        result.calibrated_confidence = self._sigmoid(fusion_score.total_score)

        # Evidence quality: based on how many categories contributed
        result.evidence_quality = fusion_score.evidence_strength

        # Uncertainty: higher when evidence is sparse or contradictory
        result.uncertainty = self._calculate_uncertainty(fusion_score, evidence)

        # Adjust confidence based on uncertainty
        # More uncertainty = confidence pulled toward 0.5
        uncertainty_penalty = result.uncertainty * 0.3
        if result.calibrated_confidence > 0.5:
            result.calibrated_confidence -= uncertainty_penalty
        else:
            result.calibrated_confidence += uncertainty_penalty

        result.calibrated_confidence = max(
            0.0, min(1.0, result.calibrated_confidence)
        )

        return result

    def _sigmoid(self, x: float) -> float:
        """Apply sigmoid function for calibration."""
        import math

        z = self.steepness * (x - self.midpoint)
        # Clamp to prevent overflow
        z = max(-500, min(500, z))
        return 1.0 / (1.0 + math.exp(-z))

    def _calculate_uncertainty(
        self,
        fusion_score: FusionScore,
        evidence: CandidateEvidence,
    ) -> float:
        """
        Calculate uncertainty (0.0-1.0).

        High uncertainty when:
        - Few evidence categories available
        - Contradictory signals (many positive AND negative)
        - Low provider consensus
        """
        uncertainty = 0.0

        # Low evidence strength increases uncertainty
        uncertainty += (1.0 - fusion_score.evidence_strength) * 0.4

        # Contradictory signals increase uncertainty
        if fusion_score.positive_count > 0 and fusion_score.negative_count > 0:
            ratio = min(fusion_score.positive_count, fusion_score.negative_count) / max(
                fusion_score.positive_count, fusion_score.negative_count
            )
            uncertainty += ratio * 0.3

        # Low provider consensus increases uncertainty
        provider_score = fusion_score.category_scores.get("provider", 0.0)
        if provider_score < 0.3:
            uncertainty += 0.2

        # Historical disagreement increases uncertainty
        if evidence.historical.large_movement:
            uncertainty += 0.1

        return min(1.0, uncertainty)

    def batch_calculate(
        self,
        candidates: List[tuple],
    ) -> List[tuple]:
        """
        Calculate confidence for multiple candidates.

        Args:
            candidates: List of (CandidateEvidence, FusionScore) tuples.

        Returns:
            List of (CandidateEvidence, FusionScore, ConfidenceResult) tuples.
        """
        results = []
        for evidence, fusion_score in candidates:
            confidence = self.calculate(fusion_score, evidence)
            results.append((evidence, fusion_score, confidence))
        return results
