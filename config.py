"""
Configuration handler for Nexus AI Assistant.

This module loads environment variables from .env file and provides configuration values.
"""
import os
import secrets
from pathlib import Path
from typing import Dict, Any

# Try to load .env file if available
try:
    from dotenv import load_dotenv
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    # If python-dotenv is not installed, ignore
    pass

class Config:
    """Configuration class for Nexus AI Assistant."""
    
    def __init__(self):
        """Initialize configuration with default values."""
        # Flask configuration
        self.SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(16))
        self.DEBUG = os.getenv('FLASK_ENV', 'production') == 'development'
        
        # Database configuration
        self.SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        
        # Google OAuth configuration
        self.GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com')
        
        # Hugging Face API configuration
        self.HF_API_TOKEN = os.getenv('HF_API_TOKEN', '')
        self.HF_ENDPOINT = os.getenv('HF_ENDPOINT', 'https://api-inference.huggingface.co/models/gpt2')
        
        # Redis configuration
        self.REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        # CORS configuration
        self.CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '*')
        
        # Plugin configuration
        self.OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '')
        
        # AI model configuration
        self.LOCAL_MODEL = os.getenv('LOCAL_MODEL', 'EleutherAI/gpt-neo-125M')
        self.THRESHOLD_CPU = int(os.getenv('THRESHOLD_CPU', '80'))
        self.THRESHOLD_GPU = int(os.getenv('THRESHOLD_GPU', '80'))
        self.CONTEXT_WINDOW = int(os.getenv('CONTEXT_WINDOW', '5'))
        
    def as_dict(self) -> Dict[str, Any]:
        """Get configuration as a dictionary.
        
        Returns:
            Dictionary containing all configuration values
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.__dict__.get(key, default)

# Create a global configuration object
config = Config()

def get_config() -> Config:
    """Get the global configuration object.
    
    Returns:
        Configuration object
    """
    return config
