"""
Agent service for Nexus AI based on OpenAI's Agents SDK.

This module provides a service interface for creating, managing, and
executing agents within the Nexus AI system.
"""
import logging
import asyncio
import json
import os
from typing import Dict, Any, List, Optional, Union, Set

from .agent import Agent
from .tools import Tool, WebSearchTool, FileSearchTool, ComputerUseTool
from .guardrails import (
    Guardrail, ContentFilterGuardrail, DataValidationGuardrail,
    RateLimitGuardrail, CompositeGuardrail
)

logger = logging.getLogger(__name__)

class AgentService:
    """Service for managing and executing AI agents."""
    
    def __init__(self, config=None):
        """Initialize agent service.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.agents: Dict[str, Agent] = {}
        self.tools: Dict[str, Tool] = {}
        self.guardrails: Dict[str, Guardrail] = {}
        self._initialize_default_tools()
        self._initialize_default_guardrails()
        logger.info("Agent service initialized")
        
    def _initialize_default_tools(self):
        """Initialize default tools."""
        # Web search tool
        web_search = WebSearchTool(self.config)
        self.register_tool(web_search)
        
        # File search tool
        file_search = FileSearchTool(self.config)
        self.register_tool(file_search)
        
        # Computer use tool (with secure defaults)
        computer_use_config = self.config.copy()
        computer_use_config.update({
            "COMMAND_SANDBOX_ENABLED": True,
            "ALLOWED_COMMANDS": ["ls", "dir", "echo", "type"],
            "BLOCKED_COMMANDS": ["rm", "del", "format", "shutdown", "reboot"]
        })
        computer_use = ComputerUseTool(computer_use_config)
        self.register_tool(computer_use)
        
    def _initialize_default_guardrails(self):
        """Initialize default guardrails."""
        # Content filter
        content_filter = ContentFilterGuardrail(self.config)
        self.register_guardrail(content_filter)
        
        # Rate limit (10 requests per minute per user)
        rate_limit = RateLimitGuardrail({"user_id": 10}, self.config)
        self.register_guardrail(rate_limit)
        
    def register_tool(self, tool: Tool):
        """Register a tool.
        
        Args:
            tool: Tool to register
        """
        self.tools[tool.name] = tool
        logger.info(f"Tool '{tool.name}' registered")
        
    def register_guardrail(self, guardrail: Guardrail):
        """Register a guardrail.
        
        Args:
            guardrail: Guardrail to register
        """
        self.guardrails[guardrail.name] = guardrail
        logger.info(f"Guardrail '{guardrail.name}' registered")
        
    def create_agent(self, name: str, model: str, instructions: str, 
                    tools: Optional[List[str]] = None,
                    guardrails: Optional[List[str]] = None,
                    config: Optional[Dict[str, Any]] = None) -> Agent:
        """Create a new agent.
        
        Args:
            name: Agent name
            model: Model to use (e.g., "gpt-4o")
            instructions: Agent instructions
            tools: List of tool names to add to the agent
            guardrails: List of guardrail names to add to the agent
            config: Additional configuration
            
        Returns:
            The created agent
        """
        # Create agent
        agent_config = self.config.copy()
        if config:
            agent_config.update(config)
            
        agent = Agent(name, model, instructions, agent_config)
        
        # Add tools
        if tools:
            for tool_name in tools:
                if tool_name in self.tools:
                    agent.add_tool(self.tools[tool_name])
                else:
                    logger.warning(f"Tool '{tool_name}' not found")
        
        # Add guardrails
        if guardrails:
            for guardrail_name in guardrails:
                if guardrail_name in self.guardrails:
                    agent.add_guardrail(self.guardrails[guardrail_name])
                else:
                    logger.warning(f"Guardrail '{guardrail_name}' not found")
        
        # Register agent
        self.agents[name] = agent
        logger.info(f"Agent '{name}' created with model {model}")
        
        return agent
    
    def get_agent(self, name: str) -> Optional[Agent]:
        """Get an agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            Agent or None if not found
        """
        return self.agents.get(name)
    
    async def execute_agent(self, agent_name: str, task: str, 
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a task using an agent.
        
        Args:
            agent_name: Agent name
            task: Task description
            context: Additional context
            
        Returns:
            Execution result
        """
        agent = self.get_agent(agent_name)
        if not agent:
            logger.error(f"Agent '{agent_name}' not found")
            return {
                "status": "error",
                "error": f"Agent '{agent_name}' not found"
            }
            
        logger.info(f"Executing agent '{agent_name}' for task: {task}")
        return await agent.execute(task, context)
    
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request using an appropriate agent.
        
        This method integrates with the Nexus service architecture.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
                - agent_name: Specific agent to use
                - context: Additional context
                
        Returns:
            Processing result
        """
        agent_name = kwargs.get('agent_name')
        context = kwargs.get('context', {})
        
        # Use specified agent if provided
        if agent_name:
            if agent_name in self.agents:
                result = await self.execute_agent(agent_name, request, context)
                return {
                    "status": result.get("status", "error"),
                    "text": result.get("result", {}).get("content", "No response generated"),
                    "agent": agent_name,
                    "details": result
                }
            else:
                return {
                    "status": "error",
                    "text": f"Agent '{agent_name}' not found",
                    "agent": None
                }
                
        # If no agent specified, try to find the best agent for the task
        # For now, use a simple heuristic based on keywords
        request_lower = request.lower()
        
        if "search web" in request_lower or "find information" in request_lower:
            # Use a search-oriented agent
            search_agent = self.get_agent("search_agent")
            if not search_agent:
                # Create a search agent if it doesn't exist
                search_agent = self.create_agent(
                    name="search_agent",
                    model="gpt-4o",
                    instructions="You are a helpful search assistant that finds information on the web.",
                    tools=["web_search"]
                )
            
            result = await search_agent.execute(request, context)
            return {
                "status": result.get("status", "error"),
                "text": result.get("result", {}).get("content", "No response generated"),
                "agent": "search_agent",
                "details": result
            }
            
        elif "file" in request_lower or "document" in request_lower:
            # Use a file-oriented agent
            file_agent = self.get_agent("file_agent")
            if not file_agent:
                # Create a file agent if it doesn't exist
                file_agent = self.create_agent(
                    name="file_agent",
                    model="gpt-4o",
                    instructions="You are a helpful assistant that works with files and documents.",
                    tools=["file_search"]
                )
            
            result = await file_agent.execute(request, context)
            return {
                "status": result.get("status", "error"),
                "text": result.get("result", {}).get("content", "No response generated"),
                "agent": "file_agent",
                "details": result
            }
            
        elif "command" in request_lower or "computer" in request_lower or "system" in request_lower:
            # Use a computer-oriented agent
            computer_agent = self.get_agent("computer_agent")
            if not computer_agent:
                # Create a computer agent if it doesn't exist
                computer_agent = self.create_agent(
                    name="computer_agent",
                    model="gpt-4o",
                    instructions="You are a helpful assistant that can execute system commands.",
                    tools=["computer_use"]
                )
            
            result = await computer_agent.execute(request, context)
            return {
                "status": result.get("status", "error"),
                "text": result.get("result", {}).get("content", "No response generated"),
                "agent": "computer_agent",
                "details": result
            }
            
        else:
            # Use a general-purpose agent
            general_agent = self.get_agent("general_agent")
            if not general_agent:
                # Create a general agent if it doesn't exist
                general_agent = self.create_agent(
                    name="general_agent",
                    model="gpt-4o",
                    instructions="You are a helpful assistant that can answer general questions.",
                    tools=["web_search", "file_search"]
                )
            
            result = await general_agent.execute(request, context)
            return {
                "status": result.get("status", "error"),
                "text": result.get("result", {}).get("content", "No response generated"),
                "agent": "general_agent",
                "details": result
            }
            
    async def handoff_between_agents(self, from_agent: str, to_agent: str, 
                                   task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Hand off a task between agents.
        
        Args:
            from_agent: Source agent name
            to_agent: Target agent name
            task: Task description
            context: Additional context
            
        Returns:
            Handoff result
        """
        source_agent = self.get_agent(from_agent)
        if not source_agent:
            logger.error(f"Source agent '{from_agent}' not found")
            return {
                "status": "error",
                "error": f"Source agent '{from_agent}' not found"
            }
            
        target_agent = self.get_agent(to_agent)
        if not target_agent:
            logger.error(f"Target agent '{to_agent}' not found")
            return {
                "status": "error",
                "error": f"Target agent '{to_agent}' not found"
            }
            
        # Record handoff in the context
        context = context or {}
        context['handoff'] = {
            'from_agent': from_agent,
            'to_agent': to_agent,
            'timestamp': asyncio.get_event_loop().time()
        }
        
        # Perform handoff
        handoff_result = await source_agent.handoff(task, to_agent, context)
        
        # Execute target agent
        target_result = await target_agent.execute(task, context)
        
        return {
            "status": "success",
            "handoff_result": handoff_result,
            "execution_result": target_result
        }
        
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get information about all registered agents.
        
        Returns:
            List of agent information
        """
        result = []
        for name, agent in self.agents.items():
            agent_info = {
                "name": name,
                "model": agent.model,
                "tools": [tool.name for tool in agent.tools],
                "guardrails": [guardrail.name for guardrail in agent.guardrails]
            }
            result.append(agent_info)
            
        return result
        
    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get information about all registered tools.
        
        Returns:
            List of tool information
        """
        result = []
        for name, tool in self.tools.items():
            tool_info = {
                "name": name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            result.append(tool_info)
            
        return result
        
    def get_all_guardrails(self) -> List[Dict[str, Any]]:
        """Get information about all registered guardrails.
        
        Returns:
            List of guardrail information
        """
        result = []
        for name, guardrail in self.guardrails.items():
            guardrail_info = {
                "name": name,
                "description": guardrail.description
            }
            result.append(guardrail_info)
            
        return result
