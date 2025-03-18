"""
RAG request processor for Nexus AI Assistant.

Handles processing of RAG requests using generation service.
"""

import logging
from typing import Dict, Any, Optional, List

from ..core.config import model_config

logger = logging.getLogger(__name__)

class RagProcessor:
    """Processor for RAG requests."""
    
    def __init__(self, app_context):
        """Initialize RAG processor.
        
        Args:
            app_context: Application context
        """
        self.app_context = app_context
        self.context_window = model_config.CONTEXT_WINDOW
        self.model_preference = model_config.get_model_preference_order()
        self.generation_service = None
        self.language_model = None
        
    async def initialize(self):
        """Initialize RAG processor."""
        logger.info("Initializing RAG Processor")
        
        # Try to get generation service
        try:
            from ..domain.rag.enhanced_rag import EnhancedRAGService
            self.generation_service = self.app_context.get_service(EnhancedRAGService)
            
            # Initialize generation service if not already initialized
            if self.generation_service and hasattr(self.generation_service, 'initialize'):
                await self.generation_service.initialize()
                
            logger.info("RAG processor initialized with EnhancedRAGService")
        except Exception as e:
            logger.warning(f"Enhanced RAG service not available: {str(e)}")
            
            # Fall back to language model service
            try:
                from ..domain.language.language_model_service import LanguageModelService
                self.language_model = self.app_context.get_service(LanguageModelService)
                
                # Initialize language model if not already initialized
                if self.language_model and hasattr(self.language_model, 'initialize'):
                    await self.language_model.initialize()
                    
                logger.info("RAG processor initialized with LanguageModelService")
            except Exception as e:
                logger.warning(f"Language model service not available: {str(e)}")
                logger.info("RAG processor initialized without available services")
        
    async def process(self, request: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process RAG request.
        
        Args:
            request: User request string
            params: Additional parameters
            
        Returns:
            RAG processing result
        """
        params = params or {}
        
        # If no services available, return error
        if not self.generation_service and not self.language_model:
            return {
                "status": "error",
                "message": "No RAG or language model services available"
            }
            
        # Use generation service if available
        if self.generation_service:
            return await self._process_with_rag_service(request, params)
        
        # Fall back to language model
        return await self._process_with_language_model(request, params)
        
    async def _process_with_rag_service(self, request: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process request using RAG service.
        
        Args:
            request: User request string
            params: Additional parameters
            
        Returns:
            RAG processing result
        """
        # Get parameters from request
        collection = params.get('collection', 'default')
        top_k = params.get('top_k', 5)
        
        # Add preferred model from config if not specified in params
        if 'model' not in params and self.model_preference:
            params['model'] = self.model_preference[0]
        
        logger.info(f"Processing RAG request with model={params.get('model')}, collection={collection}")
        
        try:
            # Process request with parameters enhanced by configuration
            response = await self.generation_service.process(
                request,
                collection=collection,
                top_k=top_k,
                model=params.get('model'),
                context_window=self.context_window
            )
            
            # Extract response for return
            if isinstance(response, dict) and 'result' in response:
                result = response['result']
                if isinstance(result, dict):
                    return {
                        "status": "success",
                        "response": result.get("response", ""),
                        "source_documents": result.get("source_documents", []),
                        "model": response.get("model", "unknown")
                    }
            
            # If response structure doesn't match expected format
            return {
                "status": "success",
                "response": str(response),
                "model": "rag"
            }
        except Exception as e:
            logger.error(f"Error processing with RAG service: {str(e)}", exc_info=True)
            # Fall back to language model if available
            if self.language_model:
                logger.info("Falling back to language model service")
                return await self._process_with_language_model(request, params)
            
            return {
                "status": "error",
                "message": f"Error processing with RAG service: {str(e)}"
            }
    
    async def _process_with_language_model(self, request: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process request using language model.
        
        Args:
            request: User request string
            params: Additional parameters
            
        Returns:
            Language model processing result
        """
        if not self.language_model:
            return {
                "status": "error",
                "message": "Language model service not available"
            }
        
        # Extract context if provided
        context = params.get('context', [])
        
        logger.info(f"Processing request with language model, context size: {len(context)}")
        
        try:
            # Process with language model
            response = await self.language_model.process(request, context=context)
            
            # Extract response text
            if isinstance(response, dict):
                return {
                    "status": "success",
                    "response": response.get("text", ""),
                    "model": response.get("model", "language_model")
                }
            
            # If response is not a dictionary
            return {
                "status": "success",
                "response": str(response),
                "model": "language_model"
            }
        except Exception as e:
            logger.error(f"Error processing with language model: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error processing with language model: {str(e)}"
            }
