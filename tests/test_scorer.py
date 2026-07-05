"""
SAT Centre Updater - Scorer Tests

Unit tests for the candidate scorer module.
"""

import pytest
from processing.scorer import CandidateScorer, GeocodeCandidate


class TestCandidateScorer:
    """Test cases for the CandidateScorer class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.scorer = CandidateScorer()

    def test_exact_match(self) -> None:
        """Test scoring an exact match."""
        reference = {
            "name": "Legacy School",
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India",
        }
        candidate = GeocodeCandidate(
            name="Legacy School",
            city="Bangalore",
            state="Karnataka",
            country="India",
            confidence=1.0,
        )
        result = self.scorer.score(reference, candidate)
        assert result.score > 0.8

    def test_fuzzy_match(self) -> None:
        """Test scoring a fuzzy match."""
        reference = {
            "name": "Legacy International School",
            "city": "Bangalore",
            "country": "India",
        }
        candidate = GeocodeCandidate(
            name="Legacy School International",
            city="Bangalore",
            country="India",
            confidence=0.8,
        )
        result = self.scorer.score(reference, candidate)
        assert result.score > 0.4  # Should still score reasonably

    def test_wrong_country_penalised(self) -> None:
        """Test that wrong country penalises score significantly."""
        reference = {
            "name": "School",
            "city": "Mumbai",
            "country": "India",
        }
        candidate = GeocodeCandidate(
            name="School",
            city="Mumbai",
            country="USA",
            confidence=1.0,
        )
        result = self.scorer.score(reference, candidate)
        # Country mismatch scores 0.0, so total = name(0.25) + city(0.20) + confidence(0.10) + distance(0.05) = 0.60
        # A correct country would add 0.20, making it 0.80 — so wrong country = 25% penalty
        assert result.score < 0.7
        assert result.breakdown["country"] == 0.0

    def test_best_candidate(self) -> None:
        """Test selecting the best candidate."""
        reference = {
            "name": "Legacy School",
            "city": "Bangalore",
            "country": "India",
        }
        candidates = [
            GeocodeCandidate(name="Random Place", city="Tokyo", country="Japan", confidence=0.9),
            GeocodeCandidate(name="Legacy School", city="Bangalore", country="India", confidence=0.95),
        ]
        best = self.scorer.best_candidate(reference, candidates)

        assert best is not None
        assert best.candidate.name == "Legacy School"

    def test_best_candidate_below_threshold(self) -> None:
        """Test that no candidate is returned when below threshold."""
        reference = {
            "name": "Very Specific School Name",
            "city": "Very Specific City",
            "country": "India",
        }
        candidates = [
            GeocodeCandidate(name="Completely Different", city="Elsewhere", country="USA", confidence=0.1),
        ]
        best = self.scorer.best_candidate(reference, candidates)
        assert best is None

    def test_best_candidate_empty_list(self) -> None:
        """Test best_candidate with empty list."""
        reference = {"name": "Test", "city": "City"}
        best = self.scorer.best_candidate(reference, [])
        assert best is None

    def test_rank_candidates(self) -> None:
        """Test ranking candidates."""
        reference = {
            "name": "Test School",
            "city": "Mumbai",
            "country": "India",
        }
        candidates = [
            GeocodeCandidate(name="Test School", city="Mumbai", country="India", confidence=1.0),
            GeocodeCandidate(name="Wrong School", city="Delhi", country="India", confidence=0.5),
        ]
        ranked = self.scorer.rank_candidates(reference, candidates)

        assert len(ranked) == 2
        assert ranked[0].score >= ranked[1].score

    def test_country_aliases(self) -> None:
        """Test country alias matching."""
        assert self.scorer._exact_or_close_score("India", "IN") == 1.0
        assert self.scorer._exact_or_close_score("USA", "United States") == 1.0
        assert self.scorer._exact_or_close_score("UK", "United Kingdom") == 1.0
        assert self.scorer._exact_or_close_score("India", "USA") < 1.0
