"""
Hardware optimization module for the Nexus MCP server.
Detects system hardware and provides optimized settings.
"""

import os
import psutil
import platform
import logging
from typing import Dict, Any

from nexus_mcp.config import HARDWARE_CONFIG

logger = logging.getLogger("nexus_mcp.hardware")

class HardwareManager:
    """Manages hardware resources for optimal MCP server performance."""
    
    def __init__(self):
        """Initialize hardware manager and detect system specifications."""
        # Detect CPU information
        self.cpu_cores = psutil.cpu_count(logical=False)
        self.cpu_threads = psutil.cpu_count(logical=True)
        
        # Get CPU model information
        if platform.system() == "Windows":
            import subprocess
            try:
                cpu_info = subprocess.check_output(["wmic", "cpu", "get", "name"]).decode().strip().split("\n")[1]
                self.cpu_model = cpu_info
            except Exception as e:
                logger.warning(f"Could not get CPU model information: {e}")
                self.cpu_model = "Unknown"
        else:
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            self.cpu_model = line.split(":")[1].strip()
                            break
                    else:
                        self.cpu_model = "Unknown"
            except Exception as e:
                logger.warning(f"Could not get CPU model information: {e}")
                self.cpu_model = "Unknown"
        
        # Check if CPU is i7-13700K
        self.is_i7_13700k = "i7-13700K" in self.cpu_model or (
            self.cpu_cores >= 16 and self.cpu_threads >= 24
        )
        
        # Detect memory information
        mem = psutil.virtual_memory()
        self.total_memory = mem.total
        self.available_memory = mem.available
        
        # Check if system has 32GB RAM
        self.is_32gb_ram = self.total_memory >= 32 * 1024 * 1024 * 1024 * 0.9  # 90% of 32GB
        
        # Detect GPU information
        self.has_gpu = False
        self.gpu_model = "None"
        self.gpu_memory = 0
        self.is_rtx_3070ti = False
        
        try:
            import torch
            if torch.cuda.is_available():
                self.has_gpu = True
                self.gpu_model = torch.cuda.get_device_name(0)
                self.gpu_memory = torch.cuda.get_device_properties(0).total_memory
                
                # Check if GPU is RTX 3070 Ti
                self.is_rtx_3070ti = "3070 Ti" in self.gpu_model
        except ImportError:
            logger.warning("PyTorch not available, GPU detection disabled")
        except Exception as e:
            logger.warning(f"Error detecting GPU: {e}")
        
        # Log detected hardware
        self._log_hardware_info()
    
    def _log_hardware_info(self):
        """Log detected hardware information."""
        logger.info("Hardware detection results:")
        logger.info(f"CPU: {self.cpu_model} ({self.cpu_cores} cores, {self.cpu_threads} threads)")
        logger.info(f"Is i7-13700K: {self.is_i7_13700k}")
        logger.info(f"RAM: {self.total_memory / (1024**3):.2f} GB")
        logger.info(f"Is 32GB RAM: {self.is_32gb_ram}")
        logger.info(f"GPU: {self.gpu_model}")
        logger.info(f"Has GPU: {self.has_gpu}")
        logger.info(f"Is RTX 3070Ti: {self.is_rtx_3070ti}")
        if self.has_gpu:
            logger.info(f"GPU Memory: {self.gpu_memory / (1024**3):.2f} GB")
    
    def get_optimal_settings(self) -> Dict[str, Any]:
        """Get optimal settings based on detected hardware."""
        # Base settings (modest defaults)
        settings = {
            "worker_processes": min(4, max(1, self.cpu_cores)),
            "max_memory_mb": int(self.total_memory / (1024**2) * 0.2),  # Use 20% of RAM
            "use_gpu": self.has_gpu,
            "gpu_memory_mb": int(self.gpu_memory / (1024**2) * 0.3) if self.has_gpu else 0,  # Use 30% of GPU memory
            "batch_size": 16,  # Default batch size
            "parallel_processing": True,
            "memory_efficient": True
        }
        
        # Optimize for i7-13700k
        if self.is_i7_13700k:
            logger.info("Applying i7-13700K optimizations")
            settings.update({
                "worker_processes": 12,  # Optimal for i7-13700K (8P+8E cores)
                "parallel_processing": True,
                "thread_priority": "above_normal"
            })
        
        # Optimize for RTX 3070Ti
        if self.is_rtx_3070ti:
            logger.info("Applying RTX 3070Ti optimizations")
            settings.update({
                "use_gpu": True,
                "gpu_memory_mb": int(self.gpu_memory / (1024**2) * 0.5),  # Use 50% of GPU memory
                "batch_size": 32,
                "gpu_precision": "mixed",  # Use mixed precision for better performance
                "tensor_cores": True
            })
        
        # Optimize for 32GB RAM
        if self.is_32gb_ram:
            logger.info("Applying 32GB RAM optimizations")
            settings.update({
                "max_memory_mb": 8192,  # Use up to 8GB RAM
                "cache_size_mb": 2048,  # 2GB cache
                "memory_efficient": False,  # Less need to be memory efficient
                "preload_resources": True
            })
        
        # Load and apply any custom configurations from the hardware config file
        try:
            import json
            if os.path.exists(HARDWARE_CONFIG):
                with open(HARDWARE_CONFIG, "r") as f:
                    custom_config = json.load(f)
                
                # Extract CPU settings
                if "cpu" in custom_config:
                    cpu_config = custom_config["cpu"]
                    if "parallel_workers" in cpu_config:
                        settings["worker_processes"] = cpu_config["parallel_workers"]
                
                # Extract GPU settings
                if "gpu" in custom_config and "cuda_enabled" in custom_config["gpu"]:
                    settings["use_gpu"] = custom_config["gpu"]["cuda_enabled"]
                
                # Extract memory settings
                if "memory" in custom_config:
                    mem_config = custom_config["memory"]
                    if "allocation" in mem_config:
                        # Parse memory string (e.g. "16GB" -> 16384)
                        alloc = mem_config["allocation"]
                        if isinstance(alloc, str):
                            value = float(alloc.rstrip("GBMKgbmk"))
                            unit = alloc[-2:].upper()
                            
                            if unit == 'GB':
                                settings["max_memory_mb"] = int(value * 1024)
                            elif unit == 'MB':
                                settings["max_memory_mb"] = int(value)
                    
                    if "buffer_size" in mem_config:
                        # Parse memory string (e.g. "4GB" -> 4096)
                        buffer = mem_config["buffer_size"]
                        if isinstance(buffer, str):
                            value = float(buffer.rstrip("GBMKgbmk"))
                            unit = buffer[-2:].upper()
                            
                            if unit == 'GB':
                                settings["cache_size_mb"] = int(value * 1024)
                            elif unit == 'MB':
                                settings["cache_size_mb"] = int(value)
                
                # Extract optimization settings
                if "optimization" in custom_config:
                    opt_config = custom_config["optimization"]
                    for key in ["parallel_processing", "gpu_acceleration", "memory_efficient", "batch_size"]:
                        if key in opt_config:
                            if key == "gpu_acceleration":
                                settings["use_gpu"] = opt_config[key]
                            else:
                                settings[key] = opt_config[key]
        
        except Exception as e:
            logger.warning(f"Error loading custom hardware configuration: {e}")
        
        logger.info("Optimal settings determined:")
        for key, value in settings.items():
            logger.info(f"  {key}: {value}")
        
        return settings
    
    def apply_settings(self, app):
        """Apply optimal settings to the application."""
        settings = self.get_optimal_settings()
        
        for key, value in settings.items():
            app.config[key] = value
            logger.info(f"Applied setting: {key}={value}")
        
        # Apply GPU settings if available
        if settings["use_gpu"]:
            try:
                import torch
                if settings.get("gpu_precision") == "mixed":
                    if hasattr(torch, "set_float32_matmul_precision"):
                        torch.set_float32_matmul_precision('medium')
                        logger.info("Set float32 matmul precision to medium")
            except ImportError:
                logger.warning("PyTorch not available, GPU settings not applied")
            except Exception as e:
                logger.warning(f"Error applying GPU settings: {e}")
        
        return app

# Create a singleton instance
hardware_manager = HardwareManager()
