"""
Advanced Language Model Providers for Nexus AI Assistant.

This module provides capability providers for various language models
including OpenAI, Anthropic Claude, Ollama, and others.
"""
import logging
import json
import aiohttp
import os
from typing import Dict, Any, List, Optional, Union

from ..abstraction import CapabilityProvider, CapabilityType

logger = logging.getLogger(__name__)

# --- Anthropic Provider ---
class AnthropicProvider(CapabilityProvider):
    """Anthropic Claude provider for text generation capabilities."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Anthropic Claude provider."""
        super().__init__("anthropic", config)
        self.api_key = self.config.get("api_key", os.environ.get("ANTHROPIC_API_KEY", ""))
        self.api_url = self.config.get("api_url", "https://api.anthropic.com/v1/messages")
        self.default_model = self.config.get("default_model", "claude-3-5-sonnet-20240620") # Updated default
        self.timeout = self.config.get("timeout", 120)
        self.max_tokens = self.config.get("max_tokens", 4096)

    async def initialize(self) -> None:
        """Initialize the provider."""
        if not self.api_key:
            logger.warning("Anthropic API key not provided, provider will be disabled")
            self.enabled = False
            return

        self.register_capability(CapabilityType.TEXT_GENERATION, self.generate_text)
        self.register_capability(CapabilityType.CODE_GENERATION, self.generate_code)

        # Test connection
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                test_data = {
                    "model": self.default_model,
                    "max_tokens": 10,
                    "messages": [{"role": "user", "content": "Hello"}]
                }
                async with session.post(self.api_url, headers=headers, json=test_data, timeout=10) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"Anthropic API test failed ({response.status}): {error_text}")
                        self.enabled = False
                    else:
                        logger.info("Anthropic API connection successful")
        except Exception as e:
            logger.warning(f"Error connecting to Anthropic API: {str(e)}")
            self.enabled = False

    async def generate_text(self,
                          prompt: str,
                          context: Optional[List[Dict[str, str]]] = None,
                          model: Optional[str] = None,
                          temperature: float = 0.7,
                          max_tokens: Optional[int] = None,
                          system_prompt: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate text using Claude."""
        if not self.enabled:
            raise RuntimeError("Anthropic provider is not enabled or failed initialization.")

        model_to_use = model or self.default_model
        max_tokens_to_use = max_tokens or self.max_tokens

        messages = []
        if context:
            # Ensure context roles are valid ('user' or 'assistant')
            for entry in context:
                role = entry.get("role")
                content = entry.get("content")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})
                # Silently skip invalid context entries or log warning?
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_to_use,
            "messages": messages,
            "max_tokens": max_tokens_to_use,
            "temperature": temperature
        }
        if system_prompt:
            payload["system"] = system_prompt

        # Add only known Anthropic parameters from kwargs
        allowed_kwargs = {"top_p", "top_k", "stop_sequences"}
        payload.update({k: v for k, v in kwargs.items() if k in allowed_kwargs})

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                async with session.post(self.api_url, headers=headers, json=payload, timeout=self.timeout) as response:
                    response_data = await response.json()
                    if response.status != 200:
                        error_detail = response_data.get("error", {}).get("message", "Unknown error")
                        raise ValueError(f"Anthropic API error ({response.status}): {error_detail}")

                    content = response_data.get("content", [])
                    text = "".join([block.get("text", "") for block in content if block.get("type") == "text"])

                    return {
                        "status": "success",
                        "text": text,
                        "model": model_to_use, # Use the actual model used
                        "usage": response_data.get("usage", {}),
                        "id": response_data.get("id", "")
                    }
        except aiohttp.ClientError as e:
            logger.error(f"Network error generating text with Claude: {str(e)}")
            raise ConnectionError(f"Network error communicating with Anthropic API: {e}") from e
        except Exception as e:
            logger.error(f"Error generating text with Claude: {str(e)}")
            raise RuntimeError(f"Failed to generate text via Anthropic: {e}") from e

    async def generate_code(self,
                          prompt: str,
                          language: str = "python",
                          model: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate code using Claude."""
        system_prompt = f"You are an expert {language} programmer. Generate clean, efficient, and well-documented {language} code. Provide ONLY the raw code, without any explanations, comments outside the code, or markdown formatting like ```."
        enhanced_prompt = f"Write {language} code for the following task:\n\n{prompt}"

        result = await self.generate_text(
            prompt=enhanced_prompt,
            model=model or self.default_model, # Use default if not specified
            system_prompt=system_prompt,
            temperature=0.2,
            **kwargs
        )

        code = result.get("text", "").strip()
        # Basic cleanup (remove potential markdown backticks if model ignored instructions)
        if code.startswith("```") and code.endswith("```"):
             code = code[3:-3].strip()
             # Remove language hint if present after backticks
             if '\n' in code:
                 first_line, rest = code.split('\n', 1)
                 if first_line.strip().lower() == language.lower():
                     code = rest.strip()

        result["code"] = code
        result["language"] = language
        return result

# --- OpenAI Provider ---
class OpenAIProvider(CapabilityProvider):
    """OpenAI provider for text and code generation capabilities."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize OpenAI provider."""
        super().__init__("openai", config)
        self.api_key = self.config.get("api_key", os.environ.get("OPENAI_API_KEY", ""))
        self.api_url = self.config.get("api_url", "https://api.openai.com/v1/chat/completions")
        self.default_model = self.config.get("default_model", "gpt-4o")
        self.timeout = self.config.get("timeout", 120)
        self.max_tokens = self.config.get("max_tokens", 4096) # Note: OpenAI uses max_tokens differently

    async def initialize(self) -> None:
        """Initialize the provider."""
        if not self.api_key:
            logger.warning("OpenAI API key not provided, provider will be disabled")
            self.enabled = False
            return

        self.register_capability(CapabilityType.TEXT_GENERATION, self.generate_text)
        self.register_capability(CapabilityType.CODE_GENERATION, self.generate_code)

        # Test connection
        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                test_data = {"model": self.default_model, "max_tokens": 10, "messages": [{"role": "user", "content": "Hello"}]}
                async with session.post(self.api_url, headers=headers, json=test_data, timeout=10) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"OpenAI API test failed ({response.status}): {error_text}")
                        self.enabled = False
                    else:
                        logger.info("OpenAI API connection successful")
        except Exception as e:
            logger.warning(f"Error connecting to OpenAI API: {str(e)}")
            self.enabled = False

    async def generate_text(self,
                          prompt: str,
                          context: Optional[List[Dict[str, str]]] = None,
                          model: Optional[str] = None,
                          temperature: float = 0.7,
                          max_tokens: Optional[int] = None,
                          system_prompt: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate text using OpenAI."""
        if not self.enabled:
             raise RuntimeError("OpenAI provider is not enabled or failed initialization.")

        model_to_use = model or self.default_model
        max_tokens_to_use = max_tokens # OpenAI uses max_tokens directly

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            for entry in context:
                 role = entry.get("role")
                 content = entry.get("content")
                 # Add tool call/result roles if present in context (OpenAI specific)
                 if role in ["user", "assistant", "tool"] and content:
                     msg = {"role": role, "content": content}
                     # Include tool_call_id if available for tool role
                     if role == "tool" and "tool_call_id" in entry:
                         msg["tool_call_id"] = entry["tool_call_id"]
                     messages.append(msg)
                 # Handle assistant messages that contain tool calls
                 elif role == "assistant" and entry.get("tool_calls"):
                     messages.append({"role": "assistant", "tool_calls": entry["tool_calls"]})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_to_use,
            "messages": messages,
            "temperature": temperature
        }
        if max_tokens_to_use is not None:
             payload["max_tokens"] = max_tokens_to_use

        # Add only known OpenAI parameters from kwargs
        allowed_kwargs = {"top_p", "frequency_penalty", "presence_penalty", "stop", "tools", "tool_choice"}
        payload.update({k: v for k, v in kwargs.items() if k in allowed_kwargs})

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                async with session.post(self.api_url, headers=headers, json=payload, timeout=self.timeout) as response:
                    response_data = await response.json()
                    if response.status != 200:
                        error_detail = response_data.get("error", {}).get("message", "Unknown error")
                        raise ValueError(f"OpenAI API error ({response.status}): {error_detail}")

                    choices = response_data.get("choices", [])
                    if not choices:
                        raise ValueError("No choices found in OpenAI response")

                    message = choices[0].get("message", {})
                    text = message.get("content") # Can be None if tool_calls are present
                    tool_calls = message.get("tool_calls") # Check for tool calls

                    # Build result
                    result = {
                        "status": "success",
                        "text": text, # Might be None
                        "model": model_to_use, # Use the actual model used
                        "usage": response_data.get("usage", {}),
                        "id": response_data.get("id", "")
                    }
                    # Include tool calls if the model decided to use tools
                    if tool_calls:
                        result["tool_calls"] = tool_calls

                    return result
        except aiohttp.ClientError as e:
            logger.error(f"Network error generating text with OpenAI: {str(e)}")
            raise ConnectionError(f"Network error communicating with OpenAI API: {e}") from e
        except Exception as e:
            logger.error(f"Error generating text with OpenAI: {str(e)}")
            raise RuntimeError(f"Failed to generate text via OpenAI: {e}") from e

    async def generate_code(self,
                          prompt: str,
                          language: str = "python",
                          model: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate code using OpenAI."""
        system_prompt = f"You are an expert {language} programmer. Generate clean, efficient, and well-documented {language} code. Provide ONLY the raw code, without any explanations, comments outside the code, or markdown formatting like ```."
        enhanced_prompt = f"Write {language} code for the following task:\n\n{prompt}"

        result = await self.generate_text(
            prompt=enhanced_prompt,
            model=model or self.default_model,
            system_prompt=system_prompt,
            temperature=0.2,
            **kwargs
        )

        code = result.get("text", "").strip()
        # Basic cleanup
        if code.startswith("```") and code.endswith("```"):
             code = code[3:-3].strip()
             if '\n' in code:
                 first_line, rest = code.split('\n', 1)
                 if first_line.strip().lower() == language.lower():
                     code = rest.strip()

        result["code"] = code
        result["language"] = language
        return result

# --- Ollama Provider ---
class OllamaProvider(CapabilityProvider):
    """Ollama provider for local text generation capabilities."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Ollama provider."""
        super().__init__("ollama", config)
        # Default to standard Ollama API endpoint
        self.api_url_base = self.config.get("api_url", os.environ.get("OLLAMA_API_URL", "http://localhost:11434")).rstrip('/')
        self.generate_endpoint = f"{self.api_url_base}/api/generate"
        self.chat_endpoint = f"{self.api_url_base}/api/chat" # Prefer chat endpoint if available
        self.tags_endpoint = f"{self.api_url_base}/api/tags"
        self.default_model = self.config.get("default_model", os.environ.get("OLLAMA_DEFAULT_MODEL", None)) # No good default, user must specify
        self.timeout = self.config.get("timeout", 300) # Longer timeout for local models
        self.keep_alive = self.config.get("keep_alive", "5m") # Keep model loaded

    async def initialize(self) -> None:
        """Initialize the provider and check connection."""
        if not self.default_model:
            logger.warning("Ollama default model not specified in config or OLLAMA_DEFAULT_MODEL env var. Provider might not function correctly without explicit model calls.")
            # Don't disable yet, allow calls with explicit model

        self.register_capability(CapabilityType.TEXT_GENERATION, self.generate_text)
        self.register_capability(CapabilityType.CODE_GENERATION, self.generate_code)

        # Test connection by listing models
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.tags_endpoint, timeout=10) as response:
                    if response.status == 200:
                        models_data = await response.json()
                        available_models = [m.get('name') for m in models_data.get('models', []) if m.get('name')]
                        logger.info(f"Ollama API connection successful. Available models: {available_models}")
                        if self.default_model and self.default_model not in available_models:
                             logger.warning(f"Ollama default model '{self.default_model}' not found in available models: {available_models}")
                        self.enabled = True
                    else:
                        error_text = await response.text()
                        logger.warning(f"Ollama API test failed ({response.status}): Could not list models at {self.tags_endpoint}. Error: {error_text}")
                        self.enabled = False
        except aiohttp.ClientConnectorError as e:
             logger.warning(f"Error connecting to Ollama API at {self.api_url_base}: {e}. Is Ollama running?")
             self.enabled = False
        except Exception as e:
            logger.warning(f"Error testing Ollama API connection: {str(e)}")
            self.enabled = False

    async def generate_text(self,
                          prompt: str,
                          context: Optional[List[Dict[str, str]]] = None,
                          model: Optional[str] = None,
                          temperature: float = 0.7,
                          max_tokens: Optional[int] = None, # Ollama doesn't use max_tokens directly
                          system_prompt: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate text using a local Ollama model."""
        if not self.enabled:
            raise RuntimeError("Ollama provider is not enabled or failed initialization.")

        model_to_use = model or self.default_model
        if not model_to_use:
             raise ValueError("Ollama model must be specified either in the call or as a default.")

        # Prefer /api/chat if context or system prompt is present
        use_chat_endpoint = bool(context or system_prompt)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            for entry in context:
                role = entry.get("role")
                content = entry.get("content")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_to_use,
            "stream": False, # Get full response at once
            "keep_alive": self.keep_alive,
            "options": {
                "temperature": temperature,
                # Add other Ollama options from kwargs if needed
                # e.g., "top_p", "top_k", "num_predict" (similar to max_tokens)
            }
        }
        # Map max_tokens to num_predict if provided
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens

        # Add known Ollama options from kwargs
        allowed_options = {"top_p", "top_k", "num_predict", "stop", "seed"}
        payload["options"].update({k: v for k, v in kwargs.items() if k in allowed_options})


        if use_chat_endpoint:
            payload["messages"] = messages
            endpoint = self.chat_endpoint
        else:
            # Use /api/generate (simpler, less context aware)
            payload["prompt"] = prompt
            if system_prompt:
                 payload["system"] = system_prompt
            endpoint = self.generate_endpoint


        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, json=payload, timeout=self.timeout) as response:
                    response_data = await response.json()
                    if response.status != 200:
                        error_detail = response_data.get("error", "Unknown Ollama error")
                        raise ValueError(f"Ollama API error ({response.status}): {error_detail}")

                    # Extract text based on endpoint used
                    if use_chat_endpoint:
                        text = response_data.get("message", {}).get("content", "")
                    else: # /api/generate
                        text = response_data.get("response", "")

                    # Extract usage data if available (might vary by model/version)
                    input_tokens = response_data.get("prompt_eval_count", 0)
                    output_tokens = response_data.get("eval_count", 0)

                    return {
                        "status": "success",
                        "text": text.strip(),
                        "model": model_to_use,
                        "usage": {
                            "input_tokens": input_tokens,
                            "output_tokens": output_tokens
                        },
                        "id": response_data.get("created_at", "") # Use timestamp as ID
                    }
        except aiohttp.ClientError as e:
            logger.error(f"Network error generating text with Ollama: {str(e)}")
            raise ConnectionError(f"Network error communicating with Ollama API: {e}") from e
        except Exception as e:
            logger.error(f"Error generating text with Ollama ({model_to_use}): {str(e)}")
            raise RuntimeError(f"Failed to generate text via Ollama: {e}") from e

    async def generate_code(self,
                          prompt: str,
                          language: str = "python",
                          model: Optional[str] = None,
                          **kwargs) -> Dict[str, Any]:
        """Generate code using Ollama."""
        # Try to use a model specifically fine-tuned for code if available, otherwise use default
        code_model_hint = f"codellama" # Or other code model names
        model_to_use = model or self.default_model
        # Simple check if default model seems like a code model
        is_code_model = any(hint in model_to_use for hint in ["code", "starcoder", "wizardcoder"]) if model_to_use else False

        if is_code_model:
             system_prompt = f"You are an expert {language} programmer. Provide ONLY the raw {language} code requested, without any explanations or markdown."
        else:
             # Instruct a general model more firmly
             system_prompt = f"You are an expert {language} programmer. Generate clean, efficient {language} code. IMPORTANT: Respond ONLY with the raw code itself, without any introduction, explanation, comments outside the code, or markdown formatting like ```."

        enhanced_prompt = f"Write {language} code for the following task:\n\n{prompt}"

        result = await self.generate_text(
            prompt=enhanced_prompt,
            model=model_to_use,
            system_prompt=system_prompt,
            temperature=0.2, # Lower temp for code
            **kwargs
        )

        code = result.get("text", "").strip()
        # Basic cleanup
        if code.startswith("```") and code.endswith("```"):
             code = code[3:-3].strip()
             if '\n' in code:
                 first_line, rest = code.split('\n', 1)
                 if first_line.strip().lower() == language.lower():
                     code = rest.strip()

        result["code"] = code
        result["language"] = language
        return result
