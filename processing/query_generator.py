"""
SAT Centre Updater - Query Generator Module

Generates multiple search queries per centre to maximize geocoding success.
Uses combinatorial strategies with school name, address, city, state, and country.

Usage:
    from processing.query_generator import QueryGenerator

    gen = QueryGenerator()
    queries = gen.generate(centre)
    print(queries)
    # ['Legacy School Bangalore', 'Legacy International School Bangalore', ...]
"""

from typing import Dict, List, Set

from processing.normalizer import SatCentre


# Common abbreviations and noise words to strip for shorter queries
NOISE_WORDS: List[str] = [
    "the",
    "a",
    "an",
    "of",
    "for",
    "and",
    "at",
    "in",
    "on",
]


class QueryGenerator:
    """
    Generates multiple geocoding search queries from a SatCentre record.

    Strategy:
    1. Full name + city + country
    2. Full name + city + state
    3. Full name only
    4. Cleaned name (without noise words) + city + country
    5. Address + city + country
    6. Name + state + country
    """

    MAX_QUERIES: int = 8

    def generate(self, centre: SatCentre) -> List[str]:
        """
        Generate ordered search queries for a centre.

        Args:
            centre: The SatCentre to generate queries for.

        Returns:
            Ordered list of search query strings, most specific first.
        """
        queries: List[str] = []
        seen: Set[str] = set()

        name = centre.name.strip()
        city = centre.city.strip()
        state = centre.state.strip()
        country = centre.country.strip()
        address = centre.address.strip()

        def _add(q: str) -> None:
            """Add a query if it hasn't been seen and is non-empty."""
            q = q.strip()
            if q and q not in seen:
                seen.add(q)
                queries.append(q)

        # 1. Name + City + Country
        if name and city and country:
            _add(f"{name} {city} {country}")

        # 2. Name + City + State
        if name and city and state:
            _add(f"{name} {city} {state}")

        # 3. Name + City
        if name and city:
            _add(f"{name} {city}")

        # 4. Name + Country
        if name and country:
            _add(f"{name} {country}")

        # 5. Name only
        if name:
            _add(name)

        # 6. Cleaned name (remove noise words) + City + Country
        cleaned_name = self._clean_name(name)
        if cleaned_name != name and cleaned_name and city and country:
            _add(f"{cleaned_name} {city} {country}")

        # 7. Address + City + Country
        if address and city and country:
            _add(f"{address} {city} {country}")

        # 8. Name + State + Country
        if name and state and country:
            _add(f"{name} {state} {country}")

        return queries[: self.MAX_QUERIES]

    def generate_batch(self, centres: List[SatCentre]) -> Dict[str, List[str]]:
        """
        Generate queries for multiple centres.

        Args:
            centres: List of SatCentre objects.

        Returns:
            Dictionary mapping centre ID to list of queries.
        """
        return {centre.id: self.generate(centre) for centre in centres}

    def _clean_name(self, name: str) -> str:
        """
        Clean a school name by removing noise words and normalising.

        Args:
            name: Raw school name.

        Returns:
            Cleaned name string.
        """
        words = name.split()
        cleaned = [w for w in words if w.lower() not in NOISE_WORDS]
        return " ".join(cleaned)
