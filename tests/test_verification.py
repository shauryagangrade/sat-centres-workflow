"""
SAT Centre Updater - Evidence-Based Verification Tests

Unit tests for the verification pipeline:
- Evidence collectors
- Fusion engine
- Confidence calculator
- Decision engine
- Full pipeline integration
"""

import math

import pytest

from verification.confidence import ConfidenceCalculator, ConfidenceResult
from verification.decision_engine import Decision, DecisionEngine, VerificationState
from verification.evidence.geography import (
    GeographyEvidenceCollector,
    _haversine_distance,
    estimate_coordinate_precision,
    is_on_land,
)
from verification.evidence.history import HistoricalEvidenceCollector
from verification.evidence.place_type import PlaceTypeEvidenceCollector
from verification.evidence.providers import (
    ProviderEvidenceCollector,
    _coordinate_variance,
)
from verification.evidence.text import TextEvidenceCollector, _normalize_text
from verification.fusion import EvidenceFusion, FusionScore
from verification.models import (
    CandidateEvidence,
    GeographyEvidence,
    HistoricalEvidence,
    PlaceTypeEvidence,
    ProviderEvidence,
    TextEvidence,
    VerificationResult,
)
from verification.report import AuditReportGenerator
from verification.verifier import LocationVerifier


# ============================================================
# Text Evidence Tests
# ============================================================


class TestTextEvidenceCollector:
    """Tests for textual evidence collection."""

    def setup_method(self):
        self.collector = TextEvidenceCollector()

    def test_exact_name_match(self):
        ref = {"name": "Legacy School", "city": "Bangalore", "country": "India"}
        evidence = self.collector.collect(
            ref, "Legacy School", "", "Bangalore", "", "India"
        )
        assert evidence.name_similarity >= 0.95
        assert evidence.city_similarity >= 0.95

    def test_fuzzy_name_match(self):
        ref = {"name": "Legacy International School", "city": "Bangalore", "country": "India"}
        evidence = self.collector.collect(
            ref, "Legacy School International", "", "Bangalore", "", "India"
        )
        assert evidence.name_similarity > 0.6

    def test_country_alias_match(self):
        ref = {"name": "Test", "country": "India"}
        evidence = self.collector.collect(ref, "Test", "", "", "", "IN")
        assert evidence.country_similarity == 1.0

    def test_wrong_country(self):
        ref = {"name": "Test", "country": "India"}
        evidence = self.collector.collect(ref, "Test", "", "", "", "USA")
        assert evidence.country_similarity < 0.5

    def test_empty_fields(self):
        ref = {"name": "", "city": ""}
        evidence = self.collector.collect(ref, "", "", "", "", "")
        assert evidence.name_similarity == 0.0

    def test_alias_detection(self):
        # "school" and "sch" are aliases in the same set
        ref = {"name": "Greenfield School"}
        evidence = self.collector.collect(ref, "Greenfield Sch", "", "", "", "")
        assert evidence.alias_detected is True

    def test_postal_code_exact(self):
        ref = {"name": "Test", "postal_code": "560001"}
        evidence = self.collector.collect(
            ref, "Test", "", "", "", "", "560001"
        )
        assert evidence.postal_similarity == 1.0

    def test_postal_code_prefix(self):
        ref = {"name": "Test", "postal_code": "560001"}
        evidence = self.collector.collect(
            ref, "Test", "", "", "", "", "5600"
        )
        assert evidence.postal_similarity == 0.5


# ============================================================
# Geography Evidence Tests
# ============================================================


class TestGeographyEvidenceCollector:
    """Tests for geographic evidence collection."""

    def setup_method(self):
        self.collector = GeographyEvidenceCollector()

    def test_on_land(self):
        assert is_on_land(12.97, 77.59) is True  # Bangalore
        assert is_on_land(51.51, -0.13) is True  # London

    def test_in_ocean(self):
        # (-20.0, 60.0) is in the Southern Indian Ocean, outside all continent bboxes
        assert is_on_land(-20.0, 60.0) is False

    def test_distance_calculation(self):
        dist = _haversine_distance(12.97, 77.59, 12.98, 77.60)
        assert dist < 2.0  # Should be close

    def test_coordinate_precision(self):
        # 6 decimals = high precision
        assert estimate_coordinate_precision(12.971593, 77.594562) > 0.9
        # 2 decimals = low precision
        assert estimate_coordinate_precision(13.0, 77.6) < 0.5

    def test_city_center_distance(self):
        ref = {"city": "Bangalore"}
        evidence = self.collector.collect(ref, 12.97, 77.59)
        assert evidence.distance_from_city_center is not None
        assert evidence.distance_from_city_center < 5.0

    def test_reverse_geocode_match(self):
        ref = {"city": "Bangalore", "country": "India"}
        reverse_data = {"city": "Bengaluru", "country": "India"}
        evidence = self.collector.collect(ref, 12.97, 77.59, reverse_data)
        assert evidence.reverse_geocode_match is True

    def test_admin_hierarchy(self):
        ref = {"state": "Karnataka", "country": "India"}
        reverse_data = {"state": "Karnataka", "country": "India"}
        evidence = self.collector.collect(ref, 12.97, 77.59, reverse_data)
        assert evidence.admin_hierarchy_valid is True


