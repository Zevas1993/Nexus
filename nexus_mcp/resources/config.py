"""
Configuration resources for the Nexus MCP server.
These resources provide access to Nexus configuration data.
"""

import logging
from typing import Dict, Any

from nexus_mcp.models.base import NexusJsonResource, NexusTextResource
from nexus_mcp.hardware import hardware_manager

logger = logging.getLogger("nexus_mcp.resources.config")

def register_config_resources(mcp_server):
    """Register all configuration resource handlers with the MCP server."""
    
    @mcp_server.resource("nexus://config")
    async def get_config(ctx) -> NexusJsonResource:
        """Provide Nexus configuration data."""
        logger.info("Retrieving Nexus configuration")
        
        # In a real implementation, this would fetch from a configuration store
        config_data = {
            "name": "Nexus AI Assistant",
            "version": "1.0.0",
            "description": "AI Assistant with MCP integration",
            "features": [
                "Natural language processing",
                "Code generation and analysis",
                "Data visualization",
                "External API integration"
            ],
            "settings": {
                "max_tokens": 4096,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
        
        return NexusJsonResource(
            resource_id="nexus://config",
            content=config_data,
            metadata={"source": "system", "updated": "2025-03-21"}
        )
    
    @mcp_server.resource("nexus://config/features")
    async def get_features(ctx) -> NexusTextResource:
        """Provide Nexus features list."""
        logger.info("Retrieving Nexus features")
        
        features = """
        Nexus AI Assistant Features:
        
        1. Natural language processing
        2. Code generation and analysis
        3. Data visualization
        4. External API integration
        5. MCP server integration
        """
        
        return NexusTextResource(
            resource_id="nexus://config/features",
            content=features,
            metadata={"source": "system", "updated": "2025-03-21"}
        )
    
    @mcp_server.resource("nexus://config/hardware")
    async def get_hardware_config(ctx) -> NexusJsonResource:
        """Provide hardware configuration information."""
        logger.info("Retrieving hardware configuration")
        
        # Get actual hardware information from the hardware manager
        hardware_settings = hardware_manager.get_optimal_settings()
        
        # Add detected hardware information
        hardware_config = {
            "cpu": {
                "model": hardware_manager.cpu_model,
                "cores": hardware_manager.cpu_cores,
                "threads": hardware_manager.cpu_threads,
                "is_i7_13700k": hardware_manager.is_i7_13700k
            },
            "gpu": {
                "model": hardware_manager.gpu_model,
                "available": hardware_manager.has_gpu,
                "is_rtx_3070ti": hardware_manager.is_rtx_3070ti
            },
            "ram": {
                "total_gb": round(hardware_manager.total_memory / (1024**3), 2),
                "is_32gb": hardware_manager.is_32gb_ram
            },
            "optimizations": {
                "worker_processes": hardware_settings.get("worker_processes", 4),
                "parallel_processing": hardware_settings.get("parallel_processing", True),
                "gpu_acceleration": hardware_settings.get("use_gpu", False),
                "memory_efficient": hardware_settings.get("memory_efficient", True),
                "batch_size": hardware_settings.get("batch_size", 16)
            }
        }
        
        return NexusJsonResource(
            resource_id="nexus://config/hardware",
            content=hardware_config,
            metadata={"source": "system", "updated": "2025-03-21"}
        )
    
    logger.info("Registered configuration resources")
    return mcp_server
