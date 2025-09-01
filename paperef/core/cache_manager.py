"""
Cache Manager Module
Intelligent caching system with TTL, size management, and performance optimization
"""

import json
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any


class CacheEntry:
    """Cache entry with TTL support"""

    def __init__(self, value: Any, ttl: int | None = None):
        """
        Initialize cache entry

        Args:
            value: Value to cache
            ttl: Time to live in seconds (None for no expiration)
        """
        self.value = value
        self.ttl = ttl
        self.created_at = time.time()

    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if self.ttl is None:
            return False
        return (time.time() - self.created_at) > self.ttl

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "value": self.value,
            "ttl": self.ttl,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CacheEntry":
        """Create from dictionary"""
        entry = cls.__new__(cls)
        entry.value = data["value"]
        entry.ttl = data["ttl"]
        entry.created_at = data["created_at"]
        return entry


class CacheManager:
    """Intelligent cache manager with TTL and size management"""

    def __init__(self, cache_file: Path, max_size: int = 1000, default_ttl: int = 86400):
        """
        Initialize cache manager

        Args:
            cache_file: Path to cache file
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self.cache_file = cache_file
        self.max_size = max_size
        self.default_ttl = default_ttl

        # Cache storage: OrderedDict for LRU behavior
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()

        # Statistics
        self._hits = 0
        self._misses = 0
        self._expired_count = 0

        # Load existing cache
        self._load_cache()

    def get(self, key: str) -> Any:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]

        # Check expiration
        if entry.is_expired():
            self._expired_count += 1
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1

        return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if None)
        """
        # Use default TTL if not specified
        if ttl is None:
            ttl = self.default_ttl

        # Create/update entry
        entry = CacheEntry(value, ttl)

        # If key exists, update it
        if key in self._cache:
            self._cache[key] = entry
            self._cache.move_to_end(key)
        else:
            # New key
            self._cache[key] = entry
            self._cache.move_to_end(key)

            # Check size limit
            if len(self._cache) > self.max_size:
                self._evict_oldest()

        # Save to disk
        self._save_cache()

    def delete(self, key: str) -> bool:
        """
        Delete key from cache

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            self._save_cache()
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
        self._expired_count = 0
        self._save_cache()

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries

        Returns:
            Number of entries removed
        """
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            self._save_cache()

        return len(expired_keys)

    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)

    def stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
        miss_rate = self._misses / total_requests if total_requests > 0 else 0.0

        return {
            "total_entries": len(self._cache),
            "expired_entries": self._expired_count,
            "hit_rate": hit_rate,
            "miss_rate": miss_rate,
            "total_requests": total_requests,
            "max_size": self.max_size,
            "default_ttl": self.default_ttl
        }

    def keys(self) -> list[str]:
        """Get all cache keys"""
        return list(self._cache.keys())

    def _evict_oldest(self) -> None:
        """Evict oldest entry (LRU)"""
        if self._cache:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

    def _load_cache(self) -> None:
        """Load cache from disk"""
        if not self.cache_file.exists():
            return

        try:
            with open(self.cache_file, encoding="utf-8") as f:
                data = json.load(f)

            # Load entries
            for key, entry_data in data.items():
                try:
                    entry = CacheEntry.from_dict(entry_data)
                    # Only load non-expired entries
                    if not entry.is_expired():
                        self._cache[key] = entry
                except (KeyError, ValueError):
                    # Skip invalid entries
                    continue

        except (OSError, json.JSONDecodeError):
            # If cache file is corrupt, start fresh
            self._cache.clear()

    def _save_cache(self) -> None:
        """Save cache to disk"""
        try:
            # Create directory if it doesn't exist
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert to serializable format
            data = {}
            for key, entry in self._cache.items():
                # Only save non-expired entries
                if not entry.is_expired():
                    data[key] = entry.to_dict()

            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except OSError:
            # If we can't save, continue without error
            pass

    def __contains__(self, key: str) -> bool:
        """Check if key exists in cache"""
        return key in self._cache and not self._cache[key].is_expired()

    def __len__(self) -> int:
        """Get cache size"""
        return self.size()

    def __getitem__(self, key: str) -> Any:
        """Get item by key"""
        result = self.get(key)
        if result is None:
            raise KeyError(key)
        return result

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item by key"""
        self.set(key, value)

    def __delitem__(self, key: str) -> None:
        """Delete item by key"""
        if not self.delete(key):
            raise KeyError(key)
