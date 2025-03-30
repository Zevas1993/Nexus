"""
Main server module for the Nexus MCP server.
This module initializes and configures the MCP server.
"""

import logging
import os
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Dict, Any, Optional

from mcp.server.fastmcp import FastMCP

from nexus_mcp.hardware import hardware_manager
from nexus_mcp.config import MCP_HOST, MCP_PORT, MCP_DEBUG
from nexus_mcp.resources import register_resources
from nexus_mcp.tools import register_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO if not MCP_DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("nexus_mcp.server")

class NexusContext:
    """Context for Nexus MCP server."""
    
    def __init__(self):
        """Initialize the Nexus MCP context."""
        self.config = {}
        logger.info("Initializing Nexus MCP server context")
    
    async def close(self):
        """Clean up resources when the server is shutting down."""
        logger.info("Cleaning up Nexus MCP server context")
        # In a real implementation, this would release resources, close connections, etc.
        pass

@asynccontextmanager
async def nexus_lifespan(mcp_server: FastMCP) -> AsyncIterator[NexusContext]:
    """Manage the lifecycle of the Nexus MCP server."""
    logger.info("Starting Nexus MCP server")
    
    # Initialize context
    context = NexusContext()
    
    try:
        # Apply hardware optimizations
        mcp_server = hardware_manager.apply_settings(mcp_server)
        logger.info("Applied hardware optimizations")
        
        # Yield context to the server
        yield context
    finally:
        # Clean up when the server is shutting down
        await context.close()
        logger.info("Nexus MCP server shutdown complete")

def create_mcp_server() -> FastMCP:
    """Create and configure the FastMCP server instance."""
    logger.info("Creating FastMCP server instance")
    
    # Create the FastMCP server
    mcp_server = FastMCP(
        "Nexus MCP",
        description="Model Context Protocol server for Nexus AI Assistant",
        version="1.0.0",
        lifespan=nexus_lifespan
    )
    
    # Register resources with the server
    mcp_server = register_resources(mcp_server)
    
    # Register tools with the server
    mcp_server = register_tools(mcp_server)
    
    # Log the number of resources and tools registered
    resource_count = len(mcp_server.resource_handlers)
    tool_count = len(mcp_server.tool_handlers)
    logger.info(f"Registered {resource_count} resources and {tool_count} tools")
    
    return mcp_server

# Create the MCP server instance
mcp = create_mcp_server()

# Get the FastAPI app from the MCP server
app = mcp.app

# Add health check endpoint
from fastapi import FastAPI
app_wrapped = FastAPI()
app_wrapped.mount("/", app)

@app_wrapped.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "server": "Nexus MCP",
        "version": "1.0.0",
        "cpu": hardware_manager.cpu_model,
        "gpu": hardware_manager.gpu_model if hardware_manager.has_gpu else "None",
        "optimization": {
            "cpu_cores": hardware_manager.cpu_cores,
            "gpu_available": hardware_manager.has_gpu,
            "ram_gb": round(hardware_manager.total_memory / (1024**3), 2)
        }
    }

# Replace the app with the wrapped app
app = app_wrapped

if __name__ == "__main__":
    # This is only used for direct execution, not for production
    import uvicorn
    
    logger.info(f"Starting Nexus MCP server on {MCP_HOST}:{MCP_PORT}")
    uvicorn.run(
        "nexus_mcp.server:app",
        host=MCP_HOST,
        port=MCP_PORT,
        reload=MCP_DEBUG
    )
