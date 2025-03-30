"""
Configuration module for the Nexus MCP server.
Provides platform-specific configurations and paths.
"""

import os
import platform
import logging

logger = logging.getLogger("nexus_mcp.config")

# Determine platform and set base directories accordingly
SYSTEM = platform.system()
if SYSTEM == "Windows":
    # Windows-specific paths
    BASE_DIR = os.path.join("C:", os.path.sep, "Users", "Chris Boyd", "nexus_mcp_project")
else:
    # Linux/macOS paths
    BASE_DIR = os.path.join("/", "home", "ubuntu", "nexus_mcp_project")

# Ensure configuration is logged
logger.info(f"Platform detected: {SYSTEM}")
logger.info(f"Base directory: {BASE_DIR}")

# Derived directories
LOGS_DIR = os.path.join(BASE_DIR, "logs")
DATA_DIR = os.path.join(BASE_DIR, "data")
SRC_DIR = os.path.join(BASE_DIR, "src")

# Ensure directories exist
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

# File paths
REGISTRATION_FILE = os.path.join(DATA_DIR, "mcp_registration.json")
NOTIFICATION_LOG = os.path.join(LOGS_DIR, "mcp_notifications.log")
HARDWARE_CONFIG = os.path.join(BASE_DIR, "hardware_config.json")
TEST_RESULTS = os.path.join(DATA_DIR, "test_results.json")
RESOURCE_TEST_RESULTS = os.path.join(DATA_DIR, "resource_test_results.json")
TOOL_TEST_RESULTS = os.path.join(DATA_DIR, "tool_test_results.json")

# Server configuration
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8000"))
MCP_DEBUG = os.environ.get("MCP_DEBUG", "false").lower() == "true"
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8000")

# Nexus configuration
NEXUS_API_URL = os.environ.get("NEXUS_API_URL", "http://localhost:5000/api/v1")
NEXUS_API_KEY = os.environ.get("NEXUS_API_KEY", "")

# Log configuration settings
logger.info(f"Logs directory: {LOGS_DIR}")
logger.info(f"Data directory: {DATA_DIR}")
logger.info(f"MCP server URL: {MCP_SERVER_URL}")
logger.info(f"Nexus API URL: {NEXUS_API_URL}")
