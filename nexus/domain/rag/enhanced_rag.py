"""
Enhanced Retrieval-Augmented Generation for Nexus AI Assistant.

This module provides advanced context retrieval and augmentation capabilities
for improving language model responses with external knowledge.
"""
import os
import logging
from typing import Dict, Any, List, Optional, Union
import json
import asyncio
import numpy as np
from numpy.linalg import norm

# Attempt to import SentenceTransformer embeddings utility
try:
    from sentence_transformers.util import cos_sim
except ImportError:
    cos_sim = None
    logging.warning("sentence_transformers.util.cos_sim not available. Cosine similarity calculation will use numpy.")


logger = logging.getLogger(__name__)

# Assuming LanguageModelService is accessible, adjust import as needed
# from ..language.language_model_service import LanguageModelService

class EnhancedRAGService:
    """Provides retrieval-augmented generation capabilities."""

    VERSION = "1.0.2" # Incremented version

    def __init__(self, app_context, config=None):
        """Initialize enhanced RAG service.

        Args:
            app_context: The application context to access other services.
            config: Configuration dictionary
        """
        self.app_context = app_context
        self.config = config or {}
        self.data_dir = self.config.get("DATA_DIR", "data/knowledge_base")
        self.max_chunks = self.config.get("MAX_CHUNKS", 3) # Reduced default chunks for context window
        self.embeddings = None
        self.vector_store = None # Placeholder for future vector store integration
        self.index = {} # In-memory index (to be replaced)
        self.language_model = None # To be fetched from app_context

    async def initialize(self):
        """Initialize the RAG service."""
        logger.info("Initializing Enhanced RAG service")

        try:
            # Ensure data directory exists
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir, exist_ok=True)
                logger.info(f"Created data directory: {self.data_dir}")

            # Initialize embeddings
            await self._initialize_embeddings()

            # Initialize Language Model Service dependency
            await self._initialize_language_model()

            # Build index from existing knowledge base
            await self._build_index() # This still uses the in-memory index for now

            logger.info("Enhanced RAG service initialized")
        except Exception as e:
            logger.error(f"Error initializing Enhanced RAG: {str(e)}", exc_info=getattr(self.app_context, 'debug', False))
            # RAG might not function correctly if initialization fails

    async def _initialize_language_model(self):
        """Initialize the language model service from app context."""
        try:
            # Dynamically import to avoid circular dependencies if necessary
            from ..language.language_model_service import LanguageModelService
            self.language_model = self.app_context.get_service(LanguageModelService)
            if not self.language_model:
                raise ValueError("LanguageModelService not found in app context.")
            # Ensure language model is initialized if needed (optional, depends on service design)
            # if hasattr(self.language_model, 'initialize') and not self.language_model.is_initialized:
            #     await self.language_model.initialize()
            logger.info("LanguageModelService obtained for RAG.")
        except (ImportError, ValueError, AttributeError) as e:
            logger.error(f"Failed to obtain or initialize LanguageModelService: {e}", exc_info=getattr(self.app_context, 'debug', False))
            self.language_model = None # Ensure it's None if unavailable

    async def _initialize_embeddings(self):
        """Initialize embeddings model."""
        try:
            # Try to use sentence-transformers if available
            from sentence_transformers import SentenceTransformer
            model_name = self.config.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            self.embeddings = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available. RAG retrieval quality will be significantly impacted.")
            # Removed the ineffective word-count fallback
            self.embeddings = None
            logger.error("No suitable embedding model found. Enhanced RAG will be disabled.")

    # Removed _initialize_local_embeddings as it was ineffective

    async def _build_index(self):
        """Build index from knowledge base files."""
        if not os.path.exists(self.data_dir):
            logger.warning(f"Knowledge base directory not found: {self.data_dir}")
            return

        try:
            # Loop through all files in the knowledge base
            for filename in os.listdir(self.data_dir):
                if not filename.endswith('.txt') and not filename.endswith('.md'):
                    continue

                file_path = os.path.join(self.data_dir, filename)
                logger.info(f"Indexing: {file_path}")

                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Split content into chunks
                chunks = self._split_content(content)

                # Create embeddings for each chunk ONLY if embeddings model is available
                if not self.embeddings:
                    logger.warning("Embeddings model not initialized, skipping indexing.")
                    break # Stop trying to index files if no embeddings

                try:
                    # Attempt batch encoding for efficiency
                    embeddings_list = self.embeddings.encode(chunks)
                except Exception as encode_error:
                    logger.error(f"Error encoding chunks for {filename}: {encode_error}", exc_info=getattr(self.app_context, 'debug', False))
                    continue # Skip this file if encoding fails

                for i, chunk in enumerate(chunks):
                    # Store in index
                    key = f"{filename}:{i}"
                    self.index[key] = {
                        "content": chunk,
                        "source": filename,
                        "chunk_id": i,
                        "embedding": embeddings_list[i] # Use pre-computed embedding
                    }

            if self.embeddings:
                logger.info(f"Indexed {len(self.index)} chunks from knowledge base")
            else:
                logger.warning("Indexing skipped due to missing embedding model.")
        except Exception as e:
            logger.error(f"Error building index: {str(e)}", exc_info=getattr(self.app_context, 'debug', False))

    def _split_content(self, content: str, chunk_size: int = 512) -> List[str]:
        """Split content into chunks.

        Args:
            content: Text content to split
            chunk_size: Maximum chunk size in characters

        Returns:
            List of text chunks
        """
        # Simple splitting by paragraphs and then by chunk size
        paragraphs = content.split('\n\n')
        chunks = []

        current_chunk = ""
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= chunk_size:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                if len(para) > chunk_size:
                    # Split paragraph into smaller chunks if it's too long
                    words = para.split()
                    current_chunk = ""
                    for word in words:
                        if len(current_chunk) + len(word) + 1 <= chunk_size:
                            if current_chunk:
                                current_chunk += " "
                            current_chunk += word
                        else:
                            chunks.append(current_chunk)
                            current_chunk = word
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a request using retrieval and generation.

        Args:
            request: Request string (used as query if 'query' not provided)
            **kwargs: Additional parameters
                - query: Specific query to retrieve information for
                - limit: Maximum number of results (defaults to self.max_chunks)
                - model: Preferred language model for generation (passed from orchestrator)
                - context_window: Max context window size for the LLM (passed from orchestrator)

        Returns:
            Processing result including generated response and sources
        """
        query = kwargs.get('query', request)
        limit = kwargs.get('limit', self.max_chunks)
        preferred_model = kwargs.get('model') # Model preference from orchestrator
        # context_window = kwargs.get('context_window') # Optional: Use if needed for prompt construction

        if not self.embeddings:
            logger.error("RAG process called but embeddings are not available.")
            return {
                "status": "error",
                "message": "Embeddings service not initialized or failed."
            }
        if not self.language_model:
            logger.error("RAG process called but language model is not available.")
            return {
                "status": "error",
                "message": "Language model service not initialized or failed."
            }

        try:
            # 1. Retrieve relevant chunks
            retrieved_results = await self._retrieve(query, limit)

            if not retrieved_results:
                logger.info(f"No relevant documents found for query: '{query}'")
                # Optionally, still try to generate a response without context
                # Or return a specific message
                # For now, let's try generating without context
                context_str = "No relevant context found."
                source_documents = []
            else:
                # Prepare context string for the language model
                context_str = "\n\n".join([f"Source: {res['source']}\nContent: {res['content']}" for res in retrieved_results])
                source_documents = [
                    {"source": res["source"], "content": res["content"]} for res in retrieved_results
                ] # Simplified source info

            # 2. Construct Prompt
            # Basic prompt template, can be made more sophisticated
            prompt = f"""Based on the following context, answer the query. If the context doesn't provide the answer, say you don't know.

