"""
Capability Service for Nexus AI Assistant.

This service manages and provides access to the capability abstraction layer,
facilitating integration with various AI providers and services.
"""
import logging
import os
from typing import Dict, Any, Optional, List

from .abstraction import CapabilityType, CapabilityManager
from .providers import (
    AnthropicProvider, OpenAIProvider, 
    BrowserlessProvider, PuppeteerLocalProvider,
    PineconeProvider, ChromaProvider
)

logger = logging.getLogger(__name__)

class CapabilityService:
    """Service for managing and accessing AI capabilities across providers."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize capability service.
        
        Args:
            config: Service configuration
        """
        self.config = config or {}
        self.manager = CapabilityManager(config)
        self._initialized = False
        
    async def initialize(self):
        """Initialize capability service."""
        if self._initialized:
            return
            
        logger.info("Initializing Capability Service")
        
        # Register providers
        await self._register_providers()
        
        # Initialize all providers
        await self.manager.initialize_all()
        
        self._initialized = True
        logger.info("Capability Service initialized")
        
    async def _register_providers(self):
        """Register capability providers."""
        # Register Anthropic provider if configured
        anthropic_config = self.config.get("anthropic", {})
        anthropic_api_key = anthropic_config.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
        
        if anthropic_api_key:
            logger.info("Registering Anthropic provider")
            anthropic = AnthropicProvider(anthropic_config)
            self.manager.register_provider(anthropic)
            
        # Register OpenAI provider if configured
        openai_config = self.config.get("openai", {})
        openai_api_key = openai_config.get("api_key", os.environ.get("OPENAI_API_KEY", ""))
        
        if openai_api_key:
            logger.info("Registering OpenAI provider")
            openai = OpenAIProvider(openai_config)
            self.manager.register_provider(openai)
            
        # Register Browserless provider if configured
        browserless_config = self.config.get("browserless", {})
        browserless_api_key = browserless_config.get("api_key", os.environ.get("BROWSERLESS_API_KEY", ""))
        
        if browserless_api_key:
            logger.info("Registering Browserless provider")
            browserless = BrowserlessProvider(browserless_config)
            self.manager.register_provider(browserless)
        
        # Register local Puppeteer provider as fallback
        puppeteer_config = self.config.get("puppeteer", {})
        if self.config.get("enable_local_puppeteer", True):
            logger.info("Registering local Puppeteer provider")
            puppeteer = PuppeteerLocalProvider(puppeteer_config)
            self.manager.register_provider(puppeteer)
            
        # Register Pinecone vector provider if configured
        pinecone_config = self.config.get("pinecone", {})
        pinecone_api_key = pinecone_config.get("api_key", os.environ.get("PINECONE_API_KEY", ""))
        pinecone_environment = pinecone_config.get("environment", os.environ.get("PINECONE_ENVIRONMENT", ""))
        
        if pinecone_api_key and pinecone_environment:
            logger.info("Registering Pinecone provider")
            pinecone = PineconeProvider(pinecone_config)
            self.manager.register_provider(pinecone)
            
        # Register ChromaDB vector provider if configured
        chroma_config = self.config.get("chroma", {})
        chroma_enabled = self.config.get("enable_chroma", True)
        
        if chroma_enabled:
            logger.info("Registering ChromaDB provider")
            chroma = ChromaProvider(chroma_config)
            self.manager.register_provider(chroma)
            
        # Set default providers based on config or availability
        default_text_provider = self.config.get("default_text_provider", "anthropic" if anthropic_api_key else "openai" if openai_api_key else None)
        if default_text_provider:
            try:
                self.manager.set_default_provider(CapabilityType.TEXT_GENERATION, default_text_provider)
                logger.info(f"Set {default_text_provider} as default for text generation")
            except ValueError as e:
                logger.warning(f"Could not set default text provider: {str(e)}")
                
        default_code_provider = self.config.get("default_code_provider", "openai" if openai_api_key else "anthropic" if anthropic_api_key else None)
        if default_code_provider:
            try:
                self.manager.set_default_provider(CapabilityType.CODE_GENERATION, default_code_provider)
                logger.info(f"Set {default_code_provider} as default for code generation")
            except ValueError as e:
                logger.warning(f"Could not set default code provider: {str(e)}")
                
        default_web_provider = self.config.get("default_web_provider", "browserless" if browserless_api_key else "puppeteer_local")
        if default_web_provider:
            try:
                self.manager.set_default_provider(CapabilityType.WEB_BROWSING, default_web_provider)
                logger.info(f"Set {default_web_provider} as default for web browsing")
            except ValueError as e:
                logger.warning(f"Could not set default web provider: {str(e)}")
                
        default_vector_provider = self.config.get("default_vector_provider", "pinecone" if pinecone_api_key and pinecone_environment else "chroma" if chroma_enabled else None)
        if default_vector_provider:
            try:
                self.manager.set_default_provider(CapabilityType.VECTOR_STORAGE, default_vector_provider)
                logger.info(f"Set {default_vector_provider} as default for vector storage")
            except ValueError as e:
                logger.warning(f"Could not set default vector provider: {str(e)}")
                
    async def generate_text(self,
                          prompt: str,
                          context: Optional[List[Dict[str, str]]] = None,
                          provider: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate text using the configured providers.
        
        Args:
            prompt: The text prompt
            context: Conversation context
            provider: Specific provider to use (optional)
            **kwargs: Additional parameters to pass to the provider
            
        Returns:
            Text generation result
        """
        if not self._initialized:
            await self.initialize()
            
        return await self.manager.execute(
            CapabilityType.TEXT_GENERATION,
            provider_name=provider,
            prompt=prompt,
            context=context,
            **kwargs
        )
        
    async def generate_code(self,
                          prompt: str,
                          language: str = "python",
                          provider: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate code using the configured providers.
        
        Args:
            prompt: The code generation prompt
            language: Programming language
            provider: Specific provider to use (optional)
            **kwargs: Additional parameters to pass to the provider
            
        Returns:
            Code generation result
        """
        if not self._initialized:
            await self.initialize()
            
        return await self.manager.execute(
            CapabilityType.CODE_GENERATION,
            provider_name=provider,
            prompt=prompt,
            language=language,
            **kwargs
        )
        
    async def browse_url(self,
                      url: str,
                      extract_text: bool = True,
                      take_screenshot: bool = False,
                      evaluate_script: Optional[str] = None,
                      provider: Optional[str] = None,
                      **kwargs) -> Dict[str, Any]:
        """Browse a URL using web browsing providers.
        
        Args:
            url: The URL to browse
            extract_text: Whether to extract text content
            take_screenshot: Whether to take a screenshot
            evaluate_script: JavaScript to execute in the page context
            provider: Specific provider to use (optional)
            **kwargs: Additional parameters to pass to the provider
            
        Returns:
            Web browsing result
        """
        if not self._initialized:
            await self.initialize()
            
        return await self.manager.execute(
            CapabilityType.WEB_BROWSING,
            provider_name=provider,
            url=url,
            extract_text=extract_text,
            take_screenshot=take_screenshot,
            evaluate_script=evaluate_script,
            **kwargs
        )
        
    async def vector_operation(self,
                             operation: str,
                             vectors: Optional[List[List[float]]] = None,
                             ids: Optional[List[str]] = None,
                             metadata: Optional[List[Dict[str, Any]]] = None,
                             query_vector: Optional[List[float]] = None,
                             provider: Optional[str] = None,
                             **kwargs) -> Dict[str, Any]:
        """Perform operations on vector databases.
        
        Args:
            operation: Operation type ("upsert", "query", "delete", "fetch" for Pinecone,
                      or "add", "query", "delete", "get" for ChromaDB)
            vectors: List of vectors to add/upsert
            ids: List of IDs for vectors
            metadata: List of metadata dictionaries for vectors
            query_vector: Vector to query
            provider: Specific provider to use (optional)
            **kwargs: Additional parameters to pass to the provider
                - top_k: Number of results to return (default: 10)
                - namespace: Pinecone namespace
                - filter: Pinecone query filter
                - collection_name: ChromaDB collection name
                - where: ChromaDB query filter
                - documents: ChromaDB documents to add
                
        Returns:
            Vector operation result
        """
        if not self._initialized:
            await self.initialize()
            
        return await self.manager.execute(
            CapabilityType.VECTOR_STORAGE,
            provider_name=provider,
            operation=operation,
            vectors=vectors,
            ids=ids,
            metadata=metadata,
            query_vector=query_vector,
            **kwargs
        )
        
    def get_available_providers(self, capability_type: CapabilityType) -> List[str]:
        """Get available providers for a capability.
        
        Args:
            capability_type: The capability type
            
        Returns:
            List of provider names
        """
        return self.manager.get_providers_for_capability(capability_type)
        
    def get_default_provider(self, capability_type: CapabilityType) -> Optional[str]:
        """Get the default provider for a capability.
        
        Args:
            capability_type: The capability type
            
        Returns:
            Provider name or None if not set
        """
        if capability_type in self.manager.default_providers:
            return self.manager.default_providers[capability_type]
        return None
        
    async def shutdown(self):
        """Shutdown the capability service."""
        if self._initialized:
            logger.info("Shutting down Capability Service")
            await self.manager.shutdown_all()
            self._initialized = False
