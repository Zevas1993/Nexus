"""
Resource management for AI assistant plugins.
"""
import logging
import asyncio
import psutil
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AIResourceManager:
    """Manages system resources for AI plugins."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize resource manager.
        
        Args:
            config: Configuration options
        """
        self.config = config or {}
        self.ram_allocation: Dict[str, int] = {}  # plugin -> MB
        self.cpu_allocation: Dict[str, float] = {}  # plugin -> percentage
        self.gpu_allocation: Dict[str, int] = {}  # plugin -> MB
        
        # Default limits from config or use reasonable defaults
        self.system_limits = {
            "ram": self.config.get("max_ram_mb", 4096),  # 4 GB max for AI plugins
            "cpu": self.config.get("max_cpu_percent", 75),    # Max 75% CPU usage
            "gpu": self.config.get("max_gpu_mb", 2048)   # 2 GB GPU memory
        }
        
        self.current_usage = {
            "ram": 0,
            "cpu": 0,
            "gpu": 0
        }
        
        # Set to track active allocations
        self.active_plugins = set()
        
    def register_plugin_requirements(self, plugin_name: str, requirements: Dict[str, Any]) -> None:
        """Register resource requirements for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            requirements: Resource requirements dictionary
        """
        self.ram_allocation[plugin_name] = requirements.get("ram_mb", 256)
        self.cpu_allocation[plugin_name] = requirements.get("cpu_percent", 10)
        self.gpu_allocation[plugin_name] = requirements.get("gpu_mb", 0)
        logger.info(f"Registered resource requirements for {plugin_name}: "
                   f"RAM={self.ram_allocation[plugin_name]}MB, "
                   f"CPU={self.cpu_allocation[plugin_name]}%, "
                   f"GPU={self.gpu_allocation[plugin_name]}MB")
        
    async def allocate_resources(self, plugin_name: str) -> bool:
        """Attempt to allocate resources for a plugin.
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            True if resources were successfully allocated
        """
        if plugin_name not in self.ram_allocation:
            logger.warning(f"Plugin {plugin_name} has no registered resource requirements")
            return False
            
        # Check if plugin already has resources allocated
        if plugin_name in self.active_plugins:
            logger.debug(f"Plugin {plugin_name} already has resources allocated")
            return True
            
        ram_needed = self.ram_allocation[plugin_name]
        cpu_needed = self.cpu_allocation[plugin_name]
        gpu_needed = self.gpu_allocation[plugin_name]
        
        # Check if we have enough resources
        if (self.current_usage["ram"] + ram_needed > self.system_limits["ram"] or
            self.current_usage["cpu"] + cpu_needed > self.system_limits["cpu"] or
            self.current_usage["gpu"] + gpu_needed > self.system_limits["gpu"]):
            logger.warning(f"Insufficient resources for plugin {plugin_name}")
            return False
            
        # Check actual system resources as well
        try:
            system_ram = psutil.virtual_memory()
            system_cpu = psutil.cpu_percent(interval=0.1)
            
            # Ensure there's enough headroom in the actual system
            if system_ram.percent > 90 or system_cpu > 90:
                logger.warning(f"System resources too constrained for plugin {plugin_name}")
                return False
        except Exception as e:
            logger.warning(f"Error checking system resources: {str(e)}")
            # Continue anyway as this is just an additional check
            
        # Allocate resources
        self.current_usage["ram"] += ram_needed
        self.current_usage["cpu"] += cpu_needed
        self.current_usage["gpu"] += gpu_needed
        self.active_plugins.add(plugin_name)
        
        logger.info(f"Resources allocated for {plugin_name}: "
                   f"RAM={ram_needed}MB, CPU={cpu_needed}%, GPU={gpu_needed}MB")
        logger.debug(f"Current usage: RAM={self.current_usage['ram']}MB, "
                    f"CPU={self.current_usage['cpu']}%, GPU={self.current_usage['gpu']}MB")
        
        return True
        
    async def release_resources(self, plugin_name: str) -> None:
        """Release resources allocated to a plugin.
        
        Args:
            plugin_name: Name of the plugin
        """
        if plugin_name not in self.ram_allocation or plugin_name not in self.active_plugins:
            logger.debug(f"No resources to release for plugin {plugin_name}")
            return
            
        self.current_usage["ram"] -= self.ram_allocation[plugin_name]
        self.current_usage["cpu"] -= self.cpu_allocation[plugin_name]
        self.current_usage["gpu"] -= self.gpu_allocation[plugin_name]
        self.active_plugins.remove(plugin_name)
        
        # Ensure we don't go negative
        self.current_usage = {k: max(0, v) for k, v in self.current_usage.items()}
        
        logger.info(f"Resources released for {plugin_name}")
        logger.debug(f"Current usage: RAM={self.current_usage['ram']}MB, "
                    f"CPU={self.current_usage['cpu']}%, GPU={self.current_usage['gpu']}MB")
        
    def get_current_usage(self) -> Dict[str, Any]:
        """Get current resource usage.
        
        Returns:
            Dictionary with current resource usage
        """
        return {
            "allocated": self.current_usage.copy(),
            "limits": self.system_limits.copy(),
            "active_plugins": list(self.active_plugins),
            "utilization": {
                "ram": self.current_usage["ram"] / self.system_limits["ram"] * 100 if self.system_limits["ram"] > 0 else 0,
                "cpu": self.current_usage["cpu"] / self.system_limits["cpu"] * 100 if self.system_limits["cpu"] > 0 else 0,
                "gpu": self.current_usage["gpu"] / self.system_limits["gpu"] * 100 if self.system_limits["gpu"] > 0 else 0
            }
        }
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics.
        
        Returns:
            Dictionary with system metrics
        """
        try:
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            return {
                "ram_total_mb": memory.total // (1024 * 1024),
                "ram_used_mb": memory.used // (1024 * 1024),
                "ram_percent": memory.percent,
                "cpu_percent": cpu_percent,
                "ai_allocation": self.get_current_usage()
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {
                "error": str(e),
                "ai_allocation": self.get_current_usage()
            }
