#!/usr/bin/env python
"""
Main entry point for the Nexus MCP server.
This script initializes the server and provides a command-line interface.
"""

import os
import sys
import logging
import argparse
import uvicorn

# Add the parent directory to the Python path so we can import nexus_mcp
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from nexus_mcp.config import MCP_HOST, MCP_PORT, MCP_DEBUG, BASE_DIR, LOGS_DIR
from nexus_mcp.hardware import hardware_manager

# Configure logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO if not MCP_DEBUG else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'mcp_server.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("nexus_mcp_main")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Nexus MCP Server")
    
    parser.add_argument(
        "--host", 
        default=MCP_HOST,
        help=f"Host to bind to (default: {MCP_HOST})"
    )
    
    parser.add_argument(
        "--port", 
        type=int, 
        default=MCP_PORT,
        help=f"Port to bind to (default: {MCP_PORT})"
    )
    
    parser.add_argument(
        "--debug", 
        action="store_true", 
        default=MCP_DEBUG,
        help="Enable debug mode"
    )
    
    parser.add_argument(
        "--reload", 
        action="store_true", 
        default=MCP_DEBUG,
        help="Enable auto-reload on code changes"
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the Nexus MCP server."""
    args = parse_arguments()
    
    # Detect hardware and log information
    logger.info(f"System hardware detected:")
    logger.info(f"  CPU: {hardware_manager.cpu_model} ({hardware_manager.cpu_cores} cores, {hardware_manager.cpu_threads} threads)")
    logger.info(f"  RAM: {hardware_manager.total_memory / (1024**3):.2f} GB")
    logger.info(f"  GPU: {hardware_manager.gpu_model if hardware_manager.has_gpu else 'None'}")
    
    # Get optimized settings
    settings = hardware_manager.get_optimal_settings()
    logger.info(f"Applied hardware-specific optimizations:")
    for key, value in settings.items():
        logger.info(f"  {key}: {value}")
    
    # Start the server
    logger.info(f"Starting Nexus MCP server on {args.host}:{args.port}")
    logger.info(f"Debug mode: {'enabled' if args.debug else 'disabled'}")
    logger.info(f"Auto-reload: {'enabled' if args.reload else 'disabled'}")
    
    uvicorn.run(
        "nexus_mcp.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="debug" if args.debug else "info"
    )

if __name__ == "__main__":
    main()
