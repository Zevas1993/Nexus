"""
Rate limiting service for Nexus AI Assistant.

This module provides rate limiting functionality to protect API endpoints.
"""

from typing import Dict, Any, Optional, Callable
import time
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for API endpoints."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize rate limiter.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.default_limit = self._parse_limit(config.get('RATE_LIMIT', '10 per minute'))
        self.limits: Dict[str, Dict[str, Any]] = {}
        self.request_history: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
    
    def _parse_limit(self, limit_str: str) -> Dict[str, Any]:
        """Parse rate limit string.
        
        Args:
            limit_str: Rate limit string (e.g., "10 per minute")
            
        Returns:
            Dictionary with limit and period
        """
        parts = limit_str.split(' per ')
        if len(parts) != 2:
            logger.warning(f"Invalid rate limit format: {limit_str}, using default")
            return {'limit': 10, 'period': 60}
        
        try:
            limit = int(parts[0])
            period_str = parts[1]
            
            if period_str == 'second':
                period = 1
            elif period_str == 'minute':
                period = 60
            elif period_str == 'hour':
                period = 3600
            elif period_str == 'day':
                period = 86400
            else:
                logger.warning(f"Invalid rate limit period: {period_str}, using default")
                period = 60
                
            return {'limit': limit, 'period': period}
        except ValueError:
            logger.warning(f"Invalid rate limit: {limit_str}, using default")
            return {'limit': 10, 'period': 60}
    
    def set_limit(self, endpoint: str, limit_str: str):
        """Set rate limit for endpoint.
        
        Args:
            endpoint: API endpoint
            limit_str: Rate limit string (e.g., "10 per minute")
        """
        self.limits[endpoint] = self._parse_limit(limit_str)
        logger.info(f"Set rate limit for {endpoint}: {limit_str}")
    
    def is_allowed(self, endpoint: str, key: str) -> bool:
        """Check if request is allowed based on rate limit.
        
        Args:
            endpoint: API endpoint
            key: Rate limit key (e.g., user ID or IP address)
            
        Returns:
            True if request is allowed, False otherwise
        """
        now = time.time()
        limit_config = self.limits.get(endpoint, self.default_limit)
        limit = limit_config['limit']
        period = limit_config['period']
        
        # Clean up old requests
        history = self.request_history[endpoint][key]
        while history and history[0] < now - period:
            history.popleft()
        
        # Check if limit exceeded
        if len(history) >= limit:
            logger.warning(f"Rate limit exceeded for {endpoint} by {key}")
            return False
        
        # Add current request
        history.append(now)
        return True
    
    def get_remaining(self, endpoint: str, key: str) -> Dict[str, Any]:
        """Get remaining requests and reset time.
        
        Args:
            endpoint: API endpoint
            key: Rate limit key (e.g., user ID or IP address)
            
        Returns:
            Dictionary with remaining requests and reset time
        """
        now = time.time()
        limit_config = self.limits.get(endpoint, self.default_limit)
        limit = limit_config['limit']
        period = limit_config['period']
        
        # Clean up old requests
        history = self.request_history[endpoint][key]
        while history and history[0] < now - period:
            history.popleft()
        
        # Calculate remaining and reset time
        remaining = max(0, limit - len(history))
        reset_time = history[0] + period if history else now + period
        
        return {
            'remaining': remaining,
            'limit': limit,
            'reset': int(reset_time)
        }
