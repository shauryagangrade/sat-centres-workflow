"""
SAT Centre Updater - Country Normalizer Module

Provides a single source of truth for mapping country name variants
to canonical uppercase forms. Used by both the scorer and validator
to ensure consistent country comparison across the pipeline.

Usage:
    from utils.country_normalizer import normalize_country
    canonical = normalize_country("United States of America")  # -> "US"
"""

from typing import Dict, Set

# Canonical forms must match the values in config.VALIDATION.VALID_COUNTRIES.
# Each key is a canonical form; values are all recognized variants (lowercase).
_COUNTRY_ALIASES: Dict[str, Set[str]] = {
    "INDIA": {
        "india",
        "in",
        "republic of india",
        "bharat",
        "भारत",
    },
    "US": {
        "us",
        "usa",
        "united states",
        "united states of america",
        "u.s.",
        "u.s.a.",
        "u.s.a",
        "u.s",
        "america",
    },
    "CANADA": {
        "canada",
        "ca",
        "dominion of canada",
    },
    "UK": {
        "uk",
        "united kingdom",
        "gb",
        "great britain",
        "u.k.",
        "england",
        "scotland",
        "wales",
        "northern ireland",
    },
    "UAE": {
        "uae",
        "united arab emirates",
        "ae",
        "u.a.e.",
        "dubai",
        "abu dhabi",
    },
    "SINGAPORE": {
        "singapore",
        "sg",
        "republic of singapore",
    },
}

# Build reverse lookup: variant (lowercase) -> canonical (uppercase)
_VARIANT_TO_CANONICAL: Dict[str, str] = {}
for canonical, variants in _COUNTRY_ALIASES.items():
    for variant in variants:
        _VARIANT_TO_CANONICAL[variant] = canonical
    # Also map the canonical form itself
    _VARIANT_TO_CANONICAL[canonical.lower()] = canonical


def normalize_country(country: str) -> str:
    """
    Normalize a country name/alias to its canonical uppercase form.

    If the input matches a known variant, returns the canonical form
    (e.g., "United States of America" -> "US"). If no match is found,
    returns the input uppercased and stripped.

    Args:
        country: Raw country string from any source (API, dataset, etc.)

    Returns:
        Canonical uppercase country code, or uppercased input if unknown.
    """
    if not country:
        return ""
    key = country.strip().lower()
    return _VARIANT_TO_CANONICAL.get(key, key.upper())


def get_all_known_variants() -> Set[str]:
    """Return all recognized country name variants (lowercase)."""
    return set(_VARIANT_TO_CANONICAL.keys())


def get_canonical_forms() -> Set[str]:
    """Return all canonical country forms (uppercase)."""
    return set(_COUNTRY_ALIASES.keys())
