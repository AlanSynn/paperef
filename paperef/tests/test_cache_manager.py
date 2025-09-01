"""
Test CacheManager - TDD approach
Tests for intelligent caching system with TTL and size management
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from paperef.core.cache_manager import CacheEntry, CacheManager


class TestCacheManager:
    """Test cases for CacheManager class"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def cache_manager(self, temp_dir):
        """Create CacheManager instance"""
        cache_file = temp_dir / "test_cache.json"
        return CacheManager(cache_file=cache_file, max_size=100, default_ttl=3600)

    def test_init(self, cache_manager):
        """Test CacheManager initialization"""
        assert cache_manager is not None
        assert hasattr(cache_manager, "get")
        assert hasattr(cache_manager, "set")
        assert hasattr(cache_manager, "delete")
        assert hasattr(cache_manager, "cleanup_expired")
        assert hasattr(cache_manager, "clear")

    def test_set_and_get_basic(self, cache_manager):
        """Test basic set and get operations"""
        # Set a value
        cache_manager.set("test_key", "test_value")

        # Get the value
        result = cache_manager.get("test_key")
        assert result == "test_value"

    def test_get_nonexistent_key(self, cache_manager):
        """Test getting a key that doesn't exist"""
        result = cache_manager.get("nonexistent_key")
        assert result is None

    def test_set_with_ttl(self, cache_manager):
        """Test setting a value with TTL"""
        # Set with short TTL
        cache_manager.set("short_ttl_key", "value", ttl=1)

        # Should exist immediately
        assert cache_manager.get("short_ttl_key") == "value"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert cache_manager.get("short_ttl_key") is None

    def test_set_with_custom_ttl(self, cache_manager):
        """Test setting values with different TTLs"""
        # Set multiple values with different TTLs
        cache_manager.set("key1", "value1", ttl=2)
        cache_manager.set("key2", "value2", ttl=10)

        # Both should exist
        assert cache_manager.get("key1") == "value1"
        assert cache_manager.get("key2") == "value2"

        # Wait for first to expire
        time.sleep(2.1)

        # First should be expired, second should still exist
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") == "value2"

    def test_delete_key(self, cache_manager):
        """Test deleting a key"""
        # Set and verify
        cache_manager.set("delete_key", "delete_value")
        assert cache_manager.get("delete_key") == "delete_value"

        # Delete
        cache_manager.delete("delete_key")

        # Should be gone
        assert cache_manager.get("delete_key") is None

    def test_delete_nonexistent_key(self, cache_manager):
        """Test deleting a key that doesn't exist"""
        # Should not raise error
        cache_manager.delete("nonexistent_key")

    def test_clear_cache(self, cache_manager):
        """Test clearing entire cache"""
        # Set multiple values
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        cache_manager.set("key3", "value3")

        # Verify they exist
        assert cache_manager.get("key1") == "value1"
        assert cache_manager.get("key2") == "value2"
        assert cache_manager.get("key3") == "value3"

        # Clear cache
        cache_manager.clear()

        # All should be gone
        assert cache_manager.get("key1") is None
        assert cache_manager.get("key2") is None
        assert cache_manager.get("key3") is None

    def test_max_size_limit(self, cache_manager):
        """Test cache size limit enforcement"""
        # Fill cache to max size
        for i in range(105):  # Over the limit
            cache_manager.set(f"key{i}", f"value{i}")

        # Should only keep the most recent entries
        assert cache_manager.size() <= 100

        # Should keep the most recent entries
        assert cache_manager.get("key104") == "value104"
        assert cache_manager.get("key100") == "value100"

        # Older entries might be evicted
        # (This depends on the eviction policy implementation)

    def test_persistence(self, temp_dir):
        """Test cache persistence across instances"""
        cache_file = temp_dir / "persistent_cache.json"

        # Create first instance and set values
        manager1 = CacheManager(cache_file=cache_file, max_size=100, default_ttl=3600)
        manager1.set("persistent_key", "persistent_value")

        # Create second instance
        manager2 = CacheManager(cache_file=cache_file, max_size=100, default_ttl=3600)

        # Should be able to retrieve persisted value
        assert manager2.get("persistent_key") == "persistent_value"

    def test_cleanup_expired(self, cache_manager):
        """Test manual cleanup of expired entries"""
        # Set values with different TTLs
        cache_manager.set("expired_key", "expired_value", ttl=1)
        cache_manager.set("valid_key", "valid_value", ttl=10)

        # Wait for expiration
        time.sleep(1.1)

        # Both should exist in cache before cleanup
        # (expired entries are only removed on access or cleanup)

        # Manual cleanup
        cache_manager.cleanup_expired()

        # Expired entry should be removed
        assert cache_manager.get("expired_key") is None
        assert cache_manager.get("valid_key") == "valid_value"

    def test_complex_data_types(self, cache_manager):
        """Test storing complex data types"""
        # Dictionary
        test_dict = {"key": "value", "number": 42, "list": [1, 2, 3]}
        cache_manager.set("dict_key", test_dict)
        assert cache_manager.get("dict_key") == test_dict

        # List
        test_list = ["item1", "item2", {"nested": "dict"}]
        cache_manager.set("list_key", test_list)
        assert cache_manager.get("list_key") == test_list

        # None value
        cache_manager.set("none_key", None)
        assert cache_manager.get("none_key") is None

    def test_key_collision_with_ttl(self, cache_manager):
        """Test overwriting keys with different TTLs"""
        # Set initial value
        cache_manager.set("collision_key", "value1", ttl=10)

        # Overwrite with different value and TTL
        cache_manager.set("collision_key", "value2", ttl=1)

        # Should get new value
        assert cache_manager.get("collision_key") == "value2"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert cache_manager.get("collision_key") is None

    def test_size_method(self, cache_manager):
        """Test size reporting"""
        # Empty cache
        assert cache_manager.size() == 0

        # Add items
        cache_manager.set("key1", "value1")
        cache_manager.set("key2", "value2")
        assert cache_manager.size() == 2

        # Delete item
        cache_manager.delete("key1")
        assert cache_manager.size() == 1

        # Clear cache
        cache_manager.clear()
        assert cache_manager.size() == 0

    def test_stats_method(self, cache_manager):
        """Test statistics reporting"""
        stats = cache_manager.stats()

        assert "total_entries" in stats
        assert "expired_entries" in stats
        assert "hit_rate" in stats
        assert "miss_rate" in stats
        assert isinstance(stats["total_entries"], int)
        assert isinstance(stats["expired_entries"], int)

    def test_cache_with_special_characters_in_key(self, cache_manager):
        """Test keys with special characters"""
        special_keys = [
            "key with spaces",
            "key-with-dashes",
            "key.with.dots",
            "key_with_underscores",
            "key/with/slashes",
            "key\\with\\backslashes"
        ]

        for key in special_keys:
            cache_manager.set(key, f"value_for_{key}")
            assert cache_manager.get(key) == f"value_for_{key}"

    @patch("json.dump")
    def test_save_error_handling(self, mock_json_dump, cache_manager):
        """Test error handling during cache save"""
        mock_json_dump.side_effect = OSError("Disk full")

        # Should not raise exception
        cache_manager.set("test_key", "test_value")
        # Cache operations should continue to work
        assert cache_manager.get("test_key") == "test_value"

    @patch("json.load")
    def test_load_error_handling(self, mock_json_load, temp_dir):
        """Test error handling during cache load"""
        cache_file = temp_dir / "corrupt_cache.json"

        # Create corrupt cache file
        cache_file.write_text("invalid json")

        # Should handle corrupt file gracefully
        manager = CacheManager(cache_file=cache_file, max_size=100, default_ttl=3600)

        # Should still work
        manager.set("test_key", "test_value")
        assert manager.get("test_key") == "test_value"


