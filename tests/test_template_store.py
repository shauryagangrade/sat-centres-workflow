"""
SAT Centre Updater - Schema Template Store Tests

Tests for saving, listing, loading, and deleting reusable schema templates.
"""

import json

import pytest

from utils.template_store import TemplateStore


class TestTemplateStore:
    """Test cases for the TemplateStore class."""

    def make_store(self, tmp_path):
        """Build a TemplateStore backed by a tmp directory."""
        self.store = TemplateStore(templates_dir=tmp_path)
        self.sample = {"name": "", "city": "", "latitude": 0.0}

    def test_save_and_get_round_trip(self, tmp_path):
        """Test that a saved template can be loaded back."""
        self.make_store(tmp_path)
        self.store.save_template("locations", self.sample)
        loaded = self.store.get_template("locations")
        assert loaded == self.sample

    def test_save_creates_dot_json_file(self, tmp_path):
        """Test the saved file gets a .json extension."""
        self.make_store(tmp_path)
        path = self.store.save_template("locations", self.sample)
        assert path == tmp_path / "locations.json"
        assert path.exists()

    def test_list_templates_sorted(self, tmp_path):
        """Test listing returns sorted names without extensions."""
        self.make_store(tmp_path)
        self.store.save_template("beta", {"a": 1})
        self.store.save_template("alpha", {"b": 2})
        self.store.save_template("gamma", {"c": 3})
        assert self.store.list_templates() == ["alpha", "beta", "gamma"]

    def test_list_templates_empty_dir(self, tmp_path):
        """Test listing an empty directory returns an empty list."""
        self.make_store(tmp_path)
        assert self.store.list_templates() == []

    def test_overwrite_existing_template(self, tmp_path):
        """Test re-saving overwrites the previous template."""
        self.make_store(tmp_path)
        self.store.save_template("locations", {"a": 1})
        self.store.save_template("locations", {"b": 2})
        loaded = self.store.get_template("locations")
        assert loaded == {"b": 2}
        assert self.store.list_templates() == ["locations"]

    def test_template_exists(self, tmp_path):
        """Test template_exists reflects saved state."""
        self.make_store(tmp_path)
        assert not self.store.template_exists("locations")
        self.store.save_template("locations", self.sample)
        assert self.store.template_exists("locations")

    def test_delete_existing(self, tmp_path):
        """Test deleting an existing template returns True."""
        self.make_store(tmp_path)
        self.store.save_template("locations", self.sample)
        assert self.store.delete_template("locations") is True
        assert self.store.list_templates() == []

    def test_delete_missing(self, tmp_path):
        """Test deleting a missing template returns False."""
        self.make_store(tmp_path)
        assert self.store.delete_template("nope") is False

    def test_get_missing_template(self, tmp_path):
        """Test getting a missing template returns None."""
        self.make_store(tmp_path)
        assert self.store.get_template("nope") is None

    def test_get_invalid_json(self, tmp_path):
        """Test getting a template with invalid JSON returns None."""
        self.make_store(tmp_path)
        (tmp_path / "broken.json").write_text("{not valid json", encoding="utf-8")
        assert self.store.get_template("broken") is None

    def test_get_non_dict_json(self, tmp_path):
        """Test getting a template that is not a JSON object returns None."""
        self.make_store(tmp_path)
        (tmp_path / "list.json").write_text("[1, 2, 3]", encoding="utf-8")
        assert self.store.get_template("list") is None

    def test_save_non_dict_raises(self, tmp_path):
        """Test saving a non-dict sample raises TypeError."""
        self.make_store(tmp_path)
        with pytest.raises(TypeError, match="JSON object"):
            self.store.save_template("bad", [1, 2, 3])

    def test_save_empty_name_raises(self, tmp_path):
        """Test saving with an empty name raises ValueError."""
        self.make_store(tmp_path)
        with pytest.raises(ValueError, match="cannot be empty"):
            self.store.save_template("  ", self.sample)

    def test_save_invalid_name_raises(self, tmp_path):
        """Test names with disallowed characters raise ValueError."""
        self.make_store(tmp_path)
        for bad in ["../escape", "a/b", "a b", "a.b"]:
            with pytest.raises(ValueError, match="Invalid template name"):
                self.store.save_template(bad, self.sample)

    def test_get_template_with_invalid_name(self, tmp_path):
        """Test getting a template with an invalid name returns None safely."""
        self.make_store(tmp_path)
        assert self.store.get_template("../nope") is None

    def test_unicode_content_round_trip(self, tmp_path):
        """Test unicode content survives a save/load round trip."""
        self.make_store(tmp_path)
        unicode_sample = {"name": "École", "city": "ཀཏམནཌུ"}
        self.store.save_template("unicode", unicode_sample)
        assert self.store.get_template("unicode") == unicode_sample

    def test_nested_sample_round_trip(self, tmp_path):
        """Test nested objects and lists survive a round trip."""
        self.make_store(tmp_path)
        nested = {"location": {"lat": 12.97, "lng": 77.59}, "links": ["a", "b"]}
        self.store.save_template("nested", nested)
        assert self.store.get_template("nested") == nested

    def test_file_content_is_json(self, tmp_path):
        """Test the saved file contains valid pretty-printed JSON."""
        self.make_store(tmp_path)
        self.store.save_template("locations", self.sample)
        content = (tmp_path / "locations.json").read_text(encoding="utf-8")
        assert json.loads(content) == self.sample
