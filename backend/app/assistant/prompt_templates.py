# backend/app/assistant/prompt_templates.py
import logging

logger = logging.getLogger(__name__)

# Example System Prompt (adjust based on chosen LLM and desired persona)
# Use placeholders for dynamic content like tool descriptions
SYSTEM_PROMPT = """You are Nexus, a helpful AI assistant integrated into the Nexus application.
Be concise, helpful, and informative.
Use the provided context and tools when necessary to answer the user's query accurately.
If you use a tool, mention it briefly in your response.
Think step-by-step if needed.

Available Tools:
{tool_descriptions}
"""

# Example template incorporating RAG context
RAG_PROMPT_TEMPLATE = """{system_prompt}

Relevant Context Retrieved:
---
{retrieved_context}
---

Conversation History (Oldest to Newest):
{history}

User Query: {user_query}
Assistant Response:"""

# Simpler template if not using RAG or tools initially
BASIC_CHAT_TEMPLATE = """{system_prompt}

Conversation History (Oldest to Newest):
{history}

User Query: {user_query}
Assistant Response:"""

# Function to format history for Ollama (list of dicts)
def format_history_ollama(history_tuples):
    """
    Formats conversation history from [(role, message), ...] tuples
    into the list of dictionaries format expected by Ollama's /api/chat.
    """
    messages = []
    if not history_tuples:
        return messages
    for role, content in history_tuples:
        # Ensure role is either 'user' or 'assistant' (or 'system' if applicable)
        if role not in ['user', 'assistant', 'system']:
             logger.warning(f"Invalid role '{role}' found in history tuple, skipping.")
             continue
        messages.append({"role": role, "content": content})
    return messages

# Function to format history as a simple string (for basic templates)
def format_history_string(history_tuples):
    """Formats history into a simple alternating string."""
    if not history_tuples:
        return "No previous conversation history."
    history_str = ""
    for role, content in history_tuples:
         # Capitalize role for readability
        history_str += f"{role.capitalize()}: {content}\n"
    return history_str.strip()

# You might add more specific templates here, e.g., for tool use decision making
