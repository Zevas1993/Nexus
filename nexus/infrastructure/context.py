"""
Application context for Nexus AI Assistant.

This module provides dependency injection and service management.
"""
import logging
from typing import Dict, Any, Type, Optional, TypeVar, Generic

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ApplicationContext:
    """Application context with dependency injection."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize application context.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.services = {}
        self.initialized = False
        logger.info("Application context created")
        
    def initialize(self):
        """Initialize application context."""
        if self.initialized:
            logger.warning("Application context already initialized")
            return
            
        logger.info("Initializing application context")
        self._register_services()
        self.initialized = True
        logger.info("Application context initialized")
        
    def _register_services(self):
        """Register core services."""
        # Import services here to avoid circular imports
        try:
            from ..domain.language.language_model_service import LanguageModelService
            self.register_service(LanguageModelService, LanguageModelService(self, self.config))
        except Exception as e:
            logger.warning(f"Failed to register LanguageModelService: {str(e)}")
            
        try:
            from ..infrastructure.security.auth import JwtAuthenticationService
            self.register_service(JwtAuthenticationService, JwtAuthenticationService(self, self.config))
        except Exception as e:
            logger.warning(f"Failed to register JwtAuthenticationService: {str(e)}")
            
        try:
            from ..infrastructure.performance.caching import RedisCacheService
            self.register_service(RedisCacheService, RedisCacheService(self, self.config))
        except Exception as e:
            logger.warning(f"Failed to register RedisCacheService: {str(e)}")
            
        try:
            from ..domain.system.system_service import SystemManagementService
            self.register_service(SystemManagementService, SystemManagementService(self, self.config))
        except Exception as e:
            logger.warning(f"Failed to register SystemManagementService: {str(e)}")
            
        # Try to register RAG service
        try:
            from ..domain.rag.enhanced_rag import EnhancedRAGService
            self.register_service(EnhancedRAGService, EnhancedRAGService(self, self.config))
        except Exception as e:
            logger.warning(f"Failed to register EnhancedRAGService: {str(e)}")
            
        # Try to register plugin loader
        try:
            from ..domain.plugins.loader import PluginLoaderService
            self.register_service(PluginLoaderService, PluginLoaderService(self, self.config))
        except Exception as e:
            logger.warning(f"Failed to register PluginLoaderService: {str(e)}")
    
    def register_service(self, service_type: Type[T], service_instance: T):
        """Register a service.
        
        Args:
            service_type: Service type
            service_instance: Service instance
        """
        self.services[service_type] = service_instance
        logger.info(f"Registered service: {service_type.__name__}")
        
    def get_service(self, service_type: Type[T]) -> Optional[T]:
        """Get a service by type.
        
        Args:
            service_type: Service type
            
        Returns:
            Service instance, or None if not found
        """
        if service_type not in self.services:
            # If service not registered, try to create it
            try:
                instance = service_type(self, self.config)
                self.register_service(service_type, instance)
                return instance
            except Exception as e:
                logger.error(f"Error creating service {service_type.__name__}: {str(e)}")
                return None
                
        return self.services.get(service_type)
