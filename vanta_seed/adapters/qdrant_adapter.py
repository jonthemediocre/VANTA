from typing import Type, TypeVar, Optional, List, Dict, Any, Callable
from pydantic import BaseModel
import uuid
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct
from qdrant_client.http.exceptions import UnexpectedResponse
import httpx # For catching httpx.ConnectError
import logging

# Import custom exceptions for the adapter to raise
from vanta_seed.exceptions import (
    ConnectionFailure,
    OperationFailure,
    StorageFailure, # Generic fallback
    EmbeddingError # If embedder fails
)

logger = logging.getLogger(__name__)

# Type variable for Pydantic models
T = TypeVar('T', bound=BaseModel)

# Define a constant for the dummy vector size if not using actual vectors
QDRANT_ADAPTER_DUMMY_VECTOR_SIZE = 10

class QdrantAdapter:
    """Adapter for simplifying interactions with Qdrant for Pydantic models."""

    def __init__(self, qdrant_client: QdrantClient, embedder: Optional[Callable[[BaseModel], List[float]]] = None):
        if not qdrant_client:
            logger.error("QdrantAdapter initialized with a null QdrantClient.")
            # This is a programming error, ValueError is appropriate.
            raise ValueError("QdrantClient cannot be None for QdrantAdapter.")
        self.client = qdrant_client
        self.embedder = embedder
        logger.info(f"QdrantAdapter initialized {'WITH' if self.embedder else 'WITHOUT'} embedder: {type(self.embedder).__name__ if self.embedder else 'None'}")

    def _generate_qdrant_point_id(self) -> str:
        """Generates a UUID string for Qdrant point ID."""
        return str(uuid.uuid4())

    def upsert_model(self, collection_name: str, model_instance: T, id_field_name: str) -> bool:
        """Upserts a Pydantic model. Returns True on success, raises StorageFailure on error."""
        try:
            qdrant_point_id = self._generate_qdrant_point_id()
            payload = model_instance.model_dump(by_alias=True)
            vector_to_store: Optional[List[float]] = None
            if self.embedder:
                try:
                    vector_to_store = self.embedder(model_instance)
                except Exception as embed_ex:
                    logger.error(f"Embedder error for model ID '{getattr(model_instance, id_field_name, 'N/A')}': {embed_ex}")
                    raise EmbeddingError(f"Embedding failed for model in '{collection_name}'", original_exception=embed_ex)
            
            point = PointStruct(id=qdrant_point_id, payload=payload, vector=vector_to_store)
            response = self.client.upsert(collection_name=collection_name, points=[point], wait=True)
            
            if response.status == models.UpdateStatus.COMPLETED:
                logger.info(f"Upserted model ID '{getattr(model_instance, id_field_name, 'N/A')}' (Qdrant ID: {qdrant_point_id}) into '{collection_name}'.")
                return True # Indicates the specific upsert operation succeeded.
            else:
                # Qdrant reported an issue with the upsert itself.
                msg = f"Upsert to '{collection_name}' failed with Qdrant status: {response.status}"
                logger.error(msg)
                # This case might be an UnexpectedResponse if status indicates an issue, 
                # or a general OperationFailure if Qdrant reports failure without a typical HTTP error code.
                raise OperationFailure(msg) 
        except httpx.ConnectError as ce:
            msg = f"Connection error during upsert to '{collection_name}'"
            logger.error(f"{msg}: {ce}")
            raise ConnectionFailure(msg, original_exception=ce)
        except UnexpectedResponse as ue: 
            msg = f"Qdrant HTTP error during upsert to '{collection_name}' (Status: {ue.status_code})"
            logger.error(f"{msg}: {ue.content.decode() if ue.content else 'No content'}")
            raise OperationFailure(msg, original_exception=ue)      
        except EmbeddingError: 
            raise
        except Exception as e:
            msg = f"Unexpected error during upsert to '{collection_name}'"
            logger.error(f"{msg}: {e}", exc_info=True)
            raise StorageFailure(msg, original_exception=e) 

    def get_model_by_id(self, collection_name: str, id_value: str, model_class: Type[T], id_field_name_in_payload: str) -> Optional[T]:
        """Retrieves a model by its natural ID. Returns model instance or None if not found. Raises StorageFailure on error."""
        try:
            search_results = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(must=[models.FieldCondition(key=id_field_name_in_payload, match=models.MatchValue(value=id_value))]),
                limit=1, with_payload=True, with_vectors=False
            )
            if search_results and search_results[0]:
                point = search_results[0][0]
                if point.payload: return model_class(**point.payload)
                logger.warning(f"Point found in '{collection_name}' for {id_field_name_in_payload}='{id_value}' but has no payload.")
                return None # Treat as not found if no payload
            logger.info(f"No model found in '{collection_name}' for {id_field_name_in_payload}='{id_value}'.")
            return None # Standard not found case
        except httpx.ConnectError as ce:
            msg = f"Connection error during get from '{collection_name}' (ID: {id_value})"
            logger.error(f"{msg}: {ce}")
            raise ConnectionFailure(msg, original_exception=ce)
        except UnexpectedResponse as ue: 
            if ue.status_code == 404: 
                logger.warning(f"Collection '{collection_name}' not found during get for ID '{id_value}'. Status: {ue.status_code}")
                return None 
            msg = f"Qdrant HTTP error during get from '{collection_name}' (ID: {id_value}, Status: {ue.status_code})"
            logger.error(f"{msg}: {ue.content.decode() if ue.content else 'No content'}")
            raise OperationFailure(msg, original_exception=ue)
        except Exception as e:
            msg = f"Unexpected error during get from '{collection_name}' (ID: {id_value})"
            logger.error(f"{msg}: {e}", exc_info=True)
            raise StorageFailure(msg, original_exception=e)

    def update_model_by_id(self, collection_name: str, id_value: str, model_update_instance: T, id_field_name_in_payload: str) -> Optional[T]:
        """Updates a model by its natural ID. Returns updated model or None if not found. Raises StorageFailure on error."""
        try:
            search_results = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(must=[models.FieldCondition(key=id_field_name_in_payload, match=models.MatchValue(value=id_value))]),
                limit=1, with_payload=True
            )
            if not (search_results and search_results[0]):
                logger.warning(f"No model found in '{collection_name}' with {id_field_name_in_payload}='{id_value}' to update.")
                return None # Not found
            
            qdrant_point_to_update = search_results[0][0]
            current_payload = qdrant_point_to_update.payload if qdrant_point_to_update.payload else {}
            update_dict = model_update_instance.model_dump(by_alias=True, exclude_unset=True)
            current_payload.update(update_dict)
            current_payload[id_field_name_in_payload] = id_value # Ensure ID integrity

            vector_to_store: Optional[List[float]] = None
            if self.embedder:
                try:
                    prospective_model_for_embedding = type(model_update_instance)(**current_payload)
                    vector_to_store = self.embedder(prospective_model_for_embedding)
                except Exception as embed_ex:
                    logger.error(f"Embedder error during update for model ID '{id_value}': {embed_ex}")
                    raise EmbeddingError(f"Embedding failed during update for model in '{collection_name}'", original_exception=embed_ex)

            updated_point = PointStruct(id=qdrant_point_to_update.id, payload=current_payload, vector=vector_to_store)
            response = self.client.upsert(collection_name=collection_name, points=[updated_point], wait=True)

            if response.status == models.UpdateStatus.COMPLETED:
                logger.info(f"Updated model in '{collection_name}' for {id_field_name_in_payload}='{id_value}'.")
                return type(model_update_instance)(**current_payload)
            else:
                msg = f"Update in '{collection_name}' failed with Qdrant status: {response.status}"
                logger.error(msg)
                raise OperationFailure(msg)
        except httpx.ConnectError as ce:
            msg = f"Connection error during update for '{collection_name}' (ID: {id_value})"
            logger.error(f"{msg}: {ce}")
            raise ConnectionFailure(msg, original_exception=ce)
        except UnexpectedResponse as ue:
            if ue.status_code == 404: # Collection not found
                logger.warning(f"Collection '{collection_name}' not found during update for ID '{id_value}'. Status: {ue.status_code}")
                return None
            msg = f"Qdrant HTTP error during update for '{collection_name}' (ID: {id_value}, Status: {ue.status_code})"
            logger.error(f"{msg}: {ue.content.decode() if ue.content else 'No content'}")
            raise OperationFailure(msg, original_exception=ue)
        except EmbeddingError: raise
        except Exception as e:
            msg = f"Unexpected error during update for '{collection_name}' (ID: {id_value})"
            logger.error(f"{msg}: {e}", exc_info=True)
            raise StorageFailure(msg, original_exception=e)

    def delete_model_by_id(self, collection_name: str, id_value: str, id_field_name_in_payload: str) -> bool:
        """Deletes model(s) by natural ID. Returns True if delete op successful, False if not found or error during op. Raises StorageFailure on connection/API error."""
        try:
            # First, check if the item exists to provide a clearer True (deleted) vs False (not found)
            # This requires a scroll call. If performance is critical and idempotency is acceptable, 
            # one might skip this check and rely on Qdrant's delete behavior.
            check_exists_results = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=models.Filter(must=[models.FieldCondition(key=id_field_name_in_payload, match=models.MatchValue(value=id_value))]),
                limit=1, with_payload=False # No need for payload here
            )
            if not (check_exists_results and check_exists_results[0]):
                logger.info(f"Model not found in '{collection_name}' with {id_field_name_in_payload}='{id_value}'. Nothing to delete.")
                return False # Item was not found, so technically not deleted now.

            response = self.client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(filter=models.Filter(
                    must=[models.FieldCondition(key=id_field_name_in_payload, match=models.MatchValue(value=id_value))])),
                wait=True
            )
            if response.status == models.UpdateStatus.COMPLETED:
                logger.info(f"Delete operation completed for {id_field_name_in_payload}='{id_value}' in '{collection_name}'.")
                return True
            else:
                msg = f"Delete from '{collection_name}' (ID: {id_value}) failed with Qdrant status: {response.status}"
                logger.error(msg)
                raise OperationFailure(msg)
        except httpx.ConnectError as ce:
            msg = f"Connection error during delete from '{collection_name}' (ID: {id_value})"
            logger.error(f"{msg}: {ce}")
            raise ConnectionFailure(msg, original_exception=ce)
        except UnexpectedResponse as ue:
            if ue.status_code == 404: # Collection not found
                logger.warning(f"Collection '{collection_name}' not found during delete for ID '{id_value}'. Status: {ue.status_code}")
                return False 
            msg = f"Qdrant HTTP error during delete from '{collection_name}' (ID: {id_value}, Status: {ue.status_code})"
            logger.error(f"{msg}: {ue.content.decode() if ue.content else 'No content'}")
            raise OperationFailure(msg, original_exception=ue)
        except Exception as e:
            msg = f"Unexpected error deleting from '{collection_name}' (ID: {id_value})"
            logger.error(f"{msg}: {e}", exc_info=True)
            raise StorageFailure(msg, original_exception=e)

    def list_all_model_ids(self, collection_name: str, id_field_name_in_payload: str, limit: int = 100) -> List[str]:
        """Lists all natural IDs. Returns list of IDs or empty list. Raises StorageFailure on error."""
        if not self.client: raise ConnectionFailure("Qdrant client not initialized for list_all_model_ids")
        ids: List[str] = []
        try:
            next_offset = None
            while True:
                points, next_offset = self.client.scroll(collection_name=collection_name, limit=limit, offset=next_offset, with_payload=True, with_vectors=False)
                for point in points: 
                    if point.payload and id_field_name_in_payload in point.payload: ids.append(str(point.payload[id_field_name_in_payload]))
                if not next_offset: break
            return list(set(ids))
        except httpx.ConnectError as ce:
            msg = f"Connection error during list_ids from '{collection_name}'"
            logger.error(f"{msg}: {ce}")
            raise ConnectionFailure(msg, original_exception=ce)
        except UnexpectedResponse as ue:
            if ue.status_code == 404:
                logger.warning(f"Collection '{collection_name}' not found during list_ids. Status: {ue.status_code}")
                return [] 
            msg = f"Qdrant HTTP error during list_ids from '{collection_name}' (Status: {ue.status_code})"
            logger.error(f"{msg}: {ue.content.decode() if ue.content else 'No content'}")
            raise OperationFailure(msg, original_exception=ue)
        except Exception as e:
            msg = f"Unexpected error listing IDs from '{collection_name}'"
            logger.error(f"{msg}: {e}", exc_info=True)
            raise StorageFailure(msg, original_exception=e)

    def search_similar_models(self, collection_name: str, query_vector: List[float], model_class: Type[T], top_k: int = 5, score_threshold: Optional[float] = None) -> List[T]:
        """Searches for similar models. Returns list of models or empty list. Raises StorageFailure on error."""
        if not self.client: raise ConnectionFailure("Qdrant client not available for search_similar_models")
        try:
            hits = self.client.search(
                collection_name=collection_name, query_vector=query_vector, limit=top_k,
                score_threshold=score_threshold, with_payload=True
            )
            models_found = []
            for hit in hits:
                if hit.payload:
                    try: models_found.append(model_class(**hit.payload))
                    except Exception as parse_ex: logger.error(f"Failed to parse payload to {model_class.__name__} for point {hit.id}: {parse_ex}")
                else: logger.warning(f"ScoredPoint ID {hit.id} in '{collection_name}' had no payload.")
            return models_found
        except httpx.ConnectError as ce:
            msg = f"Connection error during search in '{collection_name}'"
            logger.error(f"{msg}: {ce}")
            raise ConnectionFailure(msg, original_exception=ce)
        except UnexpectedResponse as ue:
            if ue.status_code == 404:
                 logger.warning(f"Collection '{collection_name}' not found during search. Status: {ue.status_code}")
                 return []
            msg = f"Qdrant HTTP error during search in '{collection_name}' (Status: {ue.status_code})"
            logger.error(f"{msg}: {ue.content.decode() if ue.content else 'No content'}")
            raise OperationFailure(msg, original_exception=ue)
        except Exception as e:
            msg = f"Unexpected error during search in '{collection_name}'"
            logger.error(f"{msg}: {e}", exc_info=True)
            raise StorageFailure(msg, original_exception=e)

