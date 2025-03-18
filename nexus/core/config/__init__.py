"""
Configuration module for Nexus AI Assistant.

This module provides access to all configuration components.
"""
from .base import ConfigProvider, get_config_provider
from .app_config import app_config, AppConfig
from .model_config import model_config, ModelConfig

__all__ = [
    'get_config_provider', 'ConfigProvider',
    'app_config', 'AppConfig',
    'model_config', 'ModelConfig',
    'get_config', 'config',
]

# For backward compatibility with old code
def get_config():
    """Get configuration components as a single object.
    
    This is provided for backward compatibility with the old config system.
    New code should use the component-specific configs directly.
    
    Returns:
        Object with all configuration components as attributes
    """
    class LegacyConfig:
        def __init__(self):
            self.app = app_config
            self.model = model_config
            
        def __getattr__(self, name):
            # Try to find the attribute in any component
            for component in [self.app, self.model]:
                if hasattr(component, name):
                    return getattr(component, name)
            raise AttributeError(f"'Config' object has no attribute '{name}'")
            
        def get(self, key, default=None):
            """Get configuration value.
            
            Args:
                key: Configuration key
                default: Default value if key not found
                
            Returns:
                Configuration value
            """
            try:
                return self.__getattr__(key)
            except AttributeError:
                return default
                
        def as_dict(self):
            """Get configuration as dictionary.
            
            Returns:
                Configuration dictionary
            """
            return get_config_provider().as_dict()
    
    return LegacyConfig()

# For current code, use this to access the new config system
config = get_config()
