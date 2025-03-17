"""
System management service for Nexus AI Assistant.

This module provides system monitoring, resource optimization, and
hardware management capabilities.
"""
import os
import logging
import platform
import time
import asyncio
import json
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class SystemManagementService:
    """System management service for monitoring and optimizing system resources."""
    
    VERSION = "1.0.0"
    
    def __init__(self, config=None):
        """Initialize system management service.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.last_check = 0
        self.check_interval = self.config.get("SYSTEM_CHECK_INTERVAL", 60)  # seconds
        self.cpu_threshold = self.config.get("CPU_THRESHOLD", 80)  # percent
        self.ram_threshold = self.config.get("RAM_THRESHOLD", 80)  # percent
        self.gpu_threshold = self.config.get("GPU_THRESHOLD", 80)  # percent
        self.has_gpu = False
        self._check_gpu_availability()
        logger.info("System management service initialized")
        
    def _check_gpu_availability(self):
        """Check if GPU is available."""
        try:
            import torch
            self.has_gpu = torch.cuda.is_available()
            if self.has_gpu:
                device_count = torch.cuda.device_count()
                device_name = torch.cuda.get_device_name(0) if device_count > 0 else "Unknown"
                logger.info(f"GPU available: {device_name} (devices: {device_count})")
            else:
                logger.info("No GPU available")
        except ImportError:
            logger.info("PyTorch not available, can't check GPU")
            self.has_gpu = False
            
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a system management request.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
                - task: Specific system task to perform
                
        Returns:
            System management result
        """
        task = kwargs.get('task', 'status')
        
        # Call appropriate method based on task
        if task == 'status':
            return await self._check_status()
        elif task == 'hardware_check':
            return await self._check_hardware()
        elif task == 'optimize_resources':
            return await self._optimize_resources()
        elif task == 'clear_cache':
            return await self._clear_cache()
        else:
            logger.warning(f"Unknown system task: {task}")
            return {
                "status": "error",
                "message": f"Unknown system task: {task}"
            }
    
    async def _check_status(self) -> Dict[str, Any]:
        """Check system status.
        
        Returns:
            System status
        """
        # Get system info
        system_info = await self._get_system_info()
        
        # Check if we need to optimize resources
        optimize = False
        reasons = []
        
        if system_info["cpu_usage"] > self.cpu_threshold:
            optimize = True
            reasons.append(f"CPU usage high: {system_info['cpu_usage']}% > {self.cpu_threshold}%")
            
        if system_info["ram_usage"] > self.ram_threshold:
            optimize = True
            reasons.append(f"RAM usage high: {system_info['ram_usage']}% > {self.ram_threshold}%")
            
        if self.has_gpu and system_info["gpu_usage"] > self.gpu_threshold:
            optimize = True
            reasons.append(f"GPU usage high: {system_info['gpu_usage']}% > {self.gpu_threshold}%")
            
        # Add optimization flag and reasons
        system_info["optimize_recommended"] = optimize
        system_info["optimize_reasons"] = reasons
        
        return {
            "status": "success",
            "data": system_info,
            "text": self._format_system_status(system_info)
        }
    
    async def _check_hardware(self) -> Dict[str, Any]:
        """Check hardware capabilities.
        
        Returns:
            Hardware information
        """
        # Get detailed hardware info
        hardware_info = {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "architecture": platform.architecture()[0],
            "python_version": platform.python_version(),
            "memory": await self._get_memory_info(),
            "disk": await self._get_disk_info(),
            "gpu": await self._get_gpu_info()
        }
        
        return {
            "status": "success",
            "data": hardware_info,
            "text": self._format_hardware_info(hardware_info)
        }
    
    async def _optimize_resources(self) -> Dict[str, Any]:
        """Optimize system resources.
        
        Returns:
            Optimization result
        """
        import gc
        
        # Start with a system status check
        system_info_before = await self._get_system_info()
        
        # Perform optimization steps
        steps_taken = []
        
        # 1. Force garbage collection
        gc.collect()
        steps_taken.append("Forced garbage collection")
        
        # 2. Clear Python caches
        try:
            from functools import lru_cache
            lru_cache.cache_clear()  # Clear all LRU caches
            steps_taken.append("Cleared LRU caches")
        except Exception:
            pass
            
        # 3. Clear torch CUDA cache if available
        if self.has_gpu:
            try:
                import torch
                torch.cuda.empty_cache()
                steps_taken.append("Cleared CUDA cache")
            except Exception:
                pass
        
        # Get system info after optimization
        system_info_after = await self._get_system_info()
        
        # Calculate improvements
        improvements = {
            "cpu_usage": system_info_before["cpu_usage"] - system_info_after["cpu_usage"],
            "ram_usage": system_info_before["ram_usage"] - system_info_after["ram_usage"],
            "gpu_usage": system_info_before["gpu_usage"] - system_info_after["gpu_usage"] if self.has_gpu else 0
        }
        
        return {
            "status": "success",
            "data": {
                "before": system_info_before,
                "after": system_info_after,
                "improvements": improvements,
                "steps_taken": steps_taken
            },
            "text": self._format_optimization_result(system_info_before, system_info_after, steps_taken)
        }
    
    async def _clear_cache(self) -> Dict[str, Any]:
        """Clear system caches.
        
        Returns:
            Cache clearing result
        """
        caches_cleared = []
        
        # 1. Try to clear Redis cache if available
        try:
            from ...infrastructure.performance.caching import RedisCacheService
            cache_service = RedisCacheService(self.config)
            cache_service.flush_all()
            caches_cleared.append("Redis cache")
        except Exception as e:
            logger.warning(f"Error clearing Redis cache: {str(e)}")
        
        # 2. Clear disk caches if available
        cache_dir = os.path.join(os.getcwd(), 'data', 'cache')
        if os.path.exists(cache_dir):
            try:
                for filename in os.listdir(cache_dir):
                    file_path = os.path.join(cache_dir, filename)
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                caches_cleared.append("Disk cache")
            except Exception as e:
                logger.warning(f"Error clearing disk cache: {str(e)}")
        
        return {
            "status": "success",
            "data": {
                "caches_cleared": caches_cleared
            },
            "text": f"Cleared caches: {', '.join(caches_cleared)}"
        }
    
    async def _get_system_info(self) -> Dict[str, Any]:
        """Get system information.
        
        Returns:
            System information
        """
        import psutil
        
        # Get CPU usage
        cpu_usage = psutil.cpu_percent(interval=0.1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        ram_usage = memory.percent
        
        # Get GPU usage if available
        gpu_usage = 0
        if self.has_gpu:
            try:
                import torch
                gpu_usage = self._get_gpu_utilization()
            except ImportError:
                pass
        
        # Get disk usage
        disk = psutil.disk_usage(os.getcwd())
        disk_usage = disk.percent
        
        return {
            "timestamp": time.time(),
            "cpu_usage": cpu_usage,
            "ram_usage": ram_usage,
            "ram_total": memory.total,
            "ram_available": memory.available,
            "gpu_usage": gpu_usage,
            "disk_usage": disk_usage,
            "disk_total": disk.total,
            "disk_free": disk.free,
            "platform": platform.system(),
            "has_gpu": self.has_gpu
        }
    
    async def _get_memory_info(self) -> Dict[str, Any]:
        """Get detailed memory information.
        
        Returns:
            Memory information
        """
        import psutil
        
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "total": memory.total,
            "available": memory.available,
            "percent": memory.percent,
            "used": memory.used,
            "free": memory.free,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent
        }
    
    async def _get_disk_info(self) -> Dict[str, Any]:
        """Get detailed disk information.
        
        Returns:
            Disk information
        """
        import psutil
        
        disk = psutil.disk_usage(os.getcwd())
        disks = []
        
        for partition in psutil.disk_partitions():
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                disks.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": partition_usage.total,
                    "used": partition_usage.used,
                    "free": partition_usage.free,
                    "percent": partition_usage.percent
                })
            except PermissionError:
                # This can happen with some mountpoints
                continue
        
        return {
            "current_directory": {
                "path": os.getcwd(),
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "partitions": disks
        }
    
    async def _get_gpu_info(self) -> Dict[str, Any]:
        """Get detailed GPU information.
        
        Returns:
            GPU information
        """
        if not self.has_gpu:
            return {
                "available": False
            }
            
        try:
            import torch
            
            result = {
                "available": True,
                "count": torch.cuda.device_count(),
                "current_device": torch.cuda.current_device(),
                "devices": []
            }
            
            for i in range(result["count"]):
                device_info = {
                    "name": torch.cuda.get_device_name(i),
                    "capability": torch.cuda.get_device_capability(i),
                    "properties": {
                        "total_memory": torch.cuda.get_device_properties(i).total_memory,
                        "multi_processor_count": torch.cuda.get_device_properties(i).multi_processor_count
                    }
                }
                result["devices"].append(device_info)
                
            return result
        except ImportError:
            return {
                "available": False,
                "error": "PyTorch not available"
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }
    
    def _get_gpu_utilization(self) -> float:
        """Get GPU utilization percentage.
        
        Returns:
            GPU utilization percentage
        """
        try:
            # Try using NVIDIA SMI if available
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                pynvml.nvmlShutdown()
                return util.gpu
            except ImportError:
                pass
                
            # Fall back to nvidia-smi command
            import subprocess
            result = subprocess.check_output([
                'nvidia-smi',
                '--query-gpu=utilization.gpu',
                '--format=csv,noheader,nounits'
            ])
            
            # Parse the result
            utilization = float(result.decode('utf-8').strip())
            return utilization
        except Exception:
            # If all else fails, return a heuristic based on PyTorch memory
            try:
                import torch
                allocated = torch.cuda.memory_allocated(0)
                reserved = torch.cuda.memory_reserved(0)
                total = torch.cuda.get_device_properties(0).total_memory
                
                # Use a heuristic to convert memory usage to utilization percentage
                return min(100, (allocated / total) * 100)
            except Exception:
                return 0
    
    def _format_system_status(self, system_info: Dict[str, Any]) -> str:
        """Format system status information.
        
        Args:
            system_info: System information
            
        Returns:
            Formatted system status
        """
        result = "System Status:\n"
        result += f"• CPU Usage: {system_info['cpu_usage']:.1f}%\n"
        result += f"• RAM Usage: {system_info['ram_usage']:.1f}% ({self._format_bytes(system_info['ram_available'])} available)\n"
        
        if system_info["has_gpu"]:
            result += f"• GPU Usage: {system_info['gpu_usage']:.1f}%\n"
            
        result += f"• Disk Usage: {system_info['disk_usage']:.1f}% ({self._format_bytes(system_info['disk_free'])} free)\n"
        
        if system_info.get("optimize_recommended", False):
            result += "\nOptimization recommended due to:\n"
            for reason in system_info.get("optimize_reasons", []):
                result += f"• {reason}\n"
                
        return result
    
    def _format_hardware_info(self, hardware_info: Dict[str, Any]) -> str:
        """Format hardware information.
        
        Args:
            hardware_info: Hardware information
            
        Returns:
            Formatted hardware information
        """
        result = "Hardware Information:\n"
        result += f"• Platform: {hardware_info['platform']}\n"
        result += f"• Processor: {hardware_info['processor']}\n"
        result += f"• Architecture: {hardware_info['architecture']}\n"
        result += f"• Python Version: {hardware_info['python_version']}\n"
        
        # Memory information
        memory = hardware_info["memory"]
        result += f"• Total Memory: {self._format_bytes(memory['total'])}\n"
        result += f"• Available Memory: {self._format_bytes(memory['available'])} ({100 - memory['percent']:.1f}% free)\n"
        
        # Disk information
        disk = hardware_info["disk"]["current_directory"]
        result += f"• Disk Space: {self._format_bytes(disk['total'])}\n"
        result += f"• Free Disk Space: {self._format_bytes(disk['free'])} ({100 - disk['percent']:.1f}% free)\n"
        
        # GPU information
        gpu = hardware_info["gpu"]
        if gpu.get("available", False):
            result += f"• GPU: {gpu['count']} device(s)\n"
            for i, device in enumerate(gpu.get("devices", [])):
                result += f"  - Device {i}: {device['name']}\n"
        else:
            result += "• GPU: Not available\n"
            
        return result
    
    def _format_optimization_result(self, before: Dict[str, Any], after: Dict[str, Any], steps: List[str]) -> str:
        """Format optimization result.
        
        Args:
            before: System information before optimization
            after: System information after optimization
            steps: Optimization steps taken
            
        Returns:
            Formatted optimization result
        """
        result = "Resource Optimization Results:\n"
        
        # Compare before and after
        cpu_diff = before["cpu_usage"] - after["cpu_usage"]
        ram_diff = before["ram_usage"] - after["ram_usage"]
        gpu_diff = before["gpu_usage"] - after["gpu_usage"] if self.has_gpu else 0
        
        result += f"• CPU Usage: {before['cpu_usage']:.1f}% → {after['cpu_usage']:.1f}% "
        result += f"({cpu_diff:+.1f}%)\n"
        
        result += f"• RAM Usage: {before['ram_usage']:.1f}% → {after['ram_usage']:.1f}% "
        result += f"({ram_diff:+.1f}%)\n"
        
        if self.has_gpu:
            result += f"• GPU Usage: {before['gpu_usage']:.1f}% → {after['gpu_usage']:.1f}% "
            result += f"({gpu_diff:+.1f}%)\n"
            
        # List steps taken
        result += "\nOptimization Steps:\n"
        for step in steps:
            result += f"• {step}\n"
            
        return result
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes value into human-readable string.
        
        Args:
            bytes_value: Bytes value
            
        Returns:
            Formatted string
        """
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_value < 1024 or unit == "TB":
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024
