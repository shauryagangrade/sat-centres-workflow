"""
SAT Centre Updater - Main Entry Point Test

Covers the schema-template CLI features added to main.py: parser flags,
template listing, saving templates from files, transforming from a saved
template, and the interactive sample/template helpers.
"""

import io
import json

from rich.console import Console

from config import settings
from processing.normalizer import Normalizer, SatCentre


def _template_store(tmp_path):
    """Build a store-local templates dir and the settings patch paths."""
    templates_dir = tmp_path / "templates"
    return templates_dir


def _make_centres(tmp_path) -> list[SatCentre]:
    """Save a small centre set to a generated dir and return the centres."""
    generated_dir = tmp_path / "generated"
    centres = [
        SatCentre(
            id="1",
            name="Legacy School",
            city="Bangalore",
            state="Karnataka",
            country="India",
            latitude=12.9716,
            longitude=77.5946,
        )
    ]
    Normalizer(generated_dir=generated_dir).save(centres)
    return centres


def _patch_paths(monkeypatch, tmp_path, *, generated: bool = False) -> None:
    """Point template + generated dirs at tmp paths."""
    monkeypatch.setattr(settings.PATHS, "TEMPLATES_DIR", tmp_path / "templates")
    if generated:
        monkeypatch.setattr(settings.PATHS, "GENERATED_DIR", tmp_path / "generated")


def _make_input(lines: list[str]):
    """Create a fake input() that yields lines then raises EOFError."""

    def fake_input(*args, **kwargs) -> str:
        if lines:
            return lines.pop(0)
        raise EOFError

    return fake_input


class TestParserFlags:
    """Tests for the template-related CLI parser flags."""

    def test_parser_exposes_template_flags(self) -> None:
        from main import get_parser

        parser = get_parser()
        args = parser.parse_args(
            [
                "--template",
                "myloc",
                "--list-templates",
                "--save-template",
                "myloc",
                "--sample-json",
                "schema.json",
                "--transform",
            ]
        )

        assert args.template == "myloc"
        assert args.list_templates is True
        assert args.save_template == "myloc"


class TestRunListTemplates:
    """Tests for run_list_templates."""

    def test_list_empty(self, capsys, monkeypatch, tmp_path) -> None:
        from main import run_list_templates

        _patch_paths(monkeypatch, tmp_path)
        run_list_templates()
        out = capsys.readouterr().out
        assert "No saved templates found" in out

    def test_list_populated(self, capsys, monkeypatch, tmp_path) -> None:
        from main import run_list_templates
        from utils.template_store import TemplateStore

        _patch_paths(monkeypatch, tmp_path)
        TemplateStore().save_template("alpha", {"name": ""})
        TemplateStore().save_template("beta", {"city": ""})

        run_list_templates()
        out = capsys.readouterr().out

        assert "alpha" in out
        assert "beta" in out


class TestRunSaveTemplate:
    """Tests for run_save_template."""

    def test_save_success(self, capsys, monkeypatch, tmp_path) -> None:
        from main import run_save_template
        from utils.template_store import TemplateStore

        _patch_paths(monkeypatch, tmp_path)
        sample_file = tmp_path / "schema.json"
        sample_file.write_text('{"name": "", "latitude": 0.0}', encoding="utf-8")

        run_save_template(str(sample_file), "myloc")
        out = capsys.readouterr().out

        assert "Saved template 'myloc'" in out
        assert TemplateStore().get_template("myloc") == {
            "name": "",
            "latitude": 0.0,
        }

    def test_save_file_not_found(self, capsys, monkeypatch, tmp_path) -> None:
        from main import run_save_template

        _patch_paths(monkeypatch, tmp_path)

        run_save_template(str(tmp_path / "missing.json"), "myloc")
        out = capsys.readouterr().out
        assert "File not found" in out

    def test_save_invalid_json(self, capsys, monkeypatch, tmp_path) -> None:
        from main import run_save_template

        _patch_paths(monkeypatch, tmp_path)
        sample_file = tmp_path / "bad.json"
        sample_file.write_text("{not json", encoding="utf-8")

        run_save_template(str(sample_file), "myloc")
        out = capsys.readouterr().out
        assert "Invalid JSON" in out

    def test_save_non_dict(self, capsys, monkeypatch, tmp_path) -> None:
        from main import run_save_template

        _patch_paths(monkeypatch, tmp_path)
        sample_file = tmp_path / "list.json"
        sample_file.write_text("[1, 2, 3]", encoding="utf-8")

        run_save_template(str(sample_file), "myloc")
        out = capsys.readouterr().out
        assert "Sample must be a JSON object" in out

    def test_save_invalid_name(self, capsys, monkeypatch, tmp_path) -> None:
        from main import run_save_template

        _patch_paths(monkeypatch, tmp_path)
        sample_file = tmp_path / "schema.json"
        sample_file.write_text('{"name": ""}', encoding="utf-8")

        run_save_template(str(sample_file), "bad name")
        out = capsys.readouterr().out
        assert "Invalid template name" in out


