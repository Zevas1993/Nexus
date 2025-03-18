"""
Base orchestrator for Nexus AI Assistant.

Coordinates request routing and delegates to specialized processors.
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, List

from ..core.config import app_config
from .plugin_processor import PluginProcessor
from .rag_processor import RagProcessor

logger = logging.getLogger(__name__)

class Orchestrator:
    """Central orchestrator for request processing."""
    
    VERSION = "1.1.0"
    
    def __init__(self, app_context):
        """Initialize orchestrator.
        
        Args:
            app_context: Application context
        """
        self.app_context = app_context
        self.debug_mode = app_config.DEBUG
        self.request_timeout = app_config.REQUEST_TIMEOUT
        
        # Specialized processors
        self.plugin_processor = None
        self.rag_processor = None
        
        # Auth service (optional)
        self.auth_service = None
        
    async def initialize(self):
        """Initialize orchestrator and processors."""
        logger.info("Initializing Orchestrator")
        
        # Initialize specialized processors
        self.plugin_processor = PluginProcessor(self.app_context)
        await self.plugin_processor.initialize()
        
        self.rag_processor = RagProcessor(self.app_context)
        await self.rag_processor.initialize()
        
        # Try to get auth service if available
        try:
            from ..infrastructure.security.auth import JwtAuthenticationService
            self.auth_service = self.app_context.get_service(JwtAuthenticationService)
            logger.info("Authentication service initialized")
        except Exception as e:
            logger.warning(f"Authentication service not available: {str(e)}")
        
        logger.info(f"Orchestrator v{self.VERSION} initialized (debug={self.debug_mode})")
        
    async def process_request(self, request: str, user_id: str, session_id: str, 
                             params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process user request by delegating to appropriate processor.
        
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
        
        # Use debug mode from app config to control logging level
        if self.debug_mode:
            logger.debug(f"Request params: {params}")
        logger.info(f"Processing request from user {user_id}: {request}")
        
        try:
            # Apply request timeout from config
            result = await asyncio.wait_for(
                self._process_with_appropriate_processor(request, user_id, session_id, params),
                timeout=self.request_timeout
            )
            
            processing_time = time.time() - start_time
            logger.info(f"Request processed in {processing_time:.2f}s")
            
            # Add processing time to result
            if isinstance(result, dict):
                result["processing_time"] = processing_time
                result["session_id"] = session_id
                
            return {
                "status": "success",
                "response": result.get("response", ""),
                **result
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Request timed out after {self.request_timeout}s")
            return {
                "status": "error",
                "message": f"Request timed out after {self.request_timeout}s",
                "session_id": session_id
            }
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error processing request: {str(e)}",
                "session_id": session_id
            }
            
    async def _process_with_appropriate_processor(self, request: str, user_id: str, 
                                                session_id: str, params: Dict[str, Any]):
        """Process with the appropriate processor based on request type.
        
        Args:
            request: User request string
            user_id: User ID
            session_id: Session ID
            params: Additional parameters
            
        Returns:
            Processing result from the appropriate processor
        """
        # Check for plugin request first
        if self.plugin_processor.detect_plugin_request(request):
            logger.debug(f"Delegating to plugin processor")
            return await self.plugin_processor.process(request, params)
        
        # If not a plugin request, use RAG processor
        logger.debug(f"Delegating to RAG processor")
        return await self.rag_processor.process(request, params)
