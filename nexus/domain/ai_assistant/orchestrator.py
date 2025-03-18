"""
Orchestrator for AI assistant plugins.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional

from .base_plugin import AIPlugin
from .plugin_registry import AIPluginRegistry

logger = logging.getLogger(__name__)

class AIAssistantOrchestrator:
    """Orchestrates multiple AI plugins with parallel execution."""
    
    def __init__(self, registry: AIPluginRegistry):
        """Initialize orchestrator with plugin registry.
        
        Args:
            registry: Plugin registry
        """
        self.registry = registry
        self.max_parallel_plugins = 3  # Configurable limit
        
    async def process_role_request(self, role: str, context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Process a request using all plugins registered for a role.
        
        Args:
            role: Role identifier
            context: Context for the request
            **kwargs: Additional parameters
            
        Returns:
            Processing result
        """
        plugins = self.registry.get_plugins_for_role(role)
        
        if not plugins:
            logger.warning(f"No plugins registered for role {role}")
            return {
                "status": "error",
                "message": f"No plugins registered for {role}"
            }
        
        # Limit concurrent plugins to prevent resource exhaustion
        active_plugins = plugins[:self.max_parallel_plugins]
        
        # Execute in parallel
        tasks = [plugin.process(f"request:{role}", context=context, **kwargs) 
                for plugin in active_plugins]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Compile results, filtering out exceptions
        valid_results = []
        for plugin, result in zip(active_plugins, results):
            if isinstance(result, Exception):
                logger.warning(f"Plugin {plugin.name} failed: {str(result)}")
            else:
                result["source"] = plugin.name
                valid_results.append(result)
                
        return {
            "status": "success" if valid_results else "error",
            "results": valid_results,
            "source_count": len(valid_results),
            "message": None if valid_results else "All plugins failed to process the request"
        }
        
    async def process_plugin_request(self, plugin_name: str, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request using a specific plugin.
        
        Args:
            plugin_name: Name of the plugin to use
            request: Request string
            **kwargs: Additional parameters
            
        Returns:
            Processing result
        """
        plugin = self.registry.get_plugin(plugin_name)
        
        if not plugin:
            logger.warning(f"Plugin {plugin_name} not found")
            return {
                "status": "error",
                "message": f"Plugin {plugin_name} not found"
            }
        
        try:
            result = await plugin.process(request, **kwargs)
            result["source"] = plugin_name
            return result
        except Exception as e:
            logger.error(f"Error processing request with plugin {plugin_name}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing request with plugin {plugin_name}: {str(e)}"
            }
            
    async def initialize_all_plugins(self) -> Dict[str, bool]:
        """Initialize all registered plugins.
        
        Returns:
            Dictionary of plugin names to initialization status
        """
        plugins = self.registry.get_all_plugins()
        results = {}
        
        for plugin in plugins:
            try:
                success = await plugin.initialize()
                results[plugin.name] = success
                if success:
                    logger.info(f"Plugin {plugin.name} initialized successfully")
                else:
                    logger.warning(f"Plugin {plugin.name} initialization failed")
            except Exception as e:
                logger.error(f"Error initializing plugin {plugin.name}: {str(e)}")
                results[plugin.name] = False
                
        return results
        
    async def shutdown_all_plugins(self) -> None:
        """Shutdown all registered plugins."""
        plugins = self.registry.get_all_plugins()
        
        for plugin in plugins:
            try:
                await plugin.shutdown()
                logger.info(f"Plugin {plugin.name} shut down")
            except Exception as e:
                logger.error(f"Error shutting down plugin {plugin.name}: {str(e)}")