Context:
{context_str}

Query: {query}

Answer:"""

            # 3. Generate Response using Language Model
            logger.debug(f"Generating response for query: '{query}' with {len(source_documents)} sources.")
            generation_params = {}
            if preferred_model:
                generation_params['model'] = preferred_model

            llm_response = await self.language_model.process(prompt, **generation_params)

            # Extract the generated text
            generated_text = llm_response.get("text", "Error: Could not extract generated text.")
            model_used = llm_response.get("model", "unknown")

            return {
                "status": "success",
                "result": { # Match the structure expected by RagProcessor
                    "response": generated_text,
                    "source_documents": source_documents,
                },
                "model": model_used # Include the model used for generation
            }

        except Exception as e:
            logger.error(f"Error during RAG process: {str(e)}", exc_info=getattr(self.app_context, 'debug', False))
            return {
                "status": "error",
                "message": f"Error during RAG processing: {str(e)}"
            }

    async def _retrieve(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks for a query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of relevant chunks with metadata
        """
        if not self.index:
            logger.warning("Retrieval attempted but index is empty.")
            return []

        try:
            # Get query embedding
            query_embedding = self.embeddings.encode(query)

            # Calculate similarity with all chunks (Inefficient - replace with vector store later)
            similarities = []
            for key, item in self.index.items():
                # Ensure item has an embedding
                if "embedding" not in item:
                    logger.warning(f"Chunk {key} missing embedding, skipping.")
                    continue
                similarity = self._calculate_similarity(query_embedding, item["embedding"])
                similarities.append((key, similarity))

            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)

            # Return top results
            results = []
            for key, similarity in similarities[:limit]:
                item = self.index[key]
                results.append({
                    "content": item["content"],
                    "source": item["source"],
                    "similarity": float(similarity) # Ensure float for JSON serialization
                })

            logger.debug(f"Retrieved {len(results)} chunks for query '{query}'.")
            return results
        except Exception as e:
            logger.error(f"Error retrieving data: {str(e)}", exc_info=getattr(self.app_context, 'debug', False))
            return []

    def _calculate_similarity(self, embedding1, embedding2) -> float:
        """Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding (numpy array or list)
            embedding2: Second embedding (numpy array or list)

        Returns:
            Similarity score (float)
        """
        # Convert to numpy arrays if they aren't already
        emb1 = np.asarray(embedding1)
        emb2 = np.asarray(embedding2)

        # Check if sentence_transformers utility is available and inputs are suitable
        if cos_sim is not None and emb1.ndim == 1 and emb2.ndim == 1:
            try:
                # cos_sim expects 2D arrays
                similarity = cos_sim(emb1.reshape(1, -1), emb2.reshape(1, -1))
                return float(similarity[0][0])
            except Exception as e:
                logger.warning(f"Error using sentence_transformers.cos_sim: {e}. Falling back to numpy.")

        # Fallback to numpy calculation
        try:
            cosine = np.dot(emb1, emb2) / (norm(emb1) * norm(emb2))
            # Handle potential NaN if norm is zero
            return float(0.0 if np.isnan(cosine) else cosine)
        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Error calculating numpy cosine similarity: {e}")
            return 0.0

    # Removed _format_response as generation now handles the final output

    async def add_to_knowledge_base(self, content: str, source: str) -> Dict[str, Any]:
        """Add content to the knowledge base.

        Args:
            content: Content to add
            source: Source identifier

        Returns:
            Result of the operation
        """
        if not self.embeddings:
            logger.error("Cannot add to knowledge base: Embeddings not available.")
            return {
                "status": "error",
                "message": "Embeddings not available"
            }

        try:
            # Ensure file has .txt extension
            if not source.endswith(".txt") and not source.endswith(".md"):
                source += ".txt"

            file_path = os.path.join(self.data_dir, source)

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write content to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Saved content to {file_path}")

            # Split content into chunks
            chunks = self._split_content(content)

            # Add to index
            if not chunks:
                logger.warning(f"No chunks generated for {source}")
                return {
                    "status": "warning",
                    "message": f"No content chunks generated for {source}",
                    "data": {"source": source, "chunks": 0}
                }

            try:
                embeddings_list = self.embeddings.encode(chunks)
            except Exception as encode_error:
                 logger.error(f"Error encoding chunks for {source} during add: {encode_error}", exc_info=getattr(self.app_context, 'debug', False))
                 return {
                    "status": "error",
                    "message": f"Failed to encode content for {source}: {encode_error}"
                 }

            added_count = 0
            for i, chunk in enumerate(chunks):
                key = f"{source}:{i}"
                self.index[key] = {
                    "content": chunk,
                    "source": source,
                    "chunk_id": i,
                    "embedding": embeddings_list[i]
                }
                added_count += 1

            logger.info(f"Added {added_count} chunks to in-memory index from {source}")
            return {
                "status": "success",
                "message": f"Added {added_count} chunks to knowledge base from {source}",
                "data": {
                    "source": source,
                    "chunks": added_count
                }
            }
        except Exception as e:
            logger.error(f"Error adding to knowledge base: {str(e)}", exc_info=getattr(self.app_context, 'debug', False))
            return {
                "status": "error",
                "message": f"Error adding to knowledge base: {str(e)}"
            }
