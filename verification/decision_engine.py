"""
Decision engine.

Consumes structured evidence and makes final accept/reject decisions.
Classifies candidates into states: Verified, Highly Likely, Likely,
Needs Review, Low Confidence, Rejected.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from verification.confidence import ConfidenceCalculator, ConfidenceResult
from verification.fusion import EvidenceFusion, FusionScore
from verification.models import CandidateEvidence, VerificationResult


class VerificationState(Enum):
    """Possible verification states for a candidate."""

    VERIFIED = "Verified"  # High confidence, strong evidence
    HIGHLY_LIKELY = "Highly Likely"  # Good confidence, solid evidence
    LIKELY = "Likely"  # Moderate confidence
    NEEDS_REVIEW = "Needs Review"  # Borderline, human review needed
    LOW_CONFIDENCE = "Low Confidence"  # Weak evidence
    REJECTED = "Rejected"  # Clear rejection or below minimum threshold


# Default thresholds for each state
DEFAULT_THRESHOLDS: Dict[VerificationState, float] = {
    VerificationState.VERIFIED: 0.85,
    VerificationState.HIGHLY_LIKELY: 0.70,
    VerificationState.LIKELY: 0.55,
    VerificationState.NEEDS_REVIEW: 0.40,
    VerificationState.LOW_CONFIDENCE: 0.25,
    VerificationState.REJECTED: 0.0,
}


@dataclass
class Decision:
    """Decision for a single candidate."""

    state: VerificationState = VerificationState.REJECTED
    confidence: float = 0.0
    raw_score: float = 0.0
    is_accepted: bool = False
    rejection_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "state": self.state.value,
            "confidence": self.confidence,
            "raw_score": self.raw_score,
            "is_accepted": self.is_accepted,
            "rejection_reasons": self.rejection_reasons,
        }


@dataclass
class VerificationDecision:
    """Complete decision result for a reference location."""

    reference_id: str = ""
    reference_name: str = ""
    best_candidate: Optional[CandidateEvidence] = None
    best_decision: Optional[Decision] = None
    all_decisions: List[Tuple[CandidateEvidence, Decision]] = field(
        default_factory=list
    )
    selected_state: Optional[VerificationState] = None

    def to_dict(self) -> Dict:
        return {
            "reference_id": self.reference_id,
            "reference_name": self.reference_name,
            "best_candidate": (
                self.best_candidate.to_dict() if self.best_candidate else None
            ),
            "best_decision": (
                self.best_decision.to_dict() if self.best_decision else None
            ),
            "all_decisions": [
                {"candidate": c.to_dict(), "decision": d.to_dict()}
                for c, d in self.all_decisions
            ],
            "selected_state": (
                self.selected_state.value if self.selected_state else None
            ),
        }


class DecisionEngine:
    """
    Makes final verification decisions based on fused evidence.

    Consumes structured evidence from the verification stage and
    classifies candidates into verification states.
    """

    def __init__(
        self,
        fusion: Optional[EvidenceFusion] = None,
        confidence_calc: Optional[ConfidenceCalculator] = None,
        thresholds: Optional[Dict[VerificationState, float]] = None,
    ) -> None:
        """
        Initialize the decision engine.

        Args:
            fusion: Evidence fusion engine.
            confidence_calc: Confidence calculator.
            thresholds: Custom state thresholds.
        """
        self.fusion = fusion or EvidenceFusion()
        self.confidence_calc = confidence_calc or ConfidenceCalculator()
        self.thresholds = thresholds or DEFAULT_THRESHOLDS.copy()

    def decide_single(
        self, evidence: CandidateEvidence
    ) -> Tuple[Decision, FusionScore, ConfidenceResult]:
        """
        Make a decision for a single candidate.

        Args:
            evidence: Evidence bundle for the candidate.

        Returns:
            Tuple of (Decision, FusionScore, ConfidenceResult).
        """
        # Fuse evidence
        fusion_score = self.fusion.fuse(evidence)

        # Calculate calibrated confidence
        confidence = self.confidence_calc.calculate(fusion_score, evidence)

        # Classify into state
        state = self._classify(confidence.calibrated_confidence)

        # Check for automatic rejection based on hard rules
        rejection_reasons = self._check_hard_rejections(evidence)
        if rejection_reasons:
            state = VerificationState.REJECTED

        decision = Decision(
            state=state,
            confidence=confidence.calibrated_confidence,
            raw_score=fusion_score.total_score,
            is_accepted=state not in (
                VerificationState.REJECTED,
                VerificationState.LOW_CONFIDENCE,
            ),
            rejection_reasons=rejection_reasons,
        )

        return decision, fusion_score, confidence

    def decide(
        self,
        evidence_list: List[CandidateEvidence],
        reference_id: str = "",
        reference_name: str = "",
    ) -> VerificationDecision:
        """
        Make decisions for all candidates of a reference location.

        Selects the best candidate and returns the complete decision.

        Args:
            evidence_list: List of evidence bundles for all candidates.
            reference_id: Reference location ID.
            reference_name: Reference location name.

        Returns:
            VerificationDecision with best candidate and all decisions.
        """
        result = VerificationDecision(
            reference_id=reference_id,
            reference_name=reference_name,
        )

        if not evidence_list:
            return result

        # Decide for each candidate
        best_decision = None
        best_candidate = None
        best_confidence = -1.0

        for evidence in evidence_list:
            decision, fusion_score, confidence = self.decide_single(evidence)
            result.all_decisions.append((evidence, decision))

            # Track best accepted candidate
            if (
                decision.is_accepted
                and confidence.calibrated_confidence > best_confidence
            ):
                best_confidence = confidence.calibrated_confidence
                best_decision = decision
                best_candidate = evidence

        result.best_candidate = best_candidate
        result.best_decision = best_decision
        result.selected_state = best_decision.state if best_decision else None

        return result

    def _classify(self, confidence: float) -> VerificationState:
        """Classify confidence into a verification state."""
        for state in [
            VerificationState.VERIFIED,
            VerificationState.HIGHLY_LIKELY,
            VerificationState.LIKELY,
            VerificationState.NEEDS_REVIEW,
            VerificationState.LOW_CONFIDENCE,
        ]:
            if confidence >= self.thresholds[state]:
                return state
        return VerificationState.REJECTED

    def _check_hard_rejections(
        self, evidence: CandidateEvidence
    ) -> List[str]:
        """
        Check for hard rejection rules that override confidence.

        Returns list of rejection reasons (empty = no rejection).
        """
        reasons = []

        # Must be on land
        if not evidence.geography.on_land:
            reasons.append("Coordinates in ocean")

        # Must have positive name similarity
        if evidence.text.name_similarity < 0.15:
            reasons.append("Extremely low name similarity")

        # Negative place type is a hard reject
        if evidence.place_type.is_negative_type:
            reasons.append(
                f"Inappropriate place type: {evidence.place_type.negative_type_detail}"
            )

        # Large historical movement without explanation
        if evidence.historical.large_movement and not evidence.historical.has_previous_data:
            reasons.append("Large unexplained movement from previous location")

        return reasons

    def get_state_label(self, state: VerificationState) -> str:
        """Get a human-readable label for a verification state."""
        labels = {
            VerificationState.VERIFIED: "✓ Verified",
            VerificationState.HIGHLY_LIKELY: "✓ Highly Likely",
            VerificationState.LIKELY: "~ Likely",
            VerificationState.NEEDS_REVIEW: "? Needs Review",
            VerificationState.LOW_CONFIDENCE: "✗ Low Confidence",
            VerificationState.REJECTED: "✗ Rejected",
        }
        return labels.get(state, state.value)
