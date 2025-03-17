"""
Document retrieval for RAG system.

This module provides functionality for retrieving relevant documents based on queries.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
import logging
import os
import json
import numpy as np
from ..base import AsyncService
from .embedding import EmbeddingService
from .indexing import Document

logger = logging.getLogger(__name__)

class RetrievalService(AsyncService):
    """Service for retrieving relevant documents."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize retrieval service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.storage_dir = self.config.get('INDEX_STORAGE_DIR', 'storage/index')
        self.embedding_service = None
    
    def _get_embedding_service(self) -> EmbeddingService:
        """Get embedding service.
        
        Returns:
            Embedding service instance
        """
        if not self.embedding_service and self.app_context:
            self.embedding_service = self.app_context.get_service(EmbeddingService)
        
        if not self.embedding_service:
            self.embedding_service = EmbeddingService(self.config)
            
        return self.embedding_service
    
    def _load_collection(self, collection: str) -> List[Dict[str, Any]]:
        """Load all documents from a collection.
        
        Args:
            collection: Collection name
            
        Returns:
            List of document dictionaries
        """
        collection_dir = os.path.join(self.storage_dir, collection)
        if not os.path.exists(collection_dir):
            logger.warning(f"Collection directory not found: {collection_dir}")
            return []
        
        documents = []
        for filename in os.listdir(collection_dir):
            if filename.endswith('.json'):
                file_path = os.path.join(collection_dir, filename)
                try:
                    with open(file_path, 'r') as f:
                        document = json.load(f)
                        documents.append(document)
                except Exception as e:
                    logger.error(f"Error loading document {file_path}: {str(e)}")
        
        logger.info(f"Loaded {len(documents)} documents from collection {collection}")
        return documents
    
    def _vector_search(self, query_embedding: np.ndarray, documents: List[Dict[str, Any]], 
                      top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform vector search on documents.
        
        Args:
            query_embedding: Query embedding
            documents: List of document dictionaries
            top_k: Number of top results to return
            
        Returns:
            List of top matching documents with scores
        """
        results = []
        
        # Normalize query embedding
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        for doc in documents:
            if 'embedding' not in doc:
                continue
                
            # Convert embedding to numpy array if it's a list
            doc_embedding = np.array(doc['embedding'])
            
            # Normalize document embedding
            doc_embedding = doc_embedding / np.linalg.norm(doc_embedding)
            
            # Calculate cosine similarity
            similarity = np.dot(query_embedding, doc_embedding)
            
            results.append({
                "document": doc,
                "score": float(similarity)
            })
        
        # Sort by score in descending order
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top k results
        return results[:top_k]
    
    def _hybrid_search(self, query: str, query_embedding: np.ndarray, 
                      documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """Perform hybrid search (vector + keyword) on documents.
        
        Args:
            query: Query string
            query_embedding: Query embedding
            documents: List of document dictionaries
            top_k: Number of top results to return
            
        Returns:
            List of top matching documents with scores
        """
        # First, get vector search results
        vector_results = self._vector_search(query_embedding, documents, top_k * 2)
        
        # Then, rerank with keyword matching
        keywords = set(query.lower().split())
        for result in vector_results:
            doc = result["document"]
            content = doc.get("content", "").lower()
            
            # Count keyword matches
            keyword_matches = sum(1 for keyword in keywords if keyword in content)
            
            # Adjust score with keyword matches
            result["score"] = result["score"] * 0.7 + (keyword_matches / max(1, len(keywords))) * 0.3
        
        # Sort by adjusted score
        vector_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Return top k results
        return vector_results[:top_k]
    
    async def _process_impl(self, request: str, **kwargs) -> Dict[str, Any]:
        """Implementation of request processing.
        
        Args:
            request: Query string
            **kwargs: Additional parameters
                - collection: Collection name
                - top_k: Number of top results to return
                - search_type: Type of search (vector, hybrid)
                
        Returns:
            Retrieval results
        """
        collection = kwargs.get('collection', 'default')
        top_k = kwargs.get('top_k', 5)
        search_type = kwargs.get('search_type', 'hybrid')
        
        # Load documents from collection
        documents = self._load_collection(collection)
        if not documents:
            return {
                "query": request,
                "results": [],
                "count": 0
            }
        
        # Get query embedding
        embedding_service = self._get_embedding_service()
        query_embedding = embedding_service.embed_text(request)
        
        # Perform search
        if search_type == 'hybrid':
            search_results = self._hybrid_search(request, query_embedding, documents, top_k)
        else:
            search_results = self._vector_search(query_embedding, documents, top_k)
        
        # Format results
        results = []
        for result in search_results:
            doc = result["document"]
            results.append({
                "id": doc.get("id"),
                "content": doc.get("content"),
                "metadata": doc.get("metadata", {}),
                "score": result["score"]
            })
        
        return {
            "query": request,
            "results": results,
            "count": len(results)
        }
