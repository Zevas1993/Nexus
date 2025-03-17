"""
Application context for Nexus AI Assistant.

This module provides a central application context for dependency injection,
configuration management, and service access.
"""
from typing import Dict, Any, Type, Optional, TypeVar, Generic, cast
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ApplicationContext:
    """Central application context for dependency injection and service access."""
    
    def __init__(self, config=None):
        """Initialize application context.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.services: Dict[Type, Any] = {}
        self.factories: Dict[Type, Any] = {}
        logger.info("Application context initialized")
        
    def initialize(self):
        """Initialize the application context."""
        logger.info("Initializing application context")
        
        # Register services from config
        if "services" in self.config:
            for service_type, service_config in self.config["services"].items():
                if isinstance(service_config, dict) and "factory" in service_config:
                    factory = service_config["factory"]
                    self.register_factory(service_type, factory)
                elif "instance" in service_config:
                    instance = service_config["instance"]
                    self.register_service(service_type, instance)
                    
        logger.info("Application context initialized")
        
    def register_service(self, service_type: Type[T], service: T) -> None:
        """Register a service.
        
        Args:
            service_type: Service type
            service: Service instance
        """
        logger.debug(f"Registering service: {service_type.__name__}")
        self.services[service_type] = service
        
    def register_factory(self, service_type: Type[T], factory) -> None:
        """Register a factory method for a service.
        
        Args:
            service_type: Service type
            factory: Factory method
        """
        logger.debug(f"Registering factory for: {service_type.__name__}")
        self.factories[service_type] = factory
        
    def get_service(self, service_type: Type[T]) -> T:
        """Get a service by type.
        
        Args:
            service_type: Service type
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not registered
        """
        # Check if service is already instantiated
        if service_type in self.services:
            return cast(T, self.services[service_type])
            
        # Check if we have a factory for this service
        if service_type in self.factories:
            # Instantiate service using factory
            factory = self.factories[service_type]
            service = factory(self)
            # Register service for future use
            self.register_service(service_type, service)
            return service
            
        # Try to instantiate service directly
        try:
            service = service_type(self.config)
            self.register_service(service_type, service)
            return service
        except Exception as e:
            logger.error(f"Error instantiating service {service_type.__name__}: {str(e)}")
            raise KeyError(f"Service {service_type.__name__} not registered and could not be instantiated")
            
    def create_child_context(self, config_override=None) -> 'ApplicationContext':
        """Create a child context with optional config override.
        
        Args:
            config_override: Configuration override
            
        Returns:
            Child application context
        """
        # Merge configuration
        merged_config = dict(self.config)
        if config_override:
            for key, value in config_override.items():
                if isinstance(value, dict) and key in merged_config and isinstance(merged_config[key], dict):
                    # Merge dictionaries
                    merged_config[key] = {**merged_config[key], **value}
                else:
                    # Replace value
                    merged_config[key] = value
                    
        # Create child context
        child = ApplicationContext(merged_config)
        
        # Inherit services
        for service_type, service in self.services.items():
            child.register_service(service_type, service)
            
        # Inherit factories
        for service_type, factory in self.factories.items():
            child.register_factory(service_type, factory)
            
        return child
