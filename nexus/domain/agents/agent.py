"""
Agent implementation for Nexus AI based on OpenAI's Agents SDK.

This module provides the core agent functionality, allowing for autonomous task execution
with defined tools, guardrails, and handoff capabilities.
"""
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable, Union, Set, Tuple

logger = logging.getLogger(__name__)

class Agent:
    """Base agent class for AI-driven task execution.
    
    Agents are AI models equipped with specific instructions and tools,
    enabling them to execute tasks effectively and autonomously.
    """
    
    def __init__(self, 
                 name: str, 
                 model: str,
                 instructions: str,
                 config: Optional[Dict[str, Any]] = None):
        """Initialize an agent.
        
        Args:
            name: Agent name
            model: The underlying AI model (e.g., "gpt-4o")
            instructions: Operational instructions for the agent
            config: Additional configuration options
        """
        self.name = name
        self.model = model
        self.instructions = instructions
        self.config = config or {}
        self.tools = []
        self.guardrails = []
        self._observations = []
        self._observers = set()
        
        logger.info(f"Agent '{name}' initialized with model: {model}")
        
    def add_tool(self, tool):
        """Add a tool to the agent.
        
        Args:
            tool: Tool object to add
        """
        self.tools.append(tool)
        logger.info(f"Tool '{tool.name}' added to agent '{self.name}'")
        
    def add_guardrail(self, guardrail):
        """Add a guardrail to the agent.
        
        Args:
            guardrail: Guardrail object to add
        """
        self.guardrails.append(guardrail)
        logger.info(f"Guardrail '{guardrail.name}' added to agent '{self.name}'")
        
    def register_observer(self, observer: Callable):
        """Register an observation callback.
        
        Args:
            observer: Callback function for observations
        """
        self._observers.add(observer)
        
    def unregister_observer(self, observer: Callable):
        """Unregister an observation callback.
        
        Args:
            observer: Callback function to remove
        """
        if observer in self._observers:
            self._observers.remove(observer)
            
    def _record_observation(self, observation: Dict[str, Any]):
        """Record an observation during agent execution.
        
        Args:
            observation: Observation data
        """
        self._observations.append(observation)
        
        # Notify observers
        for observer in self._observers:
            try:
                observer(observation)
            except Exception as e:
                logger.warning(f"Error in observer: {str(e)}")
    
    def _apply_guardrails(self, input_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Apply all guardrails to input data.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        for guardrail in self.guardrails:
            is_valid, error = guardrail.validate(input_data)
            if not is_valid:
                return False, error
                
        return True, None
        
    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a task using the agent's capabilities.
        
        Args:
            task: Task description
            context: Additional context for execution
            
        Returns:
            Execution result
        """
        context = context or {}
        exec_id = context.get('execution_id', id(task))
        
        # Start execution trace
        start_trace = {
            "type": "execution_start",
            "agent": self.name,
            "task": task,
            "execution_id": exec_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        self._record_observation(start_trace)
        
        # Apply guardrails to context
        is_valid, error = self._apply_guardrails(context)
        if not is_valid:
            error_trace = {
                "type": "guardrail_error",
                "agent": self.name,
                "execution_id": exec_id,
                "error": error,
                "timestamp": asyncio.get_event_loop().time()
            }
            self._record_observation(error_trace)
            
            return {
                "status": "error",
                "error": f"Guardrail validation failed: {error}",
                "execution_id": exec_id
            }
            
        # Prepare available tools
        available_tools = [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self.tools
        ]
        
        # Prepare execution input
        exec_input = {
            "model": self.model,
            "instructions": self.instructions,
            "tools": available_tools,
            "task": task,
            "context": context
        }
        
        try:
            # In a real implementation, this would call the OpenAI API
            # For now, we'll simulate the execution
            result = await self._simulate_execution(exec_input)
            
            # Record completion
            complete_trace = {
                "type": "execution_complete",
                "agent": self.name,
                "execution_id": exec_id,
                "result": result,
                "timestamp": asyncio.get_event_loop().time()
            }
            self._record_observation(complete_trace)
            
            return {
                "status": "success",
                "result": result,
                "execution_id": exec_id
            }
        except Exception as e:
            logger.error(f"Error executing task: {str(e)}")
            
            # Record error
            error_trace = {
                "type": "execution_error",
                "agent": self.name,
                "execution_id": exec_id,
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
            self._record_observation(error_trace)
            
            return {
                "status": "error",
                "error": str(e),
                "execution_id": exec_id
            }
    
    async def _simulate_execution(self, exec_input: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate execution for development/testing.
        
        In a production environment, this would be replaced with actual calls
        to the OpenAI API or other AI models.
        
        Args:
            exec_input: Execution input
            
        Returns:
            Execution result
        """
        # For now, return a simulated response based on the task
        task = exec_input["task"]
        
        # Simulate tool usage if appropriate
        for tool in self.tools:
            if tool.name.lower() in task.lower():
                tool_call_trace = {
                    "type": "tool_call",
                    "agent": self.name,
                    "tool": tool.name,
                    "input": task,
                    "timestamp": asyncio.get_event_loop().time()
                }
                self._record_observation(tool_call_trace)
                
                # Call the tool
                tool_result = await tool.execute(task, exec_input["context"])
                
                tool_result_trace = {
                    "type": "tool_result",
                    "agent": self.name,
                    "tool": tool.name,
                    "result": tool_result,
                    "timestamp": asyncio.get_event_loop().time()
                }
                self._record_observation(tool_result_trace)
                
                return {
                    "content": f"I used the {tool.name} tool and found: {tool_result['content']}",
                    "tool_used": tool.name,
                    "tool_result": tool_result
                }
        
        # Default response if no specific tools were used
        return {
            "content": f"I've processed your request: '{task}'. Here is my response based on my instructions."
        }
            
    async def handoff(self, task: str, agent_name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Hand off a task to another agent.
        
        Args:
            task: Task description
            agent_name: Name of agent to hand off to
            context: Additional context for handoff
            
        Returns:
            Handoff result
        """
        context = context or {}
        handoff_id = context.get('handoff_id', id(task))
        
        # Record handoff attempt
        handoff_trace = {
            "type": "handoff_attempt",
            "from_agent": self.name,
            "to_agent": agent_name,
            "task": task,
            "handoff_id": handoff_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        self._record_observation(handoff_trace)
        
        # In a real implementation, this would call the agent registry
        # to get and execute the target agent
        # For now, just return a placeholder
        return {
            "status": "success",
            "message": f"Task '{task}' handed off to agent '{agent_name}'",
            "handoff_id": handoff_id
        }

    def get_observations(self) -> List[Dict[str, Any]]:
        """Get all recorded observations.
        
        Returns:
            List of observations
        """
        return self._observations.copy()
