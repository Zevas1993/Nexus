# backend/app/assistant/llm_interface.py
import ollama
from flask import current_app # To access config like OLLAMA_URL
import logging

logger = logging.getLogger(__name__)

def get_llm_response(messages, model=None, stream=False):
    """
    Gets a response from the configured Ollama LLM.

    Args:
        messages (list): A list of message dictionaries, e.g.,
                         [{'role': 'system', 'content': '...'},
                          {'role': 'user', 'content': '...'}]
        model (str, optional): Override the default model from config.
        stream (bool): Whether to stream the response.

    Returns:
        If stream=False: The full response content (str).
        If stream=True: An iterator yielding chunks of the response content (str).
        Raises Exception on API error.
    """
    try:
        client = ollama.Client(host=current_app.config['OLLAMA_URL'])
        llm_model = model or current_app.config['OLLAMA_DEFAULT_MODEL']
        logger.info(f"Sending request to Ollama model: {llm_model} at {current_app.config['OLLAMA_URL']}")
        # logger.debug(f"Ollama Request Messages: {messages}") # Be careful logging full prompts

        response = client.chat(
            model=llm_model,
            messages=messages,
            stream=stream
        )

        if stream:
            # Generator yielding message content chunks
            def generate():
                full_response_for_log = ""
                try:
                    for chunk in response:
                        # Check if chunk is valid and has content
                        if isinstance(chunk, dict) and 'message' in chunk and 'content' in chunk['message']:
                            content_chunk = chunk['message']['content']
                            full_response_for_log += content_chunk
                            yield content_chunk # Yield only the text content part
                        else:
                            logger.warning(f"Received unexpected chunk format from Ollama stream: {chunk}")
                    logger.debug(f"Ollama Streamed Response (Full): {full_response_for_log}")
                except Exception as e:
                    logger.error(f"Error processing Ollama stream chunk: {e}", exc_info=True)
                    # Decide if you want to yield an error message or just stop
                    yield "[Error processing stream]" # Example error yield
            return generate()
        else:
            # Handle non-streaming response
            if isinstance(response, dict) and 'message' in response and 'content' in response['message']:
                 response_content = response['message']['content']
                 logger.debug(f"Ollama Response (Full): {response_content}")
                 return response_content
            else:
                 logger.error(f"Received unexpected response format from Ollama (non-stream): {response}")
                 raise ValueError("Invalid response format received from Ollama.")


    except Exception as e:
        logger.error(f"Error connecting to Ollama ({current_app.config['OLLAMA_URL']}) or during generation: {e}", exc_info=True)
        # Log the error properly
        raise # Re-raise the exception to be handled by the caller (e.g., the API route)
