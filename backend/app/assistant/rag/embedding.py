# backend/app/assistant/rag/embedding.py
import ollama
from flask import current_app
import logging
import time

logger = logging.getLogger(__name__)

# Consider adding retry logic for Ollama calls
MAX_RETRIES = 2
RETRY_DELAY = 1 # seconds

def get_embedding(text: str, model: str = None):
    """
    Generates embedding for the given text using Ollama.
    Includes basic validation and retry logic.
    """
    if not text or not isinstance(text, str) or not text.strip():
        logger.warning("Attempted to embed empty or non-string text.")
        # Return None or raise error based on how vector_store handles it
        return None

    client = ollama.Client(host=current_app.config['OLLAMA_URL'])
    embedding_model = model or current_app.config['OLLAMA_EMBEDDING_MODEL']
    attempt = 0

    while attempt < MAX_RETRIES:
        try:
            logger.debug(f"Attempt {attempt + 1}: Generating embedding with model '{embedding_model}' for text starting with: {text[:50]}...")
            response = client.embeddings(model=embedding_model, prompt=text.strip()) # Ensure text is stripped
            # Validate response structure
            if isinstance(response, dict) and 'embedding' in response and isinstance(response['embedding'], list):
                logger.debug(f"Successfully generated embedding (dimension: {len(response['embedding'])})")
                return response['embedding']
            else:
                logger.warning(f"Received unexpected embedding response format: {response}")
                # Treat unexpected format as an error for retry purposes
                raise ValueError("Invalid embedding response format")

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed to get embedding from Ollama ({embedding_model}): {e}")
            attempt += 1
            if attempt < MAX_RETRIES:
                logger.info(f"Retrying embedding generation in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"Failed to get embedding after {MAX_RETRIES} attempts.", exc_info=True)
                raise # Re-raise the final exception to be handled upstream

    # Should not be reached if MAX_RETRIES > 0, but as a fallback
    logger.error("Embedding generation failed after retries.")
    return None
