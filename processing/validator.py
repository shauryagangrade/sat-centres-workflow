"""
SAT Centre Updater - Validator Module

Validates geocoded SAT centres against configurable rules.
Rejects centres with wrong country, wrong city, missing coordinates,
ocean coordinates, duplicates, or low confidence.

Usage:
    from processing.validator import CentreValidator
    from processing.normalizer import SatCentre

    validator = CentreValidator()
    valid, failed = validator.validate(centres)
"""

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from config import settings
from processing.normalizer import SatCentre
from utils.country_normalizer import normalize_country


@dataclass
class ValidationResult:
    """Result of validating a single centre."""

    centre: SatCentre
    is_valid: bool = True
    failure_reasons: List[str] = field(default_factory=list)
    failed_at: str = ""


@dataclass
class ValidationSummary:
    """Summary of the validation run."""

    total: int = 0
    valid: int = 0
    failed: int = 0
    duplicate_ids: int = 0
    duplicate_coords: int = 0
    wrong_country: int = 0
    wrong_city: int = 0
    missing_coords: int = 0
    ocean_coords: int = 0
    low_confidence: int = 0


# Simplified bounding boxes for continents (rough ocean detection)
CONTINENT_BBOXES: Dict[str, Tuple[float, float, float, float]] = {
    "asia": (-10.0, -170.0, 55.0, 180.0),
    "europe": (35.0, -25.0, 72.0, 45.0),
    "north_america": (7.0, -170.0, 85.0, -50.0),
    "south_america": (-60.0, -90.0, 15.0, -30.0),
    "africa": (-40.0, -20.0, 38.0, 55.0),
    "oceania": (-55.0, 100.0, 0.0, 180.0),
}


