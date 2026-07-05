"""
SAT Centre Updater - Configuration Module

Centralizes all configurable settings for the application.
No hardcoded values in other modules - everything comes from here.

Usage:
    from config import settings
    print(settings.TIMEOUT)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class HTTPSettings:
    """HTTP request configuration."""

    TIMEOUT: int = 30
    RETRY_COUNT: int = 3
    RETRY_DELAY: float = 1.0
    RETRY_BACKOFF: float = 2.0
    MAX_REDIRECTS: int = 10
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


@dataclass
class GeocodingSettings:
    """Geocoding provider configuration."""

    PROVIDER_ORDER: List[str] = field(
        default_factory=lambda: ["nominatim", "photon", "geoapify", "overpass"]
    )
    CONFIDENCE_THRESHOLD: float = 0.6
    MAX_WORKERS: int = 5
    RATE_LIMIT_DELAY: float = 1.0
    GEOAPIFY_API_KEY: Optional[str] = None


@dataclass
class CacheSettings:
    """Cache configuration."""

    CACHE_DIR: Path = Path("cache")
    HTTP_CACHE_EXPIRY: int = 3600
    GEOCODE_CACHE_EXPIRY: int = 86400
    DOWNLOAD_CACHE_EXPIRY: int = 3600


@dataclass
class PathSettings:
    """File path configuration."""

    BASE_DIR: Path = Path(__file__).parent
    RAW_DIR: Path = Path("datasets/sat/raw")
    GENERATED_DIR: Path = Path("datasets/sat/generated")
    OUTPUT_DIR: Path = Path("datasets/sat/output")
    REPORTS_DIR: Path = Path("datasets/sat/reports")
    LOGS_DIR: Path = Path("logs")
    CACHE_DIR: Path = Path("cache")


@dataclass
class ValidationSettings:
    """Validation rules configuration."""

    VALID_COUNTRIES: List[str] = field(
        default_factory=lambda: [
            "INDIA",
            "US",
            "CANADA",
            "UK",
            "UAE",
            "SINGAPORE",
        ]
    )
    MAX_LATITUDE: float = 90.0
    MIN_LATITUDE: float = -90.0
    MAX_LONGITUDE: float = 180.0
    MIN_LONGITUDE: float = -180.0
    OCEAN_CHECK: bool = True


@dataclass
class ExportSettings:
    """Export configuration."""

    EXPORT_FORMAT: str = "json"
    PRETTY_PRINT: bool = True
    ENCODING: str = "utf-8"


@dataclass
class VerificationSettings:
    """Evidence-based verification configuration."""

    # Query all providers for consensus (not just first successful)
    QUERY_ALL_PROVIDERS: bool = True
    # Maximum candidates per provider per query
    CANDIDATES_PER_PROVIDER: int = 5
    # State classification thresholds
    VERIFIED_THRESHOLD: float = 0.85
    HIGHLY_LIKELY_THRESHOLD: float = 0.70
    LIKELY_THRESHOLD: float = 0.55
    NEEDS_REVIEW_THRESHOLD: float = 0.40
    LOW_CONFIDENCE_THRESHOLD: float = 0.25
    # Sigmoid calibration parameters
    SIGMOID_STEEPNESS: float = 10.0
    SIGMOID_MIDPOINT: float = 0.5
    # Evidence category weights
    TEXT_WEIGHT: float = 0.30
    GEOGRAPHY_WEIGHT: float = 0.25
    PROVIDER_WEIGHT: float = 0.20
    PLACE_TYPE_WEIGHT: float = 0.15
    HISTORICAL_WEIGHT: float = 0.10
    # Maximum movement before flagging (km)
    LARGE_MOVEMENT_THRESHOLD_KM: float = 50.0
    # Provider agreement distance threshold (km)
    PROVIDER_AGREEMENT_DISTANCE_KM: float = 5.0


@dataclass
class Settings:
    """Main settings container."""

    HTTP: HTTPSettings = field(default_factory=HTTPSettings)
    GEOCODING: GeocodingSettings = field(default_factory=GeocodingSettings)
    CACHE: CacheSettings = field(default_factory=CacheSettings)
    PATHS: PathSettings = field(default_factory=PathSettings)
    VALIDATION: ValidationSettings = field(default_factory=ValidationSettings)
    EXPORT: ExportSettings = field(default_factory=ExportSettings)
    VERIFICATION: VerificationSettings = field(default_factory=VerificationSettings)


# Global settings instance
settings = Settings()
