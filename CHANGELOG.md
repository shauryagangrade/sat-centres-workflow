# Changelog

All notable changes to **sat-centres-workflow** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Apache-2.0 LICENSE
- CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md
- .gitignore for Python projects
- GitHub issue/PR templates and CI workflow
- Dependabot configuration for automated dependency updates

---

## [1.0.0] - 2026-07-05

### Added
- Full pipeline: download → normalize → geocode → validate → update → reports
- Multi-provider geocoding with automatic fallback (Nominatim → Photon → Geoapify → Overpass)
- SQLite-backed persistent cache with namespaced TTLs
- Schema Transformer for reshaping output to any custom JSON structure
- Rich interactive CLI menu and full `--full` batch mode
- Configurable via `config.py` (HTTP, geocoding, cache, paths, validation, export)
- Pydantic v2 data models for validated `SatCentre` schema
- `pytest` test suite with async support

[Unreleased]: https://github.com/shauryagangrade/sat-centres-workflow/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/shauryagangrade/sat-centres-workflow/releases/tag/v1.0.0
