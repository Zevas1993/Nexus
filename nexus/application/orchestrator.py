"""
Request orchestration for Nexus AI Assistant.

This module provides central orchestration of services and plugins with improved intent classification,
context handling, and hybrid AI capabilities.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
import logging
import asyncio
import json
import time
import os
from ..infrastructure.context import ApplicationContext
from ..domain.language.language_model_service import LanguageModelService
from ..domain.rag import enhanced_rag
from ..infrastructure.security.auth import JwtAuthenticationService

logger = logging.getLogger(__name__)

class Orchestrator:
    """Central orchestrator for request processing with advanced features."""
    
    VERSION = "1.0.0"
    PLUGIN_DIR = "plugins"
    
    def __init__(self, app_context: ApplicationContext):
        """Initialize orchestrator.
        
        Args:
            app_context: Application context
        """
        self.app_context = app_context
        self.config = app_context.config
        self.services = {}
        self.plugin_loader = None
        self.language_model = None
        self.rag_service = None
        self.auth_service = None
        
    async def initialize(self):
        """Initialize orchestrator and load services."""
        logger.info("Initializing Orchestrator")
        
        # Get core services
        self.language_model = self.app_context.get_service(LanguageModelService)
        await self.language_model.initialize()
        
        # Load all other services
        # These will be properly initialized as we add them to the project
        try:
            from ..domain.plugins.loader import PluginLoaderService
            self.plugin_loader = self.app_context.get_service(PluginLoaderService)
            await self.plugin_loader.initialize()
        except Exception as e:
            logger.warning(f"Plugin system not available: {str(e)}")
            
        try:
            from ..domain.rag.enhanced_rag import EnhancedRAGService
            self.rag_service = self.app_context.get_service(EnhancedRAGService)
            await self.rag_service.initialize()
        except Exception as e:
            logger.warning(f"Enhanced RAG not available: {str(e)}")
            
        self.auth_service = self.app_context.get_service(JwtAuthenticationService)
        
        # Register services
        await self._register_services()
        
        logger.info("Orchestrator initialized")
        
    async def _register_services(self):
        """Register all available services."""
        # Base services - these will be properly initialized as we add them
        try:
            from ..domain.content_retrieval import ContentRetrievalService
            from ..domain.code import CodeService
            from ..domain.creative_generator import CreativeGeneratorService
            from ..domain.external_data import ExternalDataService
            from ..domain.general_query import GeneralQueryService
            from ..domain.image_description import ImageDescriptionService
            from ..domain.math_solver import MathSolverService
            from ..domain.prompt_optimization import PromptOptimizationService
            from ..domain.researcher import ResearcherService
            from ..domain.session import SessionService
            from ..domain.system import SystemManagementService
            from ..domain.voice import VoiceService
            from ..domain.calendar_event import CalendarEventService
            from ..domain.briefing_generator import BriefingGeneratorService
            
            # Initialize and register services
            service_classes = [
                ContentRetrievalService,
                CodeService,
                CreativeGeneratorService,
                ExternalDataService,
                GeneralQueryService,
                ImageDescriptionService,
                MathSolverService,
                PromptOptimizationService,
                ResearcherService,
                SessionService,
                SystemManagementService,
                VoiceService,
                CalendarEventService,
                BriefingGeneratorService
            ]
            
            for service_class in service_classes:
                try:
                    service = self.app_context.get_service(service_class)
                    if hasattr(service, 'initialize') and callable(service.initialize):
                        await service.initialize()
                    service_name = service_class.__name__
                    self.services[service_name.lower().replace('service', '')] = service
                    logger.info(f"Registered service: {service_name}")
                except Exception as e:
                    logger.warning(f"Failed to register service {service_class.__name__}: {str(e)}")
                    
        except Exception as e:
            # Log but continue if services aren't available
            logger.warning(f"Error registering services: {str(e)}")
        
        # Always add language model as a fallback
        self.services['language_model'] = self.language_model
        
        # Register any plugins
        if self.plugin_loader:
            plugin_info = await self.plugin_loader.list_plugins()
            if 'plugins' in plugin_info:
                for plugin in plugin_info['plugins']:
                    self.services[plugin['name'].lower()] = plugin
                    logger.info(f"Registered plugin: {plugin['name']}")
        
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
            # Session title handling
            if request.lower().startswith("set session title:"):
                new_title = request[len("set session title:"):].strip()
                session_title = new_title
                logger.info(f"Session title updated to: {new_title}")
                return {
                    "status": "success",
                    "message": f"Session title set to {new_title}",
                    "session_id": session_id
                }
                
            # Get context for the session
            context = await self._get_session_context(session_id, user_id)
            context.append({"user": request})
                
            # Check for session review request
            if "review sessions titled" in request.lower():
                title_to_review = request.lower().split("review sessions titled")[1].strip().strip("'\"")
                combined_context = await self._review_sessions_by_title(user_id, title_to_review)
                if not combined_context:
                    logger.warning(f"No sessions found with title: {title_to_review}")
                    return {
                        "status": "error", 
                        "message": f"No sessions found with title '{title_to_review}'",
                        "session_id": session_id
                    }
                return await self._synthesize_context(combined_context, request)
            
            # First attempt plugin-specific detection
            plugin_name = self._extract_plugin_name(request)
            if plugin_name and self.plugin_loader:
                logger.info(f"Detected plugin request for {plugin_name}")
                result = await self._process_plugin_request(request, plugin_name, params, context)
                await self._update_session_context(session_id, user_id, context, result)
                processing_time = time.time() - start_time
                logger.info(f"Request processed in {processing_time:.2f}s via plugin {plugin_name}")
                return {
                    "status": "success",
                    "results": {plugin_name: result},
                    "session_id": session_id,
                    "processing_time": processing_time
                }
                
            # If no plugin detected, classify the intent
            tasks = await self._classify_task(request, context, params)
            if not tasks:
                # Fallback to general query if classification fails
                tasks = [("language_model", {})]
                
            # Execute all identified tasks
            results = {}
            for task_type, task_params in tasks:
                service = self.services.get(task_type)
                if not service:
                    logger.warning(f"No service found for task type: {task_type}")
                    continue
                    
                logger.info(f"Executing task: {task_type}")
                full_params = {**task_params, **params, "context": context}
                result = await service.process(request, **full_params)
                results[task_type] = result
                
                # Add result to context
                context.append({
                    "assistant": result.get("text", str(result))
                })
                
            # Update session context
            await self._update_session_context(session_id, user_id, context)
            
            processing_time = time.time() - start_time
            logger.info(f"Request processed in {processing_time:.2f}s with {len(tasks)} tasks")
            
            return {
                "status": "success",
                "results": results,
                "session_id": session_id,
                "processing_time": processing_time
            }
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing request: {str(e)}",
                "session_id": session_id
            }
            
    async def _classify_task(self, request: str, context: List[Dict[str, str]], 
                             params: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
        """Classify the user request into specific tasks.
        
        Args:
            request: User request string
            context: Conversation context
            params: Additional parameters
            
        Returns:
            List of (task_type, params) tuples
        """
        # Convert context to string for the LLM
        context_text = "\n".join([
            f"User: {entry.get('user', '')}\nAssistant: {entry.get('assistant', '')}"
            for entry in context[-5:] if 'user' in entry  # Use last 5 turns at most
        ])
        
        # Generate the classification prompt
        service_names = list(self.services.keys())
        prompt = (
            f"Given this conversation:\n{context_text}\n\n"
            f"Extract intents from the latest request: '{request}' "
            f"with parameters: {json.dumps(params)}. Return a JSON list of {{'task': 'module_name', 'params': {{key: value}}}} "
            f"for valid modules: {', '.join(service_names)}. Ensure params are validated and relevant to the task."
        )
        
        # Get classification from language model
        result = await self.language_model.process(prompt, context=context)
        
        try:
            # Parse the classification result
            if "text" in result:
                # Extract JSON from text if needed
                text = result["text"]
                if "[" in text and "]" in text:
                    json_str = text[text.find("["):text.rfind("]")+1]
                else:
                    json_str = text
                    
                intents = json.loads(json_str)
                
                # Validate intents
                validated_tasks = []
                for intent in intents:
                    if "task" in intent and intent["task"] in self.services:
                        task_params = intent.get("params", {})
                        validated_tasks.append((intent["task"], task_params))
                        
                if validated_tasks:
                    return validated_tasks
                    
            # Fallback to general query if parsing fails
            return [("language_model", params)]
        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}")
            return [("language_model", params)]
            
    def _extract_plugin_name(self, request: str) -> Optional[str]:
        """Extract plugin name from request.
        
        Args:
            request: User request string
            
        Returns:
            Plugin name if detected, None otherwise
        """
        if not self.plugin_loader:
            return None
            
        # Get all plugins
        plugin_names = []
        for plugin_folder in os.listdir(self.PLUGIN_DIR):
            manifest_path = os.path.join(self.PLUGIN_DIR, plugin_folder, "manifest.json")
            if os.path.exists(manifest_path):
                try:
                    with open(manifest_path, "r") as f:
                        manifest = json.load(f)
                    plugin_names.append(manifest.get("name", "").lower())
                except:
                    pass
        
        # Check for plugin mention in request
        request_lower = request.lower()
        for plugin_name in plugin_names:
            patterns = [
                f"use {plugin_name}",
                f"using {plugin_name}",
                f"with {plugin_name}",
                f"{plugin_name} plugin"
            ]
            for pattern in patterns:
                if pattern in request_lower:
                    return plugin_name
                    
        return None
            
    async def _process_plugin_request(self, request: str, plugin_name: str, 
                                    params: Dict[str, Any], context: List[Dict[str, str]]) -> Dict[str, Any]:
        """Process plugin-specific request.
        
        Args:
            request: User request string
            plugin_name: Plugin name
            params: Additional parameters
            context: Conversation context
            
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
        return await self.plugin_loader.process(
            request,
            action='execute',
            plugin_name=plugin_name,
            plugin_inputs=plugin_inputs,
            context=context
        )
        
    async def _get_session_context(self, session_id: str, user_id: str) -> List[Dict[str, str]]:
        """Get context for the session.
        
        Args:
            session_id: Session ID
            user_id: User ID
            
        Returns:
            Session context
        """
        try:
            from ..infrastructure.performance.caching import RedisCacheService
            cache_service = self.app_context.get_service(RedisCacheService)
            context_key = f"session:{session_id}:{user_id}"
            context = cache_service.get(context_key)
            if not context:
                context = []
            return context
        except Exception as e:
            logger.warning(f"Could not retrieve session context: {str(e)}")
            return []
            
    async def _update_session_context(self, session_id: str, user_id: str, 
                                    context: List[Dict[str, str]], 
                                    result: Optional[Dict[str, Any]] = None) -> None:
        """Update context for the session.
        
        Args:
            session_id: Session ID
            user_id: User ID
            context: Session context
            result: Processing result to add to context
        """
        try:
            from ..infrastructure.performance.caching import RedisCacheService
            cache_service = self.app_context.get_service(RedisCacheService)
            context_key = f"session:{session_id}:{user_id}"
            
            if result:
                # Add result to context
                if "text" in result:
                    context.append({"assistant": result["text"]})
                else:
                    context.append({"assistant": str(result)})
                    
            cache_service.set(context_key, context, timeout=3600)
        except Exception as e:
            logger.warning(f"Could not update session context: {str(e)}")
            
    async def _review_sessions_by_title(self, user_id: str, title: str) -> List[Dict[str, str]]:
        """Review sessions with specified title.
        
        Args:
            user_id: User ID
            title: Session title
            
        Returns:
            Combined context from all sessions with given title
        """
        try:
            from ..infrastructure.performance.caching import RedisCacheService
            cache_service = self.app_context.get_service(RedisCacheService)
            
            combined_context = []
            keys = cache_service.keys(f"session:*:{title}:{user_id}")
            
            for key in keys:
                session_context = cache_service.get(key)
                if session_context:
                    combined_context.extend(session_context)
                    
            return combined_context
        except Exception as e:
            logger.warning(f"Could not review sessions: {str(e)}")
            return []
            
    async def _synthesize_context(self, combined_context: List[Dict[str, str]], 
                                request: str) -> Dict[str, Any]:
        """Synthesize context from related sessions.
        
        Args:
            combined_context: Combined context from related sessions
            request: User request string
            
        Returns:
            Synthesized response
        """
        # Format context for the model
        context_text = "\n".join([
            f"User: {entry.get('user', '')}\nAssistant: {entry.get('assistant', '')}"
            for entry in combined_context if 'user' in entry
        ])
        
        # Build synthesis prompt
        prompt = (
            f"Based on these previous interactions:\n{context_text}\n\n"
            f"Provide a coherent summary or combined response for the request: '{request}'"
        )
        
        # Generate synthesis
        result = await self.language_model.process(prompt, context=[])
        
        if "text" in result:
            return {
                "status": "success",
                "text": result["text"],
                "synthesis": True
            }
        else:
            return {
                "status": "error",
                "message": "Failed to synthesize context",
                "text": "No synthesis generated"
            }
