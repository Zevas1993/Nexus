"""
Tool implementations for the Nexus MCP server.
"""

def register_tools(mcp_server):
    """Register all tool handlers with the MCP server."""
    # Import tool modules
    from nexus_mcp.tools.processing import register_processing_tools
    
    # Register all tool handlers
    register_processing_tools(mcp_server)
    
    return mcp_server
