"""
Agent service for Nexus AI.

This module provides a service interface for creating, managing, and
executing agents within the Nexus AI system, including LLM-based routing.
"""
import logging
import asyncio
import json
import os
from typing import Dict, Any, List, Optional, Union, Set

# Assuming Agent, Tool, Guardrail, and LanguageModelService are accessible
# Adjust imports as necessary
from .agent import Agent
from .tools import Tool, WebSearchTool, FileSearchTool, ComputerUseTool
from .guardrails import (
    Guardrail, ContentFilterGuardrail, DataValidationGuardrail,
    RateLimitGuardrail # CompositeGuardrail might be useful later
)
# from ..language.language_model_service import LanguageModelService

logger = logging.getLogger(__name__)

# Define a default agent name for fallback
DEFAULT_AGENT_NAME = "general_agent"

class AgentService:
    """Service for managing and executing AI agents, including routing."""

    def __init__(self, app_context, config=None): # Added app_context
        """Initialize agent service.

        Args:
            app_context: The application context to access other services.
            config: Configuration dictionary
        """
        self.app_context = app_context
        self.config = config or {}
        self.agents: Dict[str, Agent] = {}
        self.tools: Dict[str, Tool] = {}
        self.guardrails: Dict[str, Guardrail] = {}
        self.language_model = None # For routing

        self._initialize_language_model() # Initialize LM dependency
        self._initialize_default_tools()
        self._initialize_default_guardrails()
        self._initialize_default_agents() # Initialize default agents explicitly

        logger.info("Agent service initialized")

    def _initialize_language_model(self):
        """Fetch the language model service from app context."""
        try:
            from ..language.language_model_service import LanguageModelService
            self.language_model = self.app_context.get_service(LanguageModelService)
            if not self.language_model:
                raise ValueError("LanguageModelService not found in app context for AgentService.")
            logger.info("LanguageModelService obtained for AgentService routing.")
        except (ImportError, ValueError, AttributeError) as e:
            logger.error(f"AgentService failed to obtain LanguageModelService: {e}", exc_info=getattr(self.app_context, 'debug', False))
            self.language_model = None

    def _initialize_default_tools(self):
        """Initialize and register default tools."""
        # Web search tool
        try:
            web_search = WebSearchTool(self.config)
            self.register_tool(web_search)
        except Exception as e:
            logger.error(f"Failed to initialize WebSearchTool: {e}", exc_info=getattr(self.app_context, 'debug', False))

        # File search tool
        try:
            file_search = FileSearchTool(self.config)
            self.register_tool(file_search)
        except Exception as e:
            logger.error(f"Failed to initialize FileSearchTool: {e}", exc_info=getattr(self.app_context, 'debug', False))

        # Computer use tool (with secure defaults)
        try:
            computer_use_config = self.config.copy()
            # Consider making allowed/blocked commands more configurable
            computer_use_config.update({
                "COMMAND_SANDBOX_ENABLED": True,
                "ALLOWED_COMMANDS": ["ls", "dir", "echo", "type", "cat", "head", "tail", "pwd"], # Expanded safe commands
                "BLOCKED_COMMANDS": ["rm", "del", "format", "shutdown", "reboot", "mv", "cp", "sudo", "apt", "yum", "choco"] # Expanded dangerous commands
            })
            computer_use = ComputerUseTool(computer_use_config)
            self.register_tool(computer_use)
        except Exception as e:
            logger.error(f"Failed to initialize ComputerUseTool: {e}", exc_info=getattr(self.app_context, 'debug', False))

    def _initialize_default_guardrails(self):
        """Initialize and register default guardrails."""
        try:
            content_filter = ContentFilterGuardrail(self.config)
            self.register_guardrail(content_filter)
        except Exception as e:
            logger.error(f"Failed to initialize ContentFilterGuardrail: {e}", exc_info=getattr(self.app_context, 'debug', False))

        try:
            # Example rate limit: 10 requests per minute per user_id (if user_id is in context)
            # This needs a proper implementation (e.g., using Redis or in-memory store)
            rate_limit = RateLimitGuardrail({"default_limit": "10/minute"}, self.config)
            self.register_guardrail(rate_limit)
        except Exception as e:
            logger.error(f"Failed to initialize RateLimitGuardrail: {e}", exc_info=getattr(self.app_context, 'debug', False))

    def _initialize_default_agents(self):
        """Initialize and register default agents."""
        # Ensure app_context is passed
        default_model = self.config.get("DEFAULT_AGENT_MODEL", "gpt-4o") # Use a configurable default

        # General Agent (Fallback)
        self.create_agent(
            name=DEFAULT_AGENT_NAME,
            model=default_model,
            instructions="You are a helpful general-purpose assistant. Use available tools if necessary to answer the user's request.",
            # Give it access to common tools
            tools=[tool_name for tool_name in ["web_search", "file_search"] if tool_name in self.tools]
        )

        # Search Agent
        if "web_search" in self.tools:
            self.create_agent(
                name="search_agent",
                model=default_model,
                instructions="You are a specialized web search assistant. Your primary goal is to use the web_search tool to find information online based on the user's query.",
                tools=["web_search"]
            )

        # File Agent
        if "file_search" in self.tools:
             self.create_agent(
                name="file_agent",
                model=default_model,
                instructions="You are a specialized file management assistant. Your primary goal is to use the file_search tool to find and retrieve information from local files based on the user's query.",
                tools=["file_search"]
            )

        # Computer Agent
        if "computer_use" in self.tools:
            self.create_agent(
                name="computer_agent",
                model=default_model,
                instructions="You are a specialized assistant for interacting with the computer system. Use the computer_use tool to execute safe, allowed commands based on the user's request. Be cautious and prioritize safety.",
                tools=["computer_use"]
            )
        # Add more pre-defined agents as needed

    def register_tool(self, tool: Tool):
        """Register a tool if it has a name."""
        tool_name = getattr(tool, 'name', None)
        if tool_name:
            self.tools[tool_name] = tool
            logger.info(f"Tool '{tool_name}' registered")
        else:
            logger.warning("Attempted to register a tool without a name.")

    def register_guardrail(self, guardrail: Guardrail):
        """Register a guardrail if it has a name."""
        guardrail_name = getattr(guardrail, 'name', None)
        if guardrail_name:
            self.guardrails[guardrail_name] = guardrail
            logger.info(f"Guardrail '{guardrail_name}' registered")
        else:
             logger.warning("Attempted to register a guardrail without a name.")

    def create_agent(self, name: str, model: str, instructions: str,
                    tools: Optional[List[str]] = None,
                    guardrails: Optional[List[str]] = None,
                    config: Optional[Dict[str, Any]] = None) -> Optional[Agent]:
        """Create and register a new agent."""
        if name in self.agents:
            logger.warning(f"Agent '{name}' already exists. Skipping creation.")
            return self.agents[name]

        agent_config = self.config.copy()
        if config:
            agent_config.update(config)

        try:
            # Pass app_context to the Agent constructor
            agent = Agent(self.app_context, name, model, instructions, agent_config)

            # Add tools
            if tools:
                for tool_name in tools:
                    if tool_name in self.tools:
                        agent.add_tool(self.tools[tool_name])
                    else:
                        logger.warning(f"Tool '{tool_name}' not found during agent '{name}' creation.")

            # Add guardrails
            if guardrails:
                for guardrail_name in guardrails:
                    if guardrail_name in self.guardrails:
                        agent.add_guardrail(self.guardrails[guardrail_name])
                    else:
                        logger.warning(f"Guardrail '{guardrail_name}' not found during agent '{name}' creation.")

            self.agents[name] = agent
            logger.info(f"Agent '{name}' created with model {model}")
            return agent
        except Exception as e:
             logger.error(f"Failed to create agent '{name}': {e}", exc_info=getattr(self.app_context, 'debug', False))
             return None

    def get_agent(self, name: str) -> Optional[Agent]:
        """Get a registered agent by name."""
        return self.agents.get(name)

    async def execute_agent(self, agent_name: str, task: str,
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a task using a specific agent."""
        agent = self.get_agent(agent_name)
        if not agent:
            logger.error(f"Cannot execute: Agent '{agent_name}' not found.")
            return {
                "status": "error",
                "error": f"Agent '{agent_name}' not found"
            }

        logger.info(f"Executing agent '{agent_name}' for task: {task[:100]}...") # Log truncated task
        try:
            # The agent.execute method now returns the final result structure
            return await agent.execute(task, context)
        except Exception as e:
             logger.error(f"Error during agent '{agent_name}' execution: {e}", exc_info=getattr(self.app_context, 'debug', False))
             return {
                "status": "error",
                "error": f"Agent execution failed: {str(e)}",
                "execution_id": context.get('execution_id', 'unknown') if context else 'unknown'
             }

    def _format_agents_for_routing_prompt(self) -> str:
        """Formats available agents for the routing prompt."""
        if not self.agents:
            return "No agents available."
        descriptions = []
        for name, agent in self.agents.items():
            # Use agent instructions as a description of its purpose
            descriptions.append(f"- Name: {name}\n  Purpose: {agent.instructions}")
        return "Available Agents:\n" + "\n".join(descriptions)

    async def _determine_target_agent(self, request: str) -> str:
        """Use LLM to determine the best agent for the request."""
        if not self.language_model:
            logger.warning("LLM routing disabled: LanguageModelService not available. Falling back to default agent.")
            return DEFAULT_AGENT_NAME
        if not self.agents:
             logger.warning("LLM routing disabled: No agents registered. Falling back to default agent name (which might not exist).")
             return DEFAULT_AGENT_NAME

        agent_info = self._format_agents_for_routing_prompt()

        prompt = f"""You are an expert request router. Based on the user's request and the available agents, determine the single most appropriate agent to handle the request.

{agent_info}

User Request: "{request}"

Respond ONLY with the name of the chosen agent (e.g., "search_agent", "{DEFAULT_AGENT_NAME}"). Do not add any other text or explanation.

Chosen Agent Name:"""

        try:
            logger.debug(f"Routing request: {request[:100]}...")
            # Use a potentially faster/cheaper model for routing if configured
            routing_model = self.config.get("ROUTING_MODEL", self.config.get("DEFAULT_AGENT_MODEL", "gpt-4o"))
            llm_response = await self.language_model.process(prompt, model=routing_model)
            chosen_agent_name = llm_response.get("text", "").strip()

            # Basic validation: check if the chosen name is among registered agents
            if chosen_agent_name in self.agents:
                logger.info(f"LLM routed request to agent: '{chosen_agent_name}'")
                return chosen_agent_name
            else:
                logger.warning(f"LLM chose an invalid agent name: '{chosen_agent_name}'. Falling back to default.")
                return DEFAULT_AGENT_NAME

        except Exception as e:
            logger.error(f"Error during LLM routing: {e}. Falling back to default agent.", exc_info=getattr(self.app_context, 'debug', False))
            return DEFAULT_AGENT_NAME


    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request by routing it to the most appropriate agent."""
        agent_name_override = kwargs.get('agent_name')
        context = kwargs.get('context', {})
        exec_id = context.get('execution_id', f"process-{id(request)}")
        context['execution_id'] = exec_id # Ensure exec_id is in context

        final_agent_name = None

        if agent_name_override:
            if agent_name_override in self.agents:
                logger.info(f"Using specified agent override: '{agent_name_override}'")
                final_agent_name = agent_name_override
            else:
                logger.warning(f"Specified agent override '{agent_name_override}' not found. Attempting LLM routing.")
                # Fall through to LLM routing

        if not final_agent_name:
            # Determine target agent using LLM
            final_agent_name = await self._determine_target_agent(request)

        # Ensure the chosen agent actually exists, fallback again if necessary
        if final_agent_name not in self.agents:
             logger.error(f"Target agent '{final_agent_name}' not found after routing/fallback. Cannot process request.")
             return {
                 "status": "error",
                 "text": f"Error: Could not find a suitable agent ('{final_agent_name}') to handle the request.",
                 "agent": None,
                 "execution_id": exec_id
             }

        # Execute the chosen agent
        agent_result = await self.execute_agent(final_agent_name, request, context)

        # Format the final response structure expected by the caller
        return {
            "status": agent_result.get("status", "error"),
            # Extract final content from agent's result structure
            "text": agent_result.get("result", {}).get("content", "Agent execution finished, but no content was returned."),
            "agent": final_agent_name,
            "details": agent_result, # Include the full agent result for debugging/logging
            "execution_id": exec_id
        }

    # Handoff logic might be better placed in an orchestrator or managed within the Agent loop itself
    # Keeping the placeholder here for now, but it needs rethinking.
    async def handoff_between_agents(self, from_agent: str, to_agent: str,
                                   task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Hand off a task between agents (Placeholder - Requires Orchestration)."""
        logger.warning("Handoff functionality is currently a placeholder and needs orchestration logic.")
        # This should likely trigger the 'process' method again with the target agent specified.
        context = context or {}
        context['agent_name'] = to_agent # Specify target agent for next process call
        context['original_task'] = context.get('original_task', task) # Preserve original task if needed
        context['handoff_from'] = from_agent

        # Simulate returning a structure indicating handoff occurred
        return {
            "status": "handoff_initiated",
            "message": f"Task handoff from '{from_agent}' to '{to_agent}' initiated.",
            "next_agent": to_agent,
            "task": task, # Task for the next agent
            "context": context
        }

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get information about all registered agents."""
        return [
            {
                "name": name,
                "model": agent.model,
                "instructions": agent.instructions,
                "tools": [getattr(tool, 'name', 'Unnamed') for tool in agent.tools],
                "guardrails": [getattr(gr, 'name', 'Unnamed') for gr in agent.guardrails]
            } for name, agent in self.agents.items()
        ]

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get information about all registered tools."""
        return [
            {
                "name": name,
                "description": getattr(tool, 'description', 'No description'),
                "parameters": getattr(tool, 'parameters', {})
            } for name, tool in self.tools.items()
        ]

    def get_all_guardrails(self) -> List[Dict[str, Any]]:
        """Get information about all registered guardrails."""
        return [
            {
                "name": name,
                "description": getattr(guardrail, 'description', 'No description')
            } for name, guardrail in self.guardrails.items()
        ]
