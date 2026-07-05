"""
SAT Centre Updater - Verification Package

Evidence-based location verification pipeline.
Each candidate accumulates independent pieces of evidence.
The final confidence emerges from the combination of evidence.

Usage:
    from verification import LocationVerifier, DecisionEngine

    verifier = LocationVerifier()
    evidence = verifier.verify(reference, candidates)
    engine = DecisionEngine()
    decisions = engine.decide(evidence)
"""

from verification.verifier import LocationVerifier
from verification.decision_engine import DecisionEngine, Decision, VerificationState

__all__ = ["LocationVerifier", "DecisionEngine", "Decision", "VerificationState"]
