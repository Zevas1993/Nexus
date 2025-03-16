"""
Improved plugin system for Nexus AI Assistant.

This module provides an enhanced plugin system with dynamic loading,
dependency management, and plugin communication capabilities.
"""

from typing import Dict, Any, List, Optional, Union, Set, Callable
import logging
import os
import importlib
import importlib.util
import sys
import time
import threading
import json
import inspect
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from ..domain.plugins.manifest import PluginManifest
from ..domain.plugins.registry import PluginRegistry
from ..domain.base import AsyncService, BaseService

logger = logging.getLogger(__name__)

class PluginDependencyManager:
    """Manager for plugin dependencies."""
    
    def __init__(self):
        """Initialize plugin dependency manager."""
        self.dependency_graph = {}
        self.resolved_order = []
    
    def add_plugin(self, plugin_name: str, dependencies: List[str]):
        """Add plugin to dependency graph.
        
        Args:
            plugin_name: Plugin name
            dependencies: List of plugin dependencies
        """
        self.dependency_graph[plugin_name] = dependencies
    
    def resolve_dependencies(self) -> List[str]:
        """Resolve plugin dependencies.
        
        Returns:
            List of plugin names in dependency order
            
        Raises:
            ValueError: If circular dependency detected
        """
        self.resolved_order = []
        visited = set()
        temp_visited = set()
        
        def visit(plugin: str):
            """Visit plugin in dependency graph.
            
            Args:
                plugin: Plugin name
                
            Raises:
                ValueError: If circular dependency detected
            """
            if plugin in temp_visited:
                raise ValueError(f"Circular dependency detected involving {plugin}")
            
            if plugin not in visited and plugin in self.dependency_graph:
                temp_visited.add(plugin)
                
                for dependency in self.dependency_graph[plugin]:
                    visit(dependency)
                
                temp_visited.remove(plugin)
                visited.add(plugin)
                self.resolved_order.append(plugin)
        
        for plugin in self.dependency_graph:
            if plugin not in visited:
                visit(plugin)
        
        return self.resolved_order

class PluginEventEmitter:
    """Event emitter for plugin communication."""
    
    def __init__(self):
        """Initialize plugin event emitter."""
        self.listeners = {}
    
    def on(self, event: str, callback: Callable):
        """Register event listener.
        
        Args:
            event: Event name
            callback: Callback function
        """
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)
    
    def off(self, event: str, callback: Callable):
        """Remove event listener.
        
        Args:
            event: Event name
            callback: Callback function
        """
        if event in self.listeners and callback in self.listeners[event]:
            self.listeners[event].remove(callback)
    
    def emit(self, event: str, *args, **kwargs):
        """Emit event.
        
        Args:
            event: Event name
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        if event in self.listeners:
            for callback in self.listeners[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error in event listener for {event}: {str(e)}")

class PluginFileHandler(FileSystemEventHandler):
    """File system event handler for plugin hot-reloading."""
    
    def __init__(self, loader):
        """Initialize plugin file handler.
        
        Args:
            loader: ImprovedPluginLoaderService instance
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
            path = Path(event.src_path)
            plugin_dir = path.parent.name
            
            if plugin_dir in self.loader.plugins:
                logger.info(f"Plugin file modified: {event.src_path}, reloading {plugin_dir}")
                self.loader.reload_plugin(plugin_dir)

