"""
Textual evidence collector.

Evaluates name, address, city, state, country, postal code, and street
similarity between a reference centre and a geocoding candidate.
Uses RapidFuzz for fuzzy matching with Unicode normalization.
"""

import re
import unicodedata
from typing import Dict, Optional

from rapidfuzz import fuzz

from verification.models import TextEvidence


def _normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, collapse whitespace."""
    if not text:
        return ""
    # Unicode normalize (NFKD) to handle transliterations
    text = unicodedata.normalize("NFKD", text)
    # Remove combining characters (accents)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


# Common school name aliases and abbreviations
_SCHOOL_ALIASES: Dict[str, set] = {
    "school": {"school", "sch", "sch.", "schools"},
    "international": {"international", "intl", "intl.", "global"},
    "academy": {"academy", "acad", "acad.", "academies"},
    "public": {"public", "pub", "pub.", "national"},
    "high": {"high", "hs", "senior", "sr.", "sr"},
    "college": {"college", "coll", "coll.", "university", "univ"},
    "institute": {"institute", "inst", "inst.", "instituto"},
    "montessori": {"montessori", "mont", "mont."},
    "grammar": {"grammar", "gram", "gram."},
    "preparatory": {"preparatory", "prep", "prep.", "pre-primary"},
    "secondary": {"secondary", "sec", "sec.", "middle"},
    "primary": {"primary", "pri", "pri.", "elementary", "elem"},
}


def _detect_alias(name1: str, name2: str) -> bool:
    """Check if two names share known alias pairs."""
    words1 = set(_normalize_text(name1).split())
    words2 = set(_normalize_text(name2).split())

    for _canonical, aliases in _SCHOOL_ALIASES.items():
        match1 = words1 & aliases
        match2 = words2 & aliases
        if match1 and match2 and match1 != match2:
            return True
    return False


def _detect_transliteration(name1: str, name2: str) -> bool:
    """Detect if names are likely transliterations of each other."""
    # Simple heuristic: if normalized forms share >70% of characters
    n1 = _normalize_text(name1)
    n2 = _normalize_text(name2)
    if not n1 or not n2:
        return False
    # Character-level similarity
    chars1 = set(n1)
    chars2 = set(n2)
    if not chars1 or not chars2:
        return False
    overlap = len(chars1 & chars2) / max(len(chars1), len(chars2))
    return overlap > 0.7


class TextEvidenceCollector:
    """
    Collects textual similarity evidence between a reference and candidate.

    Compares name, address, city, state, country, postal code, and street
    fields using fuzzy matching.
    """

    def collect(
        self,
        reference: Dict[str, str],
        candidate_name: str,
        candidate_address: str,
        candidate_city: str,
        candidate_state: str,
        candidate_country: str,
        candidate_postal: str = "",
        candidate_street: str = "",
    ) -> TextEvidence:
        """
        Collect textual evidence for a candidate.

        Args:
            reference: Dict with keys: name, address, city, state, country, postal_code.
            candidate_name: Candidate's name.
            candidate_address: Candidate's address.
            candidate_city: Candidate's city.
            candidate_state: Candidate's state.
            candidate_country: Candidate's country.
            candidate_postal: Candidate's postal code.
            candidate_street: Candidate's street.

        Returns:
            TextEvidence with similarity scores.
        """
        evidence = TextEvidence()

        # Name similarity
        ref_name = reference.get("name", "")
        evidence.name_similarity = self._fuzzy_score(ref_name, candidate_name)

        # Address similarity
        ref_address = reference.get("address", "")
        evidence.address_similarity = self._fuzzy_score(ref_address, candidate_address)

        # City similarity
        ref_city = reference.get("city", "")
        evidence.city_similarity = self._fuzzy_score(ref_city, candidate_city)

        # State similarity
        ref_state = reference.get("state", "")
        evidence.state_similarity = self._fuzzy_score(ref_state, candidate_state)

        # Country similarity (uses canonical normalization)
        ref_country = reference.get("country", "")
        evidence.country_similarity = self._country_score(ref_country, candidate_country)

        # Postal code similarity
        ref_postal = reference.get("postal_code", "")
        evidence.postal_similarity = self._postal_score(ref_postal, candidate_postal)

        # Street similarity
        ref_street = reference.get("address", "")
        evidence.street_similarity = self._fuzzy_score(ref_street, candidate_street)

        # Admin area (state/province/region combined)
        ref_admin = f"{ref_state} {ref_country}".strip()
        cand_admin = f"{candidate_state} {candidate_country}".strip()
        evidence.admin_area_similarity = self._fuzzy_score(ref_admin, cand_admin)

        # Alias detection
        evidence.alias_detected = _detect_alias(ref_name, candidate_name)

        # Transliteration detection
        evidence.transliteration_match = _detect_transliteration(ref_name, candidate_name)

        return evidence

    def _fuzzy_score(self, query: str, target: str) -> float:
        """
        Compute fuzzy match score between two strings.
        Returns 0.0-1.0.
        """
        if not query or not target:
            return 0.0

        q = _normalize_text(query)
        t = _normalize_text(target)

        if not q or not t:
            return 0.0

        # Exact match
        if q == t:
            return 1.0

        # Token set ratio handles word reordering well
        score = fuzz.token_set_ratio(q, t)
        return score / 100.0

    def _country_score(self, query: str, target: str) -> float:
        """
        Score country match with canonical normalization.
        Returns 0.0-1.0.
        """
        if not query or not target:
            return 0.0

        try:
            from utils.country_normalizer import normalize_country

            q_canonical = normalize_country(query)
            t_canonical = normalize_country(target)

            if q_canonical == t_canonical:
                return 1.0
        except ImportError:
            pass

        # Fuzzy fallback
        return self._fuzzy_score(query, target)

    def _postal_score(self, query: str, target: str) -> float:
        """
        Score postal code match.
        Exact match = 1.0, prefix match = 0.5, else fuzzy.
        """
        if not query or not target:
            return 0.0

        q = query.strip()
        t = target.strip()

        if q == t:
            return 1.0

        # Check if one is a prefix of the other
        if q.startswith(t) or t.startswith(q):
            return 0.5

        return self._fuzzy_score(q, t)
