# backend/app/assistant/rag/retriever.py
from .vector_store import search_similar
import logging

logger = logging.getLogger(__name__)

def retrieve_context(query: str, top_k: int = 3, filter_dict: dict = None):
    """
    Retrieves relevant document chunks from the vector store based on the query.

    Args:
        query (str): The user query or text to search for.
        top_k (int): The maximum number of documents to retrieve.
        filter_dict (dict, optional): A dictionary for metadata filtering
                                      (e.g., {"source": "manual"}). Defaults to None.

    Returns:
        list[str]: A list of relevant document text chunks, or an empty list if none found or on error.
    """
    logger.info(f"Retrieving context for query: '{query[:100]}...' (top_k={top_k}, filter={filter_dict})")
    if not query or not query.strip():
        logger.warning("Attempted context retrieval with empty query.")
        return []
    try:
        # Pass the filter dictionary to the search function
        results = search_similar(query_text=query.strip(), top_k=top_k, where_filter=filter_dict)

        if not results:
            logger.info("No relevant context found in vector store for this query.")
            return []

        logger.info(f"Retrieved {len(results)} context chunks.")
        # results should already be a list of document strings based on search_similar
        return results

    except Exception as e:
        # Log the error including the query for better debugging
        logger.error(f"Error during context retrieval for query '{query[:100]}...': {e}", exc_info=True)
        return [] # Return empty list on error
