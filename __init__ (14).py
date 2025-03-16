"""
Cache package for Nexus AI Assistant.

This package contains caching mechanisms for improved performance.
"""

from typing import Dict, Any, Optional, Union, List
import logging
import json
import time
import redis

logger = logging.getLogger(__name__)

class RedisCacheService:
    """Redis-based caching service."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Redis cache service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.redis_url = config.get('REDIS_URL', 'redis://localhost:6379/0')
        self.default_ttl = config.get('CACHE_TTL', 3600)  # 1 hour by default
        self.client = None
        self.initialize()
    
    def initialize(self):
        """Initialize Redis connection."""
        try:
            self.client = redis.from_url(self.redis_url)
            logger.info(f"Redis cache initialized with URL: {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {str(e)}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available.
        
        Returns:
            True if Redis is available, False otherwise
        """
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except:
            return False
    
    def get(self, key: str) -> Any:
        """Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.is_available():
            return None
        
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Error getting cache key {key}: {str(e)}")
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None for default)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        ttl = ttl if ttl is not None else self.default_ttl
        
        try:
            serialized = json.dumps(value)
            self.client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Error setting cache key {key}: {str(e)}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Error deleting cache key {key}: {str(e)}")
            return False
    
    def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern.
        
        Args:
            pattern: Key pattern
            
        Returns:
            List of matching keys
        """
        if not self.is_available():
            return []
        
        try:
            keys = self.client.keys(pattern)
            return [k.decode('utf-8') for k in keys]
        except Exception as e:
            logger.warning(f"Error getting keys with pattern {pattern}: {str(e)}")
            return []
    
    def flush(self) -> bool:
        """Flush all cache entries.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            return False
        
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            logger.warning(f"Error flushing cache: {str(e)}")
            return False
