"""
Unit tests for app/services/redis_cache.py
Covers: RedisCache.__init__, get, set, delete, flush_pattern
All available/unavailable branches + error paths.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.redis_cache import RedisCache


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cache_available():
    """RedisCache instance with available=True and mocked client."""
    cache = RedisCache.__new__(RedisCache)
    cache.available = True
    cache.client = MagicMock()
    return cache


def _cache_unavailable():
    """RedisCache instance with available=False (Redis down)."""
    cache = RedisCache.__new__(RedisCache)
    cache.available = False
    cache.client = None
    return cache


# ---------------------------------------------------------------------------
# __init__ — connection success / failure
# ---------------------------------------------------------------------------

class TestInit:

    def test_init01_ping_succeeds_available_true(self):
        """INIT-01: Redis ping succeeds → available=True."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        with patch("app.services.redis_cache.redis.Redis", return_value=mock_client):
            cache = RedisCache(host="localhost", port=6379)
        assert cache.available is True
        assert cache.client is mock_client

    def test_init02_ping_fails_available_false(self):
        """INIT-02: Redis connection raises exception → available=False, client=None."""
        with patch("app.services.redis_cache.redis.Redis", side_effect=ConnectionError("refused")):
            cache = RedisCache(host="localhost", port=6379)
        assert cache.available is False
        assert cache.client is None

    def test_init03_ping_exception_available_false(self):
        """INIT-03: Client constructed but ping() raises → available=False."""
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("timeout")
        with patch("app.services.redis_cache.redis.Redis", return_value=mock_client):
            cache = RedisCache()
        assert cache.available is False


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

class TestGet:

    def test_get01_unavailable_returns_none(self):
        """GET-01: not available → returns None immediately."""
        cache = _cache_unavailable()
        result = cache.get("key")
        assert result is None

    def test_get02_cache_miss_returns_none(self):
        """GET-02: key not in Redis → None."""
        cache = _cache_available()
        cache.client.get.return_value = None
        result = cache.get("missing_key")
        assert result is None

    def test_get03_cache_hit_returns_deserialized(self):
        """GET-03: key found → JSON deserialized."""
        cache = _cache_available()
        cache.client.get.return_value = json.dumps({"data": 42})
        result = cache.get("health:summary")
        assert result == {"data": 42}

    def test_get04_redis_error_returns_none(self):
        """GET-04: Redis raises exception → returns None."""
        cache = _cache_available()
        cache.client.get.side_effect = Exception("connection lost")
        result = cache.get("key")
        assert result is None


# ---------------------------------------------------------------------------
# set
# ---------------------------------------------------------------------------

class TestSet:

    def test_set01_unavailable_returns_false(self):
        """SET-01: not available → False."""
        cache = _cache_unavailable()
        result = cache.set("key", {"val": 1})
        assert result is False

    def test_set02_success_returns_true(self):
        """SET-02: available + setex succeeds → True."""
        cache = _cache_available()
        cache.client.setex.return_value = True
        result = cache.set("key", {"val": 1}, ttl=60)
        assert result is True
        cache.client.setex.assert_called_once_with("key", 60, json.dumps({"val": 1}))

    def test_set03_redis_error_returns_false(self):
        """SET-03: setex raises → False."""
        cache = _cache_available()
        cache.client.setex.side_effect = Exception("write error")
        result = cache.set("key", {"val": 1})
        assert result is False

    def test_set04_default_ttl_is_30(self):
        """SET-04: default ttl=30 used."""
        cache = _cache_available()
        cache.set("k", "v")
        args = cache.client.setex.call_args
        assert args[0][1] == 30  # ttl is second positional arg


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

class TestDelete:

    def test_del01_unavailable_returns_false(self):
        """DEL-01: not available → False."""
        cache = _cache_unavailable()
        assert cache.delete("key") is False

    def test_del02_success_returns_true(self):
        """DEL-02: available + delete succeeds → True."""
        cache = _cache_available()
        cache.client.delete.return_value = 1
        result = cache.delete("key")
        assert result is True
        cache.client.delete.assert_called_once_with("key")

    def test_del03_redis_error_returns_false(self):
        """DEL-03: delete raises → False."""
        cache = _cache_available()
        cache.client.delete.side_effect = Exception("oops")
        result = cache.delete("key")
        assert result is False


# ---------------------------------------------------------------------------
# flush_pattern
# ---------------------------------------------------------------------------

class TestFlushPattern:

    def test_fp01_unavailable_returns_zero(self):
        """FP-01: not available → 0."""
        cache = _cache_unavailable()
        assert cache.flush_pattern("health:*") == 0

    def test_fp02_no_matching_keys_returns_zero(self):
        """FP-02: keys() returns empty list → 0."""
        cache = _cache_available()
        cache.client.keys.return_value = []
        result = cache.flush_pattern("health:*")
        assert result == 0

    def test_fp03_matching_keys_deletes_and_returns_count(self):
        """FP-03: keys found → delete called, returns count."""
        cache = _cache_available()
        cache.client.keys.return_value = ["health:1", "health:2"]
        cache.client.delete.return_value = 2
        result = cache.flush_pattern("health:*")
        assert result == 2
        cache.client.delete.assert_called_once_with("health:1", "health:2")

    def test_fp04_redis_error_returns_zero(self):
        """FP-04: keys() raises → 0."""
        cache = _cache_available()
        cache.client.keys.side_effect = Exception("network error")
        result = cache.flush_pattern("health:*")
        assert result == 0
