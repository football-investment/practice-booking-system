"""
Redis Cache Service
===================

Production-grade caching layer for high-performance endpoints.

Key Features:
- Health metrics caching (30s TTL)
- Async-compatible
- Automatic fallback if Redis unavailable
- JSON serialization

Author: Claude Code
Date: 2025-10-27
"""

import json
import logging
from typing import Any, Optional
import redis

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis cache wrapper with automatic fallback.

    If Redis is unavailable, methods gracefully return None
    to allow the application to continue without caching.
    """

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        """
        Initialize Redis connection.

        Args:
            host: Redis host (default: localhost)
            port: Redis port (default: 6379)
            db: Redis database number (default: 0)
        """
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            self.client.ping()
            self.available = True
            logger.info("✅ Redis cache connected successfully")
        except Exception as e:
            self.client = None
            self.available = False
            logger.warning(f"⚠️  Redis unavailable: {str(e)} - Running without cache")

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value (deserialized from JSON), or None if not found/error
        """
        if not self.available:
            return None

        try:
            value = self.client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.warning(f"Redis GET error for key '{key}': {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: int = 30) -> bool:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON-serialized)
            ttl: Time-to-live in seconds (default: 30)

        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            return False

        try:
            serialized = json.dumps(value)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Redis SET error for key '{key}': {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.available:
            return False

        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis DELETE error for key '{key}': {str(e)}")
            return False

    def flush_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Redis pattern (e.g., "health:*")

        Returns:
            Number of keys deleted
        """
        if not self.available:
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Redis FLUSH error for pattern '{pattern}': {str(e)}")
            return 0


# Global cache instance
cache = RedisCache()
