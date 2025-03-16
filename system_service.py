"""
System management service for Nexus AI Assistant.

This module provides system monitoring and management functionality.
"""

from typing import Dict, Any, List, Optional
import logging
import psutil
import platform
import os
import time
from ...infrastructure.context import ApplicationContext

logger = logging.getLogger(__name__)

class SystemService:
    """Service for system monitoring and management."""
    
    def __init__(self, app_context: ApplicationContext):
        """Initialize system service.
        
        Args:
            app_context: Application context
        """
        self.app_context = app_context
        self.config = app_context.config
        self.cache_service = None
        self.stats_ttl = self.config.get('STATS_TTL', 60)  # 1 minute by default
        
    def initialize(self):
        """Initialize system service."""
        # Get required services
        if self.app_context:
            from ...infrastructure.cache import RedisCacheService
            self.cache_service = self.app_context.get_service(RedisCacheService)
        
        logger.info("System service initialized")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information.
        
        Returns:
            System information
        """
        # Check cache first
        if self.cache_service:
            cached_info = self.cache_service.get("system:info")
            if cached_info:
                return cached_info
        
        # Collect system information
        system_info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
            "cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "memory_total": psutil.virtual_memory().total,
            "disk_total": psutil.disk_usage('/').total,
            "boot_time": psutil.boot_time()
        }
        
        # Cache system information
        if self.cache_service:
            self.cache_service.set("system:info", system_info, ttl=3600)  # 1 hour
        
        return system_info
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics.
        
        Returns:
            System statistics
        """
        # Check cache first
        if self.cache_service:
            cached_stats = self.cache_service.get("system:stats")
            if cached_stats:
                return cached_stats
        
        # Collect system statistics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()
        
        stats = {
            "timestamp": time.time(),
            "cpu": {
                "percent": cpu_percent,
                "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True)
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }
        }
        
        # Add GPU stats if available
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_stats = []
                for gpu in gpus:
                    gpu_stats.append({
                        "id": gpu.id,
                        "name": gpu.name,
                        "load": gpu.load * 100,  # Convert to percentage
                        "memory_total": gpu.memoryTotal,
                        "memory_used": gpu.memoryUsed,
                        "memory_free": gpu.memoryFree,
                        "temperature": gpu.temperature
                    })
                stats["gpu"] = gpu_stats
        except (ImportError, Exception) as e:
            logger.debug(f"GPU stats not available: {str(e)}")
        
        # Cache system statistics
        if self.cache_service:
            self.cache_service.set("system:stats", stats, ttl=self.stats_ttl)
        
        return stats
    
    def get_process_info(self) -> Dict[str, Any]:
        """Get information about the current process.
        
        Returns:
            Process information
        """
        process = psutil.Process(os.getpid())
        
        process_info = {
            "pid": process.pid,
            "name": process.name(),
            "status": process.status(),
            "create_time": process.create_time(),
            "cpu_percent": process.cpu_percent(interval=0.1),
            "memory_info": {
                "rss": process.memory_info().rss,
                "vms": process.memory_info().vms
            },
            "threads": len(process.threads()),
            "connections": len(process.connections())
        }
        
        return process_info
    
    def check_health(self) -> Dict[str, Any]:
        """Check system health.
        
        Returns:
            Health check results
        """
        stats = self.get_system_stats()
        
        # Define thresholds
        cpu_threshold = self.config.get('HEALTH_CPU_THRESHOLD', 90)
        memory_threshold = self.config.get('HEALTH_MEMORY_THRESHOLD', 90)
        disk_threshold = self.config.get('HEALTH_DISK_THRESHOLD', 90)
        
        # Check against thresholds
        health = {
            "status": "healthy",
            "checks": {
                "cpu": {
                    "status": "healthy" if stats["cpu"]["percent"] < cpu_threshold else "warning",
                    "value": stats["cpu"]["percent"],
                    "threshold": cpu_threshold
                },
                "memory": {
                    "status": "healthy" if stats["memory"]["percent"] < memory_threshold else "warning",
                    "value": stats["memory"]["percent"],
                    "threshold": memory_threshold
                },
                "disk": {
                    "status": "healthy" if stats["disk"]["percent"] < disk_threshold else "warning",
                    "value": stats["disk"]["percent"],
                    "threshold": disk_threshold
                }
            },
            "timestamp": time.time()
        }
        
        # Add GPU health if available
        if "gpu" in stats:
            gpu_threshold = self.config.get('HEALTH_GPU_THRESHOLD', 90)
            gpu_checks = []
            
            for i, gpu in enumerate(stats["gpu"]):
                gpu_checks.append({
                    "status": "healthy" if gpu["load"] < gpu_threshold else "warning",
                    "value": gpu["load"],
                    "threshold": gpu_threshold
                })
            
            health["checks"]["gpu"] = gpu_checks
        
        # Set overall status
        for check in health["checks"].values():
            if isinstance(check, list):
                for item in check:
                    if item["status"] == "warning":
                        health["status"] = "warning"
                        break
            elif check["status"] == "warning":
                health["status"] = "warning"
                break
        
        return health
