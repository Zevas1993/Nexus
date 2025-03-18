"""
Base configuration functionality for Nexus AI Assistant.

Provides the core configuration loader and provider classes.
"""
import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Generic, Union

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    # If python-dotenv is not installed, ignore
    pass

logger = logging.getLogger(__name__)

T = TypeVar('T')

class ConfigProvider:
    """Configuration provider for Nexus AI Assistant.
    
    Manages component-specific configurations and provides
    access to configuration values.
    """
    
    def __init__(self):
        """Initialize configuration provider."""
        self._components = {}
        self._env_cache = {}
        
    def register_component(self, component_name: str, component_config: Any):
        """Register component configuration.
        
        Args:
            component_name: Component name
            component_config: Component configuration instance
        """
        self._components[component_name] = component_config
        
    def get_component(self, component_name: str) -> Any:
        """Get component configuration.
        
        Args:
            component_name: Component name
            
        Returns:
            Component configuration
            
        Raises:
            KeyError: If component not found
        """
        if component_name not in self._components:
            raise KeyError(f"Configuration component not found: {component_name}")
            
        return self._components[component_name]
    
    def get_env(self, key: str, default: Any = None) -> Any:
        """Get environment variable with caching.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        if key not in self._env_cache:
            self._env_cache[key] = os.getenv(key, default)
            
        return self._env_cache[key]
        
    def get_typed_env(self, key: str, default: T, value_type: Type[T] = None) -> T:
        """Get typed environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            value_type: Type of value (inferred from default if None)
            
        Returns:
            Typed environment variable value
        """
        value = self.get_env(key)
        if value is None:
            return default
            
        if value_type is None:
            value_type = type(default)
        
        try:
            if value_type == bool:
                return value.lower() in ('true', '1', 'yes', 'y', 't')
            return value_type(value)
        except (ValueError, TypeError) as e:
            logger.warning(f"Error converting {key}={value} to {value_type.__name__}: {str(e)}")
            return default
            
    def as_dict(self) -> Dict[str, Any]:
        """Get all configuration as a dictionary.
        
        Returns:
            Configuration dictionary
        """
        result = {}
        
        for component_name, component in self._components.items():
            if hasattr(component, 'as_dict') and callable(component.as_dict):
                result[component_name] = component.as_dict()
            else:
                result[component_name] = {
                    k: v for k, v in vars(component).items() 
                    if not k.startswith('_')
                }
                
        return result

# Create global config provider
config_provider = ConfigProvider()

def get_config_provider() -> ConfigProvider:
    """Get global configuration provider.
    
    Returns:
        Configuration provider
    """
    return config_provider
