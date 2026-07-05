"""
SAT Centre Updater - Downloader Module

Reconstructs parsed cURL requests into actual HTTP calls using the requests library.
Handles retries, timeouts, compression, response type detection, and raw file saving.

Usage:
    from processing.downloader import Downloader
    from processing.curl_parser import CurlParser

    parser = CurlParser()
    request = parser.parse(curl_command)

    downloader = Downloader()
    result = downloader.download(request)
    print(result.file_path, result.status_code)
"""

import gzip
import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import settings
from processing.curl_parser import CurlRequest


@dataclass
class DownloadResult:
    """Result of a download operation."""

    status_code: int
    headers: Dict[str, str]
    content: bytes
    text: str
    content_type: str
    encoding: str
    file_path: Optional[Path] = None
    response_format: str = "unknown"
    elapsed_seconds: float = 0.0
    success: bool = False
    error: Optional[str] = None
    redirects: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "status_code": self.status_code,
            "content_type": self.content_type,
            "response_format": self.response_format,
            "file_path": str(self.file_path) if self.file_path else None,
            "elapsed_seconds": self.elapsed_seconds,
            "success": self.success,
            "error": self.error,
            "size_bytes": len(self.content),
        }


class Downloader:
    """
    Downloads SAT centre data by reconstructing the browser request.

    Supports:
    - GET and POST methods
    - JSON and form payloads
    - Cookies and bearer tokens
    - GZip and Brotli compression
    - Automatic retries with exponential backoff
    - Response type detection (JSON, CSV, HTML, ZIP, GZIP)
    - Timestamped raw file saving
    """

    def __init__(self, raw_dir: Optional[Path] = None) -> None:
        """
        Initialize the downloader.

        Args:
            raw_dir: Directory to save raw responses. Defaults to config setting.
        """
        self.raw_dir = raw_dir or settings.PATHS.RAW_DIR
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self.timeout = settings.HTTP.TIMEOUT
        self.retry_count = settings.HTTP.RETRY_COUNT
        self.retry_delay = settings.HTTP.RETRY_DELAY

    def _build_session(self) -> requests.Session:
        """
        Build a requests.Session with retry logic and default headers.

        Returns:
            Configured requests.Session instance.
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=self.retry_count,
            backoff_factor=settings.HTTP.RETRY_BACKOFF,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _detect_format(self, content: bytes, content_type: str) -> str:
        """
        Detect the response format from content and headers.

        Args:
            content: Raw response bytes.
            content_type: Content-Type header value.

        Returns:
            Format string: 'json', 'csv', 'html', 'zip', 'gzip', or 'unknown'.
        """
        ct_lower = content_type.lower() if content_type else ""

        # Check by Content-Type header
        if "json" in ct_lower:
            return "json"
        if "csv" in ct_lower or "text/comma-separated" in ct_lower:
            return "csv"
        if "html" in ct_lower:
            return "html"
        if "zip" in ct_lower:
            return "zip"
        if "gzip" in ct_lower or "x-gzip" in ct_lower:
            return "gzip"

        # Check by magic bytes
        if len(content) >= 4:
            # ZIP magic: PK\x03\x04
            if content[:4] == b"PK\x03\x04":
                return "zip"
            # GZIP magic: \x1f\x8b
            if content[:2] == b"\x1f\x8b":
                return "gzip"

        # Try to parse as JSON
        try:
            text_sample = content[:4096].decode("utf-8", errors="ignore").strip()
            if text_sample.startswith("{") or text_sample.startswith("["):
                json.loads(content)
                return "json"
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass

        # Try to decode as text and check for HTML
        try:
            text_sample = content[:4096].decode("utf-8", errors="ignore")
            if "<html" in text_sample.lower() or "<!doctype" in text_sample.lower():
                return "html"
            # Check for CSV (contains commas and newlines)
            lines = text_sample.split("\n")
            if len(lines) > 1 and "," in lines[0]:
                return "csv"
        except UnicodeDecodeError:
            pass

        return "unknown"

    def _decompress(self, content: bytes, fmt: str) -> bytes:
        """
        Decompress content based on detected format.

        Args:
            content: Raw compressed bytes.
            fmt: Detected format.

        Returns:
            Decompressed bytes.
        """
        if fmt == "gzip":
            return gzip.decompress(content)
        if fmt == "zip":
            with zipfile.ZipFile(BytesIO(content)) as zf:
                # Return the first file in the archive
                names = zf.namelist()
                if names:
                    return zf.read(names[0])
        return content

    def _save_raw(self, content: bytes, fmt: str) -> Path:
        """
        Save raw response to datasets/sat/raw/ with a timestamped filename.

        Args:
            content: Raw response bytes.
            fmt: Detected response format.

        Returns:
            Path to the saved file.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension_map = {
            "json": "json",
            "csv": "csv",
            "html": "html",
            "zip": "zip",
            "gzip": "gz",
        }
        ext = extension_map.get(fmt, "bin")
        filename = f"sat_raw_{timestamp}.{ext}"
        file_path = self.raw_dir / filename

        file_path.write_bytes(content)
        return file_path

    def download(self, curl_request: CurlRequest) -> DownloadResult:
        """
        Execute the HTTP request reconstructed from a parsed cURL command.

        Args:
            curl_request: Parsed CurlRequest object.

        Returns:
            DownloadResult with response data and metadata.
        """
        session = self._build_session()

        try:
            start_time = datetime.now()

            # Build request kwargs
            kwargs: Dict[str, Any] = {
                "method": curl_request.method,
                "url": curl_request.url,
                "headers": curl_request.headers.copy(),
                "cookies": curl_request.cookies,
                "params": curl_request.query_params or None,
                "timeout": self.timeout,
                "allow_redirects": True,
                "stream": False,
            }

            # Add body data
            if curl_request.json_data is not None:
                kwargs["json"] = curl_request.json_data
            elif curl_request.form_data is not None:
                kwargs["data"] = curl_request.form_data
            elif curl_request.data is not None:
                kwargs["data"] = curl_request.data

            # Add auth
            if curl_request.auth:
                kwargs["auth"] = curl_request.auth

            # Add compression flag
            if curl_request.compressed:
                kwargs["headers"].setdefault("Accept-Encoding", "gzip, deflate")

            # Execute request
            response = session.request(**kwargs)

            elapsed = (datetime.now() - start_time).total_seconds()

            # Detect format
            content_type = response.headers.get("Content-Type", "")
            encoding = response.encoding or "utf-8"
            fmt = self._detect_format(response.content, content_type)

            # Save raw response
            file_path = self._save_raw(response.content, fmt)

            return DownloadResult(
                status_code=response.status_code,
                headers=dict(response.headers),
                content=response.content,
                text=response.text,
                content_type=content_type,
                encoding=encoding,
                file_path=file_path,
                response_format=fmt,
                elapsed_seconds=elapsed,
                success=200 <= response.status_code < 300,
                redirects=len(response.history),
            )

        except requests.exceptions.Timeout:
            return DownloadResult(
                status_code=0,
                headers={},
                content=b"",
                text="",
                content_type="",
                encoding="utf-8",
                success=False,
                error=f"Request timed out after {self.timeout}s",
            )
        except requests.exceptions.ConnectionError as e:
            return DownloadResult(
                status_code=0,
                headers={},
                content=b"",
                text="",
                content_type="",
                encoding="utf-8",
                success=False,
                error=f"Connection error: {str(e)}",
            )
        except requests.exceptions.RequestException as e:
            return DownloadResult(
                status_code=0,
                headers={},
                content=b"",
                text="",
                content_type="",
                encoding="utf-8",
                success=False,
                error=f"Request failed: {str(e)}",
            )
        finally:
            session.close()

    def get_latest_raw(self) -> Optional[Path]:
        """
        Get the most recently saved raw file.

        Returns:
            Path to the latest raw file, or None if no files exist.
        """
        raw_files = sorted(self.raw_dir.glob("sat_raw_*"), key=lambda p: p.stat().st_mtime)
        return raw_files[-1] if raw_files else None

    def list_raw_files(self) -> List[Path]:
        """
        List all raw files sorted by modification time (newest first).

        Returns:
            List of Path objects for raw files.
        """
        return sorted(self.raw_dir.glob("sat_raw_*"), key=lambda p: p.stat().st_mtime, reverse=True)
