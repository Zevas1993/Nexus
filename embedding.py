"""
Embedding service for RAG system.

This module provides text embedding functionality using various models.
"""

from typing import Dict, Any, List, Optional, Union
import logging
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize embedding service.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.model_name = config.get('EMBEDDING_MODEL', 'all-mpnet-base-v2')
        self.model = None
        self.dimension = None
        self.initialize()
    
    def initialize(self):
        """Initialize embedding model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            # Get embedding dimension by encoding a test string
            test_embedding = self.model.encode("test")
            self.dimension = len(test_embedding)
            logger.info(f"Embedding model loaded with dimension: {self.dimension}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise
    
    def embed_text(self, text: Union[str, List[str]]) -> np.ndarray:
        """Generate embeddings for text.
        
        Args:
            text: Text string or list of strings
            
        Returns:
            Numpy array of embeddings
            
        Raises:
            ValueError: If model is not initialized
        """
        if not self.model:
            raise ValueError("Embedding model not initialized")
        
        try:
            embeddings = self.model.encode(text)
            return embeddings
        except Exception as e:
            logger.error(f"Error generating embeddings: {str(e)}")
            raise
    
    def similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0-1)
        """
        if not self.model:
            raise ValueError("Embedding model not initialized")
        
        try:
            embedding1 = self.model.encode(text1)
            embedding2 = self.model.encode(text2)
            
            # Normalize embeddings
            embedding1 = embedding1 / np.linalg.norm(embedding1)
            embedding2 = embedding2 / np.linalg.norm(embedding2)
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            raise
