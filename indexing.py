"""
Document indexing for RAG system.

This module provides functionality for indexing documents for retrieval.
"""

from typing import Dict, Any, List, Optional, Union, Tuple
import logging
import uuid
import os
import json
from ..base import AsyncService
from .embedding import EmbeddingService

logger = logging.getLogger(__name__)

class Document:
    """Document class for RAG system."""
    
    def __init__(self, 
                 content: str, 
                 metadata: Optional[Dict[str, Any]] = None,
                 doc_id: Optional[str] = None):
        """Initialize document.
        
        Args:
            content: Document content
            metadata: Optional metadata
            doc_id: Optional document ID (generated if not provided)
        """
        self.content = content
        self.metadata = metadata or {}
        self.doc_id = doc_id or str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary.
        
        Returns:
            Dictionary representation of document
        """
        return {
            "id": self.doc_id,
            "content": self.content,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create document from dictionary.
        
        Args:
            data: Dictionary representation of document
            
        Returns:
            Document instance
        """
        return cls(
            content=data["content"],
            metadata=data.get("metadata", {}),
            doc_id=data.get("id")
        )


class DocumentChunker:
    """Service for chunking documents into smaller pieces."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize document chunker.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.chunk_size = config.get('CHUNK_SIZE', 500)
        self.chunk_overlap = config.get('CHUNK_OVERLAP', 100)
    
    def chunk_document(self, document: Document) -> List[Document]:
        """Split document into chunks.
        
        Args:
            document: Document to chunk
            
        Returns:
            List of document chunks
        """
        content = document.content
        chunks = []
        
        # Simple chunking by character count
        # In a production system, you might want to use more sophisticated
        # chunking strategies that respect sentence or paragraph boundaries
        start = 0
        while start < len(content):
            end = min(start + self.chunk_size, len(content))
            
            # Try to find a good breaking point (space or newline)
            if end < len(content):
                # Look for a space or newline to break at
                for i in range(end - 1, max(start, end - 50), -1):
                    if content[i] in [' ', '\n', '.', '!', '?']:
                        end = i + 1
                        break
            
            chunk_content = content[start:end]
            
            # Create new document for the chunk
            chunk_metadata = document.metadata.copy()
            chunk_metadata.update({
                "parent_id": document.doc_id,
                "chunk_index": len(chunks),
                "chunk_start": start,
                "chunk_end": end
            })
            
            chunk = Document(
                content=chunk_content,
                metadata=chunk_metadata,
                doc_id=f"{document.doc_id}_chunk_{len(chunks)}"
            )
            
            chunks.append(chunk)
            
            # Move start position for next chunk, considering overlap
            start = end - self.chunk_overlap
            
            # Ensure we make progress
            if start <= chunks[0].metadata["chunk_start"]:
                start = end
        
        logger.info(f"Split document {document.doc_id} into {len(chunks)} chunks")
        return chunks


class IndexingService(AsyncService):
    """Service for indexing documents."""
    
    def __init__(self, app_context=None, config=None):
        """Initialize indexing service.
        
        Args:
            app_context: Application context
            config: Configuration dictionary
        """
        super().__init__(app_context, config)
        self.storage_dir = self.config.get('INDEX_STORAGE_DIR', 'storage/index')
        self.chunker = DocumentChunker(self.config)
        self.embedding_service = None
        
        # Ensure storage directory exists
        os.makedirs(self.storage_dir, exist_ok=True)
    
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
    
    async def _process_impl(self, request: str, **kwargs) -> Dict[str, Any]:
        """Implementation of request processing.
        
        Args:
            request: Request string (ignored)
            **kwargs: Additional parameters
                - document: Document to index
                - collection: Collection name
                
        Returns:
            Indexing result
        """
        document = kwargs.get('document')
        collection = kwargs.get('collection', 'default')
        
        if not document:
            raise ValueError("Document is required")
        
        # Convert to Document object if necessary
        if isinstance(document, dict):
            document = Document.from_dict(document)
        elif isinstance(document, str):
            document = Document(content=document)
        
        # Chunk document
        chunks = self.chunker.chunk_document(document)
        
        # Get embeddings for chunks
        embedding_service = self._get_embedding_service()
        chunk_contents = [chunk.content for chunk in chunks]
        embeddings = embedding_service.embed_text(chunk_contents)
        
        # Store chunks and embeddings
        results = []
        for i, chunk in enumerate(chunks):
            chunk_embedding = embeddings[i].tolist()
            chunk_data = chunk.to_dict()
            chunk_data['embedding'] = chunk_embedding
            
            # Save to storage
            chunk_path = os.path.join(self.storage_dir, collection, f"{chunk.doc_id}.json")
            os.makedirs(os.path.dirname(chunk_path), exist_ok=True)
            
            with open(chunk_path, 'w') as f:
                json.dump(chunk_data, f)
            
            results.append({
                "id": chunk.doc_id,
                "content_length": len(chunk.content)
            })
        
        return {
            "document_id": document.doc_id,
            "collection": collection,
            "chunks": results,
            "chunk_count": len(chunks)
        }
