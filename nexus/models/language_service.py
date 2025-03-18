"""
Language service interface for Nexus AI Assistant.

This module provides a base interface for all language model implementations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class LanguageModelService(ABC):
    """Base interface for language model services."""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the language model service."""
        pass
    
    @abstractmethod
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request using the language model.
        
        Args:
            request: The user's request text
            **kwargs: Additional parameters (model-specific)
                - context: Optional conversation context
                - temperature: Optional temperature parameter
                - max_tokens: Optional maximum tokens to generate
                - etc.
        
        Returns:
            A dictionary containing the processing result
        """
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the language model.
        
        Returns:
            A dictionary with model information
        """
        pass

class HybridLanguageModelService(LanguageModelService):
    """Language model service with multiple backend implementations.
    
    This service can switch between different model implementations
    based on availability and system resources.
    """
    
    def __init__(self, config=None):
        """Initialize the hybrid language model service.
        
        Args:
            config: Configuration settings
        """
        self.config = config or {}
        self.models = {}
        self.default_model = None
        
    async def initialize(self) -> None:
        """Initialize all available language models."""
        logger.info("Initializing hybrid language model service")
        
        # Initialize all model implementations
        for model_impl in self._get_model_implementations():
            try:
                await model_impl.initialize()
                model_info = model_impl.get_model_info()
                model_name = model_info.get('name', str(model_impl.__class__.__name__))
                self.models[model_name] = model_impl
                logger.info(f"Initialized model: {model_name}")
                
                # Set as default if none set yet
                if self.default_model is None:
                    self.default_model = model_name
            except Exception as e:
                logger.warning(f"Failed to initialize model {model_impl.__class__.__name__}: {str(e)}")
        
        if not self.models:
            logger.warning("No language models were successfully initialized")
        else:
            logger.info(f"Hybrid language model service initialized with {len(self.models)} models")
    
    def _get_model_implementations(self) -> List[LanguageModelService]:
        """Get all available model implementations.
        
        Returns:
            A list of model implementations
        """
        models = []
        
        # Import and instantiate model implementations
        try:
            from .mistral_model import MistralModel
            models.append(MistralModel(self.config))
        except ImportError:
            logger.info("Mistral model not available")
        
        try:
            from .local_model import LocalModel
            models.append(LocalModel(self.config))
        except ImportError:
            logger.info("Local model not available")
            
        try:
            from .cloud_model import CloudModel
            models.append(CloudModel(self.config))
        except ImportError:
            logger.info("Cloud model not available")
        
        return models
    
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request using the most appropriate model.
        
        Args:
            request: The user's request text
            **kwargs: Additional parameters
                - model: Optional model name to use
                - fallback: Whether to try other models if the requested one fails
        
        Returns:
            A dictionary containing the processing result
        """
        if not self.models:
            return {
                "error": "No language models available",
                "text": "I'm sorry, but no language processing capability is currently available."
            }
        
        # Get the model to use
        model_name = kwargs.pop('model', self.default_model)
        fallback = kwargs.pop('fallback', True)
        
        # Get model preference order
        if 'model_preference' in self.config:
            try:
                preference_order = self.config['model_preference']
                # If requested model is not in preference order, prepend it
                if model_name not in preference_order:
                    preference_order = [model_name] + preference_order
            except Exception:
                preference_order = list(self.models.keys())
                if model_name in preference_order:
                    # Move requested model to front
                    preference_order.remove(model_name)
                    preference_order = [model_name] + preference_order
        else:
            preference_order = list(self.models.keys())
            if model_name in preference_order:
                # Move requested model to front
                preference_order.remove(model_name)
                preference_order = [model_name] + preference_order
        
        # Try models in preference order
        errors = {}
        for name in preference_order:
            if name not in self.models:
                continue
                
            model = self.models[name]
            try:
                result = await model.process(request, **kwargs)
                result['model'] = name
                return result
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Error using model {name}: {error_msg}")
                errors[name] = error_msg
                
                # If fallback is disabled, stop after first attempt
                if not fallback:
                    break
        
        # If all models failed
        return {
            "error": "All language models failed",
            "details": errors,
            "text": "I'm sorry, but I encountered an issue processing your request."
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about all available models.
        
        Returns:
            A dictionary with model information
        """
        return {
            "service_type": "hybrid",
            "available_models": list(self.models.keys()),
            "default_model": self.default_model,
            "models": {
                name: model.get_model_info()
                for name, model in self.models.items()
            }
        }
    
    def get_available_models(self) -> List[str]:
        """Get list of available model names.
        
        Returns:
            A list of model names
        """
        return list(self.models.keys())
