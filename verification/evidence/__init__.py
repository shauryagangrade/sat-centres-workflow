"""
Evidence collectors for location verification.

Each module collects independent signals about a geocoding candidate.
"""

from verification.evidence.geography import GeographyEvidenceCollector
from verification.evidence.history import HistoricalEvidenceCollector
from verification.evidence.place_type import PlaceTypeEvidenceCollector
from verification.evidence.providers import ProviderEvidenceCollector
from verification.evidence.text import TextEvidenceCollector

__all__ = [
    "GeographyEvidenceCollector",
    "HistoricalEvidenceCollector",
    "PlaceTypeEvidenceCollector",
    "ProviderEvidenceCollector",
    "TextEvidenceCollector",
]
