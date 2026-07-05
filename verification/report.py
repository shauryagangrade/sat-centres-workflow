"""
Human-readable audit report generator.

Produces explainable reports showing why each candidate was accepted or rejected.
Every decision must be transparent and auditable.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from verification.confidence import ConfidenceResult
from verification.fusion import FusionScore
from verification.models import CandidateEvidence, VerificationResult


@dataclass
class AuditEntry:
    """Single audit entry for a candidate decision."""

    candidate_id: str = ""
    provider: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    decision: str = ""
    confidence: float = 0.0
    positive_signals: List[str] = field(default_factory=list)
    negative_signals: List[str] = field(default_factory=list)
    category_scores: Dict[str, float] = field(default_factory=dict)
    raw_score: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "candidate_id": self.candidate_id,
            "provider": self.provider,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "decision": self.decision,
            "confidence": self.confidence,
            "positive_signals": self.positive_signals,
            "negative_signals": self.negative_signals,
            "category_scores": self.category_scores,
            "raw_score": self.raw_score,
        }


@dataclass
class AuditReport:
    """Complete audit report for a verification run."""

    reference_id: str = ""
    reference_name: str = ""
    timestamp: str = ""
    entries: List[AuditEntry] = field(default_factory=list)
    best_candidate_id: Optional[str] = None
    summary: str = ""

    def to_dict(self) -> Dict:
        return {
            "reference_id": self.reference_id,
            "reference_name": self.reference_name,
            "timestamp": self.timestamp,
            "entries": [e.to_dict() for e in self.entries],
            "best_candidate_id": self.best_candidate_id,
            "summary": self.summary,
        }


class AuditReportGenerator:
    """
    Generates human-readable audit reports for verification decisions.

    Produces both structured (dict/JSON) and text-based reports.
    """

    def generate_for_candidate(
        self,
        evidence: CandidateEvidence,
        fusion_score: FusionScore,
        confidence: ConfidenceResult,
        decision: str,
    ) -> AuditEntry:
        """
        Generate an audit entry for a single candidate.

        Args:
            evidence: Evidence bundle for the candidate.
            fusion_score: Fused score for the candidate.
            confidence: Calibrated confidence.
            decision: Decision state (Verified, Rejected, etc.).

        Returns:
            AuditEntry with full audit trail.
        """
        entry = AuditEntry(
            candidate_id=evidence.candidate_id,
            provider=evidence.provider,
            latitude=evidence.latitude,
            longitude=evidence.longitude,
            decision=decision,
            confidence=round(confidence.calibrated_confidence, 4),
            positive_signals=evidence.positive_signals(),
            negative_signals=evidence.negative_signals(),
            category_scores=fusion_score.category_scores,
            raw_score=fusion_score.total_score,
        )
        return entry

    def generate_report(
        self,
        result: VerificationResult,
        entries: List[AuditEntry],
    ) -> AuditReport:
        """
        Generate a complete audit report for a verification result.

        Args:
            result: Verification result with all candidates.
            entries: Audit entries for each candidate.

        Returns:
            AuditReport with full audit trail.
        """
        report = AuditReport(
            reference_id=result.reference_id,
            reference_name=result.reference_name,
            timestamp=datetime.now().isoformat(),
            entries=entries,
            best_candidate_id=result.best_candidate_id,
        )

        # Generate summary
        if entries:
            best = next(
                (e for e in entries if e.decision != "Rejected"), entries[0]
            )
            report.summary = self._format_summary(best)

        return report

    def format_text_report(self, report: AuditReport) -> str:
        """
        Format an audit report as human-readable text.

        Args:
            report: AuditReport to format.

        Returns:
            Formatted text string.
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"AUDIT REPORT: {report.reference_name}")
        lines.append(f"Reference ID: {report.reference_id}")
        lines.append(f"Timestamp: {report.timestamp}")
        lines.append("=" * 60)

        for i, entry in enumerate(report.entries, 1):
            is_best = entry.candidate_id == report.best_candidate_id
            marker = " ★ BEST" if is_best else ""

            lines.append(f"\n--- Candidate {i}{marker} ---")
            lines.append(f"  Provider: {entry.provider}")
            lines.append(
                f"  Location: ({entry.latitude:.6f}, {entry.longitude:.6f})"
            )
            lines.append(f"  Decision: {entry.decision}")
            lines.append(f"  Confidence: {entry.confidence:.1%}")
            lines.append(f"  Raw Score: {entry.raw_score:.4f}")

            lines.append("\n  Evidence Breakdown:")
            for category, score in entry.category_scores.items():
                bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
                lines.append(f"    {category:12s} [{bar}] {score:.3f}")

            if entry.positive_signals:
                lines.append("\n  ✓ Positive Signals:")
                for signal in entry.positive_signals:
                    lines.append(f"    + {signal}")

            if entry.negative_signals:
                lines.append("\n  ✗ Negative Signals:")
                for signal in entry.negative_signals:
                    lines.append(f"    - {signal}")

        lines.append("\n" + "=" * 60)
        if report.summary:
            lines.append(f"SUMMARY: {report.summary}")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _format_summary(self, best_entry: AuditEntry) -> str:
        """Format a summary for the best candidate."""
        parts = []
        parts.append(f"Accepted {best_entry.provider} candidate")
        parts.append(f"({best_entry.latitude:.4f}, {best_entry.longitude:.4f})")
        parts.append(f"with {best_entry.confidence:.1%} confidence")

        if best_entry.positive_signals:
            parts.append(
                f"based on {len(best_entry.positive_signals)} positive signals"
            )

        return " ".join(parts) + "."