# ============================================================
# Provider Evidence Tests
# ============================================================


class TestProviderEvidenceCollector:
    """Tests for provider consensus evidence."""

    def setup_method(self):
        self.collector = ProviderEvidenceCollector()

    def test_single_provider(self):
        evidence = self.collector.collect("nominatim", [])
        assert evidence.providers_agreeing == 1
        assert evidence.providers_total == 1

    def test_consensus(self):
        provider_results = {
            "nominatim": [{"latitude": 12.97, "longitude": 77.59}],
            "photon": [{"latitude": 12.98, "longitude": 77.60}],
            "geoapify": [{"latitude": 12.97, "longitude": 77.59}],
        }
        evidence = self.collector.collect(
            "nominatim",
            [{"latitude": 12.97, "longitude": 77.59}],
            provider_results,
        )
        assert evidence.providers_agreeing >= 2
        assert evidence.consensus_ratio > 0.5
        assert evidence.disagreement is False

    def test_disagreement(self):
        provider_results = {
            "nominatim": [{"latitude": 12.97, "longitude": 77.59}],
            "photon": [{"latitude": 51.51, "longitude": -0.13}],  # London!
            "geoapify": [{"latitude": 40.71, "longitude": -74.01}],  # New York!
        }
        evidence = self.collector.collect(
            "nominatim",
            [{"latitude": 12.97, "longitude": 77.59}],
            provider_results,
        )
        assert evidence.disagreement is True

    def test_coordinate_variance(self):
        coords = [(12.97, 77.59), (12.98, 77.60)]
        assert _coordinate_variance(coords) < 0.1

    def test_empty_providers(self):
        evidence = self.collector.collect("nominatim", [], {})
        # Empty dict means no providers returned results
        assert evidence.providers_total == 0


# ============================================================
# Place Type Evidence Tests
# ============================================================


class TestPlaceTypeEvidenceCollector:
    """Tests for place type evidence collection."""

    def setup_method(self):
        self.collector = PlaceTypeEvidenceCollector()

    def test_school_detected(self):
        raw = {"type": "school"}
        evidence = self.collector.collect("Test School", "", raw)
        assert evidence.is_educational is True
        assert evidence.category == "school"

    def test_negative_type(self):
        raw = {"type": "residential"}
        evidence = self.collector.collect("Some House", "", raw)
        assert evidence.is_negative_type is True

    def test_educational_keyword(self):
        evidence = self.collector.collect("Legacy Academy", "")
        assert evidence.is_educational is True

    def test_unknown_type(self):
        evidence = self.collector.collect("Some Place", "")
        assert evidence.category == "unknown"

    def test_osm_amenity(self):
        raw = {"tags": {"amenity": "university"}}
        evidence = self.collector.collect("Test University", "", raw)
        assert evidence.is_educational is True


# ============================================================
# Historical Evidence Tests
# ============================================================


class TestHistoricalEvidenceCollector:
    """Tests for historical evidence collection."""

    def setup_method(self):
        self.collector = HistoricalEvidenceCollector()

    def test_no_previous_data(self):
        evidence = self.collector.collect(12.97, 77.59, "Test", "Addr")
        assert evidence.has_previous_data is False

    def test_matches_previous(self):
        prev = {"latitude": 12.97, "longitude": 77.59, "name": "Test"}
        evidence = self.collector.collect(12.97, 77.59, "Test", "Addr", prev)
        assert evidence.matches_previous is True
        assert evidence.large_movement is False

    def test_large_movement(self):
        prev = {"latitude": 12.97, "longitude": 77.59, "name": "Test"}
        # ~5000km away (London)
        evidence = self.collector.collect(51.51, -0.13, "Test", "Addr", prev)
        assert evidence.large_movement is True

    def test_name_changed(self):
        prev = {"latitude": 12.97, "longitude": 77.59, "name": "Completely Different Name"}
        evidence = self.collector.collect(12.97, 77.59, "New School Name", "Addr", prev)
        assert evidence.name_changed is True


# ============================================================
# Fusion Engine Tests
# ============================================================