class TestCacheEntry:
    """Test cases for CacheEntry class"""

    def test_cache_entry_creation(self):
        """Test CacheEntry creation"""
        entry = CacheEntry(value="test_value", ttl=3600)

        assert entry.value == "test_value"
        assert entry.ttl == 3600
        assert entry.created_at is not None
        assert isinstance(entry.created_at, float)

    def test_cache_entry_expiration(self):
        """Test CacheEntry expiration"""
        # Create entry with 1 second TTL
        entry = CacheEntry(value="test_value", ttl=1)

        # Should not be expired immediately
        assert not entry.is_expired()

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        assert entry.is_expired()

    def test_cache_entry_no_ttl(self):
        """Test CacheEntry with no TTL (never expires)"""
        entry = CacheEntry(value="test_value", ttl=None)

        # Should never expire
        assert not entry.is_expired()

        # Even after long time
        time.sleep(0.1)
        assert not entry.is_expired()

    def test_cache_entry_serialization(self):
        """Test CacheEntry serialization"""
        entry = CacheEntry(value="test_value", ttl=3600)

        data = entry.to_dict()

        assert "value" in data
        assert "ttl" in data
        assert "created_at" in data
        assert data["value"] == "test_value"
        assert data["ttl"] == 3600

    def test_cache_entry_deserialization(self):
        """Test CacheEntry deserialization"""
        data = {
            "value": "test_value",
            "ttl": 3600,
            "created_at": time.time()
        }

        entry = CacheEntry.from_dict(data)

        assert entry.value == "test_value"
        assert entry.ttl == 3600
        assert entry.created_at == data["created_at"]
