"""
SAT Centre Updater - cURL Parser Module

Parses browser cURL commands into structured HTTP request objects.
Supports all common cURL flags from Chrome, Firefox, and Safari DevTools.

Usage:
    from processing.curl_parser import CurlParser
    
    parser = CurlParser()
    request = parser.parse(curl_command)
    print(request.url, request.method)
"""

import json
import re
import shlex
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class CurlRequest:
    """Structured representation of an HTTP request parsed from cURL."""

    method: str = "GET"
    url: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    query_params: Dict[str, str] = field(default_factory=dict)
    data: Optional[str] = None
    json_data: Optional[Dict[str, Any]] = None
    form_data: Optional[Dict[str, str]] = None
    auth: Optional[tuple] = None
    compressed: bool = False
    insecure: bool = False
    user_agent: Optional[str] = None
    referer: Optional[str] = None
    origin: Optional[str] = None
    content_type: Optional[str] = None
    accept: Optional[str] = None
    raw_curl: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert request to dictionary."""
        return {
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "cookies": self.cookies,
            "query_params": self.query_params,
            "data": self.data,
            "json_data": self.json_data,
            "form_data": self.form_data,
            "auth": self.auth,
            "compressed": self.compressed,
            "insecure": self.insecure,
        }


class CurlParser:
    """
    Parses cURL commands from browser DevTools.

    Supports:
    - Chrome/Firefox/Safari cURL formats
    - GET, POST, PUT, DELETE, PATCH methods
    - Headers (-H, --header)
    - Cookies (-b, --cookie)
    - Data (-d, --data, --data-raw)
    - JSON data (--data with JSON content-type)
    - Form data (-F, --form)
    - User agent (-A, --user-agent)
    - Referer (--referer)
    - Auth (-u, --user)
    - Compression (--compressed)
    - Insecure (-k, --insecure)
    - Query parameters in URL
    """

    def parse(self, curl_command: str) -> CurlRequest:
        """
        Parse a cURL command into a CurlRequest object.

        Args:
            curl_command: The raw cURL command string

        Returns:
            CurlRequest object with parsed data

        Raises:
            ValueError: If the cURL command is invalid or cannot be parsed
        """
        if not curl_command or not curl_command.strip():
            raise ValueError("Empty cURL command")

        # Clean and normalize the command
        curl_command = self._clean_command(curl_command)

        # Extract components
        request = CurlRequest(raw_curl=curl_command)

        # Parse method
        request.method = self._extract_method(curl_command)

        # Parse URL
        request.url = self._extract_url(curl_command)

        # Parse headers
        request.headers = self._extract_headers(curl_command)

        # Parse cookies
        request.cookies = self._extract_cookies(curl_command)

        # Parse data/body
        request.data, request.json_data, request.form_data = self._extract_data(
            curl_command
        )

        # Parse auth
        request.auth = self._extract_auth(curl_command)

        # Parse flags
        request.compressed = self._has_flag(curl_command, "--compressed")
        request.insecure = self._has_flag(curl_command, ["-k", "--insecure"])

        # Extract special headers
        request.user_agent = request.headers.get("User-Agent")
        request.referer = request.headers.get("Referer")
        request.origin = request.headers.get("Origin")
        request.content_type = request.headers.get("Content-Type")
        request.accept = request.headers.get("Accept")

        # Parse query parameters from URL
        request.query_params = self._extract_query_params(request.url)

        return request

    def _clean_command(self, curl_command: str) -> str:
        """Clean and normalize the cURL command."""
        # Remove line continuations
        command = curl_command.replace("\\\n", " ")
        command = command.replace("\\\r\n", " ")

        # Normalize whitespace
        command = " ".join(command.split())

        return command

    def _extract_method(self, command: str) -> str:
        """Extract HTTP method from cURL command."""
        # Check for explicit method flags
        method_patterns = {
            "--get": "GET",
            "-X GET": "GET",
            "--request GET": "GET",
            "-X POST": "POST",
            "--request POST": "POST",
            "-X PUT": "PUT",
            "--request PUT": "PUT",
            "-X DELETE": "DELETE",
            "--request DELETE": "DELETE",
            "-X PATCH": "PATCH",
            "--request PATCH": "PATCH",
        }

        for pattern, method in method_patterns.items():
            if pattern in command:
                return method

        # Check if data is being sent (implies POST)
        data_patterns = [
            "--data",
            "-d ",
            "--data-raw",
            "--data-binary",
            "-F ",
            "--form",
        ]
        for pattern in data_patterns:
            if re.search(rf"{re.escape(pattern)}", command):
                return "POST"

        return "GET"

    def _extract_url(self, command: str) -> str:
        """Extract URL from cURL command."""
        # Pattern to match URL (typically the first non-flag argument or after 'curl')
        # Handle both 'curl URL' and 'curl -flags URL' formats

        # Remove 'curl' prefix if present
        if command.lower().startswith("curl"):
            command = command[4:].strip()

        # Try to find URL after flags
        # Split by spaces and find the first argument that looks like a URL
        parts = shlex.split(command)

        for i, part in enumerate(parts):
            # Skip flags and their values
            if part.startswith("-"):
                continue
            # Check if this looks like a URL
            if (
                part.startswith("http://")
                or part.startswith("https://")
                or part.startswith("'http")
            ):
                # Remove surrounding quotes if present
                url = part.strip("'\"")
                return url

        # Fallback: try regex
        url_match = re.search(
            r"(?:curl\s+)?['\"]?(https?://[^\s'\"]+)['\"]?", command, re.IGNORECASE
        )

        if url_match:
            return url_match.group(1).strip("'\"")

        raise ValueError("Could not extract URL from cURL command")

    def _extract_headers(self, command: str) -> Dict[str, str]:
        """Extract headers from cURL command."""
        headers = {}

        # Pattern for -H or --header
        header_patterns = [
            r"-H\s+['\"]([^'\"]+)['\"]",
            r"--header\s+['\"]([^'\"]+)['\"]",
        ]

        for pattern in header_patterns:
            matches = re.findall(pattern, command)
            for match in matches:
                if ":" in match:
                    key, value = match.split(":", 1)
                    headers[key.strip()] = value.strip()

        return headers

    def _extract_cookies(self, command: str) -> Dict[str, str]:
        """Extract cookies from cURL command."""
        cookies = {}

        # Pattern for -b or --cookie
        cookie_patterns = [
            r"-b\s+['\"]([^'\"]+)['\"]",
            r"--cookie\s+['\"]([^'\"]+)['\"]",
        ]

        for pattern in cookie_patterns:
            matches = re.findall(pattern, command)
            for match in matches:
                # Parse cookie string (name=value; name2=value2)
                for cookie in match.split(";"):
                    cookie = cookie.strip()
                    if "=" in cookie:
                        name, value = cookie.split("=", 1)
                        cookies[name.strip()] = value.strip()

        return cookies

    def _extract_data(self, command: str) -> tuple:
        """
        Extract request body data from cURL command.

        Returns:
            Tuple of (raw_data, json_data, form_data)
        """
        raw_data = None
        json_data = None
        form_data = None

        # Check for form data first (-F or --form)
        form_patterns = [
            r"-F\s+['\"]([^'\"]+)['\"]",
            r"--form\s+['\"]([^'\"]+)['\"]",
        ]

        form_matches = []
        for pattern in form_patterns:
            matches = re.findall(pattern, command)
            form_matches.extend(matches)

        if form_matches:
            form_data = {}
            for match in form_matches:
                if "=" in match:
                    key, value = match.split("=", 1)
                    form_data[key.strip()] = value.strip()
            return raw_data, json_data, form_data

        # Check for data (-d, --data, --data-raw, --data-binary)
        # Use backreference (['"])(.*?)\1 to match same-quote delimiters,
        # allowing inner quotes of the opposite type (e.g. JSON inside single quotes)
        data_patterns = [
            r"-d\s+(['\"])(.*?)\1",
            r"--data\s+(['\"])(.*?)\1",
            r"--data-raw\s+(['\"])(.*?)\1",
            r"--data-binary\s+(['\"])(.*?)\1",
        ]

        for pattern in data_patterns:
            match = re.search(pattern, command)
            if match:
                raw_data = match.group(2)

                # Try to parse as JSON
                try:
                    json_data = json.loads(raw_data)
                except (json.JSONDecodeError, TypeError):
                    # Not valid JSON, keep as raw data
                    pass

                break

        return raw_data, json_data, form_data

    def _extract_auth(self, command: str) -> Optional[tuple]:
        """Extract authentication credentials from cURL command."""
        # Pattern for -u or --user
        auth_patterns = [
            r"-u\s+['\"]([^'\"]+)['\"]",
            r"--user\s+['\"]([^'\"]+)['\"]",
        ]

        for pattern in auth_patterns:
            match = re.search(pattern, command)
            if match:
                auth_string = match.group(1)
                if ":" in auth_string:
                    username, password = auth_string.split(":", 1)
                    return (username, password)

        return None

    def _has_flag(self, command: str, flags) -> bool:
        """Check if a flag exists in the command."""
        if isinstance(flags, str):
            flags = [flags]

        for flag in flags:
            if flag in command:
                return True

        return False

    def _extract_query_params(self, url: str) -> Dict[str, str]:
        """Extract query parameters from URL."""
        params = {}

        if "?" in url:
            query_string = url.split("?", 1)[1]
            # Remove fragment if present
            if "#" in query_string:
                query_string = query_string.split("#")[0]

            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    params[urllib.parse.unquote(key)] = urllib.parse.unquote(value)

        return params


def parse_curl_file(file_path: str) -> CurlRequest:
    """
    Parse a cURL command from a file.

    Args:
        file_path: Path to the file containing the cURL command

    Returns:
        Parsed CurlRequest object
    """
    with open(file_path, "r") as f:
        curl_command = f.read()

    parser = CurlParser()
    return parser.parse(curl_command)


def parse_curl_string(curl_string: str) -> CurlRequest:
    """
    Parse a cURL command from a string.

    Args:
        curl_string: The cURL command as a string

    Returns:
        Parsed CurlRequest object
    """
    parser = CurlParser()
    return parser.parse(curl_string)