class TestEvidenceFusion:
    """Tests for evidence fusion."""

    def setup_method(self):
        self.fusion = EvidenceFusion()

    def test_high_quality_fusion(self):
        evidence = CandidateEvidence(
            text=TextEvidence(name_similarity=0.95, city_similarity=1.0, country_similarity=1.0),
            geography=GeographyEvidence(on_land=True, reverse_geocode_match=True, distance_from_city_center=0.5),
            provider_evidence=ProviderEvidence(consensus_ratio=1.0, providers_agreeing=3, providers_total=3),
            place_type=PlaceTypeEvidence(is_educational=True, confidence=0.9),
        )
        score = self.fusion.fuse(evidence)
        assert score.total_score > 0.7

    def test_low_quality_fusion(self):
        evidence = CandidateEvidence(
            text=TextEvidence(name_similarity=0.2, city_similarity=0.1, country_similarity=0.0),
            geography=GeographyEvidence(on_land=True, distance_from_city_center=200.0),
            provider_evidence=ProviderEvidence(consensus_ratio=0.3, providers_agreeing=1, providers_total=3),
            place_type=PlaceTypeEvidence(is_negative_type=True),
        )
        score = self.fusion.fuse(evidence)
        assert score.total_score < 0.3

    def test_ranking(self):
        good = CandidateEvidence(
            candidate_id="good",
            text=TextEvidence(name_similarity=0.95, city_similarity=1.0, country_similarity=1.0),
            geography=GeographyEvidence(on_land=True),
            place_type=PlaceTypeEvidence(is_educational=True),
        )
        bad = CandidateEvidence(
            candidate_id="bad",
            text=TextEvidence(name_similarity=0.2, city_similarity=0.1),
            geography=GeographyEvidence(on_land=True),
        )
        ranked = self.fusion.rank([bad, good])
        assert ranked[0][0].candidate_id == "good"


# ============================================================
# Confidence Calculator Tests
# ============================================================


class TestConfidenceCalculator:
    """Tests for calibrated confidence."""

    def setup_method(self):
        self.calc = ConfidenceCalculator()

    def test_high_score_high_confidence(self):
        fusion = FusionScore(total_score=0.9, evidence_strength=1.0)
        evidence = CandidateEvidence()
        result = self.calc.calculate(fusion, evidence)
        assert result.calibrated_confidence > 0.8

    def test_low_score_low_confidence(self):
        fusion = FusionScore(total_score=0.1, evidence_strength=0.5)
        evidence = CandidateEvidence()
        result = self.calc.calculate(fusion, evidence)
        assert result.calibrated_confidence < 0.3

    def test_mid_score(self):
        fusion = FusionScore(total_score=0.5, evidence_strength=1.0)
        evidence = CandidateEvidence()
        result = self.calc.calculate(fusion, evidence)
        assert 0.3 < result.calibrated_confidence < 0.7

    def test_uncertainty_increases_with_contradictions(self):
        fusion_good = FusionScore(
            total_score=0.7, evidence_strength=1.0,
            positive_count=5, negative_count=0
        )
        fusion_bad = FusionScore(
            total_score=0.7, evidence_strength=0.5,
            positive_count=3, negative_count=3
        )
        evidence = CandidateEvidence()
        r1 = self.calc.calculate(fusion_good, evidence)
        r2 = self.calc.calculate(fusion_bad, evidence)
        assert r2.uncertainty > r1.uncertainty


# ============================================================
# Decision Engine Tests
# ============================================================


class TestDecisionEngine:
    """Tests for the decision engine."""

    def setup_method(self):
        self.engine = DecisionEngine()

    def test_verified_decision(self):
        evidence = CandidateEvidence(
            text=TextEvidence(name_similarity=0.95, city_similarity=1.0, country_similarity=1.0),
            geography=GeographyEvidence(on_land=True, reverse_geocode_match=True),
            provider_evidence=ProviderEvidence(consensus_ratio=1.0, providers_agreeing=3, providers_total=3),
            place_type=PlaceTypeEvidence(is_educational=True, confidence=0.9),
        )
        decision, _, _ = self.engine.decide_single(evidence)
        assert decision.state in (
            VerificationState.VERIFIED,
            VerificationState.HIGHLY_LIKELY,
        )
        assert decision.is_accepted is True

    def test_rejected_decision(self):
        evidence = CandidateEvidence(
            text=TextEvidence(name_similarity=0.1, country_similarity=0.0),
            geography=GeographyEvidence(on_land=True),
            place_type=PlaceTypeEvidence(is_negative_type=True, negative_type_detail="Residential"),
        )
        decision, _, _ = self.engine.decide_single(evidence)
        assert decision.state == VerificationState.REJECTED
        assert len(decision.rejection_reasons) > 0

    def test_ocean_rejection(self):
        evidence = CandidateEvidence(
            geography=GeographyEvidence(on_land=False),
        )
        decision, _, _ = self.engine.decide_single(evidence)
        assert decision.state == VerificationState.REJECTED
        assert any("ocean" in r.lower() for r in decision.rejection_reasons)

    def test_selects_best_candidate(self):
        good = CandidateEvidence(
            candidate_id="good",
            text=TextEvidence(name_similarity=0.95, city_similarity=1.0, country_similarity=1.0),
            geography=GeographyEvidence(on_land=True),
            provider_evidence=ProviderEvidence(consensus_ratio=1.0, providers_agreeing=3, providers_total=3),
            place_type=PlaceTypeEvidence(is_educational=True),
        )
        bad = CandidateEvidence(
            candidate_id="bad",
            text=TextEvidence(name_similarity=0.2),
            geography=GeographyEvidence(on_land=True),
        )
        result = self.engine.decide([bad, good], "ref1", "Test")
        assert result.best_candidate is not None
        assert result.best_candidate.candidate_id == "good"


