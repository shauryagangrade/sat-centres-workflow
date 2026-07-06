# SAT Centre Updater

[![CI](https://github.com/shauryagangrade/sat-centres-workflow/actions/workflows/ci.yml/badge.svg)](https://github.com/shauryagangrade/sat-centres-workflow/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

A production-quality Python application that automatically downloads, processes, geocodes, validates, and exports SAT examination centres.

**Only one user input required**: a browser cURL copied from the official SAT website's Network tab.

![SAT Centre Updater — pipeline in action](./new-workflow.gif)

> ⭐ If this tool saves you time, please star the repo — it helps others find it.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full pipeline
python main.py --full

# Or use the interactive menu
python main.py
```

## How It Works

1. **Copy cURL** from Chrome DevTools → Network tab → right-click request → Copy as cURL
2. **Paste** when prompted, or save to a file and use `--curl-file`
3. **Run** and the pipeline handles everything automatically:

```
Paste cURL → Parse → Download → Normalize → Geocode → Validate → Update → Reports
```

An optional **Schema Transform** step lets you reshape the output to any custom JSON structure.

## Usage

### Full Pipeline

```bash
python main.py --full
python main.py --full --curl-file curl.txt
python main.py --full --force-geocode
python main.py --full --transform --sample-json schema.json
```

### Individual Steps

```bash
python main.py --download --curl-file curl.txt
python main.py --normalize
python main.py --geocode
python main.py --validate
python main.py --update
python main.py --reports
python main.py --resume
python main.py --transform --sample-json schema.json
```

### Interactive Menu

```bash
python main.py
```

```
┌─ SAT Centre Updater ──────────────────────┐
│ 1  Download SAT Data                       │
│ 2  Normalize                               │
│ 3  Geocode                                 │
│ 4  Validate                                │
│ 5  Update Dataset                          │
│ 6  Reports                                 │
│ 7  Resume Failed                           │
│ 8  Full Pipeline                           │
│ 9  Transform to Custom Schema              │
│ 0  Exit                                    │
└────────────────────────────────────────────┘
```

### Options

| Flag | Description |
|------|-------------|
| `--full` | Run the full pipeline end-to-end |
| `--paste-curl` | Paste cURL interactively |
| `--curl-file <path>` | Read cURL from a file |
| `--download` | Download only |
| `--normalize` | Normalize only |
| `--geocode` | Geocode only |
| `--validate` | Validate only |
| `--update` | Update dataset only |
| `--reports` | Generate reports only |
| `--resume` | Resume failed centres |
| `--transform` | Apply schema transformation after normalize |
| `--sample-json <path>` | Path to a JSON file defining the target schema |
| `--force-geocode` | Force re-geocoding of all centres |
| `--confidence <float>` | Override confidence threshold |
| `--workers <int>` | Override max geocoding workers |
| `--log-level <level>` | Set log level (DEBUG/INFO/WARNING/ERROR) |

## Schema Transformer

The Schema Transformer lets you reshape the normalized centre data into any custom JSON structure. Paste a sample JSON excerpt showing the fields you need, and the system automatically infers which source fields to map.

### How It Works

1. Paste a sample JSON object with the keys you want (interactive mode, option 9)
2. The system infers field mappings (handles aliases like `lat` → `latitude`, `centre_name` → `name`)
3. Supports nested objects (e.g. `location.lat`, `contact.phone`)
4. Preserves literal string values (e.g. `"type": "school"` stays as-is)
5. Outputs a transformed `locations.json` file

### CLI Usage

```bash
# Pass a sample JSON file
python main.py --transform --sample-json schema.json

# Run full pipeline with transform
python main.py --full --transform --sample-json schema.json

# Interactive: paste a sample JSON object
python main.py  # then select option 9
```

### Example Schema

If your target format looks like this:

```json
{
  "location_name": "Legacy International School",
  "type": "school",
  "coordinates": {
    "lat": 12.9716,
    "lon": 77.5946
  },
  "city": "Bangalore",
  "country": "India"
}
```

The transformer infers the mapping automatically and outputs all centres in that structure.

## Map Viewer

An interactive browser-based map for visualising geocoded centres. Open `map/index.html` in any browser — no server required.

- **Auto-loads** `map/sample_centres.json` on startup (edit or replace this file with your data)
- **Drag & drop** a JSON file onto the map, or use the file picker
- Supports `latitude`/`longitude` **and** `lat`/`lng` field names
- Each pin shows a popup with centre name, address, and coordinates

## Evidence-Based Verification

The geocoding pipeline uses an evidence-based verification system instead of simple fuzzy scoring. Each candidate accumulates independent evidence signals across five categories:

| Evidence Category | Weight | Description |
|-------------------|--------|-------------|
| **Text Match** | 30% | Name/address similarity using fuzzy matching |
| **Geography** | 25% | Coordinate proximity and country/region checks |
| **Provider Consensus** | 20% | Agreement across Nominatim, Photon, Geoapify |
| **Place Type** | 15% | Category verification (school, test centre) |
| **Historical** | 10% | Consistency with previous geocoding results |

Confidence is calibrated via a sigmoid function and classified into states: **Verified**, **Highly Likely**, **Likely**, **Needs Review**, or **Low Confidence**.

## Project Structure

```
sat_updater/
├── main.py                  # CLI entry point
├── config.py                # Centralised configuration
├── requirements.txt         # Python dependencies
│
├── connectors/
│   └── sat_connector.py     # High-level SAT data connector
│
├── processing/
│   ├── curl_parser.py       # cURL command parser
│   ├── downloader.py        # HTTP downloader with retries
│   ├── normalizer.py        # Data normalisation to SatCentre schema
│   ├── query_generator.py   # Geocoding query generation
│   ├── geocoder.py          # Evidence-based geocoding orchestrator
│   ├── scorer.py            # Candidate scoring (RapidFuzz)
│   ├── validator.py         # Centre validation rules
│   ├── updater.py           # Dataset update/merge
│   ├── schema_transformer.py# Custom schema transformation
│   └── exporter.py          # Report generation (MD, HTML)
│
├── providers/
│   ├── nominatim.py         # OpenStreetMap Nominatim
│   ├── photon.py            # Komoot Photon
│   ├── geoapify.py          # Geoapify API
│   ├── overpass.py           # Overpass API (school search)
│   └── provider_manager.py  # Provider orchestration & multi-provider consensus
│
├── verification/            # Evidence-based verification system
│   ├── verifier.py          # Orchestrates evidence collection
│   ├── decision_engine.py   # State classification & candidate selection
│   ├── confidence.py        # Sigmoid-calibrated confidence scoring
│   ├── fusion.py            # Evidence fusion into unified scores
│   ├── report.py            # Audit trail generation
│   ├── models.py            # Verification data models
│   └── evidence/            # Independent evidence collectors
│       ├── text.py          # Text matching signals
│       ├── geography.py     # Geographic proximity signals
│       ├── providers.py     # Provider consensus signals
│       ├── place_type.py    # Category verification signals
│       └── history.py       # Historical consistency signals
│
├── map/
│   ├── index.html           # Interactive Leaflet.js map viewer
│   └── sample_centres.json  # Sample data for the map
│
├── cache/
│   └── cache_manager.py     # SQLite-backed persistent cache
│
├── utils/
│   ├── helpers.py           # Shared utility functions
│   ├── country_normalizer.py# Centralised country name normalisation
│   └── logger.py            # Logging configuration
│
├── datasets/
│   └── sat/
│       ├── raw/             # Raw API responses
│       ├── generated/       # Normalised centre data
│       ├── output/          # Final production-ready JSON
│       └── reports/         # Validation & change reports
│
├── tests/                   # Unit tests
└── logs/                    # Daily log files
```

## Output Files

| File | Location | Description |
|------|----------|-------------|
| `sat_centres.json` | `datasets/sat/generated/` | Normalised centre data |
| `locations.json` | `datasets/sat/generated/` | Schema-transformed data (when `--transform` is used) |
| `sat_centre.json` | `datasets/sat/output/` | Final production-ready dataset |
| `summary.md` | `datasets/sat/reports/` | Markdown summary report |
| `summary.html` | `datasets/sat/reports/` | HTML summary report |
| `changes.csv` | `datasets/sat/reports/` | Change log |
| `duplicates.csv` | `datasets/sat/reports/` | Duplicate centres |
| `failed.csv` | `datasets/sat/reports/` | Failed validations |

## Geocoding Providers

The system queries all providers for consensus evidence:

1. **Nominatim** — OpenStreetMap (free, 1 req/s)
2. **Photon** — Komoot (free, fast)
3. **Geoapify** — Commercial (free tier: 3000/day)
4. **Overpass** — School-specific search (fallback)

Provider order, rate limits, and multi-provider mode are configurable in `config.py`.

## Caching

The system uses a SQLite-backed cache (`cache/cache.db`) with namespaced TTLs to avoid redundant API calls:

| Namespace | Default TTL | Description |
|-----------|-------------|-------------|
| `geocode` | 24 hours | Geocoding results |
| `download` | 1 hour | Raw download responses |
| `http` | 1 hour | HTTP responses |
| `manual` | 1 year | Manual review overrides |

## Configuration

All settings are in `config.py`:

- **HTTP**: Timeouts, retries, user agents
- **Geocoding**: Provider order, confidence threshold, rate limits
- **Cache**: Directories and TTL values
- **Validation**: Country rules, coordinate bounds
- **Export**: Output format and encoding
- **Paths**: All file system paths

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

## Requirements

- Python 3.11+
- Internet connection (for geocoding)
- A browser cURL from the SAT website

## License

Copyright 2026 Shaurya Gangrade.  
Licensed under the [Apache License, Version 2.0](LICENSE).
