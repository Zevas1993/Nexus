"""
Agent implementation for Nexus AI.

This module provides the core agent functionality, allowing for autonomous task execution
with defined tools, guardrails, and interaction with language models.
"""
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Callable, Union, Set, Tuple

# Assuming LanguageModelService and Tool classes are accessible
# Adjust imports as necessary based on project structure
# from ..language.language_model_service import LanguageModelService
# from .tools import Tool

logger = logging.getLogger(__name__)

# Define a maximum number of steps (LLM calls + Tool calls) per execution
MAX_EXECUTION_STEPS = 10

class Agent:
    """Base agent class for AI-driven task execution.

    Agents are AI models equipped with specific instructions and tools,
    enabling them to execute tasks effectively and autonomously by interacting
    with a language model and available tools.
    """

    def __init__(self,
                 app_context, # Added app_context
                 name: str,
                 model: str,
                 instructions: str,
                 config: Optional[Dict[str, Any]] = None):
        """Initialize an agent.

        Args:
            app_context: The application context to access other services like LanguageModelService.
            name: Agent name
            model: The underlying AI model (e.g., "gpt-4o") - This might be used by the LanguageModelService.
            instructions: Operational instructions for the agent.
            config: Additional configuration options.
        """
        self.app_context = app_context
        self.name = name
        self.model = model # Store preferred model
        self.instructions = instructions
        self.config = config or {}
        self.tools: List[Any] = [] # Assuming Tool has name, description, parameters, execute
        self.guardrails: List[Any] = [] # Assuming Guardrail has name, description, validate
        self._observations: List[Dict[str, Any]] = []
        self._observers: Set[Callable] = set()
        self.language_model = None # Will be fetched from app_context

        logger.info(f"Agent '{name}' initialized with model preference: {model}")
        self._initialize_language_model() # Initialize LM dependency

    def _initialize_language_model(self):
        """Fetch the language model service from app context."""
        try:
            # Dynamically import to avoid circular dependencies if necessary
            from ..language.language_model_service import LanguageModelService
            self.language_model = self.app_context.get_service(LanguageModelService)
            if not self.language_model:
                raise ValueError("LanguageModelService not found in app context for Agent.")
            logger.info(f"LanguageModelService obtained for Agent '{self.name}'.")
        except (ImportError, ValueError, AttributeError) as e:
            logger.error(f"Agent '{self.name}' failed to obtain LanguageModelService: {e}", exc_info=getattr(self.app_context, 'debug', False))
            self.language_model = None

    def add_tool(self, tool):
        """Add a tool to the agent."""
        self.tools.append(tool)
        logger.info(f"Tool '{getattr(tool, 'name', 'Unnamed')}' added to agent '{self.name}'")

    def add_guardrail(self, guardrail):
        """Add a guardrail to the agent."""
        self.guardrails.append(guardrail)
        logger.info(f"Guardrail '{getattr(guardrail, 'name', 'Unnamed')}' added to agent '{self.name}'")

    def register_observer(self, observer: Callable):
        """Register an observation callback."""
        self._observers.add(observer)

    def unregister_observer(self, observer: Callable):
        """Unregister an observation callback."""
        self._observers.discard(observer) # Use discard to avoid KeyError

    def _record_observation(self, observation: Dict[str, Any]):
        """Record an observation and notify observers."""
        observation['agent'] = self.name # Ensure agent name is in observation
        observation.setdefault('timestamp', asyncio.get_event_loop().time())
        self._observations.append(observation)
        for observer in self._observers:
            try:
                # Consider running observers concurrently or handling errors gracefully
                observer(observation)
            except Exception as e:
                logger.warning(f"Error in observer for agent '{self.name}': {str(e)}")

    def _apply_guardrails(self, input_data: Dict[str, Any], stage: str = "input") -> Tuple[bool, Optional[str]]:
        """Apply relevant guardrails."""
        # This could be enhanced to apply different guardrails at different stages (input, output, tool_call)
        for guardrail in self.guardrails:
            # Assuming guardrails have a 'validate' method
            if hasattr(guardrail, 'validate'):
                try:
                    is_valid, error = guardrail.validate(input_data)
                    if not is_valid:
                        logger.warning(f"Guardrail '{getattr(guardrail, 'name', 'Unnamed')}' failed at stage '{stage}': {error}")
                        return False, error
                except Exception as e:
                    logger.error(f"Error applying guardrail '{getattr(guardrail, 'name', 'Unnamed')}': {e}", exc_info=getattr(self.app_context, 'debug', False))
                    return False, f"Error in guardrail '{getattr(guardrail, 'name', 'Unnamed')}'"
        return True, None

    async def execute(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a task using the agent's capabilities by interacting with an LLM and tools."""
        context = context or {}
        exec_id = context.get('execution_id', f"{self.name}-{id(task)}")
        context['execution_id'] = exec_id # Ensure exec_id is in context

        self._record_observation({
            "type": "execution_start",
            "task": task,
            "execution_id": exec_id
        })

        # Apply input guardrails
        is_valid, error = self._apply_guardrails({"task": task, "context": context}, stage="input")
        if not is_valid:
            self._record_observation({
                "type": "guardrail_error", "stage": "input",
                "error": error, "execution_id": exec_id
            })
            return {"status": "error", "error": f"Input guardrail failed: {error}", "execution_id": exec_id}

        if not self.language_model:
            self._record_observation({
                "type": "execution_error", "error": "LanguageModelService not available",
                "execution_id": exec_id
            })
            return {"status": "error", "error": "Agent cannot execute: LanguageModelService not available.", "execution_id": exec_id}

        try:
            # Run the main execution loop
            final_result = await self._run_execution_loop(task, context)

            # Apply output guardrails (if any)
            is_valid, error = self._apply_guardrails({"result": final_result}, stage="output")
            if not is_valid:
                 self._record_observation({
                    "type": "guardrail_error", "stage": "output",
                    "error": error, "execution_id": exec_id
                 })
                 # Decide whether to return error or modified result
                 return {"status": "error", "error": f"Output guardrail failed: {error}", "execution_id": exec_id}

            self._record_observation({
                "type": "execution_complete",
                "result": final_result,
                "execution_id": exec_id
            })
            return {
                "status": "success",
                "result": final_result, # The final answer from the LLM
                "execution_id": exec_id
            }

        except Exception as e:
            logger.error(f"Agent '{self.name}' execution failed: {str(e)}", exc_info=getattr(self.app_context, 'debug', False))
            self._record_observation({
                "type": "execution_error",
                "error": str(e),
                "execution_id": exec_id
            })
            return {
                "status": "error",
                "error": f"Agent execution failed: {str(e)}",
                "execution_id": exec_id
            }

    def _format_tools_for_prompt(self) -> str:
        """Formats the available tools into a string for the LLM prompt."""
        if not self.tools:
            return "No tools available."

        tool_descriptions = []
        for tool in self.tools:
            # Basic formatting, assuming tool has name, description, parameters (as dict/JSON schema)
            name = getattr(tool, 'name', 'unnamed_tool')
            description = getattr(tool, 'description', 'No description.')
            params = getattr(tool, 'parameters', {})
            param_str = json.dumps(params) if params else "None"
            tool_descriptions.append(f"- Name: {name}\n  Description: {description}\n  Parameters (JSON Schema): {param_str}")

        return "Available Tools:\n" + "\n".join(tool_descriptions)

    def _construct_prompt(self, task: str, history: List[Dict[str, Any]]) -> str:
        """Constructs the prompt for the language model."""
        tool_info = self._format_tools_for_prompt()

        # Build history string
        history_str = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

        # Basic prompt template - This needs significant refinement for robust agent behavior
        prompt = f"""{self.instructions}

You have access to the following tools:
{tool_info}

Conversation History:
{history_str}

Current Task: {task}

Based on the task and history, decide the next step.
Respond in ONE of the following JSON formats:

1. To call a tool:
   {{
     "action": "call_tool",
     "tool_name": "...",
     "arguments": {{...}}
   }}

2. To provide the final answer:
   {{
     "action": "final_answer",
     "content": "..."
   }}

Your JSON response:"""
        return prompt

    async def _run_execution_loop(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Runs the loop of LLM interaction and tool execution."""
        exec_id = context['execution_id']
        history: List[Dict[str, Any]] = context.get('history', []) # Load history if provided
        if not history: # Start history with the initial task
             history.append({"role": "user", "content": task})

        tool_map = {getattr(tool, 'name', f'tool_{i}'): tool for i, tool in enumerate(self.tools)}

        for step in range(MAX_EXECUTION_STEPS):
            self._record_observation({
                "type": "step_start", "step": step + 1,
                "history_length": len(history), "execution_id": exec_id
            })

            # 1. Construct Prompt
            prompt = self._construct_prompt(task, history)
            self._record_observation({
                "type": "llm_prompt", "step": step + 1,
                "prompt": prompt, "execution_id": exec_id # Be careful logging full prompts
            })

            # 2. Call LLM
            llm_params = {"model": self.model} # Pass preferred model
            llm_response_raw = await self.language_model.process(prompt, **llm_params)
            llm_response_text = llm_response_raw.get("text", "").strip()
            model_used = llm_response_raw.get("model", "unknown")

            self._record_observation({
                "type": "llm_response", "step": step + 1,
                "response_text": llm_response_text, "model_used": model_used,
                "execution_id": exec_id
            })

            # 3. Parse LLM Response (Attempt to parse JSON)
            try:
                # Basic JSON parsing, might need more robust handling for partial/malformed JSON
                action_data = json.loads(llm_response_text)
                action_type = action_data.get("action")
            except json.JSONDecodeError:
                logger.warning(f"Agent '{self.name}' step {step+1}: LLM response was not valid JSON: {llm_response_text}")
                # Treat non-JSON response as a potential final answer or ask for clarification?
                # For now, assume it's a final answer if it's not JSON.
                action_type = "final_answer"
                action_data = {"content": llm_response_text} # Wrap it

            # 4. Process Action
            if action_type == "final_answer":
                final_content = action_data.get("content", "No content provided.")
                self._record_observation({
                    "type": "final_answer", "step": step + 1,
                    "content": final_content, "execution_id": exec_id
                })
                # Return the content part of the final answer action
                return {"content": final_content, "model_used": model_used}

            elif action_type == "call_tool":
                tool_name = action_data.get("tool_name")
                arguments = action_data.get("arguments", {})

                if not isinstance(arguments, dict):
                     logger.warning(f"Agent '{self.name}' step {step+1}: Invalid tool arguments format for '{tool_name}'. Expected dict, got {type(arguments)}.")
                     history.append({"role": "assistant", "content": llm_response_text}) # Add raw LLM resp
                     history.append({"role": "system", "content": f"Error: Tool arguments for '{tool_name}' must be a JSON object."})
                     continue # Ask LLM again

                self._record_observation({
                    "type": "tool_call_attempt", "step": step + 1,
                    "tool_name": tool_name, "arguments": arguments,
                    "execution_id": exec_id
                })

                # Find and execute the tool
                if tool_name in tool_map:
                    tool_to_call = tool_map[tool_name]
                    try:
                        # Apply guardrails before tool execution (optional)
                        # is_valid, error = self._apply_guardrails({"tool_name": tool_name, "arguments": arguments}, stage="tool_call")
                        # if not is_valid: ... handle error ...

                        # Assuming tool.execute takes arguments as kwargs or a single dict
                        tool_result = await tool_to_call.execute(**arguments) # Or tool_to_call.execute(arguments)

                        # Ensure tool result is serializable (e.g., convert complex objects)
                        tool_result_content = json.dumps(tool_result) if not isinstance(tool_result, str) else tool_result

                        self._record_observation({
                            "type": "tool_result", "step": step + 1,
                            "tool_name": tool_name, "result": tool_result, # Log raw result
                            "execution_id": exec_id
                        })
                        # Add LLM's action and the tool's result to history
                        history.append({"role": "assistant", "content": llm_response_text}) # Record the tool call action
                        history.append({"role": "tool", "tool_name": tool_name, "content": tool_result_content})

                    except Exception as tool_error:
                        logger.error(f"Agent '{self.name}' step {step+1}: Error executing tool '{tool_name}': {tool_error}", exc_info=getattr(self.app_context, 'debug', False))
                        self._record_observation({
                            "type": "tool_error", "step": step + 1,
                            "tool_name": tool_name, "error": str(tool_error),
                            "execution_id": exec_id
                        })
                        history.append({"role": "assistant", "content": llm_response_text}) # Add raw LLM resp
                        history.append({"role": "system", "content": f"Error executing tool {tool_name}: {str(tool_error)}"})
                else:
                    logger.warning(f"Agent '{self.name}' step {step+1}: Attempted to call unknown tool '{tool_name}'.")
                    self._record_observation({
                        "type": "tool_error", "step": step + 1,
                        "tool_name": tool_name, "error": "Tool not found",
                        "execution_id": exec_id
                    })
                    history.append({"role": "assistant", "content": llm_response_text}) # Add raw LLM resp
                    history.append({"role": "system", "content": f"Error: Tool '{tool_name}' is not available."})

            else:
                logger.warning(f"Agent '{self.name}' step {step+1}: Received unknown action type '{action_type}'.")
                history.append({"role": "assistant", "content": llm_response_text}) # Add raw LLM resp
                history.append({"role": "system", "content": f"Error: Unknown action '{action_type}'. Please use 'call_tool' or 'final_answer'."})

        # If loop finishes without a final answer
        logger.warning(f"Agent '{self.name}' reached maximum execution steps ({MAX_EXECUTION_STEPS}) for task ID {exec_id}.")
        self._record_observation({
            "type": "execution_error", "error": "Maximum execution steps reached",
            "execution_id": exec_id
        })
        # Return the last piece of history or a generic message
        last_content = history[-1]['content'] if history else "Max steps reached."
        return {"content": f"Max execution steps reached. Last message: {last_content}", "model_used": model_used}


    # Removed _simulate_execution method

    async def handoff(self, task: str, agent_name: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Hand off a task to another agent (Placeholder)."""
        # This functionality likely belongs more in the AgentService or Orchestrator
        context = context or {}
        handoff_id = context.get('handoff_id', f"handoff-{id(task)}")

        self._record_observation({
            "type": "handoff_attempt",
            "from_agent": self.name, "to_agent": agent_name,
            "task": task, "handoff_id": handoff_id
        })

        # In a real system, this would involve invoking the AgentService or similar
        logger.warning(f"Agent '{self.name}' handoff is currently a placeholder.")
        return {
            "status": "success", # Simulate success
            "message": f"Placeholder: Task '{task}' handed off from '{self.name}' to '{agent_name}'",
            "handoff_id": handoff_id
        }

    def get_observations(self) -> List[Dict[str, Any]]:
        """Get all recorded observations for this agent instance."""
        return self._observations.copy()
