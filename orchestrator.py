"""
Request orchestration for Nexus AI Assistant.

This module provides central orchestration of services and plugins.
"""

from typing import Dict, Any, List, Optional, Union
import logging
import asyncio
import json
import time
from ..infrastructure.context import ApplicationContext
from ..domain.rag.generation import GenerationService
from ..domain.plugins.loader import PluginLoaderService

logger = logging.getLogger(__name__)

class Orchestrator:
    """Central orchestrator for request processing."""
    
    VERSION = "1.0.0"
    
    def __init__(self, app_context: ApplicationContext):
        """Initialize orchestrator.
        
        Args:
            app_context: Application context
        """
        self.app_context = app_context
        self.config = app_context.config
        self.services = {}
        self.plugin_loader = None
        self.generation_service = None
        
    async def initialize(self):
        """Initialize orchestrator and load services."""
        # Initialize plugin loader
        self.plugin_loader = self.app_context.get_service(PluginLoaderService)
        await self.plugin_loader.initialize()
        
        # Initialize generation service
        self.generation_service = self.app_context.get_service(GenerationService)
        
        logger.info("Orchestrator initialized")
        
    async def process_request(self, request: str, user_id: str, session_id: str, 
                             params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user request.
        
        Args:
            request: User request string
            user_id: User ID
            session_id: Session ID
            params: Additional parameters
            
        Returns:
            Processing result
        """
        start_time = time.time()
        params = params or {}
        
        logger.info(f"Processing request from user {user_id}: {request}")
        
        try:
            # Check for plugin-specific request
            plugin_name = self._extract_plugin_name(request)
            if plugin_name:
                logger.info(f"Detected plugin request for {plugin_name}")
                return await self._process_plugin_request(request, plugin_name, params)
            
            # Process as RAG request
            collection = params.get('collection', 'default')
            response = await self.generation_service.process(
                request,
                collection=collection,
                top_k=params.get('top_k', 5)
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Request processed in {processing_time:.2f}s")
            
            return {
                "status": "success",
                "response": response.get("result", {}).get("response", ""),
                "processing_time": processing_time
            }
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing request: {str(e)}"
            }
    
    def _extract_plugin_name(self, request: str) -> Optional[str]:
        """Extract plugin name from request.
        
        Args:
            request: User request string
            
        Returns:
            Plugin name if detected, None otherwise
        """
        # Simple plugin detection based on keywords
        # In a real implementation, this would be more sophisticated
        if not self.plugin_loader:
            return None
            
        plugin_info = self.plugin_loader.registry.get_all_plugin_info()
        for plugin in plugin_info:
            plugin_name = plugin.get("name", "").lower()
            if f"use {plugin_name}" in request.lower() or f"using {plugin_name}" in request.lower():
                return plugin.get("name")
                
        return None
    
    async def _process_plugin_request(self, request: str, plugin_name: str, 
                                    params: Dict[str, Any]) -> Dict[str, Any]:
        """Process plugin-specific request.
        
        Args:
            request: User request string
            plugin_name: Plugin name
            params: Additional parameters
            
        Returns:
            Plugin processing result
        """
        if not self.plugin_loader:
            return {
                "status": "error",
                "message": "Plugin system not initialized"
            }
            
        # Extract plugin inputs from request and params
        plugin_inputs = params.get('plugin_inputs', {})
        
        # Execute plugin
        result = await self.plugin_loader.process(
            request,
            action='execute',
            plugin_name=plugin_name,
            plugin_inputs=plugin_inputs
        )
        
        return result
