# SAT Centre Updater

A production-quality Python application that automatically downloads, processes, geocodes, validates, and exports SAT examination centres.

**Only one user input required**: a browser cURL copied from the official SAT website's Network tab.

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

## Usage

### Full Pipeline

```bash
python main.py --full
python main.py --full --curl-file curl.txt
python main.py --full --force-geocode
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
```

### Interactive Menu

```bash
python main.py
```

```
┌─ SAT Centre Updater ──────────────┐
│ 1  Download SAT Data               │
│ 2  Normalize                       │
│ 3  Geocode                         │
│ 4  Validate                        │
│ 5  Update Dataset                  │
│ 6  Reports                         │
│ 7  Resume Failed                   │
│ 8  Full Pipeline                   │
│ 0  Exit                            │
└────────────────────────────────────┘
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
| `--force-geocode` | Force re-geocoding of all centres |
| `--confidence <float>` | Override confidence threshold |
| `--workers <int>` | Override max geocoding workers |
| `--log-level <level>` | Set log level (DEBUG/INFO/WARNING/ERROR) |

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
│   ├── geocoder.py          # Main geocoding orchestrator
│   ├── scorer.py            # Candidate scoring (RapidFuzz)
│   ├── validator.py         # Centre validation rules
│   ├── updater.py           # Dataset update/merge
│   └── exporter.py          # Report generation (MD, HTML)
│
├── providers/
│   ├── nominatim.py         # OpenStreetMap Nominatim
│   ├── photon.py            # Komoot Photon
│   ├── geoapify.py          # Geoapify API
│   ├── overpass.py           # Overpass API (school search)
│   └── provider_manager.py  # Provider orchestration & fallback
│
├── cache/
│   └── cache_manager.py     # SQLite-backed persistent cache
│
├── utils/
│   ├── helpers.py           # Shared utility functions
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
| `sat_centre.json` | `datasets/sat/output/` | Final production-ready dataset |
| `summary.md` | `datasets/sat/reports/` | Markdown summary report |
| `summary.html` | `datasets/sat/reports/` | HTML summary report |
| `changes.csv` | `datasets/sat/reports/` | Change log |
| `duplicates.csv` | `datasets/sat/reports/` | Duplicate centres |
| `failed.csv` | `datasets/sat/reports/` | Failed validations |

## Geocoding Providers

The system tries providers in order with automatic fallback:

1. **Nominatim** — OpenStreetMap (free, 1 req/s)
2. **Photon** — Komoot (free, fast)
3. **Geoapify** — Commercial (free tier: 3000/day)
4. **Overpass** — School-specific search (fallback)

## Configuration

All settings are in `config.py`:

- **HTTP**: Timeouts, retries, user agents
- **Geocoding**: Provider order, confidence threshold, rate limits
- **Cache**: Directories and TTL values
- **Validation**: Country rules, coordinate bounds
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

MIT
