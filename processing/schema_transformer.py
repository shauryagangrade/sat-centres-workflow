"""
SAT Centre Updater - Schema Transformer Module

Infers the user's desired output schema from a sample JSON excerpt
and transforms normalized SatCentre data to match.

Usage:
    from processing.schema_transformer import SchemaTransformer

    transformer = SchemaTransformer()
    transformed = transformer.transform(centres, sample_json)
    transformer.save(transformed)
"""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from processing.normalizer import SatCentre

logger = logging.getLogger(__name__)


class SchemaTransformer:
    """
    Transforms normalized SatCentre data to match a user's desired output schema.

    Given a sample JSON excerpt, this module:
    1. Infers which fields from the normalized data map to the user's schema
    2. Supports nested objects (e.g., "location.lat" -> latitude)
    3. Supports literal values (e.g., "type": "school" stays as-is)
    4. Supports field renaming (e.g., "name" -> "centre_name")
    """

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """
        Initialize the schema transformer.

        Args:
            output_dir: Directory for transformed output. Defaults to config setting.
        """
        self.output_dir = output_dir or settings.PATHS.GENERATED_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def infer_schema(
        self, sample: Dict[str, Any], centres: List[SatCentre]
    ) -> Dict[str, Any]:
        """
        Infer the mapping between user's sample schema and available fields.

        Args:
            sample: User's sample JSON excerpt (single object).
            centres: Normalized SatCentre objects to infer from.

        Returns:
            Mapping dict: {user_field_path: source_expression}
            where source_expression is either a SatCentre field name,
            a dot-path into the raw_record, or a literal string.
        """
        # Get available fields from the first centre
        sample_record = centres[0].to_dict() if centres else {}
        raw_record = centres[0].metadata.get("raw_record", {}) if centres else {}

        # Flatten the sample to understand what the user wants
        flat_sample = self._flatten_dict(sample)

        # Flatten available data sources
        flat_centre = self._flatten_dict(sample_record)
        flat_raw = self._flatten_dict(raw_record)

        schema_map: Dict[str, Any] = {}

        for user_field, sample_value in flat_sample.items():
            # Try to find a matching field in the normalized data
            source = self._find_source(user_field, flat_centre, flat_raw)
            if source is not None:
                schema_map[user_field] = source
            elif isinstance(sample_value, str):
                # Check if it's a URL with coordinates that can be templated
                template = self._detect_url_template(sample_value)
                if template:
                    # Store both template and original for fallback
                    schema_map[user_field] = (
                        f"url_template:{template}|||{sample_value}"
                    )
                else:
                    # Preserve literal string values from the sample
                    schema_map[user_field] = f"literal:{sample_value}"

        return schema_map

    def transform(
        self,
        centres: List[SatCentre],
        sample: Dict[str, Any],
        schema_map: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Transform centres to match the user's desired schema.

        Args:
            centres: Normalized SatCentre objects.
            sample: User's sample JSON excerpt.
            schema_map: Optional pre-computed schema map.
                If None, will infer from the sample.

        Returns:
            List of transformed dictionaries matching the user's schema.
        """
        if schema_map is None:
            schema_map = self.infer_schema(sample, centres)

        logger.info(f"Schema map ({len(schema_map)} fields):")
        for field, source in schema_map.items():
            logger.info(f"  {field} <- {source}")

        results: List[Dict[str, Any]] = []
        for centre in centres:
            centre_dict = centre.to_dict()
            flat_centre = self._flatten_dict(centre_dict)
            raw_record = centre.metadata.get("raw_record", {})
            flat_raw = self._flatten_dict(raw_record)
            transformed = self._apply_schema(centre, schema_map, flat_centre, flat_raw)
            if transformed:
                results.append(transformed)

        return results

    def transform_to_json(
        self,
        centres: List[SatCentre],
        sample: Dict[str, Any],
        filename: str = "locations.json",
    ) -> Path:
        """
        Transform centres and save as JSON file.

        Args:
            centres: Normalized SatCentre objects.
            sample: User's sample JSON excerpt.
            filename: Output filename.

        Returns:
            Path to the saved file.
        """
        transformed = self.transform(centres, sample)
        return self.save(transformed, filename)

    def save(
        self,
        data: List[Dict[str, Any]],
        filename: str = "locations.json",
    ) -> Path:
        """
        Save transformed data to JSON file.

        Args:
            data: List of transformed dictionaries.
            filename: Output filename.

        Returns:
            Path to the saved file.
        """
        file_path = self.output_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(data)} records to {file_path}")
        return file_path

    def _flatten_dict(
        self, d: Dict[str, Any], parent_key: str = "", sep: str = "."
    ) -> Dict[str, Any]:
        """
        Flatten a nested dictionary.

        Args:
            d: Dictionary to flatten.
            parent_key: Prefix for nested keys.
            sep: Separator between keys.

        Returns:
            Flattened dictionary.
        """
        items: List[Tuple[str, Any]] = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep).items())
            elif isinstance(v, list):
                # For lists, store as-is (don't flatten)
                items.append((new_key, v))
            else:
                items.append((new_key, v))
        return dict(items)

    # Common field name aliases -> canonical SatCentre field names
    FIELD_ALIASES: Dict[str, str] = {
        "lat": "latitude",
        "lng": "longitude",
        "lon": "longitude",
        "centre_name": "name",
        "center_name": "name",
        "test_center_name": "name",
        "test_centre_name": "name",
        "street": "address",
        "street_address": "address",
        "town": "city",
        "province": "state",
        "region": "state",
        "zip": "postal_code",
        "zipcode": "postal_code",
        "zip_code": "postal_code",
        "postcode": "postal_code",
        "phone_number": "phone",
        "telephone": "phone",
    }

    def _find_source(
        self,
        user_field: str,
        flat_centre: Dict[str, Any],
        flat_raw: Dict[str, Any],
    ) -> Optional[str]:
        """
        Find the best source field for a user's desired field.

        Args:
            user_field: The field name the user wants.
            flat_centre: Flattened SatCentre dictionary.
            flat_raw: Flattened raw record dictionary.

        Returns:
            Source expression string, or None if not found.
        """
        # 1. Direct match in SatCentre fields
        if user_field in flat_centre:
            return user_field

        # 2. Direct match in raw record fields
        if user_field in flat_raw:
            return f"raw.{user_field}"

        # 3. Check known aliases (e.g. "lat" -> "latitude")
        canonical = self.FIELD_ALIASES.get(user_field.lower())
        if canonical and canonical in flat_centre:
            return canonical

        return None

    def _apply_schema(
        self,
        centre: SatCentre,
        schema_map: Dict[str, Any],
        flat_centre: Dict[str, Any],
        flat_raw: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Apply the schema mapping to a single centre.

        Args:
            centre: SatCentre object to transform.
            schema_map: Mapping of user fields to source expressions.
            flat_centre: Pre-flattened SatCentre dictionary.
            flat_raw: Pre-flattened raw record dictionary.

        Returns:
            Transformed dictionary, or None if transformation fails.
        """
        try:
            result: Dict[str, Any] = {}
            for user_field, source in schema_map.items():
                value = self._resolve_source(source, flat_centre, flat_raw, centre)
                self._set_nested(result, user_field, value)

            return result
        except Exception as e:
            logger.warning(f"Failed to transform centre '{centre.name}': {e}")
            return None

    def _detect_url_template(self, value: str) -> Optional[str]:
        """
        Detect if a string is a URL containing coordinates and convert to template.

        Examples:
            "https://maps.google.com/?q=12.9716,77.5946"
            -> "https://maps.google.com/?q={lat},{lng}"

            "https://example.com/place?lat=12.9716&lon=77.5946"
            -> "https://example.com/place?lat={lat}&lon={lng}"

        Args:
            value: String value to check.

        Returns:
            URL template string with {lat}/{lng} placeholders, or None.
        """
        if not value:
            return None

        value = value.strip()

        # Check if it looks like a URL
        if not (value.startswith("http://") or value.startswith("https://")):
            return None

        # Pattern 1: coordinates as query param value (e.g., ?q=lat,lng)
        # Matches: 12.9716,77.5946 or 12.9716%2C77.5946
        coord_pattern = r"([\-]?\d+\.\d{2,8})[,%]2?C?([\-]?\d+\.\d{2,8})"
        match = re.search(coord_pattern, value)
        if match:
            lat_str, lng_str = match.group(1), match.group(2)
            # Verify these look like valid coordinates
            try:
                lat, lng = float(lat_str), float(lng_str)
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    # Use position-based replacement to avoid replacing
                    # occurrences elsewhere in the URL
                    start, end = match.start(), match.end()
                    matched_text = match.group(0)
                    # Determine separator between coords in the match
                    sep_match = re.search(
                        r"[,%]2?C?", matched_text[len(lat_str) :],
                    )
                    sep = sep_match.group(0) if sep_match else ","
                    template = (
                        value[:start]
                        + f"{{lat}}{sep}{{lng}}"
                        + value[end:]
                    )
                    return template
            except ValueError:
                pass

        # Pattern 2: lat/lng as separate query params
        # e.g., ?lat=12.9716&lon=77.5946 or ?latitude=12.9716&longitude=77.5946
        lat_match = re.search(
            r"[?&](?:lat|latitude)=([\-]?\d+\.\d{2,8})", value, re.IGNORECASE
        )
        lng_match = re.search(
            r"[?&](?:lng|lon|longitude)=([\-]?\d+\.\d{2,8})", value, re.IGNORECASE
        )
        if lat_match and lng_match:
            lat_str = lat_match.group(1)
            lng_str = lng_match.group(1)
            try:
                lat, lng = float(lat_str), float(lng_str)
                if -90 <= lat <= 90 and -180 <= lng <= 180:
                    template = value
                    # Replace the lat value (use longer match first to avoid partial replacement)
                    lat_param = lat_match.group(0)
                    lng_param = lng_match.group(0)
                    lat_key = lat_param.split("=")[0]
                    lng_key = lng_param.split("=")[0]
                    # Use the matched position to replace only the coordinate values
                    lat_start = lat_match.start()
                    lat_end = lat_match.end()
                    lng_start = lng_match.start()
                    lng_end = lng_match.end()
                    # Adjust lng position since we'll modify the string
                    if lng_start > lat_start:
                        lng_start += len(f"{lat_key}={{lat}}") - len(lat_param)
                        lng_end += len(f"{lat_key}={{lat}}") - len(lat_param)
                    template = (
                        template[:lat_start]
                        + f"{lat_key}={{lat}}"
                        + template[lat_end:lng_start]
                        + f"{lng_key}={{lng}}"
                        + template[lng_end:]
                    )
                    return template
            except ValueError:
                pass

        return None

    def _resolve_source(
        self,
        source: str,
        flat_centre: Dict[str, Any],
        flat_raw: Dict[str, Any],
        centre: Optional[SatCentre] = None,
    ) -> Any:
        """
        Resolve a source expression to its value.

        Args:
            source: Source expression (field name, "raw.field_name", "literal:value",
                    or "url_template:template").
            flat_centre: Flattened SatCentre dictionary.
            flat_raw: Flattened raw record dictionary.
            centre: Optional SatCentre for coordinate substitution.

        Returns:
            The resolved value.
        """
        if source.startswith("literal:"):
            return source[8:]
        if source.startswith("url_template:"):
            parts = source[13:].split("|||", 1)
            template = parts[0]
            original = parts[1] if len(parts) > 1 else template
            if centre and centre.latitude is not None and centre.longitude is not None:
                return template.format(
                    lat=centre.latitude, lng=centre.longitude
                )
            return original
        if source.startswith("raw."):
            raw_key = source[4:]
            return flat_raw.get(raw_key)
        return flat_centre.get(source)

    def _set_nested(self, d: Dict[str, Any], key: str, value: Any) -> None:
        """
        Set a value in a nested dictionary using dot notation.

        Args:
            d: Dictionary to modify.
            key: Dot-separated key path.
            value: Value to set.
        """
        keys = key.split(".")
        current = d
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
