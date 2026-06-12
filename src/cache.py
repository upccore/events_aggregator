from datetime import datetime, timedelta

from src.metrics import cache_hits_total, cache_misses_total


class SimpleCache:
    def __init__(self):
        self._cache = {}

    def get(self, key: str):
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                cache_hits_total.inc()
                return value
            del self._cache[key]
        cache_misses_total.inc()
        return None

    def set(self, key: str, value, ttl_seconds: int = 30):
        self._cache[key] = (value, datetime.now() + timedelta(seconds=ttl_seconds))

    def delete(self, key: str):
        self._cache.pop(key, None)


seats_cache = SimpleCache()
