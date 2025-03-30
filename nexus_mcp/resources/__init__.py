"""
Resource implementations for the Nexus MCP server.
"""

def register_resources(mcp_server):
    """Register all resource handlers with the MCP server."""
    # Import resource modules
    from nexus_mcp.resources.config import register_config_resources
    
    # Register all resource handlers
    register_config_resources(mcp_server)
    
    return mcp_server
