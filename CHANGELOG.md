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
- Evidence-based verification pipeline (`verification/` module) replacing simple fuzzy scoring
  - Independent evidence collectors: text match, geography, provider consensus, place type, history
  - Sigmoid-calibrated confidence calculator with state classification (Verified → Low Confidence)
  - Decision engine with audit trail generation
  - Evidence fusion combining weighted signals into unified scores
- Multi-provider candidate retrieval for consensus assessment (`geocode_all_providers`)
- Interactive map viewer (`map/index.html`) using Leaflet.js + OpenStreetMap
  - Drag & drop or file picker for JSON input
  - Supports `latitude`/`longitude` and `lat`/`lng` field names
  - Auto-loads `sample_centres.json` on startup
- Schema Transformer URL template detection for coordinate placeholders
- Centralised country normalisation utility (`utils/country_normalizer.py`)
- Configuration section for verification settings (`VerificationSettings` in `config.py`)

### Changed
- Geocoding pipeline now queries ALL providers for consensus instead of stopping at first success
- `GeocodeResult` dataclass updated with verification state, audit entries, and evidence summary
- Centre metadata now includes `verification_state` and `evidence_summary`
- README updated with verification pipeline docs, map viewer section, and project structure

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
