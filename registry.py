"""
Plugin registry for Nexus AI Assistant.

This module provides functionality for registering and managing plugins.
"""

from typing import Dict, Any, List, Optional, Union, Type
import logging
import os
import importlib
from ..base import BaseService
from .manifest import PluginManifest

logger = logging.getLogger(__name__)

class PluginRegistry:
    """Registry for plugins."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize plugin registry.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.plugin_dir = config.get('PLUGIN_DIR', 'plugins')
        self.plugins: Dict[str, Dict[str, Any]] = {}
        self.plugin_instances: Dict[str, BaseService] = {}
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugins.
        
        Returns:
            List of discovered plugin names
        """
        discovered = []
        
        if not os.path.exists(self.plugin_dir):
            logger.warning(f"Plugin directory not found: {self.plugin_dir}")
            return discovered
        
        for plugin_folder in os.listdir(self.plugin_dir):
            plugin_path = os.path.join(self.plugin_dir, plugin_folder)
            
            if not os.path.isdir(plugin_path):
                continue
                
            manifest_path = os.path.join(plugin_path, "manifest.json")
            if not os.path.exists(manifest_path):
                logger.warning(f"No manifest.json found in plugin folder: {plugin_folder}")
                continue
                
            try:
                manifest = PluginManifest.from_file(manifest_path)
                self.plugins[manifest.name] = {
                    "manifest": manifest,
                    "path": plugin_path,
                    "module_path": f"{self.plugin_dir}.{plugin_folder}"
                }
                discovered.append(manifest.name)
                logger.info(f"Discovered plugin: {manifest.name} v{manifest.version}")
            except Exception as e:
                logger.error(f"Error loading plugin {plugin_folder}: {str(e)}")
        
        return discovered
    
    def get_plugin_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get plugin information.
        
        Args:
            name: Plugin name
            
        Returns:
            Plugin information dictionary or None if not found
        """
        if name not in self.plugins:
            return None
            
        plugin_info = self.plugins[name]
        manifest = plugin_info["manifest"]
        
        return {
            "name": manifest.name,
            "version": manifest.version,
            "description": manifest.description,
            "default_prompt": manifest.default_prompt,
            "inputs": manifest.inputs
        }
    
    def get_all_plugin_info(self) -> List[Dict[str, Any]]:
        """Get information for all plugins.
        
        Returns:
            List of plugin information dictionaries
        """
        return [self.get_plugin_info(name) for name in self.plugins]
    
    def load_plugin(self, name: str, app_context=None) -> Optional[BaseService]:
        """Load plugin instance.
        
        Args:
            name: Plugin name
            app_context: Application context
            
        Returns:
            Plugin instance or None if loading failed
        """
        if name not in self.plugins:
            logger.warning(f"Plugin not found: {name}")
            return None
            
        if name in self.plugin_instances:
            return self.plugin_instances[name]
            
        plugin_info = self.plugins[name]
        manifest = plugin_info["manifest"]
        module_path = plugin_info["module_path"]
        
        try:
            # Import plugin module
            module_name = f"{module_path}.{manifest.name.lower()}"
            module = importlib.import_module(module_name)
            
            # Get plugin class
            plugin_class = getattr(module, manifest.class_name)
            
            # Create plugin instance
            if app_context:
                plugin_instance = plugin_class(app_context=app_context)
            else:
                plugin_instance = plugin_class()
                
            self.plugin_instances[name] = plugin_instance
            logger.info(f"Loaded plugin: {name}")
            
            return plugin_instance
        except Exception as e:
            logger.error(f"Error loading plugin {name}: {str(e)}")
            return None
    
    def execute_plugin(self, name: str, request: str, inputs: Dict[str, Any] = None, 
                      app_context=None) -> Dict[str, Any]:
        """Execute plugin.
        
        Args:
            name: Plugin name
            request: Request string
            inputs: Plugin inputs
            app_context: Application context
            
        Returns:
            Plugin execution result
        """
        if name not in self.plugins:
            return {
                "status": "error",
                "message": f"Plugin not found: {name}"
            }
            
        # Load plugin if not already loaded
        plugin = self.load_plugin(name, app_context)
        if not plugin:
            return {
                "status": "error",
                "message": f"Failed to load plugin: {name}"
            }
            
        # Validate inputs
        manifest = self.plugins[name]["manifest"]
        try:
            validated_inputs = manifest.validate_input(inputs or {})
        except ValueError as e:
            return {
                "status": "error",
                "message": f"Invalid plugin inputs: {str(e)}"
            }
            
        # Execute plugin
        try:
            result = plugin.process(request, **validated_inputs)
            return result
        except Exception as e:
            logger.error(f"Error executing plugin {name}: {str(e)}")
            return {
                "status": "error",
                "message": f"Error executing plugin: {str(e)}"
            }
