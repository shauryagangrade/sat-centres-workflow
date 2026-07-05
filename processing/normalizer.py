"""
SAT Centre Updater - Normalizer Module

Converts raw SAT centre data from various formats (JSON, CSV) into a standardized schema.
Handles multiple College Board API response formats automatically.

Usage:
    from processing.normalizer import Normalizer

    normalizer = Normalizer()
    centres = normalizer.normalize(raw_data, format="json")
    normalizer.save(centres, "datasets/sat/generated/sat_centres.json")
"""

import csv
import hashlib
import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import settings


@dataclass
class SatCentre:
    """Standardized SAT centre data model."""

    id: str = ""
    name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    postal_code: str = ""
    phone: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SatCentre":
        """Create SatCentre from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            address=data.get("address", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            country=data.get("country", ""),
            postal_code=data.get("postal_code", ""),
            phone=data.get("phone", ""),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            metadata=data.get("metadata", {}),
        )


class Normalizer:
    """
    Normalizes raw SAT centre data into a standardized format.

    Supports multiple College Board API response formats:
    - Nested JSON arrays
    - Flat JSON arrays
    - CSV data
    - Various field naming conventions
    """

    # Known field mappings from College Board API to our schema
    FIELD_MAPPINGS: Dict[str, Dict[str, str]] = {
        "collegeboard": {
            "TestCenterCode": "id",
            "TestCenterName": "name",
            "Address1": "address",
            "City": "city",
            "State": "state",
            "Country": "country",
            "ZipCode": "postal_code",
            "PhoneNumber": "phone",
            "Latitude": "latitude",
            "Longitude": "longitude",
        },
        "generic": {
            "id": "id",
            "code": "id",
            "center_code": "id",
            "centre_code": "id",
            "name": "name",
            "center_name": "name",
            "centre_name": "name",
            "test_center_name": "name",
            "address": "address",
            "address1": "address",
            "street": "address",
            "street_address": "address",
            "city": "city",
            "town": "city",
            "state": "state",
            "province": "state",
            "region": "state",
            "country": "country",
            "nation": "country",
            "postal_code": "postal_code",
            "zip": "postal_code",
            "zipcode": "postal_code",
            "zip_code": "postal_code",
            "postcode": "postal_code",
            "phone": "phone",
            "phone_number": "phone",
            "telephone": "phone",
            "latitude": "latitude",
            "lat": "latitude",
            "longitude": "longitude",
            "lng": "longitude",
            "lon": "longitude",
        },
    }

    def __init__(self, generated_dir: Optional[Path] = None) -> None:
        """
        Initialize the normalizer.

        Args:
            generated_dir: Directory for generated files. Defaults to config setting.
        """
        self.generated_dir = generated_dir or settings.PATHS.GENERATED_DIR
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    def normalize(self, raw_data: Any, fmt: str = "auto") -> List[SatCentre]:
        """
        Normalize raw data into a list of SatCentre objects.

        Args:
            raw_data: Raw data (dict, list, bytes, or string).
            fmt: Format hint: 'json', 'csv', or 'auto' for auto-detection.

        Returns:
            List of normalized SatCentre objects.
        """
        # Detect format
        if fmt == "auto":
            fmt = self._detect_format(raw_data)

        # Parse raw data into a list of records
        records = self._extract_records(raw_data, fmt)

        # Normalize each record
        centres: List[SatCentre] = []
        for record in records:
            centre = self._normalize_record(record)
            if centre:
                centres.append(centre)

        return centres

    def _detect_format(self, raw_data: Any) -> str:
        """Detect the data format from the raw input."""
        if isinstance(raw_data, dict):
            return "json"
        if isinstance(raw_data, list):
            return "json"
        if isinstance(raw_data, bytes):
            try:
                json.loads(raw_data)
                return "json"
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
            try:
                raw_data.decode("utf-8")
                return "csv"
            except UnicodeDecodeError:
                pass
        if isinstance(raw_data, str):
            stripped = raw_data.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                return "json"
            return "csv"
        return "json"

    def _extract_records(self, raw_data: Any, fmt: str) -> List[Dict[str, Any]]:
        """
        Extract flat record dictionaries from raw data.

        Args:
            raw_data: Raw data input.
            fmt: Data format.

        Returns:
            List of record dictionaries.
        """
        if fmt == "csv":
            return self._parse_csv(raw_data)

        # JSON path
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode("utf-8")

        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
            except json.JSONDecodeError:
                return []

        return self._flatten_json(raw_data)

    def _parse_csv(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Parse CSV data into records."""
        if isinstance(raw_data, bytes):
            raw_data = raw_data.decode("utf-8")

        records: List[Dict[str, Any]] = []
        reader = csv.DictReader(StringIO(raw_data))
        for row in reader:
            records.append(dict(row))
        return records

    def _flatten_json(self, data: Any) -> List[Dict[str, Any]]:
        """
        Flatten JSON data into a list of record dictionaries.

        Handles various structures:
        - Direct list of objects
        - Object with a key containing the list
        - Nested objects
        """
        if isinstance(data, list):
            records: List[Dict[str, Any]] = []
            for item in data:
                if isinstance(item, dict):
                    records.append(item)
                elif isinstance(item, list):
                    # List of lists - take first row as header
                    if len(item) > 0 and isinstance(item[0], list):
                        headers = item[0]
                        for row in item[1:]:
                            record = dict(zip(headers, row))
                            records.append(record)
            return records

        if isinstance(data, dict):
            # Look for a list value in any key
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict):
                        return value

            # Single object - wrap in list
            return [data]

        return []

    def _normalize_record(self, record: Dict[str, Any]) -> Optional[SatCentre]:
        """
        Normalize a single record into a SatCentre object.

        Args:
            record: Raw record dictionary.

        Returns:
            SatCentre object or None if the record is invalid.
        """
        # Try to map fields using known mappings
        mapped = self._map_fields(record)

        # Extract name (required)
        name = self._clean_string(mapped.get("name", ""))
        if not name:
            # Try to find name from any field containing "name"
            for key, value in record.items():
                if "name" in key.lower() and value:
                    name = self._clean_string(str(value))
                    break

        if not name:
            return None

        # Generate ID if not present
        centre_id = mapped.get("id", "")
        if not centre_id:
            centre_id = self._generate_id(record)

        # Build the centre object
        centre = SatCentre(
            id=str(centre_id),
            name=name,
            address=self._clean_string(mapped.get("address", "")),
            city=self._clean_string(mapped.get("city", "")),
            state=self._clean_string(mapped.get("state", "")),
            country=self._clean_string(mapped.get("country", "")),
            postal_code=self._clean_string(mapped.get("postal_code", "")),
            phone=self._clean_string(mapped.get("phone", "")),
            latitude=self._parse_float(mapped.get("latitude")),
            longitude=self._parse_float(mapped.get("longitude")),
            metadata={
                "raw_record": record,
                "normalized_at": datetime.now().isoformat(),
            },
        )

        return centre

    def _map_fields(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Map raw field names to our schema using known mappings."""
        result: Dict[str, Any] = {}

        # Try collegeboard mapping first
        for source_key, target_key in self.FIELD_MAPPINGS["collegeboard"].items():
            if source_key in record and record[source_key]:
                result[target_key] = record[source_key]

        # Try generic mapping (won't overwrite existing)
        for source_key, target_key in self.FIELD_MAPPINGS["generic"].items():
            if source_key in record and record[source_key] and target_key not in result:
                result[target_key] = record[source_key]

        return result

    def _generate_id(self, record: Dict[str, Any]) -> str:
        """Generate a deterministic ID for a record."""
        # Try to build ID from key fields
        key_fields = ["name", "city", "state", "country"]
        parts = []
        for field_name in key_fields:
            for key in record:
                if key.lower() == field_name and record[key]:
                    parts.append(str(record[key]).strip().lower())
                    break

        if parts:
            hash_input = "|".join(parts)
            return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

        # Fallback: use UUID
        return uuid.uuid4().hex[:16]

    def _clean_string(self, value: str) -> str:
        """Clean and normalize a string value."""
        if not value:
            return ""
        # Remove extra whitespace
        value = re.sub(r"\s+", " ", value).strip()
        # Remove null bytes
        value = value.replace("\x00", "")
        return value

    def _parse_float(self, value: Any) -> Optional[float]:
        """Parse a value as float, returning None on failure."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def save(
        self, centres: List[SatCentre], filename: str = "sat_centres.json"
    ) -> Path:
        """
        Save normalised centres to a JSON file.

        Args:
            centres: List of SatCentre objects.
            filename: Output filename.

        Returns:
            Path to the saved file.
        """
        file_path = self.generated_dir / filename
        data = [c.to_dict() for c in centres]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return file_path

    def load(self, filename: str = "sat_centres.json") -> List[SatCentre]:
        """
        Load previously normalised centres from a JSON file.

        Args:
            filename: Input filename.

        Returns:
            List of SatCentre objects.
        """
        file_path = self.generated_dir / filename
        if not file_path.exists():
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [SatCentre.from_dict(record) for record in data]
