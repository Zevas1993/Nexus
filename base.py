"""
Base service classes for Nexus AI Assistant.

This module provides base classes for domain services.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseService(ABC):
    """Base class for all domain services."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize base service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        self.app_context = app_context
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
            
        Returns:
            Response dictionary
        """
        pass


class AsyncService(BaseService):
    """Base class for asynchronous services."""
    
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request asynchronously.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
            
        Returns:
            Response dictionary
        """
        self.logger.info(f"Processing request: {request}")
        try:
            result = await self._process_impl(request, **kwargs)
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    @abstractmethod
    async def _process_impl(self, request: str, **kwargs) -> Any:
        """Implementation of request processing.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
            
        Returns:
            Processing result
        """
        pass


class SyncService(BaseService):
    """Base class for synchronous services."""
    
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request synchronously.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
            
        Returns:
            Response dictionary
        """
        self.logger.info(f"Processing request: {request}")
        try:
            result = self._process_impl(request, **kwargs)
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            self.logger.error(f"Error processing request: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    @abstractmethod
    def _process_impl(self, request: str, **kwargs) -> Any:
        """Implementation of request processing.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
            
        Returns:
            Processing result
        """
        pass
