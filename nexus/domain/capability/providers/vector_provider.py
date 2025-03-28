"""
Vector Database Providers for Nexus AI Assistant.

This module provides capability providers for vector storage and retrieval
to enable enhanced RAG capabilities with various vector database solutions.
"""
import logging
import json
import aiohttp
import os
import numpy as np
from typing import Dict, Any, List, Optional, Union, Tuple

from ..abstraction import CapabilityProvider, CapabilityType

logger = logging.getLogger(__name__)

class PineconeProvider(CapabilityProvider):
    """Pinecone provider for vector storage capabilities."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Pinecone provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__("pinecone", config)
        self.api_key = self.config.get("api_key", os.environ.get("PINECONE_API_KEY", ""))
        self.environment = self.config.get("environment", os.environ.get("PINECONE_ENVIRONMENT", ""))
        self.index_name = self.config.get("index_name", "nexus-embeddings")
        self.namespace = self.config.get("namespace", "default")
        # Dimension should ideally come from embedding model config, require it here?
        self.dimension = self.config.get("dimension")
        if not self.dimension:
             logger.error("Pinecone provider requires 'dimension' in config.")
             self.enabled = False
             return
        self.timeout = self.config.get("timeout", 60)
        # Construct API URL carefully based on environment
        # Example: "https://{index_name}-{project_id}.svc.{environment}.pinecone.io" - project_id might be needed?
        # Using the provided structure for now, assuming environment includes project info if needed by Pinecone.
        self.api_url = f"https://{self.index_name}-{self.environment}.svc.{self.environment}.pinecone.io" # Verify this structure

    async def initialize(self) -> None:
        """Initialize the provider."""
        if not self.api_key or not self.environment:
            logger.warning("Pinecone API key or environment not provided, provider will be disabled")
            self.enabled = False
            return
            
        # Register capabilities
        self.register_capability(CapabilityType.VECTOR_STORAGE, self.vector_operation)
        
        # Test connection and create index if it doesn't exist
        try:
            # First check if the index exists
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Api-Key": self.api_key,
                    "Content-Type": "application/json"
                }
                
                # Check if index exists using the describe index endpoint
                async with session.get(
                    f"https://controller.{self.environment}.pinecone.io/databases/{self.index_name}",
                    headers=headers,
                    timeout=10
                ) as response:
                    if response.status != 200:
                        # Index doesn't exist, try to create it
                        logger.info(f"Pinecone index '{self.index_name}' doesn't exist, attempting creation...")

                        # Create the index - Ensure dimension is correctly passed
                        create_payload = {
                            "name": self.index_name,
                            "dimension": int(self.dimension), # Ensure it's an integer
                            "metric": "cosine", # Common default, make configurable?
                            # Add pod spec configuration if needed (e.g., environment, pod_type)
                            # "spec": { "pod": { "environment": self.environment, "pod_type": "p1.x1" } } # Example
                        }

                        async with session.post(
                            f"https://controller.{self.environment}.pinecone.io/databases",
                            headers=headers,
                            json=create_payload,
                            timeout=30
                        ) as create_response:
                            if create_response.status == 201:
                                logger.info(f"Successfully created index {self.index_name}")
                            else:
                                error_text = await create_response.text()
                                logger.warning(f"Failed to create Pinecone index: {error_text}")
                                self.enabled = False
                                return
                    else:
                        logger.info(f"Index {self.index_name} exists")
                        
                # Test a simple query to ensure the index is ready
                test_vector = [0.0] * self.dimension
                query_payload = {
                    "namespace": self.namespace,
                    "vector": test_vector,
                    "topK": 1,
                    "includeMetadata": True
                }
                
                async with session.post(
                    f"{self.api_url}/query",
                    headers=headers,
                    json=query_payload,
                    timeout=10
                ) as query_response:
                    if query_response.status != 200:
                        error_text = await query_response.text()
                        logger.warning(f"Pinecone query test failed: {error_text}")
                        self.enabled = False
                    else:
                        logger.info("Pinecone connection successful")
                        
        except Exception as e:
            logger.warning(f"Error connecting to Pinecone: {str(e)}")
            self.enabled = False
            
    async def vector_operation(self, 
                            operation: str,
                            vectors: Optional[List[List[float]]] = None,
                            ids: Optional[List[str]] = None,
                            metadata: Optional[List[Dict[str, Any]]] = None,
                            query_vector: Optional[List[float]] = None,
                            top_k: int = 10,
                            namespace: Optional[str] = None,
                            filter: Optional[Dict[str, Any]] = None,
                            **kwargs) -> Dict[str, Any]:
        """Perform vector operations with Pinecone.
        
        Args:
            operation: Operation type ("upsert", "query", "delete", "fetch")
            vectors: List of vectors to upsert
            ids: List of IDs for vectors
            metadata: List of metadata dictionaries for vectors
            query_vector: Vector to query
            top_k: Number of results to return
            namespace: Pinecone namespace
            filter: Query filter
            **kwargs: Additional parameters
            
        Returns:
            Operation result
        """
        if not self.enabled or not self.api_key:
            raise ValueError("Pinecone provider is not enabled")
            
        # Use default namespace if not specified
        namespace = namespace or self.namespace
        
        # Prepare result
        result = {
            "status": "error",
            "error": None,
            "operation": operation,
            "namespace": namespace
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Api-Key": self.api_key,
                    "Content-Type": "application/json"
                }
                
                # Handle different operations
                if operation == "upsert":
                    if not vectors or not ids:
                        raise ValueError("Vectors and IDs are required for upsert operation")
                        
                    if len(vectors) != len(ids):
                        raise ValueError("Number of vectors must match number of IDs")
                        
                    # Prepare upsert data
                    vectors_data = []
                    for i, (vector_id, vector) in enumerate(zip(ids, vectors)):
                        vector_data = {
                            "id": vector_id,
                            "values": vector
                        }
                        
                        # Add metadata if available
                        if metadata and i < len(metadata) and metadata[i]:
                            vector_data["metadata"] = metadata[i]
                            
                        vectors_data.append(vector_data)
                        
                    upsert_payload = {
                        "vectors": vectors_data,
                        "namespace": namespace
                    }
                    
                    # Send upsert request
                    async with session.post(
                        f"{self.api_url}/vectors/upsert",
                        headers=headers,
                        json=upsert_payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            result["error"] = f"Upsert failed: {error_text}"
                        else:
                            response_data = await response.json()
                            result["status"] = "success"
                            result["upserted_count"] = response_data.get("upsertedCount", 0)
                            
                elif operation == "query":
                    if not query_vector:
                        raise ValueError("Query vector is required for query operation")
                        
                    # Prepare query
                    query_payload = {
                        "vector": query_vector,
                        "topK": top_k,
                        "namespace": namespace,
                        "includeMetadata": True,
                        "includeValues": kwargs.get("include_values", False)
                    }
                    
                    # Add filter if provided
                    if filter:
                        query_payload["filter"] = filter
                        
                    # Send query request
                    async with session.post(
                        f"{self.api_url}/query",
                        headers=headers,
                        json=query_payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            result["error"] = f"Query failed: {error_text}"
                        else:
                            response_data = await response.json()
                            result["status"] = "success"
                            result["matches"] = response_data.get("matches", [])
                            result["match_count"] = len(result["matches"])
                            
                elif operation == "delete":
                    delete_payload = {
                        "namespace": namespace
                    }
                    
                    # Add IDs if provided
                    if ids:
                        delete_payload["ids"] = ids
                        
                    # Add filter if provided
                    if filter:
                        delete_payload["filter"] = filter
                        
                    if not ids and not filter:
                        # Delete all vectors in namespace if neither ids nor filter provided
                        delete_payload["deleteAll"] = True
                        
                    # Send delete request
                    async with session.post(
                        f"{self.api_url}/vectors/delete",
                        headers=headers,
                        json=delete_payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            result["error"] = f"Delete failed: {error_text}"
                        else:
                            response_data = await response.json()
                            result["status"] = "success"
                            result["deleted_count"] = response_data.get("deletedCount", 0)
                            
                elif operation == "fetch":
                    if not ids:
                        raise ValueError("IDs are required for fetch operation")
                        
                    # Prepare fetch request
                    fetch_payload = {
                        "ids": ids,
                        "namespace": namespace
                    }
                    
                    # Send fetch request
                    async with session.get(
                        f"{self.api_url}/vectors/fetch",
                        headers=headers,
                        params=fetch_payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            result["error"] = f"Fetch failed: {error_text}"
                        else:
                            response_data = await response.json()
                            result["status"] = "success"
                            result["vectors"] = response_data.get("vectors", {})
                            result["fetch_count"] = len(result["vectors"])
                            
                else:
                    raise ValueError(f"Unsupported operation: {operation}")
                    
        except Exception as e:
            logger.error(f"Error in Pinecone {operation} operation: {str(e)}")
            result["error"] = f"Operation failed: {str(e)}"
            
        return result


class ChromaProvider(CapabilityProvider):
    """ChromaDB provider for vector storage capabilities."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize ChromaDB provider.
        
        Args:
            config: Provider configuration
        """
        super().__init__("chroma", config)
        self.host = self.config.get("host", "localhost")
        self.port = self.config.get("port", 8000)
        self.collection_name = self.config.get("collection_name", "nexus-embeddings")
        self.api_url = f"http://{self.host}:{self.port}"
        # Dimension should ideally come from embedding model config
        self.dimension = self.config.get("dimension")
        # Chroma doesn't strictly require dimension at init if using default embeddings,
        # but good practice to know it for validation or if creating collection.
        if not self.dimension:
             logger.warning("Chroma provider 'dimension' not specified in config. Assuming default embedding model handles it.")
        self.timeout = self.config.get("timeout", 60)

    async def initialize(self) -> None:
        """Initialize the provider."""
        try:
            # Check if the chromadb Python package is available
            import importlib.util
            chromadb_spec = importlib.util.find_spec("chromadb")
            
            if chromadb_spec is None:
                logger.warning("ChromaDB not installed, provider will be disabled")
                self.enabled = False
                return
                
            # Register capabilities
            self.register_capability(CapabilityType.VECTOR_STORAGE, self.vector_operation)
            
            # Test connection using REST API
            async with aiohttp.ClientSession() as session:
                # Get list of collections
                async with session.get(
                    f"{self.api_url}/api/v1/collections",
                    timeout=10
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(f"ChromaDB connection test failed: {error_text}")
                        self.enabled = False
                        return
                        
                    collections_data = await response.json()
                    
                    # Check if our collection exists
                    collection_exists = False
                    for collection in collections_data:
                        if collection.get("name") == self.collection_name:
                            collection_exists = True
                            break
                            
                    # Create collection if it doesn't exist
                    if not collection_exists:
                        logger.info(f"Collection {self.collection_name} doesn't exist, creating...")
                        
                        create_payload = {
                            "name": self.collection_name,
                            # Optionally add metadata like embedding function if needed by Chroma version
                            # "metadata": {"hnsw:space": "cosine"} # Example for metric
                        }
                        # If dimension is known, maybe add it to collection metadata if supported?
                        # if self.dimension:
                        #    create_payload.setdefault("metadata", {})["dimension"] = int(self.dimension)

                        async with session.post(
                            f"{self.api_url}/api/v1/collections",
                            json=create_payload,
                            timeout=10
                        ) as create_response:
                            if create_response.status != 201:
                                error_text = await create_response.text()
                                logger.warning(f"Failed to create ChromaDB collection: {error_text}")
                                self.enabled = False
                                return
                            else:
                                logger.info(f"Successfully created collection {self.collection_name}")
                                
                logger.info("ChromaDB connection successful")
                
        except Exception as e:
            logger.warning(f"Error connecting to ChromaDB: {str(e)}")
            self.enabled = False
            
    async def vector_operation(self, 
                            operation: str,
                            vectors: Optional[List[List[float]]] = None,
                            ids: Optional[List[str]] = None,
                            metadata: Optional[List[Dict[str, Any]]] = None,
                            query_vector: Optional[List[float]] = None,
                            top_k: int = 10,
                            collection_name: Optional[str] = None,
                            where: Optional[Dict[str, Any]] = None,
                            **kwargs) -> Dict[str, Any]:
        """Perform vector operations with ChromaDB.
        
        Args:
            operation: Operation type ("add", "query", "delete", "get")
            vectors: List of vectors to add
            ids: List of IDs for vectors
            metadata: List of metadata dictionaries for vectors
            query_vector: Vector to query
            top_k: Number of results to return
            collection_name: ChromaDB collection name
            where: Query filter
            **kwargs: Additional parameters
            
        Returns:
            Operation result
        """
        if not self.enabled:
            raise ValueError("ChromaDB provider is not enabled")
            
        # Use default collection name if not specified
        collection_name = collection_name or self.collection_name
        
        # Prepare result
        result = {
            "status": "error",
            "error": None,
            "operation": operation,
            "collection": collection_name
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Handle different operations
                if operation == "add":
                    if not vectors or not ids:
                        raise ValueError("Vectors and IDs are required for add operation")
                        
                    if len(vectors) != len(ids):
                        raise ValueError("Number of vectors must match number of IDs")
                        
                    # Prepare add data
                    add_payload = {
                        "ids": ids,
                        "embeddings": vectors
                    }
                    
                    # Add metadata if available
                    if metadata and len(metadata) == len(ids):
                        add_payload["metadatas"] = metadata
                        
                    # Add documents if available
                    documents = kwargs.get("documents")
                    if documents and len(documents) == len(ids):
                        add_payload["documents"] = documents
                        
                    # Send add request
                    async with session.post(
                        f"{self.api_url}/api/v1/collections/{collection_name}/add",
                        json=add_payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 201:
                            error_text = await response.text()
                            result["error"] = f"Add failed: {error_text}"
                        else:
                            result["status"] = "success"
                            result["added_count"] = len(ids)
                            
                elif operation == "query":
                    if not query_vector:
                        raise ValueError("Query vector is required for query operation")
                        
                    # Prepare query
                    query_payload = {
                        "query_embeddings": [query_vector],
                        "n_results": top_k,
                    }
                    
                    # Add where filter if provided
                    if where:
                        query_payload["where"] = where
                        
                    # Include documents if requested
                    include_documents = kwargs.get("include_documents", True)
                    if include_documents:
                        query_payload["include"] = ["documents", "metadatas", "distances"]
                        
                    # Send query request
                    async with session.post(
                        f"{self.api_url}/api/v1/collections/{collection_name}/query",
                        json=query_payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            result["error"] = f"Query failed: {error_text}"
                        else:
                            response_data = await response.json()
                            result["status"] = "success"
                            
                            # Format query results
                            ids = response_data.get("ids", [[]])[0]
                            distances = response_data.get("distances", [[]])[0]
                            metadatas = response_data.get("metadatas", [[]])[0]
                            documents = response_data.get("documents", [[]])[0]
                            
                            matches = []
                            for i in range(len(ids)):
                                match = {
                                    "id": ids[i],
                                    "score": 1.0 - distances[i] if distances and i < len(distances) else None,
                                    "metadata": metadatas[i] if metadatas and i < len(metadatas) else {}
                                }
                                
                                if documents and i < len(documents):
                                    match["document"] = documents[i]
                                    
                                matches.append(match)
                                
                            result["matches"] = matches
                            result["match_count"] = len(matches)
                            
                elif operation == "delete":
                    delete_payload = {}
                    
                    # Add IDs if provided
                    if ids:
                        delete_payload["ids"] = ids
                        
                    # Add filter if provided
                    if where:
                        delete_payload["where"] = where
                        
                    # Send delete request
                    async with session.post(
                        f"{self.api_url}/api/v1/collections/{collection_name}/delete",
                        json=delete_payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            result["error"] = f"Delete failed: {error_text}"
                        else:
                            result["status"] = "success"
                            result["deleted_count"] = len(ids) if ids else -1  # -1 for unknown count with where filter
                            
                elif operation == "get":
                    get_payload = {}
                    
                    # Add IDs if provided
                    if ids:
                        get_payload["ids"] = ids
                        
                    # Add filter if provided
                    if where:
                        get_payload["where"] = where
                        
                    # Include options
                    include = ["metadatas"]
                    if kwargs.get("include_documents", True):
                        include.append("documents")
                    if kwargs.get("include_embeddings", False):
                        include.append("embeddings")
                        
                    get_payload["include"] = include
                    
                    # Send get request
                    async with session.post(
                        f"{self.api_url}/api/v1/collections/{collection_name}/get",
                        json=get_payload,
                        timeout=self.timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            result["error"] = f"Get failed: {error_text}"
                        else:
                            response_data = await response.json()
                            result["status"] = "success"
                            
                            # Format get results
                            ids = response_data.get("ids", [])
                            metadatas = response_data.get("metadatas", [])
                            documents = response_data.get("documents", [])
                            embeddings = response_data.get("embeddings", [])
                            
                            items = []
                            for i in range(len(ids)):
                                item = {
                                    "id": ids[i],
                                    "metadata": metadatas[i] if metadatas and i < len(metadatas) else {}
                                }
                                
                                if documents and i < len(documents):
                                    item["document"] = documents[i]
                                    
                                if embeddings and i < len(embeddings):
                                    item["embedding"] = embeddings[i]
                                    
                                items.append(item)
                                
                            result["items"] = items
                            result["item_count"] = len(items)
                            
                else:
                    raise ValueError(f"Unsupported operation: {operation}")
                    
        except Exception as e:
            logger.error(f"Error in ChromaDB {operation} operation: {str(e)}")
            result["error"] = f"Operation failed: {str(e)}"
            
        return result
