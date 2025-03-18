"""
Application-wide configuration for Nexus AI Assistant.
"""
import secrets
from .base import config_provider

class AppConfig:
    """Application-wide configuration."""
    
    def __init__(self):
        """Initialize application configuration."""
        # Flask configuration
        self.SECRET_KEY = config_provider.get_env('SECRET_KEY', secrets.token_hex(16))
        self.DEBUG = config_provider.get_typed_env('FLASK_ENV', 'production') == 'development'
        
        # General app configuration
        self.APP_NAME = config_provider.get_env('APP_NAME', 'Nexus AI Assistant')
        self.APP_VERSION = config_provider.get_env('APP_VERSION', '1.0.0')
        
        # CORS configuration
        self.CORS_ALLOWED_ORIGINS = config_provider.get_env('CORS_ALLOWED_ORIGINS', '*')
        
        # Request handling
        self.REQUEST_TIMEOUT = config_provider.get_typed_env('REQUEST_TIMEOUT', 30, int)
        
    def as_dict(self) -> dict:
        """Get configuration as dictionary.
        
        Returns:
            Configuration dictionary
        """
        return {k: v for k, v in vars(self).items() if not k.startswith('_')}

# Create and register app config
app_config = AppConfig()
config_provider.register_component('app', app_config)