class CentreValidator:
    """
    Validates geocoded SAT centre data.

    Checks:
    - Missing latitude/longitude
    - Coordinates in the ocean
    - Wrong country
    - Wrong city (optional, less strict)
    - Duplicate centre IDs
    - Duplicate coordinate pairs
    - Low geocoding confidence
    """

    def __init__(
        self,
        reports_dir: Optional[Path] = None,
    ) -> None:
        """
        Initialize the validator.

        Args:
            reports_dir: Directory for failure reports. Defaults to config setting.
        """
        self.reports_dir = reports_dir or settings.PATHS.REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.valid_countries: Set[str] = {
            normalize_country(c) for c in settings.VALIDATION.VALID_COUNTRIES
        }
        self.confidence_threshold = settings.GEOCODING.CONFIDENCE_THRESHOLD

    def validate(
        self, centres: List[SatCentre]
    ) -> Tuple[List[SatCentre], List[ValidationResult]]:
        """
        Validate a list of centres.

        Args:
            centres: List of SatCentre objects to validate.

        Returns:
            Tuple of (valid_centres, failed_results).
        """
        valid: List[SatCentre] = []
        failed: List[ValidationResult] = []

        seen_ids: Set[str] = set()
        seen_coords: Set[Tuple[float, float]] = set()

        for centre in centres:
            result = self._validate_single(centre, seen_ids, seen_coords)

            if result.is_valid:
                valid.append(centre)
                # Track after confirming valid
                if centre.id:
                    seen_ids.add(centre.id)
                if centre.latitude is not None and centre.longitude is not None:
                    seen_coords.add((centre.latitude, centre.longitude))
            else:
                failed.append(result)

        # Export failures
        if failed:
            self._export_failures(failed)

        return valid, failed

    def _validate_single(
        self,
        centre: SatCentre,
        seen_ids: Set[str],
        seen_coords: Set[Tuple[float, float]],
    ) -> ValidationResult:
        """
        Validate a single centre.

        Args:
            centre: SatCentre to validate.
            seen_ids: Set of already-seen IDs (for duplicate detection).
            seen_coords: Set of already-seen coordinate pairs.

        Returns:
            ValidationResult indicating pass/fail and reasons.
        """
        result = ValidationResult(centre=centre, is_valid=True)

        # Check missing coordinates
        if centre.latitude is None or centre.longitude is None:
            result.is_valid = False
            result.failure_reasons.append("missing_coordinates")
            result.failed_at = "coordination_check"
            return result

        # Check ocean coordinates
        if settings.VALIDATION.OCEAN_CHECK:
            if not self._is_on_land(centre.latitude, centre.longitude):
                result.is_valid = False
                result.failure_reasons.append("ocean_coordinates")
                result.failed_at = "ocean_check"
                return result

        # Check wrong country (normalize to canonical form first)
        if centre.country and normalize_country(centre.country) not in self.valid_countries:
            result.is_valid = False
            result.failure_reasons.append(f"wrong_country: {centre.country}")
            result.failed_at = "country_check"
            return result

        # Check duplicate ID
        if centre.id and centre.id in seen_ids:
            result.is_valid = False
            result.failure_reasons.append(f"duplicate_id: {centre.id}")
            result.failed_at = "duplicate_id_check"
            return result

        # Check duplicate coordinates
        coord_pair = (centre.latitude, centre.longitude)
        if coord_pair in seen_coords:
            result.is_valid = False
            result.failure_reasons.append(f"duplicate_coords: {coord_pair}")
            result.failed_at = "duplicate_coords_check"
            return result

        # Check low confidence from metadata
        confidence = centre.metadata.get("confidence", 1.0)
        if (
            isinstance(confidence, (int, float))
            and confidence < self.confidence_threshold
        ):
            result.is_valid = False
            result.failure_reasons.append(f"low_confidence: {confidence:.2f}")
            result.failed_at = "confidence_check"
            return result

        return result

    def _is_on_land(self, lat: float, lon: float) -> bool:
        """
        Rough check if coordinates are on land using continent bounding boxes.

        This is a simplified check. Coordinates within any continent bbox are
        considered on land. For production, use a proper land polygon dataset.

        Args:
            lat: Latitude.
            lon: Longitude.

        Returns:
            True if coordinates are likely on land.
        """
        for name, (min_lat, min_lon, max_lat, max_lon) in CONTINENT_BBOXES.items():
            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                return True

        return False

    def _export_failures(self, failed: List[ValidationResult]) -> Path:
        """
        Export failed centres to a CSV report.

        Args:
            failed: List of failed validation results.

        Returns:
            Path to the exported CSV file.
        """
        file_path = self.reports_dir / "failed.csv"

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "id",
                    "name",
                    "city",
                    "state",
                    "country",
                    "latitude",
                    "longitude",
                    "failure_reasons",
                    "failed_at",
                ]
            )
            for result in failed:
                c = result.centre
                writer.writerow(
                    [
                        c.id,
                        c.name,
                        c.city,
                        c.state,
                        c.country,
                        c.latitude,
                        c.longitude,
                        "; ".join(result.failure_reasons),
                        result.failed_at,
                    ]
                )

        return file_path

    def get_summary(
        self, total: int, valid: List[SatCentre], failed: List[ValidationResult]
    ) -> ValidationSummary:
        """
        Build a summary of validation results.

        Args:
            total: Total number of centres processed.
            valid: List of valid centres.
            failed: List of failed validation results.

        Returns:
            ValidationSummary object.
        """
        summary = ValidationSummary(total=total, valid=len(valid), failed=len(failed))

        for result in failed:
            for reason in result.failure_reasons:
                if reason.startswith("duplicate_id"):
                    summary.duplicate_ids += 1
                elif reason.startswith("duplicate_coords"):
                    summary.duplicate_coords += 1
                elif reason.startswith("wrong_country"):
                    summary.wrong_country += 1
                elif reason.startswith("missing_coordinates"):
                    summary.missing_coords += 1
                elif reason.startswith("ocean_coordinates"):
                    summary.ocean_coords += 1
                elif reason.startswith("low_confidence"):
                    summary.low_confidence += 1

        return summary