# ============================================================
# Verifier Integration Tests
# ============================================================


class TestLocationVerifier:
    """Tests for the full verification pipeline."""

    def setup_method(self):
        self.verifier = LocationVerifier()

    def test_full_verification(self):
        reference = {
            "id": "1",
            "name": "Legacy School",
            "city": "Bangalore",
            "state": "Karnataka",
            "country": "India",
        }
        candidates = [
            {
                "name": "Legacy School",
                "city": "Bangalore",
                "state": "Karnataka",
                "country": "India",
                "latitude": 12.97,
                "longitude": 77.59,
                "provider": "nominatim",
                "raw": {"type": "school"},
            },
            {
                "name": "Random Place",
                "city": "Mumbai",
                "country": "India",
                "latitude": 19.08,
                "longitude": 72.88,
                "provider": "photon",
            },
        ]
        result = self.verifier.verify(reference, candidates)
        assert len(result.candidates) == 2
        assert result.best_candidate_id is not None

    def test_empty_candidates(self):
        reference = {"name": "Test", "city": "Bangalore"}
        result = self.verifier.verify(reference, [])
        assert len(result.candidates) == 0

    def test_candidate_evidence_structure(self):
        reference = {
            "name": "Test School",
            "city": "Bangalore",
            "country": "India",
        }
        candidates = [
            {
                "name": "Test School",
                "city": "Bangalore",
                "country": "India",
                "latitude": 12.97,
                "longitude": 77.59,
                "provider": "nominatim",
            },
        ]
        result = self.verifier.verify(reference, candidates)
        evidence = result.candidates[0]
        assert evidence.text.name_similarity > 0.8
        assert evidence.geography.on_land is True
        assert evidence.place_type is not None


# ============================================================
# Audit Report Tests
# ============================================================


class TestAuditReportGenerator:
    """Tests for audit report generation."""

    def setup_method(self):
        self.generator = AuditReportGenerator()

    def test_generate_entry(self):
        from verification.confidence import ConfidenceResult
        from verification.fusion import FusionScore

        evidence = CandidateEvidence(
            candidate_id="c1",
            provider="nominatim",
            latitude=12.97,
            longitude=77.59,
            text=TextEvidence(name_similarity=0.95),
        )
        fusion = FusionScore(total_score=0.85)
        confidence = ConfidenceResult(calibrated_confidence=0.92)

        entry = self.generator.generate_for_candidate(
            evidence, fusion, confidence, "Verified"
        )
        assert entry.decision == "Verified"
        assert entry.confidence == 0.92
        assert len(entry.positive_signals) > 0

    def test_text_report_format(self):
        from verification.confidence import ConfidenceResult
        from verification.fusion import FusionScore
        from verification.models import VerificationResult

        evidence = CandidateEvidence(
            candidate_id="c1",
            provider="nominatim",
            latitude=12.97,
            longitude=77.59,
            text=TextEvidence(name_similarity=0.95, city_similarity=1.0),
        )
        fusion = FusionScore(total_score=0.85)
        confidence = ConfidenceResult(calibrated_confidence=0.92)
        entry = self.generator.generate_for_candidate(
            evidence, fusion, confidence, "Verified"
        )
        result = VerificationResult(
            reference_id="r1",
            reference_name="Test School",
            best_candidate_id="c1",
        )
        report = self.generator.generate_report(result, [entry])
        text = self.generator.format_text_report(report)

        assert "Test School" in text
        assert "Verified" in text
        assert "nominatim" in text
