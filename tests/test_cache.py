"""
SAT Centre Updater - Cache Manager Tests

Unit tests for the SQLite-backed cache manager.
"""

from cache.cache_manager import CacheManager


class TestCacheManager:
    """Test cases for the CacheManager class."""

    def setup_method(self) -> None:
        """Set up test fixtures with a temporary cache."""
        import tempfile

        self.tmp_dir = tempfile.mkdtemp()
        self.cache = CacheManager(cache_dir=__import__("pathlib").Path(self.tmp_dir))

    def teardown_method(self) -> None:
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_set_and_get(self) -> None:
        """Test basic set and get operations."""
        self.cache.set("test", "key1", {"value": 42})
        result = self.cache.get("test", "key1")

        assert result == {"value": 42}

    def test_get_nonexistent(self) -> None:
        """Test getting a nonexistent key returns None."""
        result = self.cache.get("test", "nonexistent")
        assert result is None

    def test_has_key(self) -> None:
        """Test checking if a key exists."""
        self.cache.set("test", "exists", "yes")
        assert self.cache.has("test", "exists") is True
        assert self.cache.has("test", "missing") is False

    def test_delete(self) -> None:
        """Test deleting a key."""
        self.cache.set("test", "del", "value")
        self.cache.delete("test", "del")
        assert self.cache.has("test", "del") is False

    def test_clear_namespace(self) -> None:
        """Test clearing all entries in a namespace."""
        self.cache.set("ns1", "a", 1)
        self.cache.set("ns1", "b", 2)
        self.cache.set("ns2", "c", 3)

        count = self.cache.clear_namespace("ns1")
        assert count == 2
        assert self.cache.has("ns1", "a") is False
        assert self.cache.has("ns2", "c") is True

    def test_clear_all(self) -> None:
        """Test clearing the entire cache."""
        self.cache.set("a", "x", 1)
        self.cache.set("b", "y", 2)
        count = self.cache.clear_all()
        assert count == 2

    def test_stats(self) -> None:
        """Test cache statistics."""
        self.cache.set("ns1", "a", 1)
        self.cache.set("ns1", "b", 2)
        self.cache.set("ns2", "c", 3)

        stats = self.cache.stats()
        assert stats["ns1"] == 2
        assert stats["ns2"] == 1

    def test_store_complex_objects(self) -> None:
        """Test storing complex nested objects."""
        data = {
            "name": "Test",
            "nested": {"key": [1, 2, 3]},
            "list": [{"a": 1}, {"b": 2}],
        }
        self.cache.set("test", "complex", data)
        result = self.cache.get("test", "complex")
        assert result == data
