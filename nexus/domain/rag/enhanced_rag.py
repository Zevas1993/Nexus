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

logger = logging.getLogger(__name__)

class EnhancedRAGService:
    """Provides retrieval-augmented generation capabilities."""
    
    VERSION = "1.0.0"
    
    def __init__(self, config=None):
        """Initialize enhanced RAG service.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.data_dir = self.config.get("DATA_DIR", "data/knowledge_base")
        self.max_chunks = self.config.get("MAX_CHUNKS", 5)
        self.embeddings = None
        self.vector_store = None
        self.index = {}
        
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
            
            # Build index from existing knowledge base
            await self._build_index()
            
            logger.info("Enhanced RAG service initialized")
        except Exception as e:
            logger.error(f"Error initializing Enhanced RAG: {str(e)}")
            # Continue without RAG if initialization fails
    
    async def _initialize_embeddings(self):
        """Initialize embeddings model."""
        try:
            # Try to use sentence-transformers if available
            from sentence_transformers import SentenceTransformer
            model_name = self.config.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
            self.embeddings = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except ImportError:
            logger.warning("sentence-transformers not available, trying to use local embeddings")
            try:
                # Fall back to a simpler tokenization-based method
                self._initialize_local_embeddings()
            except Exception as e:
                logger.error(f"Error initializing local embeddings: {str(e)}")
                raise
    
    def _initialize_local_embeddings(self):
        """Initialize simple local embeddings based on word counting."""
        # This is a very simplified embedding approach for fallback
        # In real implementation, you would use a proper embedding model
        self.embeddings = {
            "encode": lambda text: {word: text.lower().split().count(word) 
                                   for word in set(text.lower().split())}
        }
        logger.info("Using simple local embeddings (word count based)")
    
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
                
                # Create embeddings for each chunk
                if self.embeddings:
                    for i, chunk in enumerate(chunks):
                        # Store in index
                        key = f"{filename}:{i}"
                        self.index[key] = {
                            "content": chunk,
                            "source": filename,
                            "chunk_id": i,
                            "embedding": self.embeddings.encode(chunk)
                        }
                        
            logger.info(f"Indexed {len(self.index)} chunks from knowledge base")
        except Exception as e:
            logger.error(f"Error building index: {str(e)}")
    
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
        """Process a request.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
                - context: Conversation context
                - query: Specific query to retrieve information for
                - limit: Maximum number of results
                
        Returns:
            Processing result
        """
        query = kwargs.get('query', request)
        limit = kwargs.get('limit', self.max_chunks)
        
        if not self.embeddings:
            return {
                "status": "error",
                "message": "Embeddings not available"
            }
            
        # Retrieve relevant chunks
        results = await self._retrieve(query, limit)
        
        # Format response
        response = self._format_response(results, query)
        
        return {
            "status": "success",
            "data": {
                "query": query, 
                "results": results
            },
            "text": response
        }
    
    async def _retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant chunks for a query.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of relevant chunks with metadata
        """
        if not self.index:
            return []
            
        try:
            # Get query embedding
            query_embedding = self.embeddings.encode(query)
            
            # Calculate similarity with all chunks
            similarities = []
            for key, item in self.index.items():
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
                    "similarity": similarity
                })
                
            return results
        except Exception as e:
            logger.error(f"Error retrieving data: {str(e)}")
            return []
    
    def _calculate_similarity(self, embedding1, embedding2) -> float:
        """Calculate similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Similarity score
        """
        if isinstance(embedding1, dict) and isinstance(embedding2, dict):
            # Simple similarity for word count vectors
            # Calculate cosine similarity
            intersection = set(embedding1.keys()) & set(embedding2.keys())
            if not intersection:
                return 0.0
                
            numerator = sum(embedding1[x] * embedding2[x] for x in intersection)
            sum1 = sum(embedding1[x]**2 for x in embedding1)
            sum2 = sum(embedding2[x]**2 for x in embedding2)
            denominator = (sum1 * sum2) ** 0.5
            
            if denominator == 0:
                return 0.0
                
            return numerator / denominator
        else:
            # For tensor-based embeddings, use a different approach
            # This would be implemented with proper vector similarity in a real system
            return 0.5  # Placeholder
    
    def _format_response(self, results: List[Dict[str, Any]], query: str) -> str:
        """Format retrieval results into a readable response.
        
        Args:
            results: Retrieved results
            query: Original query
            
        Returns:
            Formatted response
        """
        if not results:
            return f"No information found for '{query}'."
            
        response = f"Information retrieved for '{query}':\n\n"
        
        for i, result in enumerate(results, 1):
            response += f"Source: {result['source']}\n"
            response += f"Relevance: {result['similarity']:.2f}\n"
            response += f"Content:\n{result['content']}\n\n"
            
        return response
    
    async def add_to_knowledge_base(self, content: str, source: str) -> Dict[str, Any]:
        """Add content to the knowledge base.
        
        Args:
            content: Content to add
            source: Source identifier
            
        Returns:
            Result of the operation
        """
        if not self.embeddings:
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
                
            # Split content into chunks
            chunks = self._split_content(content)
            
            # Add to index
            for i, chunk in enumerate(chunks):
                key = f"{source}:{i}"
                self.index[key] = {
                    "content": chunk,
                    "source": source,
                    "chunk_id": i,
                    "embedding": self.embeddings.encode(chunk)
                }
                
            return {
                "status": "success",
                "message": f"Added {len(chunks)} chunks to knowledge base from {source}",
                "data": {
                    "source": source,
                    "chunks": len(chunks)
                }
            }
        except Exception as e:
            logger.error(f"Error adding to knowledge base: {str(e)}")
            return {
                "status": "error",
                "message": f"Error adding to knowledge base: {str(e)}"
            }
