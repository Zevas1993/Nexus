"""
Application context and dependency injection for Nexus AI Assistant.

This module provides a central application context for managing services
and dependencies throughout the application.
"""

from typing import Dict, Type, Any, Optional, TypeVar, Generic, cast
import inspect

T = TypeVar('T')

class ApplicationContext:
    """Application context for managing services and dependencies."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize application context.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.services: Dict[Type, Any] = {}
        self._initializers: Dict[Type, Any] = {}
    
    def register(self, service_class: Type[T], instance: Optional[T] = None, initializer=None):
        """Register a service with the application context.
        
        Args:
            service_class: Service class type
            instance: Optional pre-initialized instance
            initializer: Optional function to initialize service
        """
        if instance:
            self.services[service_class] = instance
        elif initializer:
            self._initializers[service_class] = initializer
    
    def get_service(self, service_class: Type[T]) -> T:
        """Get a service from the application context.
        
        If the service is not yet initialized, it will be initialized
        using the registered initializer or by calling the constructor.
        
        Args:
            service_class: Service class type
            
        Returns:
            Service instance
            
        Raises:
            ValueError: If service cannot be initialized
        """
        if service_class not in self.services:
            if service_class in self._initializers:
                # Initialize using registered initializer
                self.services[service_class] = self._initializers[service_class]()
            else:
                # Try to initialize using constructor
                try:
                    # Check if constructor requires config
                    sig = inspect.signature(service_class.__init__)
                    if 'config' in sig.parameters:
                        self.services[service_class] = service_class(config=self.config)
                    elif 'app_context' in sig.parameters:
                        self.services[service_class] = service_class(app_context=self)
                    else:
                        self.services[service_class] = service_class()
                except Exception as e:
                    raise ValueError(f"Could not initialize service {service_class.__name__}: {str(e)}")
        
        return cast(T, self.services[service_class])
    
    def initialize(self):
        """Initialize all registered services."""
        # This method can be extended to perform additional initialization
        # such as establishing database connections, etc.
        pass
