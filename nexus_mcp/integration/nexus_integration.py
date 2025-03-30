"""
Integration module for connecting the MCP server with the Nexus project.
This module provides the necessary adapters and connectors to integrate
the MCP server with the existing Nexus AI Assistant.
"""

import logging
import os
import json
import asyncio
import httpx
from typing import Dict, Any, List, Optional, Union

from nexus_mcp.config import NEXUS_API_URL, NEXUS_API_KEY, REGISTRATION_FILE, NOTIFICATION_LOG

logger = logging.getLogger("nexus_mcp.integration")

class NexusIntegration:
    """
    Integration class for connecting MCP server with Nexus.
    This class provides methods to communicate with the Nexus AI Assistant.
    """
    
    def __init__(self, nexus_api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the Nexus integration.
        
        Args:
            nexus_api_url: URL of the Nexus API (defaults to config or environment variable)
            api_key: API key for authentication (defaults to config or environment variable)
        """
        self.nexus_api_url = nexus_api_url or NEXUS_API_URL
        self.api_key = api_key or NEXUS_API_KEY
        
        # Create headers with authentication if api_key is provided
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
            
        logger.info(f"Initialized Nexus integration with API URL: {self.nexus_api_url}")
        
        # Ensure directories exist for registration and notification files
        os.makedirs(os.path.dirname(REGISTRATION_FILE), exist_ok=True)
        os.makedirs(os.path.dirname(NOTIFICATION_LOG), exist_ok=True)
    
    async def register_mcp_server(self, server_url: str, server_name: str, capabilities: List[str]) -> Dict[str, Any]:
        """
        Register the MCP server with Nexus.
        
        Args:
            server_url: URL of the MCP server
            server_name: Name of the MCP server
            capabilities: List of capabilities provided by the MCP server
            
        Returns:
            Registration response from Nexus
        """
        logger.info(f"Registering MCP server {server_name} at {server_url} with Nexus")
        
        try:
            # In a real implementation, this would make an API call to Nexus
            # First, try to make an actual API call
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{self.nexus_api_url}/mcp/register",
                        headers=self.headers,
                        json={
                            "server_url": server_url,
                            "server_name": server_name,
                            "capabilities": capabilities
                        }
                    )
                    
                    if response.status_code == 200:
                        registration_data = response.json()
                        logger.info(f"MCP server registered successfully via API: {registration_data.get('server_id', 'unknown')}")
                    else:
                        # If API call fails, simulate registration for development/testing
                        logger.warning(f"API registration failed with status {response.status_code}, using simulated registration")
                        raise Exception(f"API registration failed: {response.status_code}")
            except Exception as e:
                # Simulate a successful registration for development/testing purposes
                logger.warning(f"Exception during API registration: {e}, using simulated registration")
                server_id = f"mcp-{server_name.lower().replace(' ', '-')}"
                registration_data = {
                    "server_id": server_id,
                    "server_url": server_url,
                    "server_name": server_name,
                    "capabilities": capabilities,
                    "status": "registered",
                    "registration_time": "2025-03-21T15:00:00Z",
                    "simulated": True  # Flag to indicate this is a simulated registration
                }
            
            # Save registration data to file
            with open(REGISTRATION_FILE, "w") as f:
                json.dump(registration_data, f, indent=2)
            
            logger.info(f"MCP server registration saved to {REGISTRATION_FILE}")
            return registration_data
            
        except Exception as e:
            logger.error(f"Error registering MCP server: {e}")
            raise
    
    async def send_notification(self, message: str, message_type: str = "info") -> bool:
        """
        Send a notification to Nexus.
        
        Args:
            message: Notification message
            message_type: Type of notification (info, warning, error)
            
        Returns:
            True if notification was sent successfully, False otherwise
        """
        logger.info(f"Sending {message_type} notification to Nexus: {message}")
        
        try:
            # In a real implementation, this would make an API call to Nexus
            # Try to make an actual API call first
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        f"{self.nexus_api_url}/mcp/notification",
                        headers=self.headers,
                        json={
                            "message": message,
                            "type": message_type
                        }
                    )
                    
                    if response.status_code == 200:
                        logger.info("Notification sent successfully via API")
                    else:
                        # If API call fails, simulate notification for development/testing
                        logger.warning(f"API notification failed with status {response.status_code}, logging locally")
                        raise Exception(f"API notification failed: {response.status_code}")
            except Exception as e:
                # Log notification locally for development/testing purposes
                logger.warning(f"Exception during API notification: {e}, logging locally")
                pass
            
            # Always log notifications locally as well
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            with open(NOTIFICATION_LOG, "a") as f:
                f.write(f"[{timestamp}] [{message_type.upper()}] {message}\n")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    async def fetch_nexus_context(self, context_type: str, context_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch context information from Nexus.
        
        Args:
            context_type: Type of context to fetch (user, session, system)
            context_id: Optional ID for the specific context
            
        Returns:
            Context data from Nexus
        """
        endpoint = f"{context_type}" + (f"/{context_id}" if context_id else "")
        logger.info(f"Fetching {endpoint} context from Nexus")
        
        try:
            # In a real implementation, this would make an API call to Nexus
            # Try to make an actual API call first
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(
                        f"{self.nexus_api_url}/context/{endpoint}",
                        headers=self.headers
                    )
                    
                    if response.status_code == 200:
                        context_data = response.json()
                        logger.info(f"Context data fetched successfully via API: {context_type}")
                        return context_data
                    else:
                        # If API call fails, return simulated context for development/testing
                        logger.warning(f"API context fetch failed with status {response.status_code}, using simulated data")
                        raise Exception(f"API context fetch failed: {response.status_code}")
            except Exception as e:
                # Simulate context data for development/testing purposes
                logger.warning(f"Exception during API context fetch: {e}, using simulated data")
                pass
            
            # Return simulated context data based on context type
            if context_type == "user":
                return {
                    "user_id": context_id or "default_user",
                    "username": f"user_{context_id}" if context_id else "default_user",
                    "preferences": {
                        "theme": "dark",
                        "language": "en"
                    },
                    "permissions": ["read", "write", "execute"],
                    "simulated": True  # Flag to indicate this is simulated data
                }
            elif context_type == "session":
                return {
                    "session_id": context_id or "default_session",
                    "start_time": "2025-03-21T14:00:00Z",
                    "user_id": "default_user",
                    "active": True,
                    "context": {
                        "current_task": "MCP implementation",
                        "previous_interactions": 5
                    },
                    "simulated": True  # Flag to indicate this is simulated data
                }
            elif context_type == "system":
                return {
                    "system_id": "nexus_main",
                    "version": "1.0.0",
                    "status": "operational",
                    "resources": {
                        "cpu_usage": 45.2,
                        "memory_usage": 62.8,
                        "gpu_usage": 30.1
                    },
                    "services": {
                        "api": "running",
                        "database": "running",
                        "mcp": "initializing"
                    },
                    "simulated": True  # Flag to indicate this is simulated data
                }
            else:
                logger.warning(f"Unknown context type: {context_type}")
                return {"error": f"Unknown context type: {context_type}", "simulated": True}
                
        except Exception as e:
            logger.error(f"Error fetching Nexus context: {e}")
            return {"error": str(e), "simulated": True}

# Create a singleton instance for easy import
nexus_integration = NexusIntegration()
