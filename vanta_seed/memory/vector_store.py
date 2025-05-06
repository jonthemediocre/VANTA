"""
Abstract base class and concrete implementations for vector memory storage.
"""

import abc
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np

# Qdrant specific imports - handle potential ImportError if not installed
try:
    from qdrant_client import QdrantClient, models
    from qdrant_client.http.models import Distance, VectorParams, PointStruct, UpdateStatus
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    # Define dummy classes or raise error if Qdrant is mandatory
    class QdrantClient:
        pass
    class models:
        Distance = None
        VectorParams = None
        PointStruct = None
        UpdateStatus = None

logger = logging.getLogger(__name__)

class VectorMemoryStore(abc.ABC):
    """Abstract base class for a vector memory store."""

    @abc.abstractmethod
    async def initialize(self, **kwargs):
        """Initialize the connection to the vector store."""
        raise NotImplementedError

    @abc.abstractmethod
    async def shutdown(self):
        """Cleanly disconnect or shut down the vector store connection."""
        raise NotImplementedError

    @abc.abstractmethod
    async def ensure_collection(self, collection_name: str, vector_size: int, distance_metric: str = 'cosine'):
        """Ensure a collection exists with the specified configuration."""
        raise NotImplementedError

    @abc.abstractmethod
    async def upsert_points(self, collection_name: str, points: List[Dict[str, Any]]) -> bool:
        """Upsert (insert or update) points into a collection.

        Args:
            collection_name: The name of the collection.
            points: A list of points, where each point is a dict containing at least
                    'id' (str or int), 'vector' (List[float] or np.ndarray),
                    and optionally 'payload' (Dict[str, Any]).

        Returns:
            True if the operation was successful (or likely successful), False otherwise.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def query(self, collection_name: str, query_vector: Union[List[float], np.ndarray],
                  limit: int = 5, with_payload: bool = True, with_vector: bool = False,
                  score_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """Query the collection for points similar to the query_vector.

        Args:
            collection_name: The name of the collection.
            query_vector: The vector to search against.
            limit: The maximum number of results to return.
            with_payload: Whether to include the payload in the results.
            with_vector: Whether to include the vector in the results.
            score_threshold: Minimum similarity score threshold.

        Returns:
            A list of search results, each potentially containing 'id', 'score',
            'payload', and 'vector'.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def delete_points(self, collection_name: str, point_ids: List[Union[str, int]]) -> bool:
        """Delete specific points from a collection by their IDs."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_point(self, collection_name: str, point_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Retrieve a specific point by its ID."""
        raise NotImplementedError


