"""
Caching services for Nexus AI Assistant.

This module provides caching mechanisms for performance optimization.
"""
import logging
import time
from typing import Dict, Any, List, Optional, Union
import os
import json

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, falling back to in-memory cache")

class CacheService:
    """Base cache service interface."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize cache service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        self.app_context = app_context
        self.config = config or {}
        
    def get(self, key: str) -> Any:
        """Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value, or None if not found
        """
        raise NotImplementedError("Subclasses must implement this")
        
    def set(self, key: str, value: Any, timeout: int = None) -> bool:
        """Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Expiration time in seconds, or None for no expiration
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement this")
        
    def delete(self, key: str) -> bool:
        """Delete a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement this")
        
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern.
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            List of matching keys
        """
        raise NotImplementedError("Subclasses must implement this")
        
    def clear(self) -> bool:
        """Clear all cache.
        
        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement this")

class RedisCacheService(CacheService):
    """Redis-based cache service."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize Redis cache service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.redis_url = self.config.get("REDIS_URL", "redis://localhost:6379/0")
        self._client = None
        
        # Try to connect to Redis
        if REDIS_AVAILABLE:
            try:
                self._client = redis.from_url(self.redis_url)
                self._client.ping()
                logger.info(f"Connected to Redis at {self.redis_url}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis at {self.redis_url}: {str(e)}")
                self._client = None
        
        # Fall back to in-memory cache if Redis not available
        if not self._client:
            logger.warning("Using in-memory cache instead of Redis")
            self._memory_cache = {}
            self._expirations = {}
            
    def get(self, key: str) -> Any:
        """Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value, or None if not found
        """
        # Check if using Redis
        if self._client:
            value = self._client.get(key)
            if value:
                try:
                    return json.loads(value)
                except Exception as e:
                    logger.error(f"Error deserializing value for key {key}: {str(e)}")
                    return None
            return None
            
        # Otherwise use in-memory cache
        if key in self._memory_cache:
            # Check for expiration
            if key in self._expirations and self._expirations[key] < time.time():
                del self._memory_cache[key]
                del self._expirations[key]
                return None
                
            return self._memory_cache[key]
        return None
        
    def set(self, key: str, value: Any, timeout: int = None) -> bool:
        """Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Expiration time in seconds, or None for no expiration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert value to JSON
            json_value = json.dumps(value)
            
            # Use Redis if available
            if self._client:
                if timeout:
                    return bool(self._client.setex(key, timeout, json_value))
                else:
                    return bool(self._client.set(key, json_value))
                    
            # Otherwise use in-memory cache
            self._memory_cache[key] = value
            if timeout:
                self._expirations[key] = time.time() + timeout
            elif key in self._expirations:
                del self._expirations[key]
                
            return True
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {str(e)}")
            return False
            
    def delete(self, key: str) -> bool:
        """Delete a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use Redis if available
            if self._client:
                return bool(self._client.delete(key))
                
            # Otherwise use in-memory cache
            if key in self._memory_cache:
                del self._memory_cache[key]
                if key in self._expirations:
                    del self._expirations[key]
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {str(e)}")
            return False
            
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern.
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            List of matching keys
        """
        try:
            # Use Redis if available
            if self._client:
                return [key.decode() for key in self._client.keys(pattern)]
                
            # Otherwise use in-memory cache (simple glob matching)
            import fnmatch
            return fnmatch.filter(self._memory_cache.keys(), pattern)
        except Exception as e:
            logger.error(f"Error getting cache keys with pattern {pattern}: {str(e)}")
            return []
            
    def clear(self) -> bool:
        """Clear all cache.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use Redis if available
            if self._client:
                return bool(self._client.flushdb())
                
            # Otherwise use in-memory cache
            self._memory_cache.clear()
            self._expirations.clear()
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False

class FileCacheService(CacheService):
    """File-based cache service."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize file-based cache service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.cache_dir = self.config.get("CACHE_DIR", os.path.join(os.getcwd(), "cache"))
        
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"Using file cache at {self.cache_dir}")
        
    def _get_cache_path(self, key: str) -> str:
        """Get cache file path for a key.
        
        Args:
            key: Cache key
            
        Returns:
            Cache file path
        """
        # Replace any characters that would be invalid in a filename
        safe_key = key.replace("/", "_").replace("\\", "_").replace(":", "_")
        return os.path.join(self.cache_dir, f"{safe_key}.json")
        
    def get(self, key: str) -> Any:
        """Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value, or None if not found
        """
        cache_path = self._get_cache_path(key)
        if not os.path.exists(cache_path):
            return None
            
        try:
            # Check expiration first
            metadata_path = f"{cache_path}.metadata"
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                if "expiration" in metadata and metadata["expiration"] < time.time():
                    # Expired, remove files
                    os.remove(cache_path)
                    os.remove(metadata_path)
                    return None
            
            # Not expired, load value
            with open(cache_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading cache for key {key}: {str(e)}")
            return None
            
    def set(self, key: str, value: Any, timeout: int = None) -> bool:
        """Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            timeout: Expiration time in seconds, or None for no expiration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_path = self._get_cache_path(key)
            
            # Write value
            with open(cache_path, "w") as f:
                json.dump(value, f)
                
            # Write metadata if there's a timeout
            if timeout:
                metadata_path = f"{cache_path}.metadata"
                metadata = {"expiration": time.time() + timeout}
                with open(metadata_path, "w") as f:
                    json.dump(metadata, f)
                    
            return True
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {str(e)}")
            return False
            
    def delete(self, key: str) -> bool:
        """Delete a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cache_path = self._get_cache_path(key)
            metadata_path = f"{cache_path}.metadata"
            
            # Remove files if they exist
            if os.path.exists(cache_path):
                os.remove(cache_path)
            if os.path.exists(metadata_path):
                os.remove(metadata_path)
                
            return True
        except Exception as e:
            logger.error(f"Error deleting cache for key {key}: {str(e)}")
            return False
            
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern.
        
        Args:
            pattern: Key pattern to match
            
        Returns:
            List of matching keys
        """
        try:
            import fnmatch
            
            # Get all JSON files in cache directory
            all_files = [f for f in os.listdir(self.cache_dir) if f.endswith(".json") and not f.endswith(".metadata.json")]
            
            # Convert back to keys (remove .json extension)
            all_keys = [os.path.splitext(f)[0] for f in all_files]
            
            # Filter by pattern
            return fnmatch.filter(all_keys, pattern)
        except Exception as e:
            logger.error(f"Error getting cache keys with pattern {pattern}: {str(e)}")
            return []
            
    def clear(self) -> bool:
        """Clear all cache.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            for filename in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False
