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
import importlib.util

logger = logging.getLogger(__name__)

class Orchestrator:
    """Central orchestrator for request processing with advanced features."""
    
    VERSION = "1.0.0"
    PLUGIN_DIR = "plugins"
    
    def __init__(self, app_context):
        """Initialize orchestrator.
        
        Args:
            app_context: Application context
        """
        self.app_context = app_context
        self.config = app_context.config if hasattr(app_context, 'config') else {}
        self.services = {}
        self.plugin_loader = None
        self.language_model = None
        self.rag_service = None
        self.auth_service = None
        self.agent_service = None
        self.capability_service = None
        
    async def initialize(self):
        """Initialize orchestrator and load services."""
        logger.info("Initializing Orchestrator")
        
        # Get core services
        try:
            from ..domain.language.language_model_service import LanguageModelService
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
                
            try:
                from ..infrastructure.security.auth import JwtAuthenticationService
                self.auth_service = self.app_context.get_service(JwtAuthenticationService)
            except Exception as e:
                logger.warning(f"Authentication service not available: {str(e)}")
                
            # Initialize Agent Service
            try:
                from ..domain.agents import AgentService
                self.agent_service = self.app_context.get_service(AgentService)
                if not self.agent_service:
                    self.agent_service = AgentService(self.config)
                    self.app_context.register_service(AgentService, self.agent_service)
                logger.info("Agent Service initialized")
            except Exception as e:
                logger.warning(f"Agent Service not available: {str(e)}")
                
            # Initialize Capability Service
            try:
                from ..domain.capability import CapabilityService
                self.capability_service = self.app_context.get_service(CapabilityService)
                if not self.capability_service:
                    self.capability_service = CapabilityService(self.config.get("capabilities", {}))
                    self.app_context.register_service(CapabilityService, self.capability_service)
                await self.capability_service.initialize()
                logger.info("Capability Service initialized")
            except Exception as e:
                logger.warning(f"Capability Service not available: {str(e)}")
            
            # Register services
            await self._register_services()
            
            # Initialize default agents if agent service is available
            if self.agent_service:
                await self._initialize_default_agents()
            
            logger.info("Orchestrator initialized")
        except Exception as e:
            logger.error(f"Error initializing orchestrator: {str(e)}")
            raise
        
    async def _register_services(self):
        """Register all available services."""
        # Base services - these will be properly initialized as we add them
        try:
            service_classes = []
            
            # Try to import and register core services
            try:
                from ..domain.content_retrieval import ContentRetrievalService
                service_classes.append(ContentRetrievalService)
            except ImportError:
                pass
                
            try:
                from ..domain.code import CodeService
                service_classes.append(CodeService)
            except ImportError:
                pass
                
            try:
                from ..domain.creative_generator import CreativeGeneratorService
                service_classes.append(CreativeGeneratorService)
            except ImportError:
                pass
                
            try:
                from ..domain.external_data import ExternalDataService
                service_classes.append(ExternalDataService)
            except ImportError:
                pass
                
            try:
                from ..domain.general_query import GeneralQueryService
                service_classes.append(GeneralQueryService)
            except ImportError:
                pass
                
            try:
                from ..domain.image_description import ImageDescriptionService
                service_classes.append(ImageDescriptionService)
            except ImportError:
                pass
                
            try:
                from ..domain.math_solver import MathSolverService
                service_classes.append(MathSolverService)
            except ImportError:
                pass
                
            try:
                from ..domain.prompt_optimization import PromptOptimizationService
                service_classes.append(PromptOptimizationService)
            except ImportError:
                pass
                
            try:
                from ..domain.researcher import ResearcherService
                service_classes.append(ResearcherService)
            except ImportError:
                pass
                
            try:
                from ..domain.session import SessionService
                service_classes.append(SessionService)
            except ImportError:
                pass
                
            try:
                from ..domain.system.system_service import SystemManagementService
                service_classes.append(SystemManagementService)
            except ImportError:
                pass
                
            try:
                from ..domain.voice import VoiceService
                service_classes.append(VoiceService)
            except ImportError:
                pass
                
            try:
                from ..domain.calendar_event import CalendarEventService
                service_classes.append(CalendarEventService)
            except ImportError:
                pass
                
            try:
                from ..domain.briefing_generator import BriefingGeneratorService
                service_classes.append(BriefingGeneratorService)
            except ImportError:
                pass
                
            # Initialize and register service classes
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
        if self.language_model:
            self.services['language_model'] = self.language_model
            
        # Register agent service
        if self.agent_service:
            self.services['agent'] = self.agent_service
            
        # Register capability service
        if self.capability_service:
            self.services['capability'] = self.capability_service
        
        # Register any plugins
        if self.plugin_loader:
            try:
                plugin_info = await self.plugin_loader.list_plugins()
                if 'plugins' in plugin_info:
                    for plugin in plugin_info['plugins']:
                        self.services[plugin['name'].lower()] = plugin
                        logger.info(f"Registered plugin: {plugin['name']}")
            except Exception as e:
                logger.warning(f"Error loading plugins: {str(e)}")
        else:
            # Load plugins directly if plugin loader not available
            self._load_plugins_directly()
    
    async def _initialize_default_agents(self):
        """Initialize default agents."""
        if not self.agent_service:
            return
            
        try:
            # Create a general conversational agent
            self.agent_service.create_agent(
                name="conversation_agent",
                model="gpt-4o",
                instructions="You are a helpful assistant that engages in natural conversations, answers questions, and provides assistance.",
                tools=["web_search", "file_search"],
                guardrails=["content_filter"]
            )
            
            # Create a research agent
            self.agent_service.create_agent(
                name="research_agent",
                model="gpt-4o",
                instructions="You are a research assistant that finds and summarizes information from various sources.",
                tools=["web_search", "file_search"],
                guardrails=["content_filter", "rate_limit"]
            )
            
            # Create a system agent
            self.agent_service.create_agent(
                name="system_agent",
                model="gpt-4o",
                instructions="You are a system assistant that can help with computer tasks and file management.",
                tools=["computer_use", "file_search"],
                guardrails=["content_filter"]
            )
            
            logger.info("Default agents initialized")
        except Exception as e:
            logger.warning(f"Error initializing default agents: {str(e)}")
    
    def _load_plugins_directly(self):
        """Load plugins directly from the plugins directory."""
        if not os.path.exists(self.PLUGIN_DIR):
            logger.info(f"Plugin directory not found: {self.PLUGIN_DIR}")
            return
            
        plugin_directories = [
            d for d in os.listdir(self.PLUGIN_DIR) 
            if os.path.isdir(os.path.join(self.PLUGIN_DIR, d))
        ]
        
        for plugin_dir in plugin_directories:
            manifest_path = os.path.join(self.PLUGIN_DIR, plugin_dir, "manifest.json")
            if not os.path.exists(manifest_path):
                continue
                
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                    
                plugin_name = manifest.get("name")
                plugin_class_name = manifest.get("class")
                
                if not plugin_name or not plugin_class_name:
                    continue
                    
                # Find main plugin file
                plugin_files = [
                    f for f in os.listdir(os.path.join(self.PLUGIN_DIR, plugin_dir))
                    if f.endswith(".py")
                ]
                
                if not plugin_files:
                    continue
                    
                # Assuming the plugin file has the same name as the plugin
                main_file = next(
                    (f for f in plugin_files if f.startswith(plugin_name.lower())), 
                    plugin_files[0]
                )
                
                plugin_file_path = os.path.join(self.PLUGIN_DIR, plugin_dir, main_file)
                
                # Load module
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{plugin_name}", plugin_file_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Get plugin class
                plugin_class = getattr(module, plugin_class_name)
                plugin_instance = plugin_class()
                
                # Register plugin
                self.services[plugin_name.lower()] = plugin_instance
                logger.info(f"Registered plugin from directory: {plugin_name}")
                
            except Exception as e:
                logger.error(f"Error loading plugin from {plugin_dir}: {str(e)}")
        
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
            # Detect if this is an agent-directed request
            if self._is_agent_request(request) and self.agent_service:
                logger.info("Using Agent SDK for request processing")
                return await self._process_agent_request(request, user_id, session_id, params)
            
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
            if plugin_name and plugin_name in self.services:
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
            
    def _is_agent_request(self, request: str) -> bool:
        """Determine if a request should be processed by the Agent SDK.
        
        Args:
            request: User request string
            
        Returns:
            True if request should use Agent SDK
        """
        if not self.agent_service:
            return False
            
        request_lower = request.lower()
        agent_indicators = [
            "search the web",
            "find information",
            "search for",
            "look up",
            "run command",
            "execute",
            "find files",
            "search files"
        ]
        
        # Check for explicit agent mentions
        if "agent" in request_lower:
            return True
            
        # Check for tool usage indicators
        for indicator in agent_indicators:
            if indicator in request_lower:
                return True
                
        return False
        
    async def _process_agent_request(self, request: str, user_id: str, 
                                   session_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process request using the Agent SDK.
        
        Args:
            request: User request string
            user_id: User ID
            session_id: Session ID
            params: Additional parameters
            
        Returns:
            Processing result
        """
        start_time = time.time()
        
        # Get context for the session
        context = await self._get_session_context(session_id, user_id)
        
        # Add user ID and session ID to context
        agent_context = {
            "user_id": user_id,
            "session_id": session_id,
            "conversation_history": context,
            **params
        }
        
        # Determine which agent to use
        request_lower = request.lower()
        agent_name = None
        
        if "web" in request_lower or "search" in request_lower or "find information" in request_lower:
            agent_name = "research_agent"
        elif "computer" in request_lower or "system" in request_lower or "command" in request_lower:
            agent_name = "system_agent"
        else:
            agent_name = "conversation_agent"
            
        # Process request with agent
        logger.info(f"Processing request with agent: {agent_name}")
        result = await self.agent_service.process(request, agent_name=agent_name, context=agent_context)
        
        # Update session context
        if "text" in result:
            context.append({"user": request})
            context.append({"assistant": result["text"]})
            await self._update_session_context(session_id, user_id, context)
            
        processing_time = time.time() - start_time
        logger.info(f"Request processed in {processing_time:.2f}s with agent {agent_name}")
        
        return {
            "status": "success",
            "result": result,
            "agent": result.get("agent", agent_name),
            "session_id": session_id,
            "processing_time": processing_time
        }
    
    async def _get_session_context(self, session_id: str, user_id: str) -> List[Dict[str, str]]:
        """Get context for a session.
        
        Args:
            session_id: Session ID
            user_id: User ID
            
        Returns:
            Conversation context
        """
        # This would typically use a caching service like Redis
        # For now, return an empty context
        return []
        
    async def _update_session_context(self, session_id: str, user_id: str, 
                                     context: List[Dict[str, str]], 
                                     result: Optional[Dict[str, Any]] = None) -> None:
        """Update context for a session.
        
        Args:
            session_id: Session ID
            user_id: User ID
            context: Updated context
            result: Processing result
        """
        # This would typically use a caching service like Redis
        pass
        
    async def _review_sessions_by_title(self, user_id: str, title: str) -> List[Dict[str, str]]:
        """Review sessions by title.
        
        Args:
            user_id: User ID
            title: Session title
            
        Returns:
            Combined context
        """
        # This would typically query a database or cache
        return []
        
    async def _synthesize_context(self, combined_context: List[Dict[str, str]], 
                                 request: str) -> Dict[str, Any]:
        """Synthesize context from multiple sessions.
        
        Args:
            combined_context: Combined context
            request: User request
            
        Returns:
            Synthesis result
        """
        # Try to use the capability service first if available
        if self.capability_service:
            try:
                context_str = "\n".join([
                    f"User: {entry.get('user', '')}\nAssistant: {entry.get('assistant', '')}"
                    for entry in combined_context[-10:]  # Limit to the last 10 turns
                ])
                
                prompt = (
                    f"Based on these previous interactions:\n{context_str}\n"
                    f"Provide a coherent summary or combined response for the request: '{request}'"
                )
                
                result = await self.capability_service.generate_text(
                    prompt=prompt,
                    temperature=0.5
                )
                
                return {
                    "status": "success",
                    "text": result.get("text", "No synthesis generated"),
                    "from_sessions": True,
                    "provider": result.get("provider", "capability")
                }
            except Exception as e:
                logger.warning(f"Error using capability service for synthesis: {str(e)}")
                # Fall back to language model if capability service fails
        
        # Fall back to language model if capability service not available or failed
        if not self.language_model:
            return {"status": "error", "message": "No language processing available"}
            
        context_str = "\n".join([
            f"User: {entry.get('user', '')}\nAssistant: {entry.get('assistant', '')}"
            for entry in combined_context[-10:]  # Limit to the last 10 turns
        ])
        
        prompt = (
            f"Based on these previous interactions:\n{context_str}\n"
            f"Provide a coherent summary or combined response for the request: '{request}'"
        )
        
        response = await self.language_model.process(prompt, [])
        
        return {
            "status": "success",
            "text": response.get("text", "No synthesis generated"),
            "from_sessions": True
        }
        
    def _extract_plugin_name(self, request: str) -> Optional[str]:
        """Extract plugin name from request.
        
        Args:
            request: User request
            
        Returns:
            Plugin name if detected, None otherwise
        """
        # Simple extraction - could be improved with ML-based classification
        request_lower = request.lower()
        
        # Get list of all plugin names
        plugin_names = [
            name for name in self.services.keys()
            if name != "language_model" and not name.endswith("service")
        ]
        
        # Check if any plugin name is mentioned
        for plugin_name in plugin_names:
            if plugin_name in request_lower:
                return plugin_name
                
        # Check for common prefixes
        prefixes = [
            "use the ",
            "with the ",
            "using the ",
            "through the ",
            "via the "
        ]
        
        for prefix in prefixes:
            for plugin_name in plugin_names:
                if f"{prefix}{plugin_name}" in request_lower:
                    return plugin_name
                    
        return None
        
    async def _process_plugin_request(self, request: str, plugin_name: str, 
                                     params: Dict[str, Any], 
                                     context: List[Dict[str, str]]) -> Dict[str, Any]:
        """Process request using a plugin.
        
        Args:
            request: User request
            plugin_name: Plugin name
            params: Additional parameters
            context: Conversation context
            
        Returns:
            Plugin processing result
        """
        plugin = self.services.get(plugin_name)
        if not plugin:
            return {
                "status": "error",
                "message": f"Plugin {plugin_name} not found"
            }
            
        # Extract plugin-specific inputs if available
        plugin_inputs = {}
        
        try:
            # Process the request
            full_params = {**params, "plugin_inputs": plugin_inputs, "context": context}
            result = await plugin.process(request, **full_params)
            return result
        except Exception as e:
            logger.error(f"Error processing request with plugin {plugin_name}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing request with plugin {plugin_name}: {str(e)}"
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
        # Try to use the capability service for classification if available
        if self.capability_service:
            try:
                # Build context string
                context_text = "\n".join([
                    f"User: {entry.get('user', '')}\nAssistant: {entry.get('assistant', '')}"
                    for entry in context[-5:] if 'user' in entry  # Use last 5 turns at most
                ])
                
                # Service names for classification
                service_names = list(self.services.keys())
                
                # Prepare and send classification prompt
                classification_prompt = (
                    f"Given this conversation:\n{context_text}\n\n"
                    f"Extract intents from the latest request: '{request}' "
                    f"with parameters: {json.dumps(params)}. Return a JSON list of {{'task': 'module_name', 'params': {{key: value}}}} "
                    f"for valid modules: {', '.join(service_names)}. Ensure params are validated and relevant to the task."
                )
                
                # Use capability service to classify
                classification_result = await self.capability_service.generate_text(
                    prompt=classification_prompt,
                    temperature=0.2  # Low temperature for more deterministic results
                )
                
                if "text" in classification_result:
                    # Extract JSON from text if needed
                    text = classification_result["text"]
                    if "[" in text and "]" in text:
                        json_str = text[text.find("["):text.rfind("]")+1]
                    else:
                        json_str = text
                        
                    try:
                        intents = json.loads(json_str)
                        
                        # Validate intents
                        validated_tasks = []
                        for intent in intents:
                            if "task" in intent and intent["task"] in self.services:
                                task_params = intent.get("params", {})
                                validated_tasks.append((intent["task"], task_params))
                                
                        if validated_tasks:
                            return validated_tasks
                    except json.JSONDecodeError:
                        logger.warning(f"Error parsing classification result: {text}")
            except Exception as e:
                logger.warning(f"Error using capability service for classification: {str(e)}")
                # Fall back to language model if capability service fails
        
        # Fall back to language model if capability service not available or failed
        if self.language_model:
            # Use language model for classification
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
            result = await self.language_model.process(prompt, context=[])
            
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
                        
                # Fallback to simple rule-based classification
                return self._simple_classify(request)
            except Exception as e:
                logger.error(f"Intent classification failed: {str(e)}")
                return self._simple_classify(request)
        else:
            # If no language model available, use simple rule-based classification
            # This is a simplified implementation
            request_lower = request.lower()
            
            if "weather" in request_lower:
                return [("weather", {})]
            elif any(word in request_lower for word in ["code", "programming", "function"]):
                return [("code", {})]
            elif any(word in request_lower for word in ["image", "picture", "photo"]):
                return [("image_description", {})]
            else:
                return [("language_model", {})]
        
        # Use language model for classification
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
        result = await self.language_model.process(prompt, context=[])
        
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
                    
            # Fallback to simple rule-based classification
            return self._simple_classify(request)
        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}")
            return self._simple_classify(request)
            
    def _simple_classify(self, request: str) -> List[Tuple[str, Dict[str, Any]]]:
        """Simple rule-based classification.
        
        Args:
            request: User request
            
        Returns:
            List of (task_type, params) tuples
        """
        # This is a simplified implementation
        request_lower = request.lower()
        
        if "weather" in request_lower and "weather" in self.services:
            return [("weather", {})]
        elif any(word in request_lower for word in ["code", "programming", "function"]) and "code" in self.services:
            return [("code", {})]
        elif any(word in request_lower for word in ["image", "picture", "photo"]) and "image_description" in self.services:
            return [("image_description", {})]
        elif "language_model" in self.services:
            return [("language_model", {})]
        else:
            # Return first available service as fallback
            for service_name in self.services:
                if service_name != "plugin_loader":
                    return [(service_name, {})]
            
            # If no services available, return empty list
            return []
