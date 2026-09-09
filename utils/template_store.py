"""
SAT Centre Updater - Schema Template Store

Manages reusable JSON schema templates for the "Transform to Custom Schema"
feature. Each template is a saved sample JSON object (a single dict) stored as
a .json file in the templates directory.

Usage:
    from utils.template_store import TemplateStore

    store = TemplateStore()
    names = store.list_templates()
    sample = store.get_template("locations")
    store.save_template("locations", sample)
    store.delete_template("locations")
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


class TemplateStore:
    """
    Manage saved JSON schema templates.

    Templates are plain JSON objects (dicts) stored one-per-file in the
    templates directory. Their content is exactly what would otherwise be
    pasted interactively as a sample JSON excerpt for schema transformation.
    """

    VALID_NAME_RE = re.compile(r"^[\w\-]+$")

    def __init__(self, templates_dir: Path | None = None) -> None:
        """
        Initialize the template store.

        Args:
            templates_dir: Directory holding template files. Defaults to the
                configured templates directory.
        """
        self.templates_dir = templates_dir or settings.PATHS.TEMPLATES_DIR
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self) -> list[str]:
        """
        List all saved template names (sorted).

        Returns:
            Sorted list of template names without the .json extension.
        """
        names: list[str] = []
        if not self.templates_dir.is_dir():
            return names
        for path in self.templates_dir.glob("*.json"):
            if path.is_file():
                names.append(path.stem)
        return sorted(names)

    def template_exists(self, name: str) -> bool:
        """Return True if a template with the given name exists."""
        return self._path_for(name).is_file()

    def get_template(self, name: str) -> dict[str, Any] | None:
        """
        Load a saved template by name.

        Args:
            name: Template name (without .json extension).

        Returns:
            The template object, or None if it does not exist, is invalid,
            or is not a JSON object.
        """
        path = self._path_for(name)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning(f"Template '{name}' is not valid JSON: {path}")
            return None
        if not isinstance(data, dict):
            logger.warning(
                f"Template '{name}' must be a JSON object, got {type(data).__name__}"
            )
            return None
        return data

    def save_template(self, name: str, sample: dict[str, Any]) -> Path:
        """
        Save a sample JSON object as a named template.

        Args:
            name: Template name (no extension). Restricted to word chars/dash.
            sample: The sample JSON object to save.

        Returns:
            Path to the saved template file.

        Raises:
            ValueError: If the name is invalid.
            TypeError: If the sample is not a dict.
        """
        name = self._validate_name(name)
        if not isinstance(sample, dict):
            raise TypeError("Template must be a JSON object (dict).")

        path = self._path_for(name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved template '{name}' -> {path}")
        return path

    def delete_template(self, name: str) -> bool:
        """
        Delete a saved template by name.

        Args:
            name: Template name.

        Returns:
            True if a template was removed, False if it did not exist.
        """
        path = self._path_for(name)
        if not path.is_file():
            return False
        path.unlink()
        logger.info(f"Deleted template '{name}'")
        return True

    def _validate_name(self, name: str) -> str:
        """Validate and normalize a template name."""
        name = name.strip()
        if not name:
            raise ValueError("Template name cannot be empty.")
        if not self.VALID_NAME_RE.match(name):
            raise ValueError(
                f"Invalid template name '{name}'. Use letters, digits, '_' or '-'."
            )
        return name

    def _path_for(self, name: str) -> Path:
        """Return the file path for a template name."""
        return self.templates_dir / f"{name}.json"
