"""
SAT Centre Updater - SAT Connector

High-level connector that ties together cURL parsing, downloading, and normalization.
This is the main entry point for Step 1-3 of the pipeline: paste cURL -> download -> normalize.

Usage:
    from connectors.sat_connector import SatConnector

    connector = SatConnector()
    centres = connector.run(curl_command)
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from config import settings
from processing.curl_parser import CurlParser, CurlRequest
from processing.downloader import Downloader, DownloadResult
from processing.normalizer import Normalizer, SatCentre

logger = logging.getLogger(__name__)


class SatConnector:
    """
    High-level connector for the SAT data acquisition pipeline.

    Pipeline:
    1. Parse cURL command
    2. Download SAT centre data
    3. Normalize into standard schema
    4. Save to datasets/sat/generated/sat_centres.json
    """

    def __init__(self) -> None:
        """Initialize the connector with its dependencies."""
        self.parser = CurlParser()
        self.downloader = Downloader()
        self.normalizer = Normalizer()

    def run(
        self,
        curl_command: Optional[str] = None,
        curl_file: Optional[str] = None,
    ) -> List[SatCentre]:
        """
        Execute the full acquisition pipeline.

        Args:
            curl_command: Raw cURL command string.
            curl_file: Path to a file containing the cURL command.

        Returns:
            List of normalized SatCentre objects.

        Raises:
            ValueError: If neither curl_command nor curl_file is provided.
        """
        # Step 1: Get cURL command
        if curl_command:
            raw_curl = curl_command
        elif curl_file:
            raw_curl = self._read_curl_file(curl_file)
        else:
            raise ValueError("Provide either curl_command or curl_file")

        # Step 2: Parse cURL
        logger.info("Parsing cURL command...")
        curl_request = self.parser.parse(raw_curl)
        logger.info(f"  Method: {curl_request.method}")
        logger.info(f"  URL: {curl_request.url}")
        logger.info(f"  Headers: {len(curl_request.headers)}")

        # Step 3: Download
        logger.info("Downloading SAT centre data...")
        result = self.downloader.download(curl_request)

        if not result.success:
            raise RuntimeError(
                f"Download failed (HTTP {result.status_code}): {result.error or 'Unknown error'}"
            )

        logger.info(f"  Status: {result.status_code}")
        logger.info(f"  Format: {result.response_format}")
        logger.info(f"  Size: {len(result.content)} bytes")
        logger.info(f"  Saved to: {result.file_path}")

        # Step 4: Normalize
        logger.info("Normalizing data...")
        centres = self.normalizer.normalize(result.content, fmt=result.response_format)
        logger.info(f"  Normalized {len(centres)} centres")

        # Step 5: Save
        output_path = self.normalizer.save(centres)
        logger.info(f"  Saved to: {output_path}")

        return centres

    def download_only(
        self,
        curl_command: Optional[str] = None,
        curl_file: Optional[str] = None,
    ) -> DownloadResult:
        """
        Execute only the download step (no normalization).

        Args:
            curl_command: Raw cURL command string.
            curl_file: Path to a file containing the cURL command.

        Returns:
            DownloadResult with response data.
        """
        if curl_command:
            raw_curl = curl_command
        elif curl_file:
            raw_curl = self._read_curl_file(curl_file)
        else:
            raise ValueError("Provide either curl_command or curl_file")

        curl_request = self.parser.parse(raw_curl)
        return self.downloader.download(curl_request)

    def _read_curl_file(self, file_path: str) -> str:
        """Read a cURL command from a file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"cURL file not found: {file_path}")

        return path.read_text(encoding="utf-8")
