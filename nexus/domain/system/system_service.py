"""
System management services for Nexus AI Assistant.

This module provides system monitoring, diagnostics, and resource optimization.
"""
import logging
import platform
import os
import time
import psutil
from typing import Dict, Any, List, Optional, Union

logger = logging.getLogger(__name__)

# Try to import GPU monitoring tools
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available, GPU monitoring will be limited")

try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except ImportError:
    GPUTIL_AVAILABLE = False
    logger.warning("GPUtil not available, detailed GPU monitoring will be limited")

try:
    import pynvml
    pynvml.nvmlInit()
    NVML_AVAILABLE = True
except (ImportError, Exception):
    NVML_AVAILABLE = False
    logger.warning("NVIDIA Management Library not available, detailed GPU monitoring will be limited")

from ...domain.base import AsyncService

class SystemManagementService(AsyncService):
    """System management service with monitoring and optimization."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize system management service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.throttle_threshold_cpu = self.config.get("THROTTLE_THRESHOLD_CPU", 90)
        self.throttle_threshold_memory = self.config.get("THROTTLE_THRESHOLD_MEMORY", 90)
        self.throttle_threshold_gpu = self.config.get("THROTTLE_THRESHOLD_GPU", 90)
        self.last_check = 0
        self.check_interval = 5  # seconds
        
    async def initialize(self):
        """Initialize system management service."""
        logger.info("System Management Service initializing")
        
        # Log system info
        system_info = self._get_system_info()
        logger.info(f"System: {system_info['system']} {system_info['version']}")
        logger.info(f"CPU: {system_info['cpu_name']} ({system_info['cpu_cores']} cores)")
        logger.info(f"Memory: {system_info['memory_total']} GB")
        
        if system_info.get('gpu_count', 0) > 0:
            gpus = system_info.get('gpus', [])
            for i, gpu in enumerate(gpus):
                logger.info(f"GPU {i}: {gpu.get('name', 'Unknown')} ({gpu.get('memory', 0)} MB)")
                
        logger.info("System Management Service initialized")
    
    async def _process_impl(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a system management request.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
                - task: Specific task to perform
                
        Returns:
            Processing result
        """
        task = kwargs.get('task', 'status')
        
        if task == 'status' or task == 'hardware_check':
            return self._check_system_status()
        elif task == 'optimize_resources':
            return await self._optimize_resources()
        elif task == 'diagnostics':
            return self._run_diagnostics()
        elif task == 'clear_cache':
            return await self._clear_cache()
        else:
            return {"error": f"Unknown task: {task}"}
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information.
        
        Returns:
            System information
        """
        info = {
            "system": platform.system(),
            "version": platform.version(),
            "architecture": platform.architecture()[0],
            "cpu_name": platform.processor(),
            "cpu_cores": psutil.cpu_count(logical=True),
            "cpu_physical_cores": psutil.cpu_count(logical=False),
            "memory_total": round(psutil.virtual_memory().total / (1024**3), 2),  # GB
            "python_version": platform.python_version(),
        }
        
        # GPU information
        gpu_info = self._get_gpu_info()
        info.update(gpu_info)
        
        return info
    
    def _get_gpu_info(self) -> Dict[str, Any]:
        """Get GPU information.
        
        Returns:
            GPU information
        """
        gpu_info = {
            "gpu_count": 0,
            "gpus": []
        }
        
        # Try PyTorch first
        if TORCH_AVAILABLE and torch.cuda.is_available():
            gpu_info["gpu_count"] = torch.cuda.device_count()
            for i in range(gpu_info["gpu_count"]):
                gpu_info["gpus"].append({
                    "name": torch.cuda.get_device_name(i),
                    "index": i
                })
                
        # If PyTorch detected GPUs, try to get more detailed info
        if gpu_info["gpu_count"] > 0:
            # Try NVIDIA Management Library first
            if NVML_AVAILABLE:
                try:
                    for i in range(gpu_info["gpu_count"]):
                        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        if i < len(gpu_info["gpus"]):
                            gpu_info["gpus"][i]["memory"] = int(info.total / (1024**2))  # MB
                except Exception as e:
                    logger.warning(f"Error getting GPU memory info: {str(e)}")
            
            # Try GPUtil as a fallback
            elif GPUTIL_AVAILABLE:
                try:
                    gpus = GPUtil.getGPUs()
                    for i, gpu in enumerate(gpus):
                        if i < len(gpu_info["gpus"]):
                            gpu_info["gpus"][i]["memory"] = int(gpu.memoryTotal)  # MB
                except Exception as e:
                    logger.warning(f"Error getting GPU info from GPUtil: {str(e)}")
            
        return gpu_info
    
    def _check_system_status(self) -> Dict[str, Any]:
        """Check system status.
        
        Returns:
            System status information
        """
        # Current timestamp
        timestamp = time.time()
        
        # Limit how often we check to reduce system load
        if timestamp - self.last_check < self.check_interval:
            # Return cached result
            if hasattr(self, '_last_status'):
                return self._last_status
                
        self.last_check = timestamp
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # GPU usage
        gpu_stats = []
        
        if TORCH_AVAILABLE and torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            
            # Try NVML first
            if NVML_AVAILABLE:
                try:
                    for i in range(gpu_count):
                        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                        name = pynvml.nvmlDeviceGetName(handle)
                        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
                        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        temperature = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                        
                        gpu_stats.append({
                            "index": i,
                            "name": name,
                            "load": utilization.gpu,  # percent
                            "memory_used": int(memory.used / (1024**2)),  # MB
                            "memory_total": int(memory.total / (1024**2)),  # MB
                            "memory_percent": round(memory.used / memory.total * 100, 1),
                            "temperature": temperature
                        })
                except Exception as e:
                    logger.warning(f"Error getting detailed GPU stats: {str(e)}")
            
            # Try GPUtil as fallback
            elif GPUTIL_AVAILABLE:
                try:
                    gpus = GPUtil.getGPUs()
                    for i, gpu in enumerate(gpus):
                        gpu_stats.append({
                            "index": i,
                            "name": gpu.name,
                            "load": gpu.load * 100,  # convert to percent
                            "memory_used": int(gpu.memoryUsed),  # MB
                            "memory_total": int(gpu.memoryTotal),  # MB
                            "memory_percent": gpu.memoryUtil * 100,  # convert to percent
                            "temperature": gpu.temperature
                        })
                except Exception as e:
                    logger.warning(f"Error getting GPU stats from GPUtil: {str(e)}")
            
            # Minimal info if other methods fail
            if not gpu_stats:
                for i in range(gpu_count):
                    try:
                        name = torch.cuda.get_device_name(i)
                        gpu_stats.append({
                            "index": i,
                            "name": name,
                            "load": 0,  # Unknown
                            "memory_used": 0,  # Unknown
                            "memory_total": 0,  # Unknown
                            "memory_percent": 0  # Unknown
                        })
                    except Exception:
                        pass
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Network stats
        try:
            net_io = psutil.net_io_counters()
            network = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv
            }
        except Exception:
            network = {"error": "Unable to get network stats"}
        
        # Build status
        status = {
            "timestamp": timestamp,
            "system_stats": {
                "cpu": {
                    "percent": cpu_percent,
                    "cores": psutil.cpu_count(logical=True),
                    "physical_cores": psutil.cpu_count(logical=False)
                },
                "memory": {
                    "total": int(memory.total / (1024**2)),  # MB
                    "available": int(memory.available / (1024**2)),  # MB
                    "used": int(memory.used / (1024**2)),  # MB
                    "percent": memory_percent
                },
                "disk": {
                    "total": int(disk.total / (1024**3)),  # GB
                    "used": int(disk.used / (1024**3)),  # GB
                    "free": int(disk.free / (1024**3)),  # GB
                    "percent": disk.percent
                },
                "network": network
            }
        }
        
        if gpu_stats:
            status["system_stats"]["gpu"] = gpu_stats
        
        # Save for caching
        self._last_status = status
        
        return status
    
    async def _optimize_resources(self) -> Dict[str, Any]:
        """Optimize system resources.
        
        Returns:
            Optimization result
        """
        # Check current system status
        status = self._check_system_status()
        
        # Check if we need to take action
        cpu_percent = status["system_stats"]["cpu"]["percent"]
        memory_percent = status["system_stats"]["memory"]["percent"]
        
        # Initialize results
        results = {
            "actions_taken": [],
            "current_status": status
        }
        
        # Check if we need to reduce AI model size or switch to cloud
        if cpu_percent > self.throttle_threshold_cpu:
            results["actions_taken"].append("Switch to cloud AI due to high CPU usage")
            
        if memory_percent > self.throttle_threshold_memory:
            results["actions_taken"].append("Reduce memory usage by clearing caches")
            # Try to clear some caches
            await self._clear_cache()
            
        # GPU throttling
        if "gpu" in status["system_stats"]:
            for gpu in status["system_stats"]["gpu"]:
                if gpu.get("load", 0) > self.throttle_threshold_gpu:
                    results["actions_taken"].append(f"Switch to cloud AI due to high GPU {gpu['index']} usage")
                if gpu.get("memory_percent", 0) > self.throttle_threshold_memory:
                    results["actions_taken"].append(f"Reduce GPU {gpu['index']} memory usage")
                    
        if not results["actions_taken"]:
            results["actions_taken"].append("No optimization needed")
            
        return results
    
    def _run_diagnostics(self) -> Dict[str, Any]:
        """Run system diagnostics.
        
        Returns:
            Diagnostics results
        """
        # Get basic system info
        system_info = self._get_system_info()
        
        # Get current status
        status = self._check_system_status()
        
        # Check for potential issues
        issues = []
        warnings = []
        
        # CPU check
        cpu_percent = status["system_stats"]["cpu"]["percent"]
        if cpu_percent > 90:
            issues.append("CPU usage is critically high (>90%)")
        elif cpu_percent > 70:
            warnings.append("CPU usage is high (>70%)")
            
        # Memory check
        memory_percent = status["system_stats"]["memory"]["percent"]
        if memory_percent > 90:
            issues.append("Memory usage is critically high (>90%)")
        elif memory_percent > 70:
            warnings.append("Memory usage is high (>70%)")
            
        # Disk check
        disk_percent = status["system_stats"]["disk"]["percent"]
        if disk_percent > 90:
            issues.append("Disk usage is critically high (>90%)")
        elif disk_percent > 70:
            warnings.append("Disk usage is high (>70%)")
            
        # GPU check
        if "gpu" in status["system_stats"]:
            for gpu in status["system_stats"]["gpu"]:
                if gpu.get("load", 0) > 90:
                    issues.append(f"GPU {gpu['index']} usage is critically high (>90%)")
                elif gpu.get("load", 0) > 70:
                    warnings.append(f"GPU {gpu['index']} usage is high (>70%)")
                    
                if gpu.get("temperature", 0) > 85:
                    issues.append(f"GPU {gpu['index']} temperature is critically high (>85°C)")
                elif gpu.get("temperature", 0) > 75:
                    warnings.append(f"GPU {gpu['index']} temperature is high (>75°C)")
        
        # Return diagnostics
        return {
            "system_info": system_info,
            "current_status": status,
            "issues": issues,
            "warnings": warnings,
            "recommendations": self._generate_recommendations(issues, warnings)
        }
    
    def _generate_recommendations(self, issues: List[str], warnings: List[str]) -> List[str]:
        """Generate recommendations based on issues and warnings.
        
        Args:
            issues: List of critical issues
            warnings: List of warnings
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # CPU recommendations
        if any("CPU usage" in issue for issue in issues):
            recommendations.append("Consider using cloud AI instead of local processing")
            recommendations.append("Close unnecessary applications to free up CPU resources")
            
        elif any("CPU usage" in warning for warning in warnings):
            recommendations.append("Monitor CPU usage and consider switching to cloud AI if it increases further")
            
        # Memory recommendations
        if any("Memory usage" in issue for issue in issues):
            recommendations.append("Clear application caches to free up memory")
            recommendations.append("Close memory-intensive applications")
            recommendations.append("Consider using smaller AI models")
            
        elif any("Memory usage" in warning for warning in warnings):
            recommendations.append("Monitor memory usage and consider clearing caches if it increases further")
            
        # Disk recommendations
        if any("Disk usage" in issue for issue in issues):
            recommendations.append("Delete unnecessary files to free up disk space")
            recommendations.append("Move large files to external storage")
            
        elif any("Disk usage" in warning for warning in warnings):
            recommendations.append("Clean up temporary files to free up disk space")
            
        # GPU recommendations
        if any("GPU" in issue and "usage" in issue for issue in issues):
            recommendations.append("Use smaller or quantized AI models to reduce GPU load")
            recommendations.append("Consider using CPU processing or cloud AI instead")
            
        if any("GPU" in issue and "temperature" in issue for issue in issues):
            recommendations.append("Improve cooling for your GPU")
            recommendations.append("Reduce GPU workload to decrease temperature")
            
        # Default recommendations
        if not recommendations:
            recommendations.append("No specific recommendations at this time")
            
        return recommendations
    
    async def _clear_cache(self) -> Dict[str, Any]:
        """Clear system and application caches.
        
        Returns:
            Cache clearing result
        """
        results = {
            "cache_cleared": []
        }
        
        # Try to clear Redis cache if available
        try:
            from ...infrastructure.performance.caching import RedisCacheService
            cache_service = self.app_context.get_service(RedisCacheService)
            if cache_service and hasattr(cache_service, 'clear'):
                success = cache_service.clear()
                if success:
                    results["cache_cleared"].append("Redis cache")
        except Exception as e:
            logger.warning(f"Failed to clear Redis cache: {str(e)}")
            
        # Try to clear file cache if available
        try:
            from ...infrastructure.performance.caching import FileCacheService
            file_cache_service = self.app_context.get_service(FileCacheService)
            if file_cache_service and hasattr(file_cache_service, 'clear'):
                success = file_cache_service.clear()
                if success:
                    results["cache_cleared"].append("File cache")
        except Exception as e:
            logger.warning(f"Failed to clear file cache: {str(e)}")
            
        # Try to clear PyTorch cache if available
        if TORCH_AVAILABLE and torch.cuda.is_available():
            try:
                # Record initial memory
                initial_memory = []
                for i in range(torch.cuda.device_count()):
                    torch.cuda.set_device(i)
                    initial_memory.append(torch.cuda.memory_allocated(i))
                
                # Clear cache
                torch.cuda.empty_cache()
                
                # Check if memory was freed
                memory_freed = []
                for i in range(torch.cuda.device_count()):
                    torch.cuda.set_device(i)
                    new_memory = torch.cuda.memory_allocated(i)
                    freed = max(0, initial_memory[i] - new_memory)
                    memory_freed.append(freed)
                    
                if any(freed > 0 for freed in memory_freed):
                    results["cache_cleared"].append("PyTorch CUDA cache")
                    results["memory_freed"] = {
                        f"gpu_{i}": f"{freed / (1024**2):.2f} MB" 
                        for i, freed in enumerate(memory_freed) if freed > 0
                    }
            except Exception as e:
                logger.warning(f"Failed to clear PyTorch CUDA cache: {str(e)}")
                
        # If no caches were cleared
        if not results["cache_cleared"]:
            results["cache_cleared"].append("No caches available to clear")
            
        return results
