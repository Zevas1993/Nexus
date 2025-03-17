"""
Logging configuration for Nexus AI Assistant.

This module provides structured logging functionality.
"""

import logging
import logging.config
import os
import json
from typing import Dict, Any, Optional

def configure_logging(config: Dict[str, Any]):
    """Configure logging based on application configuration.
    
    Args:
        config: Application configuration
    """
    log_level = config.get('LOG_LEVEL', 'INFO')
    log_format = config.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = config.get('LOG_FILE')
    
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': log_format
            },
            'json': {
                'format': '%(message)s',
                'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'standard',
                'stream': 'ext://sys.stdout'
            }
        },
        'loggers': {
            '': {
                'handlers': ['console'],
                'level': log_level,
                'propagate': True
            }
        }
    }
    
    # Add file handler if log file is specified
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        logging_config['handlers']['file'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': log_level,
            'formatter': 'json' if config.get('LOG_JSON', False) else 'standard',
            'filename': log_file,
            'maxBytes': config.get('LOG_MAX_BYTES', 10485760),  # 10MB
            'backupCount': config.get('LOG_BACKUP_COUNT', 5)
        }
        logging_config['loggers']['']['handlers'].append('file')
    
    # Configure logging
    logging.config.dictConfig(logging_config)
    
    # Log configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")
    if log_file:
        logger.info(f"Log file: {log_file}")
