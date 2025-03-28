"""
Plugin request processor for Nexus AI Assistant.

Handles detection and processing of plugin-specific requests.
"""

import logging
from typing import Dict, Any, Optional, List

from ..core.config import plugin_config

logger = logging.getLogger(__name__)

class PluginProcessor:
    """Processor for plugin-specific requests."""
    
    def __init__(self, app_context):
        """Initialize plugin processor.
        
        Args:
            app_context: Application context
        """
        self.app_context = app_context
        self.plugin_loader = None
        
    async def initialize(self):
        """Initialize plugin processor."""
        logger.info("Initializing Plugin Processor")
        
        # Get plugin loader service
        try:
            from ..domain.plugins.loader import PluginLoaderService
            self.plugin_loader = self.app_context.get_service(PluginLoaderService)
            
            # Initialize plugin loader if not already initialized
            if self.plugin_loader and hasattr(self.plugin_loader, 'initialize'):
                await self.plugin_loader.initialize()
                
            logger.info("Plugin processor initialized successfully")
        except Exception as e:
            logger.warning(f"Plugin system not available: {str(e)}")
            logger.info("Plugin processor initialized without plugin system")
        
    def detect_plugin_request(self, request: str) -> bool:
        """Detect if request is for a plugin.
        
        Args:
            request: User request string
            
        Returns:
            True if request is for a plugin, False otherwise
        """
        if not self.plugin_loader:
            return False
            
        plugin_name = self._extract_plugin_name(request)
        return plugin_name is not None
        
    def _extract_plugin_name(self, request: str) -> Optional[str]:
        """Extract plugin name from request.
        
        Args:
            request: User request string
            
        Returns:
            Plugin name if detected, None otherwise
        """
        if not self.plugin_loader or not hasattr(self.plugin_loader, 'registry'):
            logger.debug("Plugin loader or registry not available for extraction.")
            return None

        try:
            plugin_info = self.plugin_loader.registry.get_all_plugin_info()
            request_lower = request.lower().strip()

            # Prioritize explicit activation phrases
            activation_phrases = ["use plugin ", "activate plugin ", "run plugin ", "using plugin "]
            for plugin in plugin_info:
                plugin_name = plugin.get("name", "")
                plugin_name_lower = plugin_name.lower()
                if not plugin_name_lower:
                    continue

                for phrase in activation_phrases:
                    if request_lower.startswith(phrase + plugin_name_lower):
                        logger.debug(f"Detected plugin '{plugin_name}' via activation phrase: '{phrase}'")
                        return plugin_name
                
                # Check for variations like "use the [plugin_name] plugin"
                if f"use the {plugin_name_lower} plugin" in request_lower or \
                   f"using the {plugin_name_lower} plugin" in request_lower:
                     logger.debug(f"Detected plugin '{plugin_name}' via specific phrase.")
                     return plugin_name

            # Less specific matching (potential for false positives, lower priority)
            # Consider adding keywords from manifest here in the future
            # for plugin in plugin_info:
            #     plugin_name = plugin.get("name", "")
            #     plugin_name_lower = plugin_name.lower()
            #     if plugin_name_lower in request_lower:
            #         # Add more context checks if using direct name matching to reduce false positives
            #         logger.debug(f"Potentially detected plugin '{plugin_name}' via name mention (lower confidence).")
            #         # return plugin_name # Be cautious enabling this

        except Exception as e:
            logger.warning(f"Error extracting plugin name: {str(e)}", exc_info=self.app_context.debug)

        return None
        
    async def process(self, request: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process plugin-specific request.
        
        Args:
            request: User request string
            params: Additional parameters
            
        Returns:
            Plugin processing result
        """
        if not self.plugin_loader:
            return {
                "status": "error",
                "message": "Plugin system not initialized"
            }
            
        # Extract plugin name
        plugin_name = self._extract_plugin_name(request)
        if not plugin_name:
            return {
                "status": "error",
                "message": "No plugin detected in request"
            }
            
        # Extract plugin inputs from request and params
        params = params or {}
        plugin_inputs = params.get('plugin_inputs', {})
        
        logger.info(f"Processing plugin request for {plugin_name}")
        
        try:
            # Execute plugin
            if hasattr(self.plugin_loader, 'process'):
                result = await self.plugin_loader.process(
                    request,
                    action='execute',
                    plugin_name=plugin_name,
                    plugin_inputs=plugin_inputs
                )
                
                return {
                    "status": "success",
                    "plugin": plugin_name,
                    "response": self._extract_response(result),
                    "result": result
                }
            else:
                # Try getting the plugin directly if process method not available
                plugin_instance = self.plugin_loader.registry.get_plugin_instance(plugin_name)
                if hasattr(plugin_instance, 'execute'):
                    result = await plugin_instance.execute(request, **plugin_inputs)
                    
                    return {
                        "status": "success",
                        "plugin": plugin_name,
                        "response": self._extract_response(result),
                        "result": result
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"Plugin {plugin_name} does not support execution"
                    }
        except Exception as e:
            logger.error(f"Error processing plugin request: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error processing plugin request: {str(e)}"
            }
            
    def _extract_response(self, result: Dict[str, Any]) -> str:
        """Extract a user-friendly response from plugin result.
        
        Args:
            result: Plugin execution result
            
        Returns:
            User-friendly response
        """
        # Try different keys for response
        if isinstance(result, dict):
            for key in ['response', 'text', 'message', 'result']:
                if key in result and isinstance(result[key], str):
                    return result[key]
                    
            # For nested results
            if 'result' in result and isinstance(result['result'], dict):
                for key in ['response', 'text', 'message']:
                    if key in result['result'] and isinstance(result['result'][key], str):
                        return result['result'][key]
        
        # If no suitable response is found, convert to string
        return str(result)
