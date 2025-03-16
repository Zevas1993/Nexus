"""
Enhanced RAG system for Nexus AI Assistant.

This module provides an improved RAG system with hybrid search, 
reranking, and multi-vector retrieval capabilities.
"""

from typing import Dict, Any, List, Optional, Union
import logging
import numpy as np
from sentence_transformers import SentenceTransformer, util
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
from ...domain.rag.embedding import EmbeddingService
from ...domain.rag.retrieval import RetrievalService
from ...domain.rag.generation import GenerationService
from ...domain.base import AsyncService

logger = logging.getLogger(__name__)

class EnhancedRAGService(AsyncService):
    """Enhanced RAG service with hybrid search and reranking."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize enhanced RAG service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.embedding_service = None
        self.retrieval_service = None
        self.generation_service = None
        self.reranker_model = None
        self.reranker_tokenizer = None
        self.use_hybrid_search = self.config.get('USE_HYBRID_SEARCH', True)
        self.use_reranking = self.config.get('USE_RERANKING', True)
        self.top_k = self.config.get('RAG_TOP_K', 5)
        self.reranking_top_k = self.config.get('RERANKING_TOP_K', 20)
        self.hybrid_alpha = self.config.get('HYBRID_ALPHA', 0.7)  # Weight for semantic search vs BM25
    
    async def initialize(self):
        """Initialize enhanced RAG service."""
        # Get required services
        if self.app_context:
            self.embedding_service = self.app_context.get_service(EmbeddingService)
            self.retrieval_service = self.app_context.get_service(RetrievalService)
            self.generation_service = self.app_context.get_service(GenerationService)
        
        # Initialize reranker if enabled
        if self.use_reranking:
            try:
                model_name = self.config.get('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
                self.reranker_model = AutoModelForSequenceClassification.from_pretrained(model_name)
                self.reranker_tokenizer = AutoTokenizer.from_pretrained(model_name)
                
                # Move to GPU if available
                if torch.cuda.is_available():
                    self.reranker_model = self.reranker_model.to('cuda')
                
                logger.info(f"Initialized reranker model: {model_name}")
            except Exception as e:
                logger.error(f"Error initializing reranker: {str(e)}")
                self.use_reranking = False
        
        logger.info("Enhanced RAG service initialized")
    
    async def _process_impl(self, request: str, **kwargs) -> Dict[str, Any]:
        """Implementation of request processing.
        
        Args:
            request: User query
            **kwargs: Additional parameters
                - collection: Collection name
                - top_k: Number of results to retrieve
                - use_hybrid_search: Whether to use hybrid search
                - use_reranking: Whether to use reranking
                
        Returns:
            Processing result
        """
        collection = kwargs.get('collection', 'default')
        top_k = kwargs.get('top_k', self.top_k)
        use_hybrid_search = kwargs.get('use_hybrid_search', self.use_hybrid_search)
        use_reranking = kwargs.get('use_reranking', self.use_reranking)
        
        try:
            # Step 1: Retrieve relevant documents
            if use_hybrid_search:
                # Hybrid search (semantic + keyword)
                results = await self._hybrid_search(request, collection, top_k)
            else:
                # Standard semantic search
                results = await self._semantic_search(request, collection, top_k)
            
            # Step 2: Rerank results if enabled
            if use_reranking and self.reranker_model:
                results = await self._rerank_results(request, results)
            
            # Step 3: Generate response
            context = self._format_context(results)
            response = await self._generate_response(request, context)
            
            return {
                "status": "success",
                "result": {
                    "query": request,
                    "response": response,
                    "sources": [
                        {
                            "content": doc["content"],
                            "metadata": doc["metadata"],
                            "score": doc["score"]
                        }
                        for doc in results[:top_k]
                    ]
                }
            }
        except Exception as e:
            logger.error(f"Error processing RAG request: {str(e)}")
            return {
                "status": "error",
                "message": f"Error processing RAG request: {str(e)}"
            }
    
    async def _semantic_search(self, query: str, collection: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform semantic search.
        
        Args:
            query: User query
            collection: Collection name
            top_k: Number of results to retrieve
            
        Returns:
            List of retrieved documents
        """
        # Get query embedding
        query_embedding = await self.embedding_service.process(
            query,
            action='embed'
        )
        
        if not query_embedding.get("status") == "success":
            raise ValueError("Failed to generate query embedding")
        
        # Retrieve documents
        retrieval_result = await self.retrieval_service.process(
            query,
            embedding=query_embedding["result"]["embedding"],
            collection=collection,
            top_k=top_k
        )
        
        if not retrieval_result.get("status") == "success":
            raise ValueError("Failed to retrieve documents")
        
        return retrieval_result["result"]["documents"]
    
    async def _hybrid_search(self, query: str, collection: str, top_k: int) -> List[Dict[str, Any]]:
        """Perform hybrid search (semantic + keyword).
        
        Args:
            query: User query
            collection: Collection name
            top_k: Number of results to retrieve
            
        Returns:
            List of retrieved documents
        """
        # Get more results for reranking
        retrieval_top_k = max(top_k * 2, self.reranking_top_k) if self.use_reranking else top_k
        
        # Get query embedding
        query_embedding = await self.embedding_service.process(
            query,
            action='embed'
        )
        
        if not query_embedding.get("status") == "success":
            raise ValueError("Failed to generate query embedding")
        
        # Retrieve documents using semantic search
        semantic_result = await self.retrieval_service.process(
            query,
            embedding=query_embedding["result"]["embedding"],
            collection=collection,
            top_k=retrieval_top_k
        )
        
        if not semantic_result.get("status") == "success":
            raise ValueError("Failed to retrieve documents with semantic search")
        
        # Retrieve documents using keyword search (BM25)
        keyword_result = await self.retrieval_service.process(
            query,
            action='keyword_search',
            collection=collection,
            top_k=retrieval_top_k
        )
        
        if not keyword_result.get("status") == "success":
            raise ValueError("Failed to retrieve documents with keyword search")
        
        # Combine results with weighted scores
        semantic_docs = semantic_result["result"]["documents"]
        keyword_docs = keyword_result["result"]["documents"]
        
        # Create document ID to score mappings
        semantic_scores = {doc["id"]: doc["score"] for doc in semantic_docs}
        keyword_scores = {doc["id"]: doc["score"] for doc in keyword_docs}
        
        # Normalize scores
        if semantic_scores:
            max_semantic = max(semantic_scores.values())
            min_semantic = min(semantic_scores.values())
            semantic_range = max_semantic - min_semantic
            if semantic_range > 0:
                semantic_scores = {k: (v - min_semantic) / semantic_range for k, v in semantic_scores.items()}
        
        if keyword_scores:
            max_keyword = max(keyword_scores.values())
            min_keyword = min(keyword_scores.values())
            keyword_range = max_keyword - min_keyword
            if keyword_range > 0:
                keyword_scores = {k: (v - min_keyword) / keyword_range for k, v in keyword_scores.items()}
        
        # Combine document sets
        all_doc_ids = set(semantic_scores.keys()) | set(keyword_scores.keys())
        combined_docs = []
        
        for doc_id in all_doc_ids:
            # Get document from either result set
            doc = next((d for d in semantic_docs if d["id"] == doc_id), None)
            if not doc:
                doc = next((d for d in keyword_docs if d["id"] == doc_id), None)
            
            # Calculate combined score
            semantic_score = semantic_scores.get(doc_id, 0)
            keyword_score = keyword_scores.get(doc_id, 0)
            combined_score = self.hybrid_alpha * semantic_score + (1 - self.hybrid_alpha) * keyword_score
            
            # Add to combined results
            doc_copy = doc.copy()
            doc_copy["score"] = combined_score
            doc_copy["semantic_score"] = semantic_score
            doc_copy["keyword_score"] = keyword_score
            combined_docs.append(doc_copy)
        
        # Sort by combined score
        combined_docs.sort(key=lambda x: x["score"], reverse=True)
        
        return combined_docs[:retrieval_top_k]
    
    async def _rerank_results(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rerank retrieved documents.
        
        Args:
            query: User query
            documents: Retrieved documents
            
        Returns:
            Reranked documents
        """
        if not self.reranker_model or not documents:
            return documents
        
        # Prepare pairs for reranking
        pairs = []
        for doc in documents:
            pairs.append([query, doc["content"]])
        
        # Tokenize
        features = self.reranker_tokenizer(
            pairs,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=512
        )
        
        # Move to GPU if available
        if torch.cuda.is_available():
            for key in features:
                features[key] = features[key].to('cuda')
        
        # Get scores
        with torch.no_grad():
            scores = self.reranker_model(**features).logits
            scores = scores.cpu().numpy()
        
        # Update document scores
        for i, doc in enumerate(documents):
            doc["original_score"] = doc["score"]
            doc["score"] = float(scores[i][0])
        
        # Sort by new scores
        documents.sort(key=lambda x: x["score"], reverse=True)
        
        return documents
    
    def _format_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents as context.
        
        Args:
            documents: Retrieved documents
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for i, doc in enumerate(documents[:self.top_k]):
            # Format metadata
            metadata_str = ""
            if doc.get("metadata"):
                metadata_items = []
                for key, value in doc["metadata"].items():
                    if key != "text" and value:  # Skip text field and empty values
                        metadata_items.append(f"{key}: {value}")
                if metadata_items:
                    metadata_str = f" ({', '.join(metadata_items)})"
            
            # Add document to context
            context_parts.append(f"[{i+1}]{metadata_str}\n{doc['content']}\n")
        
        return "\n".join(context_parts)
    
    async def _generate_response(self, query: str, context: str) -> str:
        """Generate response based on query and context.
        
        Args:
            query: User query
            context: Retrieved context
            
        Returns:
            Generated response
        """
        # Generate response
        generation_result = await self.generation_service.process(
            query,
            context=context
        )
        
        if not generation_result.get("status") == "success":
            raise ValueError("Failed to generate response")
        
        return generation_result["result"]["response"]
