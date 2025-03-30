"""
Base data models for the Nexus MCP server.
These models provide type safety and validation using Pydantic.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union


class ResourceRequest(BaseModel):
    """Model for resource request parameters"""
    resource_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolRequest(BaseModel):
    """Model for tool execution request"""
    tool_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class NexusUser(BaseModel):
    """Model for Nexus user data"""
    user_id: str
    username: str
    email: Optional[str] = None
    preferences: Dict[str, Any] = Field(default_factory=dict)


class NexusResource(BaseModel):
    """Base model for Nexus resources"""
    resource_id: str
    content: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)
    mime_type: str = "text/plain"


class NexusTextResource(NexusResource):
    """Model for text-based Nexus resources"""
    content: str
    mime_type: str = "text/plain"


class NexusJsonResource(NexusResource):
    """Model for JSON-based Nexus resources"""
    content: Dict[str, Any]
    mime_type: str = "application/json"


class NexusToolResult(BaseModel):
    """Model for tool execution results"""
    success: bool
    result: Any
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NexusPrompt(BaseModel):
    """Model for Nexus prompts"""
    prompt_id: str
    template: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None