class ImprovedPluginLoaderService(AsyncService):
    """Improved service for loading and managing plugins."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize improved plugin loader service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.registry = PluginRegistry(self.config)
        self.dependency_manager = PluginDependencyManager()
        self.event_emitter = PluginEventEmitter()
        self.plugins = {}
        self.plugin_instances = {}
        self.hot_reload = self.config.get('PLUGIN_HOT_RELOAD', True)
        self.observer = None
        self.plugin_hooks = {}
        
    async def initialize(self):
        """Initialize plugin loader."""
        # Discover plugins
        plugin_names = await self._discover_plugins()
        
        # Build dependency graph
        for name, plugin_info in self.plugins.items():
            manifest = plugin_info.get("manifest")
            if manifest:
                self.dependency_manager.add_plugin(name, manifest.dependencies)
        
        # Resolve dependencies
        try:
            load_order = self.dependency_manager.resolve_dependencies()
            logger.info(f"Plugin load order: {', '.join(load_order)}")
            
            # Load plugins in dependency order
            for plugin_name in load_order:
                await self._load_plugin(plugin_name)
        except ValueError as e:
            logger.error(f"Error resolving plugin dependencies: {str(e)}")
        
        # Start file watcher if hot reload is enabled
        if self.hot_reload:
            self._start_file_watcher()
            
        logger.info(f"Improved plugin loader initialized with {len(plugin_names)} plugins")
        return plugin_names
    
    async def _discover_plugins(self) -> List[str]:
        """Discover available plugins.
        
        Returns:
            List of discovered plugin names
        """
        plugin_dir = self.config.get('PLUGIN_DIR', 'plugins')
        discovered = []
        
        if not os.path.exists(plugin_dir):
            logger.warning(f"Plugin directory not found: {plugin_dir}")
            return discovered
        
        for plugin_folder in os.listdir(plugin_dir):
            plugin_path = os.path.join(plugin_dir, plugin_folder)
            
            if not os.path.isdir(plugin_path):
                continue
                
            manifest_path = os.path.join(plugin_path, "manifest.json")
            if not os.path.exists(manifest_path):
                logger.warning(f"No manifest.json found in plugin folder: {plugin_folder}")
                continue
                
            try:
                manifest = PluginManifest.from_file(manifest_path)
                
                self.plugins[plugin_folder] = {
                    "manifest": manifest,
                    "path": plugin_path,
                    "module_path": f"{plugin_dir}.{plugin_folder}",
                    "loaded": False,
                    "last_modified": time.time(),
                    "instance": None
                }
                
                discovered.append(plugin_folder)
                logger.info(f"Discovered plugin: {manifest.name} v{manifest.version}")
                
                # Register plugin with registry
                self.registry.plugins[manifest.name] = {
                    "manifest": manifest,
                    "path": plugin_path,
                    "module_path": f"{plugin_dir}.{plugin_folder}"
                }
            except Exception as e:
                logger.error(f"Error loading plugin {plugin_folder}: {str(e)}")
        
        return discovered
    
    async def _load_plugin(self, plugin_name: str) -> Optional[BaseService]:
        """Load plugin.
        
        Args:
            plugin_name: Plugin name
            
        Returns:
            Plugin instance or None if loading failed
        """
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin not found: {plugin_name}")
            return None
            
        plugin_info = self.plugins[plugin_name]
        if plugin_info.get("loaded") and plugin_info.get("instance"):
            return plugin_info["instance"]
            
        manifest = plugin_info["manifest"]
        module_path = plugin_info["module_path"]
        
        try:
            # Import plugin module
            module_name = f"{module_path}.{manifest.name.lower()}"
            module = importlib.import_module(module_name)
            
            # Get plugin class
            plugin_class = getattr(module, manifest.class_name)
            
            # Create plugin instance
            if self.app_context:
                plugin_instance = plugin_class(app_context=self.app_context)
            else:
                plugin_instance = plugin_class()
            
            # Initialize plugin if it has initialize method
            if hasattr(plugin_instance, 'initialize') and callable(plugin_instance.initialize):
                if inspect.iscoroutinefunction(plugin_instance.initialize):
                    await plugin_instance.initialize()
                else:
                    plugin_instance.initialize()
            
            # Register plugin hooks
            self._register_plugin_hooks(plugin_name, plugin_instance)
            
            # Update plugin info
            plugin_info["loaded"] = True
            plugin_info["instance"] = plugin_instance
            self.plugin_instances[plugin_name] = plugin_instance
            
            # Register with registry
            self.registry.plugin_instances[manifest.name] = plugin_instance
            
            # Emit plugin loaded event
            self.event_emitter.emit('plugin_loaded', plugin_name, plugin_instance)
            
            logger.info(f"Loaded plugin: {plugin_name}")
            return plugin_instance
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_name}: {str(e)}")
            return None
    
    def _register_plugin_hooks(self, plugin_name: str, plugin_instance: BaseService):
        """Register plugin hooks.
        
        Args:
            plugin_name: Plugin name
            plugin_instance: Plugin instance
        """
        # Find methods with hook decorator
        hooks = {}
        
        for attr_name in dir(plugin_instance):
            if attr_name.startswith('__'):
                continue
                
            attr = getattr(plugin_instance, attr_name)
            if callable(attr) and hasattr(attr, '_hook_name'):
                hook_name = getattr(attr, '_hook_name')
                hooks[hook_name] = attr
        
        if hooks:
            self.plugin_hooks[plugin_name] = hooks
            logger.info(f"Registered {len(hooks)} hooks for plugin {plugin_name}")
    
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
    
    async def reload_plugin(self, name: str) -> bool:
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
            plugin_info = self.plugins[name]
            manifest = plugin_info["manifest"]
            
            # Unload plugin
            if plugin_info.get("loaded") and plugin_info.get("instance"):
                instance = plugin_info["instance"]
                
                # Call unload method if available
                if hasattr(instance, 'unload') and callable(instance.unload):
                    if inspect.iscoroutinefunction(instance.unload):
                        await instance.unload()
                    else:
                        instance.unload()
                
                # Remove plugin hooks
                if name in self.plugin_hooks:
                    del self.plugin_hooks[name]
                
                # Emit plugin unloaded event
                self.event_emitter.emit('plugin_unloaded', name, instance)
            
            # Remove plugin instance from registry
            if manifest.name in self.registry.plugin_instances:
                del self.registry.plugin_instances[manifest.name]
                
            # Remove plugin instance
            if name in self.plugin_instances:
                del self.plugin_instances[name]
                
            # Reload plugin module
            module_path = plugin_info["module_path"]
            module_name = f"{module_path}.{manifest.name.lower()}"
            
            # Reload module if it's loaded
            if module_name in sys.modules:
                importlib.reload(sys.modules[module_name])
                
            # Update last modified time
            plugin_info["loaded"] = False
            plugin_info["last_modified"] = time.time()
            plugin_info["instance"] = None
            
            # Load plugin
            await self._load_plugin(name)
            
            logger.info(f"Reloaded plugin: {name}")
            return True
        except Exception as e:
            logger.error(f"Error reloading plugin {name}: {str(e)}")
            return False
    
    async def invoke_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Invoke plugin hooks.
        
        Args:
            hook_name: Hook name
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            List of hook results
        """
        results = []
        
        for plugin_name, hooks in self.plugin_hooks.items():
            if hook_name in hooks:
                hook_func = hooks[hook_name]
                try:
                    if inspect.iscoroutinefunction(hook_func):
                        result = await hook_func(*args, **kwargs)
                    else:
                        result = hook_func(*args, **kwargs)
                    
                    results.append({
                        "plugin": plugin_name,
                        "result": result
                    })
                except Exception as e:
                    logger.error(f"Error invoking hook {hook_name} in plugin {plug<response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>