"""
Core functionality for Nexus AI Assistant.

This package contains core components of the Nexus AI Assistant,
including configuration, context handling, and monitoring.
"""

# Import core components for easier access
from .config import config, app_config, model_config

__all__ = [
    'config', 'app_config', 'model_config',
]
