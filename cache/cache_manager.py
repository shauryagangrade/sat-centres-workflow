"""
SAT Centre Updater - Cache Module

Provides persistent caching for downloads, HTTP responses, and geocoding results.
Uses SQLite for reliable, thread-safe caching with automatic expiry.

Usage:
    from cache.cache_manager import CacheManager

    cache = CacheManager()
    cache.set("geocode", "Legacy School Bangalore", result_data, ttl=86400)
    cached = cache.get("geocode", "Legacy School Bangalore")
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

from config import settings


class CacheManager:
    """
    Persistent SQLite-backed cache with namespaced keys and TTL expiry.

    Supports multiple namespaces:
    - 'download': Raw download responses
    - 'http': HTTP response caching
    - 'geocode': Geocoding results
    - 'manual': Manual review overrides
    """

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        """
        Initialize the cache manager.

        Args:
            cache_dir: Directory for the SQLite database. Defaults to config setting.
        """
        self.cache_dir = cache_dir or settings.PATHS.CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.db_path = self.cache_dir / "cache.db"
        self._init_db()

    def _init_db(self) -> None:
        """Create the cache table if it doesn't exist."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    PRIMARY KEY (namespace, key)
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON cache (expires_at)")
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        """Create a new database connection."""
        return sqlite3.connect(str(self.db_path))

    def get(self, namespace: str, key: str) -> Optional[Any]:
        """
        Retrieve a cached value if it exists and hasn't expired.

        Args:
            namespace: Cache namespace.
            key: Cache key.

        Returns:
            Cached value or None if not found or expired.
        """
        now = time.time()
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT value, expires_at FROM cache WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            value_str, expires_at = row
            if expires_at < now:
                # Expired — delete and return None
                conn.execute(
                    "DELETE FROM cache WHERE namespace = ? AND key = ?",
                    (namespace, key),
                )
                conn.commit()
                return None

            try:
                return json.loads(value_str)
            except (json.JSONDecodeError, TypeError):
                return value_str

    def set(
        self, namespace: str, key: str, value: Any, ttl: Optional[int] = None
    ) -> None:
        """
        Store a value in the cache.

        Args:
            namespace: Cache namespace.
            key: Cache key.
            value: Value to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds. Uses default if not provided.
        """
        if ttl is None:
            ttl = self._default_ttl(namespace)

        now = time.time()
        expires_at = now + ttl

        try:
            value_str = json.dumps(value, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            value_str = json.dumps(str(value))

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache (namespace, key, value, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (namespace, key, value_str, now, expires_at),
            )
            conn.commit()

    def has(self, namespace: str, key: str) -> bool:
        """
        Check if a key exists in the cache and hasn't expired.

        Args:
            namespace: Cache namespace.
            key: Cache key.

        Returns:
            True if the key exists and is valid.
        """
        return self.get(namespace, key) is not None

    def delete(self, namespace: str, key: str) -> None:
        """
        Remove a specific key from the cache.

        Args:
            namespace: Cache namespace.
            key: Cache key.
        """
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM cache WHERE namespace = ? AND key = ?",
                (namespace, key),
            )
            conn.commit()

    def clear_namespace(self, namespace: str) -> int:
        """
        Clear all entries in a namespace.

        Args:
            namespace: Cache namespace.

        Returns:
            Number of entries deleted.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM cache WHERE namespace = ?",
                (namespace,),
            )
            conn.commit()
            return cursor.rowcount

    def clear_all(self) -> int:
        """
        Clear the entire cache.

        Returns:
            Number of entries deleted.
        """
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM cache")
            conn.commit()
            return cursor.rowcount

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from the cache.

        Returns:
            Number of entries removed.
        """
        now = time.time()
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM cache WHERE expires_at < ?",
                (now,),
            )
            conn.commit()
            return cursor.rowcount

    def stats(self) -> Dict[str, int]:
        """
        Get cache statistics by namespace.

        Returns:
            Dictionary mapping namespace to entry count.
        """
        with self._connect() as conn:
            cursor = conn.execute(
                "SELECT namespace, COUNT(*) FROM cache GROUP BY namespace"
            )
            return dict(cursor.fetchall())

    def _default_ttl(self, namespace: str) -> int:
        """Get the default TTL for a namespace."""
        ttl_map = {
            "download": settings.CACHE.DOWNLOAD_CACHE_EXPIRY,
            "http": settings.CACHE.HTTP_CACHE_EXPIRY,
            "geocode": settings.CACHE.GEOCODE_CACHE_EXPIRY,
            "manual": 31536000,  # 1 year for manual overrides
        }
        return ttl_map.get(namespace, settings.CACHE.HTTP_CACHE_EXPIRY)
