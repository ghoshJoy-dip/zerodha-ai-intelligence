import time
import logging
from typing import Any, Optional

logger = logging.getLogger("CacheService")

class SimpleCache:
    """
    In-memory short-lived cache with TTL (default 90 seconds)
    to prevent repetitive API rate-limiting against Yahoo Finance and DuckDuckGo.
    """
    def __init__(self, default_ttl_seconds: int = 90):
        self._cache = {}
        self._default_ttl = default_ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if not entry:
            return None
        value, expiry = entry
        if time.time() > expiry:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
        expiry = time.time() + ttl
        self._cache[key] = (value, expiry)

    def delete(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]

    def clear(self) -> None:
        self._cache.clear()

# Global cache instance
cache_service = SimpleCache(default_ttl_seconds=90)

