"""
Configuration management for Nexus AI Assistant.

This module handles loading configuration from environment variables,
configuration files, and default values.
"""

import os
from typing import Dict, Any, Optional
import json


class Config:
    """Configuration manager for Nexus AI Assistant."""
    
    DEFAULT_CONFIG = {
        # Core settings
        'APP_NAME': 'Nexus AI Assistant',
        'DEBUG': False,
        'SECRET_KEY': 'default_secret_key_change_in_production',
        'LOG_LEVEL': 'INFO',
        'PORT': 5000,
        'HOST': 'localhost',
        
        # Database and caching
        'DATABASE_URL': 'sqlite:///app.db',
        'REDIS_URL': 'redis://localhost:6379/0',
        'CELERY_BROKER_URL': 'redis://localhost:6379/0',
        'CELERY_RESULT_BACKEND': 'redis://localhost:6379/0',
        
        # Authentication
        'GOOGLE_CLIENT_ID': '',
        'CORS_ALLOWED_ORIGINS': '*',
        
        # API Rate limiting
        'RATE_LIMIT': '10 per minute',
        
        # Plugins
        'PLUGIN_DIR': 'plugins',
        
        # Base Language Model
        'HF_API_TOKEN': '',
        'HF_ENDPOINT': 'https://api-inference.huggingface.co/models/gpt2',
        'LOCAL_MODEL': 'EleutherAI/gpt-neo-125M',
        
        # Embeddings
        'EMBEDDING_MODEL': 'all-mpnet-base-v2',
        'MAX_TOKENS': 1024,
        
        # System thresholds
        'THRESHOLD_CPU': 80,
        'THRESHOLD_GPU': 80,
        'MAX_LENGTH': 512,
        'CONTEXT_WINDOW': 5,
        
        # Manus AI - Language Models
        'ANTHROPIC_API_KEY': '',
        'OPENAI_API_KEY': '',
        
        # Manus AI - Web Browsing
        'BROWSERLESS_API_KEY': '',
        
        # Manus AI - Vector Storage
        'PINECONE_API_KEY': '',
        'PINECONE_ENVIRONMENT': '',
        'PINECONE_INDEX_NAME': 'nexus-embeddings',
        
        # Manus AI - Default providers
        'DEFAULT_TEXT_PROVIDER': '',
        'DEFAULT_CODE_PROVIDER': '',
        'DEFAULT_WEB_PROVIDER': '',
        'DEFAULT_VECTOR_PROVIDER': '',
        
        # Manus AI - Feature toggles
        'ENABLE_LOCAL_PUPPETEER': True,
        'ENABLE_CHROMA': True,
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_file: Path to configuration file (JSON format)
        """
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load from config file if provided
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
        
        # Override with environment variables
        for key in self.config:
            env_value = os.getenv(key)
            if env_value is not None:
                # Convert string representations to appropriate types
                if isinstance(self.config[key], bool):
                    self.config[key] = env_value.lower() in ('true', 'yes', '1')
                elif isinstance(self.config[key], int):
                    self.config[key] = int(env_value)
                else:
                    self.config[key] = env_value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        return self.config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Get configuration value using dictionary syntax.
        
        Args:
            key: Configuration key
            
        Returns:
            Configuration value
            
        Raises:
            KeyError: If key not found
        """
        return self.config[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if configuration key exists.
        
        Args:
            key: Configuration key
            
        Returns:
            True if key exists, False otherwise
        """
        return key in self.config
    
    def as_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary.
        
        Returns:
            Dictionary of configuration values
        """
        return self.config.copy()
