#!/usr/bin/env python
"""
Connection script for the Nexus MCP server.
This script registers the MCP server with the Nexus AI Assistant.
"""

import os
import sys
import logging
import argparse
import asyncio

# Add the parent directory to the Python path so we can import nexus_mcp
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from nexus_mcp.config import NEXUS_API_URL, MCP_SERVER_URL, LOGS_DIR
from nexus_mcp.integration.nexus_integration import nexus_integration

# Configure logging
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, 'mcp_connect.log')),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("nexus_mcp_connect")

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Nexus MCP Connection Utility")
    
    parser.add_argument(
        "--server-url", 
        default=MCP_SERVER_URL,
        help=f"URL of the MCP server (default: {MCP_SERVER_URL})"
    )
    
    parser.add_argument(
        "--nexus-url", 
        default=NEXUS_API_URL,
        help=f"URL of the Nexus API (default: {NEXUS_API_URL})"
    )
    
    parser.add_argument(
        "--server-name", 
        default="Nexus MCP Server",
        help="Name of the MCP server"
    )
    
    return parser.parse_args()

async def connect_to_nexus(server_url, nexus_url, server_name):
    """Connect to Nexus and register the MCP server."""
    logger.info(f"Connecting to Nexus at {nexus_url}")
    logger.info(f"Registering MCP server '{server_name}' at {server_url}")
    
    # Define server capabilities
    capabilities = [
        "resources.config",
        "resources.hardware",
        "tools.processing",
        "tools.analysis"
    ]
    
    try:
        # Register the MCP server with Nexus
        registration = await nexus_integration.register_mcp_server(
            server_url=server_url,
            server_name=server_name,
            capabilities=capabilities
        )
        
        logger.info(f"MCP server registered with Nexus: {registration['server_id']}")
        
        # Send notification about successful registration
        await nexus_integration.send_notification(
            message=f"MCP server {registration['server_id']} connected successfully",
            message_type="info"
        )
        
        # Fetch system context from Nexus
        system_context = await nexus_integration.fetch_nexus_context("system")
        logger.info(f"Nexus system status: {system_context.get('status', 'unknown')}")
        
        if system_context.get("simulated", False):
            logger.warning("Using simulated Nexus context (Nexus API not available)")
        
        return registration
    
    except Exception as e:
        logger.error(f"Error connecting to Nexus: {str(e)}")
        # Send notification about failed registration
        try:
            await nexus_integration.send_notification(
                message=f"MCP server connection failed: {str(e)}",
                message_type="error"
            )
        except Exception:
            pass
        return None

async def main_async():
    """Asynchronous main function."""
    args = parse_arguments()
    
    # Connect to Nexus
    registration = await connect_to_nexus(
        server_url=args.server_url,
        nexus_url=args.nexus_url,
        server_name=args.server_name
    )
    
    if registration:
        logger.info("Nexus MCP connection successful")
        return 0
    else:
        logger.error("Nexus MCP connection failed")
        return 1

def main():
    """Main entry point for connecting the MCP server to Nexus."""
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Connection process interrupted")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error in connection process: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
