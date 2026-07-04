"""
api/cache_service.py
=====================
Caches API responses in MySQL to avoid rate limits.

HOW THE CACHE WORKS:
    1. App wants data for AAPL
    2. Check cache: is there a fresh entry for 'stock_info_AAPL'?
    3a. YES (cache hit)  → return cached data immediately
    3b. NO  (cache miss) → fetch from API, save to cache, return data

WHY CACHE IN MYSQL INSTEAD OF MEMORY?
    Memory cache is lost when the app closes.
    MySQL cache persists between sessions — if you fetched
    AAPL's data 5 minutes ago and restart the app,
    it doesn't need to fetch again.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class CacheService:
    """
    Manages API response caching in the api_cache table.
    """

    DEFAULT_TTL_MINUTES = 15   # Cache expires after 15 minutes by default

    def get(self, cache_key: str) -> Optional[dict]:
        """
        Retrieves a cached value if it exists and hasn't expired.

        Args:
            cache_key: Unique string identifying this cached item
                       e.g. 'stock_info_AAPL', 'history_MSFT_1y'

        Returns:
            Parsed dict from cache, or None if missing/expired
        """
        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """SELECT response_data, expires_at
                   FROM api_cache
                   WHERE cache_key = %s
                   AND expires_at > NOW()""",
                (cache_key,)
            )
            row = cursor.fetchone()
            cursor.close()

            if row:
                logger.debug(f"Cache HIT for key: {cache_key}")
                return json.loads(row['response_data'])

            logger.debug(f"Cache MISS for key: {cache_key}")
            return None

        except Exception as e:
            logger.warning(f"Cache read failed for {cache_key}: {e}")
            return None
        finally:
            conn.close()

    def set(self, cache_key: str, data: dict,
            ttl_minutes: int = DEFAULT_TTL_MINUTES) -> bool:
        """
        Saves data to the cache with an expiry time.

        Args:
            cache_key:   Unique key for this cached item
            data:        Dict to cache (must be JSON-serialisable)
            ttl_minutes: Minutes until this cache entry expires

        Returns:
            True on success, False on failure
        """
        conn = DatabaseConnection.get_connection()
        try:
            expires_at = datetime.now() + timedelta(minutes=ttl_minutes)
            json_data  = json.dumps(data, default=str)

            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO api_cache
                   (cache_key, response_data, expires_at)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE
                       response_data = VALUES(response_data),
                       cached_at     = NOW(),
                       expires_at    = VALUES(expires_at)""",
                (cache_key, json_data, expires_at)
            )
            conn.commit()
            cursor.close()
            logger.debug(f"Cache SET for key: {cache_key} (TTL={ttl_minutes}m)")
            return True

        except Exception as e:
            conn.rollback()
            logger.warning(f"Cache write failed for {cache_key}: {e}")
            return False
        finally:
            conn.close()

    def invalidate(self, cache_key: str) -> None:
        """Forces a cache entry to expire immediately."""
        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM api_cache WHERE cache_key = %s",
                (cache_key,)
            )
            conn.commit()
            cursor.close()
            logger.debug(f"Cache invalidated: {cache_key}")
        except Exception as e:
            conn.rollback()
            logger.warning(f"Cache invalidation failed: {e}")
        finally:
            conn.close()

    def clear_expired(self) -> int:
        """
        Deletes all expired cache entries.
        Run this periodically to keep the table clean.
        Returns number of entries deleted.
        """
        conn = DatabaseConnection.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM api_cache WHERE expires_at <= NOW()"
            )
            conn.commit()
            count = cursor.rowcount
            cursor.close()
            if count:
                logger.info(f"Cleared {count} expired cache entries.")
            return count
        except Exception as e:
            conn.rollback()
            logger.warning(f"Cache clear failed: {e}")
            return 0
