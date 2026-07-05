"""
SAT Centre Updater - Updater Module

Updates the final sat_centre.json dataset by merging geocoded data with any existing dataset.
Preserves all unrelated fields and only updates location-related fields.

Usage:
    from processing.updater import DatasetUpdater

    updater = DatasetUpdater()
    summary = updater.update(old_centres, new_centres)
"""

import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from config import settings
from processing.normalizer import SatCentre

logger = logging.getLogger(__name__)


@dataclass
class UpdateSummary:
    """Summary of the update operation."""

    total: int = 0
    new_centres: int = 0
    updated_centres: int = 0
    removed_centres: int = 0
    unchanged_centres: int = 0
    changes: List[Dict[str, Any]] = field(default_factory=list)


class DatasetUpdater:
    """
    Merges new geocoded centres into the existing output dataset.

    Update logic:
    - New centres (not in existing): added with full data
    - Existing centres (matched by ID): location fields updated, rest preserved
    - Removed centres (in existing but not new): removed from output
    """

    # Fields considered "location-related" and eligible for update
    LOCATION_FIELDS: Set[str] = {
        "latitude",
        "longitude",
        "address",
        "city",
        "state",
        "country",
        "postal_code",
    }

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        """
        Initialize the updater.

        Args:
            output_dir: Directory for output files. Defaults to config setting.
        """
        self.output_dir = output_dir or settings.PATHS.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir = settings.PATHS.REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def update(
        self,
        existing_centres: List[SatCentre],
        new_centres: List[SatCentre],
    ) -> Tuple[List[SatCentre], UpdateSummary]:
        """
        Merge new centres into existing dataset.

        Args:
            existing_centres: Previously exported centres.
            new_centres: Newly geocoded centres.

        Returns:
            Tuple of (merged_centres, summary).
        """
        summary = UpdateSummary(total=len(new_centres))

        existing_map: Dict[str, SatCentre] = {c.id: c for c in existing_centres if c.id}
        new_map: Dict[str, SatCentre] = {c.id: c for c in new_centres if c.id}

        existing_ids: Set[str] = set(existing_map.keys())
        new_ids: Set[str] = set(new_map.keys())

        merged: List[SatCentre] = []

        # Process new centres
        for centre in new_centres:
            if centre.id in existing_ids:
                # Update existing
                old = existing_map[centre.id]
                updated = self._merge_centre(old, centre)
                if updated:
                    summary.updated_centres += 1
                    summary.changes.append(updated)
                else:
                    summary.unchanged_centres += 1
                merged.append(existing_map[centre.id] if not updated else centre)
            else:
                # New centre
                summary.new_centres += 1
                merged.append(centre)

        # Track removed centres
        removed_ids = existing_ids - new_ids
        summary.removed_centres = len(removed_ids)

        # Export change report
        if summary.changes:
            self._export_changes(summary.changes)

        return merged, summary

    def _merge_centre(
        self, old: SatCentre, new: SatCentre
    ) -> Optional[Dict[str, Any]]:
        """
        Merge location fields from new into old, preserving other fields.

        Args:
            old: Existing centre.
            new: New centre with updated location data.

        Returns:
            Dictionary describing the change, or None if no change.
        """
        changes: Dict[str, Any] = {"id": old.id, "name": old.name}

        for field_name in self.LOCATION_FIELDS:
            new_val = getattr(new, field_name, None)
            old_val = getattr(old, field_name, None)

            if new_val is not None and new_val != old_val:
                changes[field_name] = {"old": old_val, "new": new_val}
                setattr(old, field_name, new_val)

        # Update metadata
        old.metadata.update(new.metadata)

        if len(changes) > 1:  # More than just 'id' and 'name'
            return changes

        return None

    def _export_changes(self, changes: List[Dict[str, Any]]) -> Path:
        """
        Export change details to CSV.

        Args:
            changes: List of change dictionaries.

        Returns:
            Path to the exported CSV.
        """
        file_path = self.reports_dir / "changes.csv"

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "field", "old_value", "new_value"])

            for change in changes:
                centre_id = change.get("id", "")
                name = change.get("name", "")

                for field_name, vals in change.items():
                    if field_name in ("id", "name"):
                        continue
                    if isinstance(vals, dict):
                        writer.writerow([
                            centre_id,
                            name,
                            field_name,
                            vals.get("old", ""),
                            vals.get("new", ""),
                        ])

        return file_path

    def save(
        self, centres: List[SatCentre], filename: str = "sat_centre.json"
    ) -> Path:
        """
        Save the final dataset to JSON.

        Args:
            centres: List of SatCentre objects.
            filename: Output filename.

        Returns:
            Path to the saved file.
        """
        file_path = self.output_dir / filename

        data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_centres": len(centres),
                "version": "1.0.0",
            },
            "centres": [c.to_dict() for c in centres],
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return file_path

    def load_existing(self, filename: str = "sat_centre.json") -> List[SatCentre]:
        """
        Load the existing output dataset.

        Args:
            filename: Input filename.

        Returns:
            List of SatCentre objects.
        """
        file_path = self.output_dir / filename
        if not file_path.exists():
            return []

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        centres_data = data.get("centres", data) if isinstance(data, dict) else data
        return [SatCentre.from_dict(record) for record in centres_data]

    def export_duplicates(self, centres: List[SatCentre]) -> Optional[Path]:
        """
        Find and export duplicate centres.

        Args:
            centres: List of centres to check.

        Returns:
            Path to duplicates CSV, or None if no duplicates found.
        """
        seen: Dict[str, List[SatCentre]] = {}

        for centre in centres:
            key = f"{centre.latitude}_{centre.longitude}"
            if key in seen:
                seen[key].append(centre)
            else:
                seen[key] = [centre]

        duplicates = {k: v for k, v in seen.items() if len(v) > 1}
        if not duplicates:
            return None

        file_path = self.reports_dir / "duplicates.csv"
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "name", "city", "state", "country", "latitude", "longitude"])
            for coords, centre_list in duplicates.items():
                for c in centre_list:
                    writer.writerow([c.id, c.name, c.city, c.state, c.country, c.latitude, c.longitude])

        return file_path
