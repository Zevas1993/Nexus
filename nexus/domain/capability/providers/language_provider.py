"""
Advanced Language Model Providers for Nexus AI Assistant.

This module provides capability providers for various language models
including OpenAI, Anthropic Claude, and others.
"""
import logging
import json
import aiohttp
import os
from typing import Dict, Any, List, Optional, Union

from ..abstraction import CapabilityProvider, CapabilityType

logger = logging.getLogger(__name__)

class AnthropicProvider(CapabilityProvider):
    """Anthropic Claude provider for text generation capabilities."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Anthropic Claude provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__("anthropic", config)
        self.api_key = self.config.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
        self.api_url = self.config.get("api_url", "https://api.anthropic.com/v1/messages")
        self.default_model = self.config.get("default_model", "claude-3-5-sonnet")
        self.timeout = self.config.get("timeout", 120)
        self.max_tokens = self.config.get("max_tokens", 4096)
        
    async def initialize(self) -> None:
        """Initialize the provider."""
        if not self.api_key:
            logger.warning("Anthropic API key not provided, provider will be disabled")
            self.enabled = False
            return
            
        # Register capabilities
        self.register_capability(CapabilityType.TEXT_GENERATION, self.generate_text)
        self.register_capability(CapabilityType.CODE_GENERATION, self.generate_code)
        
        # Test connection
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                
                # Simple test request
                test_data = {
                    "model": self.default_model,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hello"}]
                }
                
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=test_data,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"Anthropic API test failed: {error_text}")
                        self.enabled = False
                    else:
                        logger.info("Anthropic API connection successful")
        except Exception as e:
            logger.warning(f"Error connecting to Anthropic API: {str(e)}")
            self.enabled = False
            
    async def generate_text(self, 
                          prompt: str, 
                          context: Optional[List[Dict[str, str]]] = None,
                          model: Optional[str] = None,
                          temperature: float = 0.7,
                          max_tokens: Optional[int] = None,
                          system_prompt: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate text using Claude.
        
        Args:
            prompt: User prompt
            context: Conversation context
            model: Model name (default: claude-3-5-sonnet)
            temperature: Generation temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            system_prompt: System instructions
            **kwargs: Additional parameters
            
        Returns:
            Generated text result
        """
        if not self.enabled or not self.api_key:
            raise ValueError("Anthropic provider is not enabled")
            
        # Prepare request
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens
        
        # Build messages from context
        messages = []
        if context:
            for entry in context:
                if "user" in entry:
                    messages.append({"role": "user", "content": entry["user"]})
                if "assistant" in entry:
                    messages.append({"role": "assistant", "content": entry["assistant"]})
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        # Add any additional parameters
        for key, value in kwargs.items():
            if key not in payload and key not in ["context", "prompt"]:
                payload[key] = value
                
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"Anthropic API error: {error_text}")
                        
                    response_data = await response.json()
                    
                    # Extract content
                    content = response_data.get("content", [])
                    text = "".join([block.get("text", "") for block in content if block.get("type") == "text"])
                    
                    # Build result
                    result = {
                        "status": "success",
                        "text": text,
                        "model": model,
                        "usage": {
                            "input_tokens": response_data.get("usage", {}).get("input_tokens", 0),
                            "output_tokens": response_data.get("usage", {}).get("output_tokens", 0)
                        },
                        "id": response_data.get("id", "")
                    }
                    
                    return result
        except Exception as e:
            logger.error(f"Error generating text with Claude: {str(e)}")
            raise
            
    async def generate_code(self, 
                          prompt: str,
                          language: str = "python",
                          model: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate code using Claude.
        
        Args:
            prompt: Code generation prompt
            language: Programming language
            model: Model name
            **kwargs: Additional parameters
            
        Returns:
            Generated code result
        """
        # Use a code-optimized system prompt
        system_prompt = f"""You are an expert {language} programmer. 
        Generate clean, efficient, and well-documented {language} code that follows best practices.
        Provide only the code without explanations or comments outside the code."""
        
        # Create an enhanced prompt
        enhanced_prompt = f"""Write {language} code for the following task:
        
        {prompt}
        
        Only return the code without any explanation or markdown formatting.
        """
        
        # Call text generation with the enhanced prompt
        result = await self.generate_text(
            prompt=enhanced_prompt,
            model=model or "claude-3-5-sonnet",
            system_prompt=system_prompt,
            temperature=0.2,  # Lower temperature for more deterministic code
            **kwargs
        )
        
        # Extract code from the result
        code = result.get("text", "")
        
        # Clean up the code (remove markdown if present)
        if code.startswith("```") and "```" in code[3:]:
            # Extract code block
            code_block = code.split("```", 2)[1]
            if code_block.startswith(language):
                code = code_block[len(language):].strip()
            else:
                code = code_block.strip()
        
        # Update result
        result["code"] = code
        result["language"] = language
        
        return result


class OpenAIProvider(CapabilityProvider):
    """OpenAI provider for text and code generation capabilities."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize OpenAI provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__("openai", config)
        self.api_key = self.config.get("api_key", os.environ.get("OPENAI_API_KEY", ""))
        self.api_url = self.config.get("api_url", "https://api.openai.com/v1/chat/completions")
        self.default_model = self.config.get("default_model", "gpt-4o")
        self.timeout = self.config.get("timeout", 120)
        self.max_tokens = self.config.get("max_tokens", 4096)
        
    async def initialize(self) -> None:
        """Initialize the provider."""
        if not self.api_key:
            logger.warning("OpenAI API key not provided, provider will be disabled")
            self.enabled = False
            return
            
        # Register capabilities
        self.register_capability(CapabilityType.TEXT_GENERATION, self.generate_text)
        self.register_capability(CapabilityType.CODE_GENERATION, self.generate_code)
        
        # Test connection
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Simple test request
                test_data = {
                    "model": self.default_model,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hello"}]
                }
                
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=test_data,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"OpenAI API test failed: {error_text}")
                        self.enabled = False
                    else:
                        logger.info("OpenAI API connection successful")
        except Exception as e:
            logger.warning(f"Error connecting to OpenAI API: {str(e)}")
            self.enabled = False
            
    async def generate_text(self, 
                          prompt: str, 
                          context: Optional[List[Dict[str, str]]] = None,
                          model: Optional[str] = None,
                          temperature: float = 0.7,
                          max_tokens: Optional[int] = None,
                          system_prompt: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate text using OpenAI.
        
        Args:
            prompt: User prompt
            context: Conversation context
            model: Model name (default: gpt-4o)
            temperature: Generation temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            system_prompt: System instructions
            **kwargs: Additional parameters
            
        Returns:
            Generated text result
        """
        if not self.enabled or not self.api_key:
            raise ValueError("OpenAI provider is not enabled")
            
        # Prepare request
        model = model or self.default_model
        max_tokens = max_tokens or self.max_tokens
        
        # Build messages
        messages = []
        
        # Add system message if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # Add conversation context
        if context:
            for entry in context:
                if "user" in entry:
                    messages.append({"role": "user", "content": entry["user"]})
                if "assistant" in entry:
                    messages.append({"role": "assistant", "content": entry["assistant"]})
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})
        
        # Prepare request payload
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # Add any additional parameters
        for key, value in kwargs.items():
            if key not in payload and key not in ["context", "prompt", "system_prompt"]:
                payload[key] = value
                
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise ValueError(f"OpenAI API error: {error_text}")
                        
                    response_data = await response.json()
                    
                    # Extract content
                    choices = response_data.get("choices", [])
                    if not choices:
                        raise ValueError("No content in OpenAI response")
                        
                    message = choices[0].get("message", {})
                    text = message.get("content", "")
                    
                    # Build result
                    result = {
                        "status": "success",
                        "text": text,
                        "model": model,
                        "usage": response_data.get("usage", {}),
                        "id": response_data.get("id", "")
                    }
                    
                    return result
        except Exception as e:
            logger.error(f"Error generating text with OpenAI: {str(e)}")
            raise
            
    async def generate_code(self, 
                          prompt: str,
                          language: str = "python",
                          model: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate code using OpenAI.
        
        Args:
            prompt: Code generation prompt
            language: Programming language
            model: Model name
            **kwargs: Additional parameters
            
        Returns:
            Generated code result
        """
        # Use a code-optimized system prompt
        system_prompt = f"""You are an expert {language} programmer. 
        Generate clean, efficient, and well-documented {language} code that follows best practices.
        Provide only the code without explanations or comments outside the code."""
        
        # Create an enhanced prompt
        enhanced_prompt = f"""Write {language} code for the following task:
        
        {prompt}
        
        Only return the code without any explanation or markdown formatting.
        """
        
        # Call text generation with the enhanced prompt
        result = await self.generate_text(
            prompt=enhanced_prompt,
            model=model or self.default_model,
            system_prompt=system_prompt,
            temperature=0.2,  # Lower temperature for more deterministic code
            **kwargs
        )
        
        # Extract code from the result
        code = result.get("text", "")
        
        # Clean up the code (remove markdown if present)
        if code.startswith("```") and "```" in code[3:]:
            # Extract code block
            code_block = code.split("```", 2)[1]
            if code_block.startswith(language):
                code = code_block[len(language):].strip()
            else:
                code = code_block.strip()
        
        # Update result
        result["code"] = code
        result["language"] = language
        
        return result