class TestRunTransformTemplate:
    """Tests for running a transform from a saved template."""

    def test_transform_success(self, capsys, monkeypatch, tmp_path) -> None:
        from main import run_transform
        from utils.template_store import TemplateStore

        _patch_paths(monkeypatch, tmp_path, generated=True)
        _make_centres(tmp_path)
        TemplateStore().save_template("myloc", {"name": "Test", "latitude": 0.0})

        run_transform(template_name="myloc")
        out = capsys.readouterr().out

        assert "Using template 'myloc'" in out
        assert "Transformed 1 records" in out
        assert (tmp_path / "generated" / "locations.json").exists()

    def test_transform_missing_template(self, capsys, monkeypatch, tmp_path) -> None:
        from main import run_transform

        _patch_paths(monkeypatch, tmp_path, generated=True)
        _make_centres(tmp_path)

        run_transform(template_name="nope")
        out = capsys.readouterr().out
        assert "Template 'nope' not found or invalid" in out

    def test_transform_no_centres(self, capsys, monkeypatch, tmp_path) -> None:
        from main import run_transform
        from utils.template_store import TemplateStore

        _patch_paths(monkeypatch, tmp_path, generated=True)
        TemplateStore().save_template("myloc", {"name": ""})

        run_transform(template_name="myloc")
        out = capsys.readouterr().out
        assert "No centres found" in out

    def test_transform_output_content(self, monkeypatch, tmp_path) -> None:
        from utils.template_store import TemplateStore

        _patch_paths(monkeypatch, tmp_path, generated=True)
        _make_centres(tmp_path)
        TemplateStore().save_template("myloc", {"centre_name": "Test", "lat": 0.0})

        from main import run_transform

        run_transform(template_name="myloc")

        output = json.loads(
            (tmp_path / "generated" / "locations.json").read_text(encoding="utf-8")
        )
        assert output[0]["centre_name"] == "Legacy School"
        assert output[0]["lat"] == 12.9716


class TestPromptSampleJson:
    """Tests for the interactive sample JSON helper."""

    def test_returns_dict(self, monkeypatch) -> None:
        from main import _prompt_sample_json

        monkeypatch.setattr("builtins.input", _make_input(['{"name": "", "city": ""}']))
        console = Console(file=io.StringIO(), width=100)

        sample = _prompt_sample_json(console)
        assert sample == {"name": "", "city": ""}

    def test_returns_none_on_empty(self, monkeypatch) -> None:
        from main import _prompt_sample_json

        monkeypatch.setattr("builtins.input", _make_input([]))
        console = Console(file=io.StringIO(), width=100)

        assert _prompt_sample_json(console) is None

    def test_returns_none_on_invalid_json(self, monkeypatch) -> None:
        from main import _prompt_sample_json

        monkeypatch.setattr("builtins.input", _make_input(["{bad"]))
        buffer = io.StringIO()
        console = Console(file=buffer, width=100)

        assert _prompt_sample_json(console) is None
        assert "Invalid JSON" in buffer.getvalue()

    def test_returns_none_on_non_dict(self, monkeypatch) -> None:
        from main import _prompt_sample_json

        monkeypatch.setattr("builtins.input", _make_input(["[1, 2, 3]"]))
        buffer = io.StringIO()
        console = Console(file=buffer, width=100)

        assert _prompt_sample_json(console) is None
        assert "Sample must be a JSON object" in buffer.getvalue()


class TestAddTemplateInteractive:
    """Tests for the interactive add-template helper."""

    def test_saves_template(self, monkeypatch, tmp_path) -> None:
        from main import _add_template_interactive
        from utils.template_store import TemplateStore

        lines = ["myloc", '{"name": "", "lat": 0.0}']
        monkeypatch.setattr("builtins.input", _make_input(lines))
        console = Console(file=io.StringIO(), width=100)

        store = TemplateStore(templates_dir=tmp_path)
        _add_template_interactive(console, store)

        assert store.get_template("myloc") == {"name": "", "lat": 0.0}

    def test_saves_multi_line_json(self, monkeypatch, tmp_path) -> None:
        from main import _add_template_interactive
        from utils.template_store import TemplateStore

        lines = [
            "myloc",
            "{",
            '"name": "Test",',
            '"coordinates": {"lat": 12.97, "lng": 77.59}',
            "}",
        ]
        monkeypatch.setattr("builtins.input", _make_input(lines))
        console = Console(file=io.StringIO(), width=100)

        store = TemplateStore(templates_dir=tmp_path)
        _add_template_interactive(console, store)

        assert store.get_template("myloc") == {
            "name": "Test",
            "coordinates": {"lat": 12.97, "lng": 77.59},
        }

    def test_reports_invalid_name(self, monkeypatch, tmp_path) -> None:
        from main import _add_template_interactive
        from utils.template_store import TemplateStore

        lines = ["../escape", '{"name": ""}']
        monkeypatch.setattr("builtins.input", _make_input(lines))
        buffer = io.StringIO()
        console = Console(file=buffer, width=100)

        store = TemplateStore(templates_dir=tmp_path)
        _add_template_interactive(console, store)

        assert "Invalid template name" in buffer.getvalue()
        assert store.list_templates() == []
