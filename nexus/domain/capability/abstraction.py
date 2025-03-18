"""
Capability Abstraction Layer for Nexus AI Assistant.

This module provides a unified interface for accessing different capabilities
across multiple providers, enabling service switching, fallbacks, and consistent
interfaces regardless of the underlying implementation.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable, Type
from enum import Enum

logger = logging.getLogger(__name__)

class CapabilityType(Enum):
    """Types of capabilities supported by the abstraction layer."""
    TEXT_GENERATION = "text_generation"
    IMAGE_PROCESSING = "image_processing"  
    IMAGE_GENERATION = "image_generation"
    AUDIO_TRANSCRIPTION = "audio_transcription"
    AUDIO_GENERATION = "audio_generation"
    WEB_BROWSING = "web_browsing"
    CODE_EXECUTION = "code_execution"
    CODE_GENERATION = "code_generation"
    KNOWLEDGE_SEARCH = "knowledge_search"
    FILE_OPERATION = "file_operation"
    VECTOR_STORAGE = "vector_storage"

class CapabilityProvider:
    """Base class for capability providers."""
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """Initialize capability provider.
        
        Args:
            name: Provider name
            config: Provider configuration
        """
        self.name = name
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.capabilities = {}
        
    async def initialize(self) -> None:
        """Initialize the provider."""
        pass
        
    async def shutdown(self) -> None:
        """Shutdown the provider."""
        pass
        
    def register_capability(self, capability_type: CapabilityType, implementation: Callable) -> None:
        """Register a capability implementation.
        
        Args:
            capability_type: Type of capability
            implementation: Function implementing the capability
        """
        self.capabilities[capability_type] = implementation
        logger.info(f"Registered {capability_type.value} capability for provider {self.name}")
        
    def supports_capability(self, capability_type: CapabilityType) -> bool:
        """Check if provider supports a capability.
        
        Args:
            capability_type: Type of capability
            
        Returns:
            True if supported
        """
        return capability_type in self.capabilities
        
    async def execute_capability(self, 
                              capability_type: CapabilityType, 
                              **kwargs) -> Dict[str, Any]:
        """Execute a capability.
        
        Args:
            capability_type: Type of capability
            **kwargs: Arguments for the capability
            
        Returns:
            Execution result
            
        Raises:
            ValueError: If capability not supported
        """
        if not self.supports_capability(capability_type) or not self.enabled:
            raise ValueError(f"Capability {capability_type.value} not supported by {self.name}")
            
        implementation = self.capabilities[capability_type]
        try:
            return await implementation(**kwargs)
        except Exception as e:
            logger.error(f"Error executing {capability_type.value} with provider {self.name}: {str(e)}")
            raise

class CapabilityManager:
    """Manager for capability providers with fallbacks and routing."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize capability manager.
        
        Args:
            config: Configuration 
        """
        self.config = config or {}
        self.providers = {}
        self.default_providers = {}
        
    def register_provider(self, provider: CapabilityProvider) -> None:
        """Register a capability provider.
        
        Args:
            provider: Provider to register
        """
        self.providers[provider.name] = provider
        logger.info(f"Registered provider: {provider.name}")
        
        # Automatically set as default for supported capabilities if none set
        for capability_type in CapabilityType:
            if (provider.supports_capability(capability_type) and 
                capability_type not in self.default_providers):
                self.default_providers[capability_type] = provider.name
                logger.info(f"Set {provider.name} as default for {capability_type.value}")
                
    def set_default_provider(self, capability_type: CapabilityType, provider_name: str) -> None:
        """Set default provider for a capability.
        
        Args:
            capability_type: Type of capability
            provider_name: Provider name
            
        Raises:
            ValueError: If provider not registered or doesn't support capability
        """
        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not registered")
            
        provider = self.providers[provider_name]
        if not provider.supports_capability(capability_type):
            raise ValueError(f"Provider {provider_name} doesn't support {capability_type.value}")
            
        self.default_providers[capability_type] = provider_name
        logger.info(f"Set {provider_name} as default for {capability_type.value}")
        
    def get_providers_for_capability(self, capability_type: CapabilityType) -> List[str]:
        """Get all providers supporting a capability.
        
        Args:
            capability_type: Type of capability
            
        Returns:
            List of provider names
        """
        return [
            name for name, provider in self.providers.items()
            if provider.supports_capability(capability_type) and provider.enabled
        ]
        
    async def execute(self, 
                    capability_type: CapabilityType, 
                    provider_name: Optional[str] = None,
                    fallback: bool = True,
                    **kwargs) -> Dict[str, Any]:
        """Execute a capability with specified provider or default.
        
        Args:
            capability_type: Type of capability
            provider_name: Name of provider to use (optional)
            fallback: Whether to try other providers if primary fails
            **kwargs: Arguments for the capability
            
        Returns:
            Execution result
            
        Raises:
            ValueError: If no suitable provider found
        """
        # Determine provider to use
        if provider_name is not None:
            provider_names = [provider_name]
        elif capability_type in self.default_providers:
            provider_names = [self.default_providers[capability_type]]
        else:
            provider_names = []
            
        # Add fallbacks if enabled
        if fallback:
            all_providers = self.get_providers_for_capability(capability_type)
            for p in all_providers:
                if p not in provider_names:
                    provider_names.append(p)
        
        if not provider_names:
            raise ValueError(f"No provider available for {capability_type.value}")
        
        # Try providers in order
        last_error = None
        for name in provider_names:
            if name not in self.providers:
                logger.warning(f"Provider {name} not found")
                continue
                
            provider = self.providers[name]
            if not provider.supports_capability(capability_type) or not provider.enabled:
                continue
                
            try:
                logger.info(f"Executing {capability_type.value} with provider {name}")
                result = await provider.execute_capability(capability_type, **kwargs)
                
                # Add provider information to result
                if isinstance(result, dict):
                    result["provider"] = name
                    
                return result
            except Exception as e:
                logger.warning(f"Error with provider {name}: {str(e)}")
                last_error = e
                
                # If not falling back, re-raise the error
                if not fallback:
                    raise
        
        # If we get here, all providers failed
        error_msg = f"All providers failed for {capability_type.value}"
        if last_error:
            error_msg += f": {str(last_error)}"
            
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    async def initialize_all(self) -> None:
        """Initialize all registered providers."""
        for name, provider in self.providers.items():
            try:
                await provider.initialize()
                logger.info(f"Initialized provider: {name}")
            except Exception as e:
                logger.error(f"Error initializing provider {name}: {str(e)}")
                provider.enabled = False
                
    async def shutdown_all(self) -> None:
        """Shutdown all registered providers."""
        for name, provider in self.providers.items():
            try:
                await provider.shutdown()
                logger.info(f"Shut down provider: {name}")
            except Exception as e:
                logger.error(f"Error shutting down provider {name}: {str(e)}")
