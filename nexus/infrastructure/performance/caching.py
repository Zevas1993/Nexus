"""
Caching service for Nexus AI Assistant.

This module provides caching services for improved performance
and reduced load on external APIs.
"""
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union, Set

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache")

class RedisCacheService:
    """Redis-based caching service with fallback to in-memory caching."""
    
    def __init__(self, config=None):
        """Initialize caching service.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.redis_url = self.config.get("REDIS_URL", "redis://localhost:6379/0")
        self.default_timeout = self.config.get("CACHE_TIMEOUT", 3600)  # 1 hour
        self._redis = None
        self._memory_cache = {}
        self._memory_expiry = {}
        
        # Try to connect to Redis
        if REDIS_AVAILABLE:
            try:
                self._redis = redis.from_url(self.redis_url)
                self._redis.ping()
                logger.info(f"Connected to Redis: {self.redis_url}")
            except Exception as e:
                logger.warning(f"Error connecting to Redis: {str(e)}")
                self._redis = None
        
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        # Try Redis first
        if self._redis:
            try:
                value = self._redis.get(key)
                if value:
                    logger.debug(f"Cache hit (Redis): {key}")
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Error getting from Redis: {str(e)}")
        
        # Fall back to memory cache
        if key in self._memory_cache:
            # Check if expired
            if key in self._memory_expiry and self._memory_expiry[key] < time.time():
                # Expired
                logger.debug(f"Cache expired: {key}")
                del self._memory_cache[key]
                del self._memory_expiry[key]
                return None
            
            logger.debug(f"Cache hit (memory): {key}")
            return self._memory_cache[key]
        
        logger.debug(f"Cache miss: {key}")
        return None
    
    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Cache timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        timeout = timeout or self.default_timeout
        
        # Try Redis first
        if self._redis:
            try:
                serialized = json.dumps(value)
                self._redis.setex(key, timeout, serialized)
                logger.debug(f"Cached in Redis: {key} (timeout: {timeout}s)")
                return True
            except Exception as e:
                logger.warning(f"Error setting in Redis: {str(e)}")
        
        # Fall back to memory cache
        try:
            self._memory_cache[key] = value
            self._memory_expiry[key] = time.time() + timeout
            logger.debug(f"Cached in memory: {key} (timeout: {timeout}s)")
            return True
        except Exception as e:
            logger.error(f"Error setting in memory cache: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        success = False
        
        # Try Redis
        if self._redis:
            try:
                self._redis.delete(key)
                logger.debug(f"Deleted from Redis: {key}")
                success = True
            except Exception as e:
                logger.warning(f"Error deleting from Redis: {str(e)}")
        
        # Also check memory cache
        if key in self._memory_cache:
            del self._memory_cache[key]
            if key in self._memory_expiry:
                del self._memory_expiry[key]
            logger.debug(f"Deleted from memory: {key}")
            success = True
        
        return success
    
    def keys(self, pattern: str) -> Set[str]:
        """Get keys matching a pattern.
        
        Args:
            pattern: Key pattern with glob-style wildcards
            
        Returns:
            Set of matching keys
        """
        result = set()
        
        # Try Redis
        if self._redis:
            try:
                redis_keys = self._redis.keys(pattern)
                result.update(k.decode('utf-8') for k in redis_keys)
                logger.debug(f"Found {len(redis_keys)} keys in Redis matching: {pattern}")
            except Exception as e:
                logger.warning(f"Error getting keys from Redis: {str(e)}")
        
        # Also check memory cache
        # This is a simplified implementation - in a real system,
        # we would use proper pattern matching
        for k in self._memory_cache.keys():
            if self._simple_match(k, pattern):
                # Check if expired
                if k in self._memory_expiry and self._memory_expiry[k] < time.time():
                    continue
                
                result.add(k)
        
        return result
    
    def _simple_match(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for keys.
        
        Args:
            key: Key to check
            pattern: Pattern with * wildcards
            
        Returns:
            True if key matches pattern
        """
        # Convert glob pattern to a simple regex pattern
        import re
        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", key))
    
    def flush_all(self) -> bool:
        """Flush all cached values.
        
        Returns:
            True if successful, False otherwise
        """
        success = False
        
        # Try Redis
        if self._redis:
            try:
                self._redis.flushdb()
                logger.debug("Flushed Redis DB")
                success = True
            except Exception as e:
                logger.warning(f"Error flushing Redis: {str(e)}")
        
        # Also flush memory cache
        self._memory_cache = {}
        self._memory_expiry = {}
        logger.debug("Flushed memory cache")
        success = True
        
        return success
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Cache statistics
        """
        stats = {
            "backend": "redis" if self._redis else "memory",
            "memory_keys": len(self._memory_cache),
            "redis_connected": self._redis is not None
        }
        
        # Add Redis stats if available
        if self._redis:
            try:
                redis_info = self._redis.info()
                stats.update({
                    "redis_used_memory": redis_info.get("used_memory_human"),
                    "redis_hits": redis_info.get("keyspace_hits"),
                    "redis_misses": redis_info.get("keyspace_misses"),
                    "redis_keys": sum(db.get("keys", 0) for db_name, db in redis_info.items() if db_name.startswith("db"))
                })
            except Exception as e:
                logger.warning(f"Error getting Redis stats: {str(e)}")
        
        return stats
