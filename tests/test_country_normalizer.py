"""
SAT Centre Updater - Country Normalizer Tests

Unit tests for the shared country normalization utility.
"""

from utils.country_normalizer import (
    get_all_known_variants,
    get_canonical_forms,
    normalize_country,
)


class TestNormalizeCountry:
    """Test cases for the normalize_country function."""

    def test_canonical_us_forms(self) -> None:
        """All US variants normalize to 'US'."""
        us_variants = [
            "US", "us", "Us",
            "USA", "usa", "Usa",
            "United States", "united states", "UNITED STATES",
            "United States of America", "united states of america",
            "U.S.", "u.s.", "U.S.A.", "u.s.a.",
            "America", "america",
        ]
        for variant in us_variants:
            assert normalize_country(variant) == "US", f"Failed for: {variant}"

    def test_canonical_india_forms(self) -> None:
        """All India variants normalize to 'INDIA'."""
        india_variants = [
            "India", "india", "INDIA",
            "IN", "in",
            "Republic of India", "republic of india",
            "Bharat", "bharat", "BHARAT",
        ]
        for variant in india_variants:
            assert normalize_country(variant) == "INDIA", f"Failed for: {variant}"

    def test_canonical_uk_forms(self) -> None:
        """All UK variants normalize to 'UK'."""
        uk_variants = [
            "UK", "uk", "Uk",
            "United Kingdom", "united kingdom", "UNITED KINGDOM",
            "GB", "gb",
            "Great Britain", "great britain",
            "U.K.", "u.k.",
            "England", "england",
        ]
        for variant in uk_variants:
            assert normalize_country(variant) == "UK", f"Failed for: {variant}"

    def test_canonical_canada_forms(self) -> None:
        """All Canada variants normalize to 'CANADA'."""
        canada_variants = [
            "Canada", "canada", "CANADA",
            "CA", "ca",
        ]
        for variant in canada_variants:
            assert normalize_country(variant) == "CANADA", f"Failed for: {variant}"

    def test_canonical_uae_forms(self) -> None:
        """All UAE variants normalize to 'UAE'."""
        uae_variants = [
            "UAE", "uae", "Uae",
            "United Arab Emirates", "united arab emirates",
            "AE", "ae",
            "U.A.E.", "u.a.e.",
        ]
        for variant in uae_variants:
            assert normalize_country(variant) == "UAE", f"Failed for: {variant}"

    def test_canonical_singapore_forms(self) -> None:
        """All Singapore variants normalize to 'SINGAPORE'."""
        sg_variants = [
            "Singapore", "singapore", "SINGAPORE",
            "SG", "sg",
            "Republic of Singapore", "republic of singapore",
        ]
        for variant in sg_variants:
            assert normalize_country(variant) == "SINGAPORE", f"Failed for: {variant}"

    def test_unknown_country_uppercased(self) -> None:
        """Unknown country names are uppercased as fallback."""
        assert normalize_country("Germany") == "GERMANY"
        assert normalize_country("japan") == "JAPAN"
        assert normalize_country("FRANCE") == "FRANCE"

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert normalize_country("") == ""

    def test_whitespace_handling(self) -> None:
        """Leading/trailing whitespace is stripped."""
        assert normalize_country("  US  ") == "US"
        assert normalize_country("  United States  ") == "US"
        assert normalize_country("  India  ") == "INDIA"

    def test_case_insensitive(self) -> None:
        """Matching is case-insensitive."""
        assert normalize_country("uNiTeD sTaTeS") == "US"
        assert normalize_country("iNdIa") == "INDIA"

    def test_canonical_forms_match_valid_countries(self) -> None:
        """All canonical forms should be valid country identifiers."""
        canonical = get_canonical_forms()
        assert "INDIA" in canonical
        assert "US" in canonical
        assert "CANADA" in canonical
        assert "UK" in canonical
        assert "UAE" in canonical
        assert "SINGAPORE" in canonical

    def test_known_variants_are_lowercase(self) -> None:
        """All known variants should be lowercase for reliable matching."""
        variants = get_all_known_variants()
        for v in variants:
            assert v == v.lower(), f"Variant not lowercase: {v}"
