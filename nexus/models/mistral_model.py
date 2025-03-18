"""
Mistral AI model implementation for Nexus AI Assistant.

This module provides integration with Mistral Small 3.1.
"""

import logging
import json
import aiohttp
from typing import Dict, Any, List, Optional, Union

from ..core.config import model_config
from .language_service import LanguageModelService

logger = logging.getLogger(__name__)

class MistralModel(LanguageModelService):
    """Implementation of Mistral Small 3.1 language model."""
    
    def __init__(self, config=None):
        """Initialize Mistral model service.
        
        Args:
            config: Configuration dictionary (optional, will use model_config if not provided)
        """
        self.config = config or {}
        self.api_key = self.config.get('MISTRAL_SMALL_API_KEY', model_config.MISTRAL_SMALL_API_KEY)
        self.endpoint = self.config.get('MISTRAL_ENDPOINT', model_config.MISTRAL_ENDPOINT)
        self.initialized = False
        self.model_name = "mistral-small-3.1"
        
    async def initialize(self) -> None:
        """Initialize Mistral model service."""
        if not self.api_key:
            raise ValueError("Mistral API key is required")
            
        logger.info(f"Initializing Mistral model: {self.model_name}")
        
        # Test connection to Mistral API
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                async with session.get("https://api.mistral.ai/v1/models", headers=headers) as response:
                    if response.status == 200:
                        models = await response.json()
                        available_models = [model.get("id") for model in models.get("data", [])]
                        
                        if self.model_name not in available_models:
                            logger.warning(f"Mistral model {self.model_name} not found in available models: {available_models}")
                            logger.info(f"Will try to use {self.model_name} anyway")
                    else:
                        error_text = await response.text()
                        logger.warning(f"Error testing Mistral API: {response.status} - {error_text}")
                        
            self.initialized = True
            logger.info("Mistral model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Mistral model: {str(e)}")
            raise
    
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request using Mistral Small 3.1.
        
        Args:
            request: The user's request text
            **kwargs: Additional parameters including:
                - context: Conversation context
                - temperature: Sampling temperature (default: 0.7)
                - max_tokens: Maximum tokens to generate (default: 1024)
                - top_p: Nucleus sampling parameter (default: 0.95)
                - stop: Sequence(s) at which to stop generation
        
        Returns:
            A dictionary containing the processing result
        """
        if not self.initialized:
            await self.initialize()
            
        # Extract parameters from kwargs
        context = kwargs.get('context', [])
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 1024)
        top_p = kwargs.get('top_p', 0.95)
        stop = kwargs.get('stop', None)
        stream = kwargs.get('stream', False)
        
        # If context is provided, format it as messages
        messages = self._prepare_messages(request, context)
        
        # Prepare API request
        api_request = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream
        }
        
        if stop:
            api_request["stop"] = stop
            
        logger.info(f"Sending request to Mistral API: {api_request['model']}")
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Full Mistral API request: {json.dumps(api_request)}")
        
        # Send request to Mistral API
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                async with session.post(
                    "https://api.mistral.ai/v1/chat/completions", 
                    headers=headers,
                    json=api_request
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Error from Mistral API: {response.status} - {error_text}")
                        return {
                            "error": f"Mistral API error: {response.status}",
                            "text": "I encountered an issue with the language model service."
                        }
                    
                    result = await response.json()
                    
                    # Extract the generated text
                    if "choices" in result and len(result["choices"]) > 0:
                        choice = result["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            generated_text = choice["message"]["content"]
                            
                            # Get token counts
                            prompt_tokens = result.get("usage", {}).get("prompt_tokens", 0)
                            completion_tokens = result.get("usage", {}).get("completion_tokens", 0)
                            total_tokens = result.get("usage", {}).get("total_tokens", 0)
                            
                            return {
                                "text": generated_text,
                                "model": self.model_name,
                                "prompt_tokens": prompt_tokens,
                                "completion_tokens": completion_tokens,
                                "total_tokens": total_tokens
                            }
                    
                    # If extraction failed, return the raw result
                    return {
                        "text": "Failed to extract response from Mistral API",
                        "raw_result": result
                    }
        except Exception as e:
            logger.error(f"Error processing request with Mistral: {str(e)}")
            return {
                "error": f"Mistral processing error: {str(e)}",
                "text": "I encountered an issue processing your request."
            }
    
    def _prepare_messages(self, request: str, context: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Prepare messages from request and context.
        
        Args:
            request: User request text
            context: Conversation context
            
        Returns:
            List of message dictionaries for the Mistral API
        """
        # Start with a system message
        messages = [
            {
                "role": "system",
                "content": "You are Nexus, a helpful and versatile AI assistant developed by the Nexus team. Provide accurate, helpful, and concise responses."
            }
        ]
        
        # Add context messages if available
        if context:
            for entry in context:
                if "user" in entry:
                    messages.append({
                        "role": "user",
                        "content": entry["user"]
                    })
                if "assistant" in entry:
                    messages.append({
                        "role": "assistant",
                        "content": entry["assistant"]
                    })
        
        # Add the current request
        messages.append({
            "role": "user",
            "content": request
        })
        
        return messages
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model.
        
        Returns:
            A dictionary with model information
        """
        return {
            "name": "mistral",
            "model": self.model_name,
            "provider": "Mistral AI",
            "capabilities": [
                "chat",
                "reasoning",
                "coding",
                "instruction-following"
            ],
            "context_window": 8192,  # Mistral Small context window
            "initialized": self.initialized
        }
