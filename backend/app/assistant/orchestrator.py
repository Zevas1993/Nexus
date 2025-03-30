# backend/app/assistant/orchestrator.py
from .llm_interface import get_llm_response
from .rag.retriever import retrieve_context
# Adjust tool import based on final structure in tools/__init__.py
from .tools import get_tool, get_tool_descriptions
from .prompt_templates import SYSTEM_PROMPT, RAG_PROMPT_TEMPLATE, BASIC_CHAT_TEMPLATE, format_history_ollama, format_history_string
from app.models import ConversationTurn # To save history
from app import db
from flask import current_app
import json # For potential tool argument parsing
import logging

logger = logging.getLogger(__name__)

# --- Placeholder for loading tools ---
# This is handled by tools/__init__.py now
# tool_descriptions = get_tool_descriptions() # Get descriptions from the tool registry
# formatted_system_prompt = SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions)
# --- End Placeholder ---

# Simple in-memory history for demonstration - REPLACE WITH DATABASE logic
# This is NOT suitable for production or multiple users.
# conversation_histories = {} # { "user_id_session_id": [(role, message), ...] }

def load_history_from_db(user_id: int, session_id: str = None, limit: int = 5):
    """Loads the last N turns of conversation history from the database."""
    try:
        query = ConversationTurn.query.filter_by(user_id=user_id)
        if session_id:
            query = query.filter_by(session_id=session_id)
        # Order by timestamp descending, limit, then reverse to get oldest first
        turns = query.order_by(ConversationTurn.timestamp.desc()).limit(limit).all()
        # Reverse the list to get chronological order (oldest first)
        turns.reverse()

        history_tuples = []
        for turn in turns:
            if turn.user_message:
                history_tuples.append(("user", turn.user_message))
            if turn.assistant_response:
                history_tuples.append(("assistant", turn.assistant_response))
        logger.info(f"Loaded {len(turns)} turns from DB for user {user_id}, session {session_id}")
        return history_tuples
    except Exception as e:
        logger.error(f"Failed to load history from DB: {e}", exc_info=True)
        return [] # Return empty list on error


def run_assistant_pipeline(user_id: int, user_message: str, session_id: str = None, stream: bool = False):
    """
    Main pipeline for processing user message with RAG and potential tools.
    (This is a simplified example)
    """
    logger.info(f"Running pipeline for User {user_id}, Session: {session_id}, Stream: {stream}, Message: '{user_message[:100]}...'")

    # --- 1. Load History from DB ---
    history = load_history_from_db(user_id, session_id, limit=5) # Load last 5 turns

    # --- 2. RAG Step ---
    try:
        # TODO: Add logic to decide IF RAG is needed based on query/history
        context_docs = retrieve_context(user_message, top_k=2) # Get top 2 relevant docs
        retrieved_context_str = "\n---\n".join([doc for doc in context_docs]) # Simple join for now
        logger.debug(f"Retrieved Context:\n{retrieved_context_str}")
    except Exception as e:
        logger.error(f"RAG retrieval failed: {e}", exc_info=True)
        retrieved_context_str = "Context retrieval failed."
        # Decide if you want to halt or proceed without context

    # --- 3. Prepare Prompt ---
    # Get available tool descriptions
    tool_descriptions = get_tool_descriptions()
    formatted_system_prompt = SYSTEM_PROMPT.format(tool_descriptions=tool_descriptions or "No tools available.")

    # Format history for the LLM
    formatted_history = format_history_ollama(history) # Use Ollama format

    # Create the messages list for Ollama
    messages = []
    messages.append({"role": "system", "content": formatted_system_prompt})

    # Add formatted history (if any)
    if formatted_history:
        messages.extend(formatted_history)

    # Add RAG context and User Query
    # Simple approach: just prepend context to the user message.
    # More sophisticated approaches might involve structuring the prompt differently
    # or having the LLM specifically reference the context section.
    user_query_with_context = user_message
    if retrieved_context_str and retrieved_context_str != "Context retrieval failed.":
         # Use a template that explicitly includes context
         # This requires adjusting the prompt templates and how history is inserted
         # For simplicity here, just prepend.
         user_query_with_context = f"Use the following context if relevant:\nContext:\n{retrieved_context_str}\n\nUser Query: {user_message}"

    messages.append({"role": "user", "content": user_query_with_context})

    # --- 4. Call LLM ---
    try:
        # TODO: Implement logic to decide if tools are needed BEFORE the main call,
        # potentially using a separate LLM call or specific prompt structure.
        # TODO: Implement parsing LLM output for tool calls and executing them.
        # For now, just get a direct response.

        response_data = get_llm_response(messages, stream=stream) # Pass stream preference

        # If streaming, the response_data is a generator, return it directly
        if stream:
            # We need to handle saving the full response *after* streaming is complete.
            # This is tricky. The API route currently handles yielding.
            # We might need a wrapper or callback mechanism.
            # For now, we won't save the streamed response accurately to DB in this simple version.
            logger.info("Streaming response initiated.")
            # The generator itself is returned to the route
            # Saving to DB happens *after* this function returns in the streaming case (needs adjustment)
            return response_data

        # If not streaming, response_data is the full string
        assistant_response = response_data
        logger.debug(f"LLM Response (non-stream): {assistant_response}")

    except Exception as e:
        logger.error(f"LLM generation failed: {e}", exc_info=True)
        assistant_response = "Sorry, I encountered an error trying to generate a response."
        # If streaming was requested, we can't easily return an error generator here
        # The exception should propagate to the route handler.
        if stream:
             raise # Let the route handler catch it for streaming error message

    # --- 5. Save to Database (Only for non-streaming responses in this version) ---
    if not stream:
        try:
            turn = ConversationTurn(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message, # Save original message, not the one with context
                assistant_response=assistant_response,
                retrieved_context=retrieved_context_str if retrieved_context_str else None,
                # tool_used=tool_name if used else None, # Add tool tracking later
            )
            db.session.add(turn)
            db.session.commit()
            logger.info(f"Saved non-streamed conversation turn ID {turn.id} to DB.")
        except Exception as e:
            logger.error(f"Failed to save conversation turn to DB: {e}", exc_info=True)
            db.session.rollback() # Important to roll back on error

    # Return the final response (string if not streaming, generator if streaming)
    return assistant_response
