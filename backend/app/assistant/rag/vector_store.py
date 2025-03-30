# backend/app/assistant/rag/vector_store.py
import chromadb
# Ensure chromadb is installed (add to requirements.txt)
# from chromadb.utils import embedding_functions # Not using built-in EF for Ollama directly here
from flask import current_app, g # Use Flask's 'g' object for request context caching
from .embedding import get_embedding # Use our Ollama embedding function
import logging
import uuid
import os

logger = logging.getLogger(__name__)

# --- ChromaDB Client and Collection Management ---

def get_chroma_client():
    """Gets a ChromaDB client instance, caching it in Flask's request context 'g'."""
    if 'chroma_client' not in g:
        try:
            db_path = current_app.config['VECTOR_DB_PATH']
            # Ensure the directory exists
            os.makedirs(db_path, exist_ok=True)
            logger.info(f"Initializing ChromaDB PersistentClient at path: {db_path}")
            g.chroma_client = chromadb.PersistentClient(path=db_path)
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}", exc_info=True)
            raise RuntimeError("Could not connect to vector database.") from e
    return g.chroma_client

def get_vector_db_collection():
    """
    Initializes and returns the ChromaDB collection, caching it in Flask's 'g'.
    Uses the client from get_chroma_client().
    """
    if 'chroma_collection' not in g:
        client = get_chroma_client()
        collection_name = current_app.config['VECTOR_DB_COLLECTION']
        try:
            logger.info(f"Getting or creating ChromaDB collection: {collection_name}")
            # Note: We are NOT specifying an embedding_function here because we'll
            # generate embeddings manually using our get_embedding function before adding/querying.
            # This gives more control over the embedding process (e.g., retries).
            g.chroma_collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"} # Specify distance metric (cosine is common for embeddings)
            )
            logger.info(f"Vector DB Collection '{collection_name}' ready.")
        except Exception as e:
            logger.error(f"Failed to get or create ChromaDB collection '{collection_name}': {e}", exc_info=True)
            raise RuntimeError(f"Could not get or create vector collection '{collection_name}'.") from e
    return g.chroma_collection

# --- Document Operations ---

def add_document(text: str, metadata: dict = None, doc_id: str = None):
    """
    Adds a document chunk to the vector store after generating its embedding.
    """
    collection = get_vector_db_collection()
    if not text or not text.strip():
        logger.warning("Attempted to add empty document.")
        return None

    doc_id = doc_id or str(uuid.uuid4()) # Generate unique ID if not provided
    metadata = metadata or {}
    metadata['source'] = metadata.get('source', 'unknown') # Ensure source is present

    try:
        # 1. Generate embedding first
        embedding = get_embedding(text.strip())
        if embedding is None:
             logger.error(f"Failed to generate embedding for doc_id {doc_id}, cannot add to store.")
             return None # Or raise an error

        # 2. Add to ChromaDB collection
        collection.add(
            ids=[doc_id],
            embeddings=[embedding], # Provide pre-generated embedding
            documents=[text.strip()],
            metadatas=[metadata]
        )
        logger.info(f"Added document with ID: {doc_id} (Source: {metadata['source']})")
        return doc_id
    except chromadb.errors.IDAlreadyExistsError:
         logger.warning(f"Document with ID {doc_id} already exists. Skipping addition.")
         # Optionally implement update logic here using collection.update()
         return doc_id # Return existing ID
    except Exception as e:
        logger.error(f"Failed to add document ID {doc_id} to vector store: {e}", exc_info=True)
        return None

def search_similar(query_text: str, top_k: int = 3, where_filter: dict = None):
    """
    Searches for documents similar to the query text using its embedding.
    Returns only the document texts.
    """
    collection = get_vector_db_collection()
    if not query_text or not query_text.strip():
        logger.warning("Attempted search with empty query.")
        return []
    try:
        # 1. Generate query embedding
        query_embedding = get_embedding(query_text.strip())
        if query_embedding is None:
            logger.error("Failed to generate query embedding for search.")
            return []

        # 2. Query the collection
        logger.debug(f"Querying collection '{collection.name}' with top_k={top_k}, filter={where_filter}")
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=['documents', 'metadatas', 'distances'], # Include desired fields
            where=where_filter # Optional metadata filter (e.g., {"source": "manual"})
        )

        # Extract and log results carefully
        docs = results.get('documents', [[]])[0]
        # metadatas = results.get('metadatas', [[]])[0]
        # distances = results.get('distances', [[]])[0]
        logger.debug(f"Vector search found {len(docs)} results for query: '{query_text[:50]}...'")
        # logger.debug(f"Distances: {distances}") # Log distances for relevance check

        return docs # Return only the document text for simplicity

    except Exception as e:
        logger.error(f"Failed during vector search: {e}", exc_info=True)
        return []

# --- Optional: Utility functions ---
def count_documents():
    """Returns the total number of documents in the collection."""
    try:
        collection = get_vector_db_collection()
        return collection.count()
    except Exception as e:
        logger.error(f"Failed to count documents: {e}", exc_info=True)
        return -1 # Indicate error

def delete_document(doc_id: str):
    """Deletes a document by its ID."""
    try:
        collection = get_vector_db_collection()
        collection.delete(ids=[doc_id])
        logger.info(f"Deleted document with ID: {doc_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete document ID {doc_id}: {e}", exc_info=True)
        return False
