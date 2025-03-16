"""
Plugin loader for Nexus AI Assistant.

This module provides functionality for loading and hot-reloading plugins.
"""

from typing import Dict, Any, List, Optional, Union
import logging
import os
import importlib
import importlib.util
import sys
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from ..base import AsyncService
from .registry import PluginRegistry

logger = logging.getLogger(__name__)

class PluginFileHandler(FileSystemEventHandler):
    """File system event handler for plugin hot-reloading."""
    
    def __init__(self, loader):
        """Initialize plugin file handler.
        
        Args:
            loader: PluginLoaderService instance
        """
        self.loader = loader
        
    def on_modified(self, event):
        """Handle file modification event.
        
        Args:
            event: File system event
        """
        if event.is_directory:
            return
            
        if event.src_path.endswith('.py') or event.src_path.endswith('manifest.json'):
            # Extract plugin name from path
            path_parts = event.src_path.split(os.sep)
            if len(path_parts) >= 2 and path_parts[-2] in self.loader.plugins:
                plugin_name = path_parts[-2]
                logger.info(f"Plugin file modified: {event.src_path}, reloading {plugin_name}")
                self.loader.reload_plugin(plugin_name)

class PluginLoaderService(AsyncService):
    """Service for loading and managing plugins."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize plugin loader service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.registry = PluginRegistry(self.config)
        self.plugins = {}
        self.hot_reload = self.config.get('PLUGIN_HOT_RELOAD', False)
        self.observer = None
        
    async def initialize(self):
        """Initialize plugin loader."""
        # Discover plugins
        plugin_names = self.registry.discover_plugins()
        self.plugins = {name: {"loaded": False, "last_modified": time.time()} for name in plugin_names}
        
        # Start file watcher if hot reload is enabled
        if self.hot_reload:
            self._start_file_watcher()
            
        logger.info(f"Plugin loader initialized with {len(plugin_names)} plugins")
        return plugin_names
    
    def _start_file_watcher(self):
        """Start file watcher for hot reloading."""
        try:
            self.observer = Observer()
            handler = PluginFileHandler(self)
            plugin_dir = self.config.get('PLUGIN_DIR', 'plugins')
            
            if os.path.exists(plugin_dir):
                self.observer.schedule(handler, plugin_dir, recursive=True)
                self.observer.start()
                logger.info(f"Started plugin file watcher for hot reloading")
            else:
                logger.warning(f"Plugin directory not found: {plugin_dir}")
        except Exception as e:
            logger.error(f"Error starting plugin file watcher: {str(e)}")
    
    def reload_plugin(self, name: str):
        """Reload plugin.
        
        Args:
            name: Plugin name
            
        Returns:
            True if reloaded successfully, False otherwise
        """
        if name not in self.plugins:
            logger.warning(f"Plugin not found for reloading: {name}")
            return False
            
        try:
            # Remove plugin instance from registry
            if name in self.registry.plugin_instances:
                del self.registry.plugin_instances[name]
                
            # Reload plugin module
            plugin_info = self.registry.plugins.get(name)
            if plugin_info:
                module_path = plugin_info["module_path"]
                module_name = f"{module_path}.{name.lower()}"
                
                # Reload module if it's loaded
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                    
            # Update last modified time
            self.plugins[name]["last_modified"] = time.time()
            self.plugins[name]["loaded"] = False
            
            logger.info(f"Reloaded plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Error reloading plugin {name}: {str(e)}")
            return False
    
    async def _process_impl(self, request: str, **kwargs) -> Dict[str, Any]:
        """Implementation of request processing.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
                - action: Action to perform (list, load, execute)
                - plugin_name: Plugin name for load/execute actions
                - plugin_inputs: Plugin inputs for execute action
                
        Returns:
            Action result
        """
        action = kwargs.get('action', 'list')
        
        if action == 'list':
            return {
                "plugins": self.registry.get_all_plugin_info(),
                "count": len(self.plugins)
            }
        elif action == 'load':
            plugin_name = kwargs.get('plugin_name')
            if not plugin_name:
                return {
                    "status": "error",
                    "message": "Plugin name required for load action"
                }
                
            plugin = self.registry.load_plugin(plugin_name, self.app_context)
            if plugin:
                self.plugins[plugin_name]["loaded"] = True
                return {
                    "status": "success",
                    "message": f"Plugin {plugin_name} loaded successfully",
                    "plugin_info": self.registry.get_plugin_info(plugin_name)
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to load plugin {plugin_name}"
                }
        elif action == 'execute':
            plugin_name = kwargs.get('plugin_name')
            plugin_inputs = kwargs.get('plugin_inputs', {})
            
            if not plugin_name:
                return {
                    "status": "error",
                    "message": "Plugin name required for execute action"
                }
                
            result = self.registry.execute_plugin(
                plugin_name, 
                request, 
                plugin_inputs, 
                self.app_context
            )
            
            return result
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
