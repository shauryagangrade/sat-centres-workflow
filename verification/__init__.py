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

from verification.decision_engine import Decision, DecisionEngine, VerificationState
from verification.verifier import LocationVerifier

__all__ = ["Decision", "DecisionEngine", "LocationVerifier", "VerificationState"]
