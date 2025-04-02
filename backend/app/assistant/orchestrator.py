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

    # Format history for the LLM (Ollama format)
    formatted_history_list = format_history_ollama(history)

    # Decide which base prompt template to use
    # If we have context and it wasn't an error, use the RAG template
    use_rag_template = bool(retrieved_context_str and retrieved_context_str != "Context retrieval failed.")

    # Create the messages list for Ollama
    messages = []
    messages.append({"role": "system", "content": formatted_system_prompt})

    # Add formatted history (if any)
    if formatted_history_list:
        messages.extend(formatted_history_list)

    # Add the final user query, potentially incorporating context via the template structure
    if use_rag_template:
        # Format history as a string for insertion into the RAG template's history section
        history_str_for_template = format_history_string(history)
        final_user_prompt = RAG_PROMPT_TEMPLATE.format(
            system_prompt="", # System prompt is already a separate message
            retrieved_context=retrieved_context_str,
            history=history_str_for_template,
            user_query=user_message
        )
        # Remove the initial system prompt part from the template if it was included
        final_user_prompt = final_user_prompt.split("Conversation History (Oldest to Newest):", 1)[-1]
        final_user_prompt = f"Conversation History (Oldest to Newest):{final_user_prompt}" # Add back the header
    else:
        # Use basic chat template structure or just the user message if no history
        if history:
             history_str_for_template = format_history_string(history)
             # Using BASIC_CHAT_TEMPLATE structure implicitly by placing history before query
             final_user_prompt = f"Conversation History (Oldest to Newest):\n{history_str_for_template}\n\nUser Query: {user_message}"
             # Alternatively, just append user message if history is already in messages list
             # final_user_prompt = user_message # If history is handled by messages list
        else:
             final_user_prompt = user_message # No history, just the query

    # Append the final constructed user message
    messages.append({"role": "user", "content": final_user_prompt})
    logger.debug(f"Final prompt messages structure for LLM: {messages}")

    # --- 4. Call LLM & Handle Potential Tool Use ---
    try:
        # --- Tool Use Implementation Placeholder ---
        # This is where the logic for tool use needs to be implemented.
        # A typical flow might involve:
        # 1. First LLM Call: Ask the LLM if a tool is needed based on the user query,
        #    history, context, and available tool descriptions. Use specific prompting
        #    to encourage a structured response indicating the tool name and arguments
        #    (e.g., JSON format).
        #
        # initial_llm_response = get_llm_response(messages, stream=False) # Non-streaming for tool check
        #
        # 2. Parse Response: Check if initial_llm_response indicates a tool call.
        #    Parse out the tool name and arguments.
        #    tool_name, tool_args = parse_tool_call(initial_llm_response) # Implement this parsing function
        #
        # 3. Execute Tool (if requested):
        #    if tool_name and tool_args is not None:
        #        logger.info(f"LLM requested tool: {tool_name} with args: {tool_args}")
        #        tool_instance = get_tool(tool_name)
        #        if tool_instance:
        #            try:
        #                tool_result = tool_instance.run(tool_args) # Assuming run takes string/dict args
        #                logger.info(f"Tool {tool_name} executed. Result: {tool_result[:100]}...")
        #            except Exception as tool_err:
        #                logger.error(f"Error executing tool {tool_name}: {tool_err}", exc_info=True)
        #                tool_result = f"Error executing tool {tool_name}: {tool_err}"
        #        else:
        #            tool_result = f"Error: Tool '{tool_name}' not found."
        #
        #        # 4. Second LLM Call (with tool result): Append the tool result to the
        #        #    message history and call the LLM again to get the final natural
        #        #    language response for the user.
        #        messages.append({"role": "assistant", "content": initial_llm_response}) # Record LLM's tool request
        #        messages.append({"role": "tool", "content": tool_result}) # Add tool result (role might vary based on LLM)
        #        # Now call LLM again for final response
        #        response_data = get_llm_response(messages, stream=stream)
        #
        #    else:
        #        # No tool requested, use the initial response directly (or call again if needed)
        #        # If the first call was just for tool check, might need to call again for final answer
        #        logger.info("No tool requested by LLM.")
        #        response_data = get_llm_response(messages, stream=stream) # Call LLM for final answer
        #
        # --- End Tool Use Implementation Placeholder ---

        # --- Simplified Call (No Tool Logic) ---
        # For now, we bypass the tool logic and make a direct call for the final response.
        logger.warning("Tool use logic is not implemented. Proceeding with direct LLM call.")
        response_data = get_llm_response(messages, stream=stream)
        # --- End Simplified Call ---


        # If streaming, the response_data is a generator, return it with the initial turn object
        if stream:
            # We need to handle saving the full response *after* streaming is complete.
            # This is tricky. The API route currently handles yielding.
            # We might need a wrapper or callback mechanism.
            # For now, we won't save the streamed response accurately to DB in this simple version.
            logger.info("Streaming response initiated.")
            # For streaming, we need to save *after* the stream is consumed.
            # We'll create the DB object now but save it later in the route handler.
            # Return the generator AND the initial turn object (without response).
            logger.info("Streaming response initiated. DB save deferred.")
            initial_turn = ConversationTurn(
                user_id=user_id,
                session_id=session_id,
                user_message=user_message,
                assistant_response=None, # Will be filled later
                retrieved_context=retrieved_context_str if retrieved_context_str else None,
                # tool_used=... # Add tool tracking later
            )
            # Return tuple: (generator, initial_db_object)
            return response_data, initial_turn

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

    # --- 5. Save to Database (Only for non-streaming responses here) ---
    # Streaming responses are saved via the route handler after consumption.
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

    # Return the final response (string if not streaming, tuple if streaming)
    return assistant_response