# Example usage (illustrative, not run directly here)
# if __name__ == '__main__':
#     class MyData(BaseModel):
#         my_id: str
#         value: str
#         timestamp: Optional[datetime] = None

#     # Assume client is initialized QdrantClient()
#     # client = QdrantClient(url="http://localhost:6333") 
#     # adapter = QdrantAdapter(client)
#     # COLLECTION_NAME = "my_test_collection"
    
#     # # Ensure collection exists (simplified)
#     # try:
#     #     client.get_collection(COLLECTION_NAME)
#     # except:
#     #     client.create_collection(COLLECTION_NAME, vectors_config=models.VectorParams(size=10, distance=models.Distance.COSINE))
#     #     client.create_payload_index(COLLECTION_NAME, field_name="my_id", field_schema=models.PayloadSchemaType.KEYWORD)

#     # data1 = MyData(my_id="test_id_1", value="Hello Qdrant Adapter")
#     # adapter.upsert_model(COLLECTION_NAME, data1, id_field_name="my_id")

#     # retrieved = adapter.get_model_by_id(COLLECTION_NAME, "test_id_1", MyData, id_field_name_in_payload="my_id")
#     # print(f"Retrieved: {retrieved}")

#     # if retrieved:
#     #     retrieved.value = "Updated Value"
#     #     retrieved.timestamp = datetime.utcnow()
#     #     adapter.update_model_by_id(COLLECTION_NAME, "test_id_1", retrieved, id_field_name_in_payload="my_id")
#     #     updated_retrieved = adapter.get_model_by_id(COLLECTION_NAME, "test_id_1", MyData, id_field_name_in_payload="my_id")
#     #     print(f"Updated and Retrieved: {updated_retrieved}")

#     # ids = adapter.list_all_model_ids(COLLECTION_NAME, "my_id")
#     # print(f"All IDs: {ids}")

#     # adapter.delete_model_by_id(COLLECTION_NAME, "test_id_1", id_field_name_in_payload="my_id")
#     # print(f"Retrieved after delete: {adapter.get_model_by_id(COLLECTION_NAME, "test_id_1", MyData, id_field_name_in_payload="my_id")}") 