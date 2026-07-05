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
        self, centre: SatCentre, schema_map: Dict[str, Any],
        flat_centre: Dict[str, Any], flat_raw: Dict[str, Any],
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
                value = self._resolve_source(source, flat_centre, flat_raw)
                self._set_nested(result, user_field, value)

            return result
        except Exception as e:
            logger.warning(f"Failed to transform centre '{centre.name}': {e}")
            return None

    def _resolve_source(
        self, source: str, flat_centre: Dict[str, Any], flat_raw: Dict[str, Any]
    ) -> Any:
        """
        Resolve a source expression to its value.

        Args:
            source: Source expression (field name, "raw.field_name", or "literal:value").
            flat_centre: Flattened SatCentre dictionary.
            flat_raw: Flattened raw record dictionary.

        Returns:
            The resolved value.
        """
        if source.startswith("literal:"):
            return source[8:]
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