class QdrantVectorStore(VectorMemoryStore):
    """Concrete implementation using Qdrant."""

    def __init__(self, host: str = "localhost", port: int = 6333, api_key: Optional[str] = None, **kwargs):
        if not QDRANT_AVAILABLE:
            raise ImportError("Qdrant client is not installed. Please install with `pip install qdrant-client`")
        
        self.client: Optional[QdrantClient] = None
        self._host = host
        self._port = port
        self._api_key = api_key
        self._client_kwargs = kwargs # For other QdrantClient options like https, prefix
        self._distance_map = {
            'cosine': models.Distance.COSINE,
            'dot': models.Distance.DOT,
            'euclid': models.Distance.EUCLID
        }

    async def initialize(self):
        """Initializes the Qdrant client."""
        logger.info(f"Initializing Qdrant client connection to host='{self._host}' port={self._port}...")
        try:
            self.client = QdrantClient(
                host=self._host,
                port=self._port,
                api_key=self._api_key,
                **self._client_kwargs
            )
            # Test connection (optional, but good practice)
            # self.client.health_check() # Note: health_check might not be async
            logger.info("Qdrant client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}", exc_info=True)
            self.client = None
            raise

    async def shutdown(self):
        """Closes the Qdrant client connection."""
        if self.client:
            logger.info("Shutting down Qdrant client connection...")
            # QdrantClient uses HTTP requests, often managed by httpx; explicit close might not be needed,
            # but good practice if a persistent connection pool exists.
            # self.client.close() # Check QdrantClient documentation for explicit close method if available
            self.client = None
            logger.info("Qdrant client connection closed.")

    async def ensure_collection(self, collection_name: str, vector_size: int, distance_metric: str = 'cosine'):
        """Ensures a Qdrant collection exists."""
        if not self.client:
            raise ConnectionError("Qdrant client not initialized. Call initialize() first.")

        distance = self._distance_map.get(distance_metric.lower())
        if distance is None:
            raise ValueError(f"Unsupported distance metric: {distance_metric}. Supported: {list(self._distance_map.keys())}")

        try:
            collections = await asyncio.to_thread(self.client.get_collections) # Use to_thread for sync SDK call
            collection_names = [c.name for c in collections.collections]
            
            if collection_name not in collection_names:
                logger.info(f"Collection '{collection_name}' not found. Creating...")
                await asyncio.to_thread(
                    self.client.create_collection,
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(size=vector_size, distance=distance)
                )
                logger.info(f"Collection '{collection_name}' created successfully.")
            else:
                logger.debug(f"Collection '{collection_name}' already exists.")
        except Exception as e:
            logger.error(f"Failed to ensure collection '{collection_name}': {e}", exc_info=True)
            raise

    async def upsert_points(self, collection_name: str, points: List[Dict[str, Any]]) -> bool:
        """Upserts points into a Qdrant collection."""
        if not self.client:
            raise ConnectionError("Qdrant client not initialized.")
        if not points:
            return True # Nothing to do

        qdrant_points = []
        for point in points:
            if not all(k in point for k in ['id', 'vector']):
                logger.warning(f"Skipping invalid point (missing id or vector): {point.get('id', 'N/A')}")
                continue
            qdrant_points.append(models.PointStruct(
                id=point['id'],
                vector=point['vector'],
                payload=point.get('payload', {})
            ))
        
        if not qdrant_points:
             logger.warning("No valid points provided for upsert.")
             return False

        try:
            # Use wait=True for synchronous confirmation, or handle async nature if wait=False
            operation_info = await asyncio.to_thread(
                self.client.upsert,
                collection_name=collection_name, 
                points=qdrant_points, 
                wait=True
            )
            logger.debug(f"Upsert operation status for {len(qdrant_points)} points: {operation_info.status}")
            return operation_info.status == UpdateStatus.COMPLETED
        except Exception as e:
            logger.error(f"Failed to upsert points into '{collection_name}': {e}", exc_info=True)
            return False

    async def query(self, collection_name: str, query_vector: Union[List[float], np.ndarray],
                  limit: int = 5, with_payload: bool = True, with_vector: bool = False,
                  score_threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        """Queries a Qdrant collection."""
        if not self.client:
            raise ConnectionError("Qdrant client not initialized.")

        if isinstance(query_vector, np.ndarray):
            query_vector = query_vector.flatten().tolist() # Ensure it's a flat list

        try:
            search_result = await asyncio.to_thread(
                self.client.search,
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=with_payload,
                with_vectors=with_vector,
                score_threshold=score_threshold
            )
            
            # Convert Qdrant Hit objects to dictionaries
            results = []
            for hit in search_result:
                result_dict = {
                    "id": hit.id,
                    "score": hit.score,
                }
                if with_payload:
                    result_dict["payload"] = hit.payload
                if with_vector:
                    result_dict["vector"] = hit.vector
                results.append(result_dict)
            return results
        except Exception as e:
            logger.error(f"Failed to query collection '{collection_name}': {e}", exc_info=True)
            return [] # Return empty list on error

    async def delete_points(self, collection_name: str, point_ids: List[Union[str, int]]) -> bool:
        """Deletes points from a Qdrant collection."""
        if not self.client:
            raise ConnectionError("Qdrant client not initialized.")
        if not point_ids:
            return True

        try:
            operation_info = await asyncio.to_thread(
                self.client.delete,
                collection_name=collection_name,
                points_selector=models.PointIdsList(points=point_ids),
                wait=True
            )
            logger.debug(f"Delete operation status for {len(point_ids)} points: {operation_info.status}")
            return operation_info.status == UpdateStatus.COMPLETED
        except Exception as e:
            logger.error(f"Failed to delete points from '{collection_name}': {e}", exc_info=True)
            return False

    async def get_point(self, collection_name: str, point_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """Retrieves a specific point by ID from Qdrant."""
        if not self.client:
            raise ConnectionError("Qdrant client not initialized.")
        try:
            points = await asyncio.to_thread(
                self.client.retrieve,
                collection_name=collection_name,
                ids=[point_id],
                with_payload=True,
                with_vectors=True # Retrieve vector as well
            )
            if points:
                hit = points[0]
                return {
                     "id": hit.id,
                     "payload": hit.payload,
                     "vector": hit.vector
                 }
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve point '{point_id}' from '{collection_name}': {e}", exc_info=True)
            return None

# Example Placeholder for other backends
class ChromaVectorStore(VectorMemoryStore):
     async def initialize(self, **kwargs): raise NotImplementedError
     async def shutdown(self): raise NotImplementedError
     async def ensure_collection(self, collection_name: str, vector_size: int, distance_metric: str = 'cosine'): raise NotImplementedError
     async def upsert_points(self, collection_name: str, points: List[Dict[str, Any]]) -> bool: raise NotImplementedError
     async def query(self, collection_name: str, query_vector: Union[List[float], np.ndarray], limit: int = 5, with_payload: bool = True, with_vector: bool = False, score_threshold: Optional[float] = None) -> List[Dict[str, Any]]: raise NotImplementedError
     async def delete_points(self, collection_name: str, point_ids: List[Union[str, int]]) -> bool: raise NotImplementedError
     async def get_point(self, collection_name: str, point_id: Union[str, int]) -> Optional[Dict[str, Any]]: raise NotImplementedError

class PGVectorStore(VectorMemoryStore):
     async def initialize(self, **kwargs): raise NotImplementedError
     async def shutdown(self): raise NotImplementedError
     async def ensure_collection(self, collection_name: str, vector_size: int, distance_metric: str = 'cosine'): raise NotImplementedError
     async def upsert_points(self, collection_name: str, points: List[Dict[str, Any]]) -> bool: raise NotImplementedError
     async def query(self, collection_name: str, query_vector: Union[List[float], np.ndarray], limit: int = 5, with_payload: bool = True, with_vector: bool = False, score_threshold: Optional[float] = None) -> List[Dict[str, Any]]: raise NotImplementedError
     async def delete_points(self, collection_name: str, point_ids: List[Union[str, int]]) -> bool: raise NotImplementedError
     async def get_point(self, collection_name: str, point_id: Union[str, int]) -> Optional[Dict[str, Any]]: raise NotImplementedError 