"""
Service for managing AI assistant capabilities.
"""
import logging
import os
import asyncio
from typing import Dict, Any, List, Optional, Union

from .base_plugin import AIPlugin
from .plugin_registry import AIPluginRegistry
from .orchestrator import AIAssistantOrchestrator
from .aggregator import SuggestionAggregator, AnalysisAggregator
from .resource_manager import AIResourceManager

logger = logging.getLogger(__name__)

class AIAssistantService:
    """Service for managing AI coding assistants."""
    
    def __init__(self, app_context: Any):
        """Initialize AI assistant service.
        
        Args:
            app_context: Application context
        """
        self.app_context = app_context
        self.config = app_context.config if hasattr(app_context, 'config') else {}
        
        # Create core components
        self.registry = AIPluginRegistry()
        self.orchestrator = AIAssistantOrchestrator(self.registry)
        self.suggestion_aggregator = SuggestionAggregator()
        self.analysis_aggregator = AnalysisAggregator()
        self.resource_manager = AIResourceManager(self.config.get("ai_assistant", {}))
        
        self._initialized = False
        
    async def initialize(self) -> None:
        """Initialize service and load plugins."""
        if self._initialized:
            return
            
        logger.info("Initializing AI Assistant Service")
        
        try:
            # Load AI assistant plugins
            await self._load_plugins()
            
            # Initialize all plugins
            init_results = await self.orchestrator.initialize_all_plugins()
            logger.info(f"Initialized {sum(1 for v in init_results.values() if v)} plugins")
            
            self._initialized = True
            logger.info("AI Assistant Service initialized")
        except Exception as e:
            logger.error(f"Error initializing AI Assistant Service: {str(e)}")
            raise
            
    async def _load_plugins(self) -> None:
        """Load AI assistant plugins."""
        try:
            # Get plugin loader service from app context
            plugin_loader = None
            if hasattr(self.app_context, 'get_service'):
                try:
                    # Try to get the plugin loader from the app context
                    from ..plugins.loader import PluginLoaderService
                    plugin_loader = self.app_context.get_service(PluginLoaderService)
                except Exception as e:
                    logger.warning(f"Plugin loader service not available: {str(e)}")
            
            if plugin_loader:
                # Load plugins through the plugin loader
                ai_completion_plugins = await plugin_loader.load_plugins_by_category("ai_completion")
                for plugin in ai_completion_plugins:
                    # Register resource requirements
                    requirements = plugin.get_resource_requirements()
                    self.resource_manager.register_plugin_requirements(plugin.name, requirements)
                    
                    # Register plugin roles
                    roles = plugin.get_supported_roles()
                    priority = plugin.get_priority()
                    self.registry.register_plugin(plugin, roles, priority)
                    
                ai_analysis_plugins = await plugin_loader.load_plugins_by_category("ai_analysis")
                for plugin in ai_analysis_plugins:
                    requirements = plugin.get_resource_requirements()
                    self.resource_manager.register_plugin_requirements(plugin.name, requirements)
                    
                    roles = plugin.get_supported_roles()
                    priority = plugin.get_priority()
                    self.registry.register_plugin(plugin, roles, priority)
            else:
                # Load plugins manually
                await self._load_plugins_manually()
                
        except Exception as e:
            logger.error(f"Error loading AI assistant plugins: {str(e)}")
            raise
            
    async def _load_plugins_manually(self) -> None:
        """Load plugins manually if plugin loader is not available."""
        # We'll implement this in a future update
        logger.info("Loading AI assistant plugins manually")
        
        # TODO: Implement manual plugin loading
        # This would scan the plugins directory and load any AI assistant plugins
        
    async def get_code_suggestions(self, code_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get code suggestions from all relevant plugins.
        
        Args:
            code_context: Context for the code (code, filename, position, etc.)
            
        Returns:
            Suggestions from plugins
        """
        if not self._initialized:
            await self.initialize()
            
        # Get suggestions from all completion plugins
        results = await self.orchestrator.process_role_request(
            "COMPLETION", code_context
        )
        
        if results["status"] != "success":
            return results
            
        # Aggregate and deduplicate suggestions
        aggregated = self.suggestion_aggregator.aggregate_suggestions(results["results"])
        
        return {
            "status": "success",
            "suggestions": aggregated,
            "source_count": results["source_count"]
        }
        
    async def analyze_code(self, code: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Analyze code with all analysis plugins.
        
        Args:
            code: Code to analyze
            filename: Filename (optional)
            
        Returns:
            Analysis results
        """
        if not self._initialized:
            await self.initialize()
            
        code_context = {"code": code}
        if filename:
            code_context["filename"] = filename
        
        # Get analysis from all analysis plugins
        results = await self.orchestrator.process_role_request(
            "ANALYSIS", code_context
        )
        
        if results["status"] != "success":
            return results
            
        # Merge analysis results
        grouped_issues = self.analysis_aggregator.aggregate_issues(results["results"])
        
        return {
            "status": "success",
            "issues": grouped_issues,
            "source_count": results["source_count"]
        }
        
    async def get_system_resources(self) -> Dict[str, Any]:
        """Get system resource information.
        
        Returns:
            System resource information
        """
        return self.resource_manager.get_system_metrics()
        
    async def shutdown(self) -> None:
        """Shutdown the service."""
        if not self._initialized:
            return
            
        logger.info("Shutting down AI Assistant Service")
        await self.orchestrator.shutdown_all_plugins()
        self._initialized = False
        logger.info("AI Assistant Service shutdown complete")
