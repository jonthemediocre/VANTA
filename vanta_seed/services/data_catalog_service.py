import logging
import os
import uuid # Added for generating Qdrant point IDs
from typing import Dict, Any, Optional, List
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct, Distance, VectorParams, UpdateStatus, Filter, FieldCondition, MatchValue
from pydantic import BaseModel, Field, Extra, ValidationError as PydanticValidationError # Alias Pydantic's
from qdrant_client.http.exceptions import UnexpectedResponse
import httpx

# Import MemoryAgent schemas
from vanta_seed.schemas.memory_agent_schemas import ContextualData, KnowledgeData, OperationalData
# Import QdrantAdapter
from vanta_seed.adapters.qdrant_adapter import QdrantAdapter
# Import the embedder and its dimension constant
from vanta_seed.embeddings.knowledge_embedders import SimpleKnowledgeEmbedder, KNOWLEDGE_EMBEDDING_DIMENSION
# Import custom exceptions
from vanta_seed.exceptions import (
    DataCatalogException, # Base for service level
    NotFound, 
    StorageFailure, 
    ConnectionFailure, 
    OperationFailure,
    ConfigurationError,
    EmbeddingError,
    ValidationError # Custom validation error
)
# Import Mythic Schemas
from vanta_seed.schemas.mythic_schemas import MythicObject, MythicLink

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

METADATA_COLLECTION = "vanta_metadata_catalog"
SCHEMA_COLLECTION = "vanta_schema_registry"

# --- New MemoryAgent Collection Names ---
CONTEXTUAL_DATA_COLLECTION = "vanta_memory_contextual"
KNOWLEDGE_DATA_COLLECTION = "vanta_memory_knowledge"
OPERATIONAL_DATA_COLLECTION = "vanta_memory_operational"

# --- New Mythic Layer Collection Names ---
MYTHIC_OBJECT_COLLECTION = "vanta_mythic_objects"
MYTHIC_LINK_COLLECTION = "vanta_mythic_links"

DUMMY_VECTOR_SIZE = 10 # Required by Qdrant, but not used for primary functionality here

# Field names for natural IDs of Metadata and Schema, must match their Pydantic model field names
METADATA_ID_FIELD = "data_source_id" # Assuming DataSourceMetadata will have this field
SCHEMA_ID_FIELD = "schema_id"       # Assuming SchemaDefinition will have this field

# Field names for primary IDs in MemoryAgent data (used for Qdrant point IDs or filtering)
# These match the Pydantic model field names for clarity.
SESSION_ID_FIELD = "session_id"
KNOWLEDGE_ID_FIELD = "knowledge_id"
OPERATION_ID_FIELD = "operation_id"

# Field names for primary IDs in Mythic Layer data
MYTHIC_OBJECT_ID_FIELD = "id" # Corresponds to MythicObject.id
MYTHIC_LINK_ID_FIELD = "id"   # Corresponds to MythicLink.id

# --- Pydantic Models for Validation (Now with explicit ID fields) ---

class DataSourceMetadata(BaseModel):
    data_source_id: str = Field(..., description="The unique, user-defined identifier for the data source.")
    description: str
    type: str # e.g., "PostgreSQL", "KafkaTopic", "S3Bucket", "APIEndpoint"
    owner: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    # Allow other fields to be present for flexibility
    class Config:
        extra = 'allow'

class SchemaProperty(BaseModel):
    type: str
    format: Optional[str] = None
    description: Optional[str] = None
    # Allow other JSON schema attributes
    class Config:
        extra = 'allow'

class SchemaDefinition(BaseModel):
    schema_id: str = Field(..., description="The unique, user-defined identifier for the schema.")
    schema_type: str = Field(default="object", alias="type") # Common JSON schema field
    properties: Dict[str, SchemaProperty] = Field(default_factory=dict)
    required: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = None
    # Allow other top-level JSON schema fields
    class Config:
        extra = 'allow'
        populate_by_name = True # Allows using 'type' in input data for 'schema_type'

class DataCatalogService:
    """
    Manages metadata and schemas for data sources within the VANTA ecosystem using Qdrant.
    Provides endpoints for registering, querying, and managing data assets.
    """
    def __init__(self, qdrant_url: Optional[str] = None):
        self.qdrant_url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        if not self.qdrant_url:
            # This is a fatal configuration error if no URL is found.
            logger.critical("QDRANT_URL not configured and no default provided to DataCatalogService.")
            raise ConfigurationError("QDRANT_URL is not configured for DataCatalogService.")

        self.client: Optional[QdrantClient] = None
        
        # Adapters for different data types / vectorization strategies
        self.metadata_adapter: Optional[QdrantAdapter] = None
        self.schema_adapter: Optional[QdrantAdapter] = None
        self.contextual_adapter: Optional[QdrantAdapter] = None
        self.knowledge_adapter: Optional[QdrantAdapter] = None
        self.operational_adapter: Optional[QdrantAdapter] = None
        self.mythic_object_adapter: Optional[QdrantAdapter] = None # New Adapter
        self.mythic_link_adapter: Optional[QdrantAdapter] = None   # New Adapter
        self.knowledge_embedder: Optional[SimpleKnowledgeEmbedder] = None

        try:
            logger.info(f"Attempting to connect to Qdrant at {self.qdrant_url}...")
            self.client = QdrantClient(url=self.qdrant_url, timeout=10) # Added timeout
            self.client.get_collections() 
            logger.info(f"Successfully connected to Qdrant at {self.qdrant_url}.")

            self.metadata_adapter = QdrantAdapter(self.client)
            self.schema_adapter = QdrantAdapter(self.client)
            self.contextual_adapter = QdrantAdapter(self.client)
            
            try:
                self.knowledge_embedder = SimpleKnowledgeEmbedder()
                if self.knowledge_embedder.model: 
                    self.knowledge_adapter = QdrantAdapter(self.client, embedder=self.knowledge_embedder)
                    logger.info("Knowledge adapter initialized WITH SimpleKnowledgeEmbedder.")
                else:
                    logger.warning("Knowledge embedder model failed to load. Initializing knowledge adapter WITHOUT embedder.")
                    self.knowledge_adapter = QdrantAdapter(self.client) 
            except Exception as embed_init_ex:
                logger.error(f"Failed to initialize SimpleKnowledgeEmbedder: {embed_init_ex}. Knowledge adapter will be without embedder.")
                self.knowledge_adapter = QdrantAdapter(self.client) 

            self.operational_adapter = QdrantAdapter(self.client) 
            
            self.mythic_object_adapter = QdrantAdapter(self.client) 
            self.mythic_link_adapter = QdrantAdapter(self.client)

            logger.info("Qdrant Adapters initialized.")
            
            self._ensure_all_collections_exist()

        except httpx.ConnectError as ce:
            logger.critical(f"QDRANT CONNECTION FAILED for DataCatalogService at {self.qdrant_url}: {ce}")
            self._cleanup_on_init_failure()
            raise ConnectionFailure(f"Failed to connect to Qdrant at {self.qdrant_url}", original_exception=ce)
        except UnexpectedResponse as ue: # Catch specific Qdrant HTTP errors
            logger.critical(f"QDRANT HTTP API ERROR during DataCatalogService initialization: {ue} (Status: {ue.status_code})")
            self._cleanup_on_init_failure()
            raise OperationFailure(f"Qdrant API error during service init: {ue.status_code}", original_exception=ue)
        except Exception as e: # Catch other errors (e.g. from SimpleKnowledgeEmbedder init, or other Qdrant client errors not UnexpectedResponse)
            logger.critical(f"UNEXPECTED ERROR during DataCatalogService initialization: {e}", exc_info=True)
            self._cleanup_on_init_failure()
            # Determine if it's a Qdrant client error not caught by UnexpectedResponse or something else
            if "qdrant" in str(type(e)).lower(): # Basic check if it might be another Qdrant lib error
                 raise OperationFailure(f"Qdrant related error during service init: {e}", original_exception=e)
            raise ConfigurationError(f"Unexpected error during DataCatalogService setup: {e}", original_exception=e)

    def _cleanup_on_init_failure(self):
        if self.client:
            try: self.client.close()
            except Exception: pass # Ignore errors during cleanup close
        self.client = None
        self.metadata_adapter = self.schema_adapter = self.contextual_adapter = self.knowledge_adapter = self.operational_adapter = None
        self.mythic_object_adapter = self.mythic_link_adapter = None # Cleanup new adapters
        self.knowledge_embedder = None
        logger.info("Cleaned up resources after DataCatalogService initialization failure.")

    def _ensure_all_collections_exist(self):
        """Wrapper to ensure all necessary collections and their indexes are set up."""
        # This method itself could raise QdrantConnectionError or QdrantOperationError if client not set or API calls fail
        if not self.client: # Should be caught by __init__ but as a safeguard
            raise ConnectionFailure("Cannot ensure collections: Qdrant client not initialized.")
        
        collections_to_ensure = [
            (METADATA_COLLECTION, METADATA_ID_FIELD, DUMMY_VECTOR_SIZE),
            (SCHEMA_COLLECTION, SCHEMA_ID_FIELD, DUMMY_VECTOR_SIZE),
            (CONTEXTUAL_DATA_COLLECTION, SESSION_ID_FIELD, DUMMY_VECTOR_SIZE),
            (KNOWLEDGE_DATA_COLLECTION, KNOWLEDGE_ID_FIELD, 
             KNOWLEDGE_EMBEDDING_DIMENSION if self.knowledge_embedder and self.knowledge_embedder.model else DUMMY_VECTOR_SIZE),
            (OPERATIONAL_DATA_COLLECTION, OPERATION_ID_FIELD, DUMMY_VECTOR_SIZE),
            (MYTHIC_OBJECT_COLLECTION, MYTHIC_OBJECT_ID_FIELD, DUMMY_VECTOR_SIZE), # Using DUMMY_VECTOR_SIZE for now
            (MYTHIC_LINK_COLLECTION, MYTHIC_LINK_ID_FIELD, DUMMY_VECTOR_SIZE)      # Links likely won't be vectorized
        ]
        for name, id_field, vec_size in collections_to_ensure:
            self._ensure_collection_with_index(name, id_field, vec_size)

    def _ensure_collection_with_index(self, collection_name: str, id_field_for_index: str, vector_size: int):
        """Ensures a Qdrant collection exists with specified vector size and a payload index."""
        if not self.client: return
        try:
            self.client.get_collection(collection_name=collection_name)
            logger.info(f"Collection '{collection_name}' (vector_size: {vector_size}) already exists.")
            # TODO: Optionally verify if existing collection vector_size matches desired, recreate if not (destructive).
            # For now, assume it's compatible or was created correctly previously.
        except UnexpectedResponse as ue: # Specifically catch collection not found case
            if ue.status_code == 404:
                logger.info(f"Collection '{collection_name}' not found. Attempting to create with vector_size: {vector_size}...")
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE)
                )
                logger.info(f"Collection '{collection_name}' created successfully with vector_size: {vector_size}.")
            else:
                raise # Re-raise other unexpected responses
        try:
            self.client.create_payload_index(collection_name=collection_name, field_name=id_field_for_index, field_schema=models.PayloadSchemaType.KEYWORD)
            logger.info(f"Payload index ensured on '{id_field_for_index}' for collection '{collection_name}'.")
        except Exception as e_index:
            logger.warning(f"Could not create payload index on '{id_field_for_index}' for '{collection_name}': {e_index}")

    def close_qdrant_client(self):
        if self.client:
            try:
                self.client.close()
                logger.info("Qdrant client closed successfully.")
            except Exception as e:
                logger.error(f"Error closing Qdrant client: {e}")
            finally:
                self.client = None
                self.metadata_adapter = self.schema_adapter = self.contextual_adapter = self.knowledge_adapter = self.operational_adapter = None
                self.mythic_object_adapter = self.mythic_link_adapter = None # Also nullify new adapters
                self.knowledge_embedder = None

    # --- Metadata Management (Refactored to use QdrantAdapter) ---
    def register_metadata(self, data: DataSourceMetadata) -> bool: # Takes model instance
        if not self.metadata_adapter: raise ConfigurationError("MetadataAdapter not initialized")
        try: 
            # Pydantic validation happens on model instantiation if data is dict, or by adapter if model passed
            return self.metadata_adapter.upsert_model(METADATA_COLLECTION, data, METADATA_ID_FIELD)
        except PydanticValidationError as ve: raise ValidationError("Invalid metadata for registration", ve)
        except DataCatalogException: raise # Re-raise our specific exceptions from adapter
        except Exception as e: raise StorageFailure("Unexpected error registering metadata", e)

    def get_metadata(self, data_source_id: str) -> Optional[DataSourceMetadata]:
        if not self.metadata_adapter: raise ConfigurationError("MetadataAdapter not initialized")
        try: return self.metadata_adapter.get_model_by_id(METADATA_COLLECTION, data_source_id, DataSourceMetadata, METADATA_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Unexpected error getting metadata for ID '{data_source_id}'", e)

    def update_metadata(self, data_source_id: str, data_update: DataSourceMetadata) -> Optional[DataSourceMetadata]: # Expects full model for update
        if not self.metadata_adapter: raise ConfigurationError("MetadataAdapter not initialized")
        try: 
            if data_update.data_source_id != data_source_id:
                # This check is important: the ID in path must match the ID in the payload being updated.
                # Adapter will use id_value (path) for lookup, but model_update_instance payload is used for update content.
                raise ValidationError(f"Path ID '{data_source_id}' does not match payload ID '{data_update.data_source_id}' for metadata update.")
            return self.metadata_adapter.update_model_by_id(METADATA_COLLECTION, data_source_id, data_update, METADATA_ID_FIELD)
        except PydanticValidationError as ve: raise ValidationError("Invalid metadata for update", ve)
        except DataCatalogException: raise 
        except Exception as e: raise StorageFailure(f"Unexpected error updating metadata for ID '{data_source_id}'", e)

    def delete_metadata(self, data_source_id: str) -> bool:
        if not self.metadata_adapter: raise ConfigurationError("MetadataAdapter not initialized")
        try: return self.metadata_adapter.delete_model_by_id(METADATA_COLLECTION, data_source_id, METADATA_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Unexpected error deleting metadata for ID '{data_source_id}'", e)

    def list_data_sources(self) -> List[str]:
        if not self.metadata_adapter: raise ConfigurationError("MetadataAdapter not initialized")
        try: return self.metadata_adapter.list_all_model_ids(METADATA_COLLECTION, METADATA_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure("Unexpected error listing data sources", e)

    # --- Schema Management (Refactored to use QdrantAdapter) ---
    def register_schema(self, data: SchemaDefinition) -> bool:
        if not self.schema_adapter: raise ConfigurationError("SchemaAdapter not initialized")
        try: return self.schema_adapter.upsert_model(SCHEMA_COLLECTION, data, SCHEMA_ID_FIELD)
        except PydanticValidationError as ve: raise ValidationError("Invalid schema for registration", ve)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure("Unexpected error registering schema", e)

    def get_schema(self, schema_id: str) -> Optional[SchemaDefinition]:
        if not self.schema_adapter: raise ConfigurationError("SchemaAdapter not initialized")
        try: return self.schema_adapter.get_model_by_id(SCHEMA_COLLECTION, schema_id, SchemaDefinition, SCHEMA_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Unexpected error getting schema for ID '{schema_id}'", e)

    def update_schema(self, schema_id: str, data_update: SchemaDefinition) -> Optional[SchemaDefinition]:
        if not self.schema_adapter: raise ConfigurationError("SchemaAdapter not initialized")
        try:
            if data_update.schema_id != schema_id: 
                raise ValidationError(f"Path ID '{schema_id}' does not match payload ID '{data_update.schema_id}' for schema update.")
            return self.schema_adapter.update_model_by_id(SCHEMA_COLLECTION, schema_id, data_update, SCHEMA_ID_FIELD)
        except PydanticValidationError as ve: raise ValidationError("Invalid schema for update", ve)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Unexpected error updating schema for ID '{schema_id}'", e)

    def delete_schema(self, schema_id: str) -> bool:
        if not self.schema_adapter: raise ConfigurationError("SchemaAdapter not initialized")
        try: return self.schema_adapter.delete_model_by_id(SCHEMA_COLLECTION, schema_id, SCHEMA_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Unexpected error deleting schema for ID '{schema_id}'", e)
    
    def list_schemas(self) -> List[str]:
        if not self.schema_adapter: raise ConfigurationError("SchemaAdapter not initialized")
        try: return self.schema_adapter.list_all_model_ids(SCHEMA_COLLECTION, SCHEMA_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure("Unexpected error listing schemas", e)

    # --- MemoryAgent Data Handlers (Contextual, Knowledge, Operational - already use adapter) ---
    # These methods can also benefit from wrapping adapter calls to catch DataCatalogException 
    # and re-raise as more specific service errors or add logging if needed.
    # For consistency, I'll add similar try-except blocks.

    def register_contextual(self, data: ContextualData) -> Optional[ContextualData]:
        if not self.contextual_adapter: raise ConfigurationError("ContextualAdapter not initialized")
        try: 
            success = self.contextual_adapter.upsert_model(CONTEXTUAL_DATA_COLLECTION, data, SESSION_ID_FIELD)
            return data if success else None
        except DataCatalogException: raise 
        except Exception as e: raise StorageFailure("Error registering contextual data", e)

    def get_contextual(self, session_id: str) -> Optional[ContextualData]:
        if not self.contextual_adapter: raise ConfigurationError("ContextualAdapter not initialized")
        try: return self.contextual_adapter.get_model_by_id(CONTEXTUAL_DATA_COLLECTION, session_id, ContextualData, SESSION_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Error getting contextual data for session '{session_id}'", e)

    def update_contextual(self, session_id: str, data_update: ContextualData) -> Optional[ContextualData]:
        if not self.contextual_adapter: return None
        # Ensure session_id in path matches session_id in body if it's part of the model and required for identification
        if data_update.session_id != session_id:
            logger.error(f"Path session_id '{session_id}' does not match payload session_id '{data_update.session_id}' for update_contextual.")
            # Depending on API spec, could raise error or just use path param for lookup and body for data
            # For now, let's assume the body's session_id should match or be ignored if path is authoritative.
            # Or, more simply, ensure the model sent for update *has* the correct session_id.
            # The adapter's update_model_by_id assumes id_value is the lookup key, and model_update_instance contains the new state.
            # The natural ID (session_id) *must* be in the payload that model_update_instance serializes to for the adapter.
            data_update.session_id = session_id # Ensure the model being used for update has the correct ID for payload storage
        logger.info(f"Updating contextual data for session_id: {session_id}")
        return self.contextual_adapter.update_model_by_id(CONTEXTUAL_DATA_COLLECTION, session_id, data_update, SESSION_ID_FIELD)

    def delete_contextual(self, session_id: str) -> bool:
        if not self.contextual_adapter: return False
        logger.info(f"Deleting contextual data for session_id: {session_id}")
        return self.contextual_adapter.delete_model_by_id(CONTEXTUAL_DATA_COLLECTION, session_id, SESSION_ID_FIELD)
    
    def list_contextual_sessions(self) -> List[str]: # New method for API
        if not self.contextual_adapter: return []
        return self.contextual_adapter.list_all_model_ids(CONTEXTUAL_DATA_COLLECTION, SESSION_ID_FIELD)

    # --- KnowledgeData Handlers (Using QdrantAdapter with Embedder) ---
    def register_knowledge(self, data: KnowledgeData) -> Optional[KnowledgeData]:
        if not self.knowledge_adapter: 
            logger.warning("Knowledge adapter not available for register_knowledge.")
            return None
        success = self.knowledge_adapter.upsert_model(KNOWLEDGE_DATA_COLLECTION, data, KNOWLEDGE_ID_FIELD)
        return data if success else None

    def get_knowledge(self, knowledge_id: str) -> Optional[KnowledgeData]:
        if not self.knowledge_adapter: return None
        logger.info(f"Getting knowledge data for id: {knowledge_id}")
        return self.knowledge_adapter.get_model_by_id(KNOWLEDGE_DATA_COLLECTION, knowledge_id, KnowledgeData, KNOWLEDGE_ID_FIELD)

    def update_knowledge(self, knowledge_id: str, data_update: KnowledgeData) -> Optional[KnowledgeData]:
        if not self.knowledge_adapter: 
            logger.warning("Knowledge adapter not available for update_knowledge.")
            return None
        if data_update.knowledge_id != knowledge_id:
            logger.warning(f"Knowledge update: Path id '{knowledge_id}' differs from payload '{data_update.knowledge_id}'. Using path ID.")
            data_update.knowledge_id = knowledge_id
        return self.knowledge_adapter.update_model_by_id(KNOWLEDGE_DATA_COLLECTION, knowledge_id, data_update, KNOWLEDGE_ID_FIELD)

    def delete_knowledge(self, knowledge_id: str) -> bool:
        if not self.knowledge_adapter: return False
        logger.info(f"Deleting knowledge data for id: {knowledge_id}")
        return self.knowledge_adapter.delete_model_by_id(KNOWLEDGE_DATA_COLLECTION, knowledge_id, KNOWLEDGE_ID_FIELD)

    def list_knowledge_items(self) -> List[str]: # New method for API
        if not self.knowledge_adapter: return []
        return self.knowledge_adapter.list_all_model_ids(KNOWLEDGE_DATA_COLLECTION, KNOWLEDGE_ID_FIELD)

    def search_similar_knowledge(self, query_text: str, top_k: int = 5, score_threshold: Optional[float] = None) -> List[KnowledgeData]:
        """Searches for knowledge items similar to the query_text."""
        if not self.knowledge_adapter or not self.knowledge_embedder or not self.knowledge_embedder.model:
            logger.warning("Knowledge adapter or embedder not available for search.")
            return []
        try:
            query_vector = self.knowledge_embedder.model.encode(query_text).tolist()
            return self.knowledge_adapter.search_similar_models(
                KNOWLEDGE_DATA_COLLECTION, 
                query_vector, 
                KnowledgeData, 
                top_k=top_k,
                score_threshold=score_threshold
            )
        except Exception as e:
            logger.error(f"Error during similarity search for knowledge: {e}")
            return []

    # --- OperationalData Handlers (Using QdrantAdapter) ---
    def register_operational(self, data: OperationalData) -> Optional[OperationalData]:
        if not self.operational_adapter: return None
        logger.info(f"Registering operational data with id: {data.operation_id}")
        success = self.operational_adapter.upsert_model(OPERATIONAL_DATA_COLLECTION, data, OPERATION_ID_FIELD)
        return data if success else None

    def get_operational(self, operation_id: str) -> Optional[OperationalData]:
        if not self.operational_adapter: return None
        logger.info(f"Getting operational data for id: {operation_id}")
        return self.operational_adapter.get_model_by_id(OPERATIONAL_DATA_COLLECTION, operation_id, OperationalData, OPERATION_ID_FIELD)

    def update_operational(self, operation_id: str, data_update: OperationalData) -> Optional[OperationalData]:
        if not self.operational_adapter: return None
        if data_update.operation_id != operation_id:
            logger.warning(f"Operational update: Path id '{operation_id}' differs from payload '{data_update.operation_id}'. Using path ID.")
            data_update.operation_id = operation_id
        logger.info(f"Updating operational data for id: {operation_id}")
        return self.operational_adapter.update_model_by_id(OPERATIONAL_DATA_COLLECTION, operation_id, data_update, OPERATION_ID_FIELD)

    def delete_operational(self, operation_id: str) -> bool:
        if not self.operational_adapter: return False
        logger.info(f"Deleting operational data for id: {operation_id}")
        return self.operational_adapter.delete_model_by_id(OPERATIONAL_DATA_COLLECTION, operation_id, OPERATION_ID_FIELD)

    def list_operational_items(self) -> List[str]: # New method for API
        if not self.operational_adapter: return []
        return self.operational_adapter.list_all_model_ids(OPERATIONAL_DATA_COLLECTION, OPERATION_ID_FIELD)

    # --- MythicObject Management ---
    def register_mythic_object(self, data: MythicObject) -> bool:
        if not self.mythic_object_adapter: raise ConfigurationError("MythicObjectAdapter not initialized")
        try:
            return self.mythic_object_adapter.upsert_model(MYTHIC_OBJECT_COLLECTION, data, MYTHIC_OBJECT_ID_FIELD)
        except PydanticValidationError as ve: raise ValidationError("Invalid MythicObject for registration", original_exception=ve)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure("Unexpected error registering MythicObject", original_exception=e)

    def get_mythic_object(self, mythic_object_id: str) -> Optional[MythicObject]:
        if not self.mythic_object_adapter: raise ConfigurationError("MythicObjectAdapter not initialized")
        try:
            return self.mythic_object_adapter.get_model_by_id(MYTHIC_OBJECT_COLLECTION, mythic_object_id, MythicObject, MYTHIC_OBJECT_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Unexpected error getting MythicObject for ID '{mythic_object_id}'", original_exception=e)

    def update_mythic_object(self, mythic_object_id: str, data_update: MythicObject) -> Optional[MythicObject]:
        if not self.mythic_object_adapter: raise ConfigurationError("MythicObjectAdapter not initialized")
        try:
            if data_update.id != mythic_object_id: 
                raise ValidationError(f"Path ID '{mythic_object_id}' does not match payload ID '{data_update.id}' for MythicObject update.")
            return self.mythic_object_adapter.update_model_by_id(MYTHIC_OBJECT_COLLECTION, mythic_object_id, data_update, MYTHIC_OBJECT_ID_FIELD)
        except PydanticValidationError as ve: raise ValidationError("Invalid MythicObject for update", original_exception=ve)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Unexpected error updating MythicObject for ID '{mythic_object_id}'", original_exception=e)

    def delete_mythic_object(self, mythic_object_id: str) -> bool:
        if not self.mythic_object_adapter: raise ConfigurationError("MythicObjectAdapter not initialized")
        try:
            return self.mythic_object_adapter.delete_model_by_id(MYTHIC_OBJECT_COLLECTION, mythic_object_id, MYTHIC_OBJECT_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Unexpected error deleting MythicObject for ID '{mythic_object_id}'", original_exception=e)
    
    def list_mythic_objects(self) -> List[str]:
        if not self.mythic_object_adapter: raise ConfigurationError("MythicObjectAdapter not initialized")
        try:
            return self.mythic_object_adapter.list_all_model_ids(MYTHIC_OBJECT_COLLECTION, MYTHIC_OBJECT_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure("Unexpected error listing MythicObjects", original_exception=e)

    # --- MythicLink Management ---
    def register_mythic_link(self, data: MythicLink) -> bool:
        if not self.mythic_link_adapter: raise ConfigurationError("MythicLinkAdapter not initialized")
        try:
            return self.mythic_link_adapter.upsert_model(MYTHIC_LINK_COLLECTION, data, MYTHIC_LINK_ID_FIELD)
        except PydanticValidationError as ve: raise ValidationError("Invalid MythicLink for registration", original_exception=ve)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure("Unexpected error registering MythicLink", original_exception=e)

    def get_mythic_link(self, mythic_link_id: str) -> Optional[MythicLink]:
        if not self.mythic_link_adapter: raise ConfigurationError("MythicLinkAdapter not initialized")
        try:
            return self.mythic_link_adapter.get_model_by_id(MYTHIC_LINK_COLLECTION, mythic_link_id, MythicLink, MYTHIC_LINK_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Unexpected error getting MythicLink for ID '{mythic_link_id}'", original_exception=e)

    def update_mythic_link(self, mythic_link_id: str, data_update: MythicLink) -> Optional[MythicLink]:
        if not self.mythic_link_adapter: raise ConfigurationError("MythicLinkAdapter not initialized")
        try:
            if data_update.id != mythic_link_id: 
                raise ValidationError(f"Path ID '{mythic_link_id}' does not match payload ID '{data_update.id}' for MythicLink update.")
            return self.mythic_link_adapter.update_model_by_id(MYTHIC_LINK_COLLECTION, mythic_link_id, data_update, MYTHIC_LINK_ID_FIELD)
        except PydanticValidationError as ve: raise ValidationError("Invalid MythicLink for update", original_exception=ve)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Unexpected error updating MythicLink for ID '{mythic_link_id}'", original_exception=e)

    def delete_mythic_link(self, mythic_link_id: str) -> bool:
        if not self.mythic_link_adapter: raise ConfigurationError("MythicLinkAdapter not initialized")
        try:
            return self.mythic_link_adapter.delete_model_by_id(MYTHIC_LINK_COLLECTION, mythic_link_id, MYTHIC_LINK_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure(f"Unexpected error deleting MythicLink for ID '{mythic_link_id}'", original_exception=e)

    def list_mythic_links(self) -> List[str]:
        if not self.mythic_link_adapter: raise ConfigurationError("MythicLinkAdapter not initialized")
        try:
            return self.mythic_link_adapter.list_all_model_ids(MYTHIC_LINK_COLLECTION, MYTHIC_LINK_ID_FIELD)
        except DataCatalogException: raise
        except Exception as e: raise StorageFailure("Unexpected error listing MythicLinks", original_exception=e)

    # --- API Endpoint Integration (Placeholder - to be implemented with FastAPI, etc.) ---
    async def handle_register_metadata_request(self, request_data: Dict[str, Any]):
        # Needs parsing, validation, calling self.register_metadata
        # Example: self.register_metadata(request_data['id'], request_data['metadata'])
        pass

    async def handle_get_metadata_request(self, data_source_id: str):
        # Example: return self.get_metadata(data_source_id)
        pass

    # --- Memory Agent Integration ---
    def get_schema_for_memory(self, data_topic: str) -> Optional[Dict[str, Any]]:
        """
        Provides the schema relevant for a given data topic, potentially used by MemoryAgent.
        This logic needs refinement based on how topics map to schemas.
        """
        # TODO: Implement robust logic to map data_topic to schema_id
        # This might involve looking up a mapping in metadata or another Qdrant collection.
        # For now, using a direct naming convention:
        schema_id = f"schema_for_{data_topic.replace(' ', '_').lower()}"
        logger.info(f"Attempting to retrieve schema '{schema_id}' for topic '{data_topic}' based on direct mapping.")
        schema_def = self.get_schema(schema_id)
        return schema_def.model_dump(by_alias=True) if schema_def else None

if __name__ == '__main__':
    # Example usage/basic test
    # Ensure Qdrant is running (e.g., via Docker: docker run -p 6333:6333 qdrant/qdrant)
    
    catalog = DataCatalogService()

    if catalog.client and catalog.contextual_adapter and catalog.knowledge_adapter and catalog.operational_adapter: # Check adapter too
        # Register Metadata
        meta1_orig_id = "user_profiles_db_v3"
        meta1_payload_dict = {"description": "Main user profile database (Validated)", "type": "PostgreSQL", "owner": "auth_team", "tags": ["users", "pii"]}
        catalog.register_metadata(DataSourceMetadata(**meta1_payload_dict))

        meta2_orig_id = "clickstream_kafka_v3"
        meta2_payload_dict = {"description": "Real-time user clicks (Validated)", "type": "KafkaTopic", "custom_field": "example"}
        catalog.register_metadata(DataSourceMetadata(**meta2_payload_dict))

        # Attempt to register invalid metadata
        invalid_meta_payload = {"name": "missing_description_and_type"} # Missing required fields
        logger.info(f"Attempting to register invalid metadata for '{invalid_meta_payload.get('name', 'unknown_id')}'...")
        catalog.register_metadata(DataSourceMetadata(**invalid_meta_payload))

        # Get Metadata
        retrieved_meta = catalog.get_metadata(meta1_orig_id)
        print(f"Metadata for {meta1_orig_id}: {retrieved_meta}")
        # Adjust assertion to match Pydantic model (tags will be present even if empty in input if not provided)
        expected_meta1 = DataSourceMetadata(**meta1_payload_dict).model_dump(by_alias=True)
        assert retrieved_meta == expected_meta1 if retrieved_meta else False, f"Expected {expected_meta1}, got {retrieved_meta}"

        # List sources
        print(f"Data sources: {catalog.list_data_sources()}")
        assert meta1_orig_id in catalog.list_data_sources()

        # Register Schema
        schema1_orig_id = "schema_user_profiles_v3"
        user_schema_payload_dict = {
            "type": "object", # This corresponds to schema_type in the Pydantic model
            "description": "Validated user profile schema",
            "properties": {
                "userId": {"type": "string", "description": "Unique user identifier"},
                "email": {"type": "string", "format": "email"},
                "profile_version": {"type": "integer"},
                "custom_prop": {"type": "boolean", "extra_attr": "allowed"} # Example of extra fields in property
            },
            "required": ["userId", "email"]
        }
        catalog.register_schema(SchemaDefinition(**user_schema_payload_dict))
        
        # Attempt to register invalid schema (e.g., property type missing)
        invalid_schema_payload = {
            "type": "object",
            "properties": {"bad_prop": {"description": "missing type"}}
        }
        logger.info(f"Attempting to register invalid schema for 'invalid_schema_test'...")
        catalog.register_schema(SchemaDefinition(**invalid_schema_payload))
        
        retrieved_schema_payload = catalog.get_schema(schema1_orig_id)
        print(f"Schema for {schema1_orig_id}: {retrieved_schema_payload}")
        expected_schema1 = SchemaDefinition(**user_schema_payload_dict).model_dump(by_alias=True)
        assert retrieved_schema_payload == expected_schema1 if retrieved_schema_payload else False, f"Expected {expected_schema1}, got {retrieved_schema_payload}"

        # Get Schema for Memory Agent (Example)
        memory_topic = "user profiles v3" # Example topic
        schema_for_memory_orig_id = f"schema_for_{memory_topic.replace(' ', '_').lower()}"
        schema_for_memory_payload = {"type": "object", "properties": {"userId": {"type": "string"}, "email": {"type": "string"}}, "required": ["userId"]}
        catalog.register_schema(SchemaDefinition(**schema_for_memory_payload))
        
        retrieved_schema_for_memory = catalog.get_schema_for_memory(memory_topic)
        print(f"Schema for '{memory_topic}' topic: {retrieved_schema_for_memory}")
        assert retrieved_schema_for_memory is not None

        # Update metadata example
        catalog.update_metadata(meta1_orig_id, DataSourceMetadata(data_source_id=meta1_orig_id, description="Main user profile database (Updated)", type="PostgreSQL", owner="auth_team", tags=["users", "pii"]))
        updated_meta = catalog.get_metadata(meta1_orig_id)
        print(f"Updated metadata for {meta1_orig_id}: {updated_meta}")
        assert updated_meta and updated_meta.description == "Main user profile database (Updated)", f"Update failed, description is {updated_meta.description if updated_meta else None}"

        # Delete
        catalog.delete_metadata(meta1_orig_id)
        catalog.delete_metadata(meta2_orig_id)
        catalog.delete_schema(schema1_orig_id)
        catalog.delete_schema("invalid_schema_test") # Clean up example schema
        
        print(f"Data sources after all deletes: {catalog.list_data_sources()}")
        assert meta1_orig_id not in catalog.list_data_sources()
        print(f"Schema {schema1_orig_id} after delete: {catalog.get_schema(schema1_orig_id)}")
        assert catalog.get_schema(schema1_orig_id) is None

        # Test Contextual Data
        ctx1 = ContextualData(session_id="session_abc_123", user_id="user1", current_focus="testing_adapter")
        reg_ctx1 = catalog.register_contextual(ctx1)
        assert reg_ctx1 is not None and reg_ctx1.session_id == "session_abc_123"
        get_ctx1 = catalog.get_contextual("session_abc_123")
        assert get_ctx1 is not None and get_ctx1.current_focus == "testing_adapter"
        
        updated_ctx_payload = ContextualData(session_id="session_abc_123", current_focus="adapter_update_tested", active_tools=["qdrant_adapter"])
        upd_ctx1 = catalog.update_contextual("session_abc_123", updated_ctx_payload)
        assert upd_ctx1 is not None and upd_ctx1.active_tools == ["qdrant_adapter"]
        assert upd_ctx1.current_focus == "adapter_update_tested"

        # Test Knowledge Data
        know1 = KnowledgeData(type="test_pattern", content={"detail": "Adapter pattern is useful"}, tags=["testing"])
        # knowledge_id is auto-generated, so we get it from the returned object
        reg_know1 = catalog.register_knowledge(know1)
        assert reg_know1 is not None
        know1_id = reg_know1.knowledge_id
        get_know1 = catalog.get_knowledge(know1_id)
        assert get_know1 is not None and get_know1.content.get("detail") == "Adapter pattern is useful"

        # Test Operational Data
        op1 = OperationalData(agent_id="test_agent_007", task_type="adapter_test", status="pending", inputs={"param": 1})
        reg_op1 = catalog.register_operational(op1)
        assert reg_op1 is not None
        op1_id = reg_op1.operation_id
        get_op1 = catalog.get_operational(op1_id)
        assert get_op1 is not None and get_op1.status == "pending"

        print("\n--- Listing Memory Data IDs ---")
        print(f"Contextual Session IDs: {catalog.list_contextual_sessions()}")
        print(f"Knowledge IDs: {catalog.list_knowledge_items()}")
        print(f"Operational IDs: {catalog.list_operational_items()}")

        # Clean up test data
        del_ctx1 = catalog.delete_contextual("session_abc_123")
        assert del_ctx1 is True
        assert catalog.get_contextual("session_abc_123") is None
        
        del_know1 = catalog.delete_knowledge(know1_id)
        assert del_know1 is True
        assert catalog.get_knowledge(know1_id) is None

        del_op1 = catalog.delete_operational(op1_id)
        assert del_op1 is True
        assert catalog.get_operational(op1_id) is None
        
        print("\nCRUD tests for MemoryAgent data types passed.")

        # --- Test MythicObject and MythicLink CRUD (Conceptual) ---
        if catalog.mythic_object_adapter and catalog.mythic_link_adapter:
            print("--- Testing Mythic Layer CRUD ---")
            mo1_payload = {"source_ids": ["kd_test1"], "type": "test_object", "collapsed_content": {"detail": "test"}}
            mo1 = MythicObject(**mo1_payload)
            
            reg_mo1_success = catalog.register_mythic_object(mo1)
            assert reg_mo1_success, "Failed to register MythicObject"
            
            get_mo1 = catalog.get_mythic_object(mo1.id)
            assert get_mo1 is not None and get_mo1.type == "test_object", f"Failed to get MythicObject or type mismatch: {get_mo1}"
            print(f"Registered and retrieved MythicObject: {get_mo1.id}")

            mo1_update_payload = {"source_ids": ["kd_test1", "kd_test2"], "type": "updated_test_object", "collapsed_content": {"detail": "updated test"}, "tags": ["updated"]}
            # Need to pass the ID for update payload
            mo1_update = MythicObject(id=mo1.id, **mo1_update_payload)
            upd_mo1 = catalog.update_mythic_object(mo1.id, mo1_update)
            assert upd_mo1 is not None and upd_mo1.type == "updated_test_object" and "updated" in upd_mo1.tags, f"Failed to update MythicObject: {upd_mo1}"
            print(f"Updated MythicObject: {upd_mo1.id}")

            all_mo_ids = catalog.list_mythic_objects()
            assert mo1.id in all_mo_ids, "MythicObject ID not in list"
            print(f"Listed MythicObject IDs: {all_mo_ids}")

            # MythicLink
            ml1_payload = {"source_object_id": mo1.id, "target_object_id": "another_mythic_id_placeholder", "link_type": "test_link"}
            ml1 = MythicLink(**ml1_payload)
            
            reg_ml1_success = catalog.register_mythic_link(ml1)
            assert reg_ml1_success, "Failed to register MythicLink"

            get_ml1 = catalog.get_mythic_link(ml1.id)
            assert get_ml1 is not None and get_ml1.link_type == "test_link", f"Failed to get MythicLink or type mismatch: {get_ml1}"
            print(f"Registered and retrieved MythicLink: {get_ml1.id}")
            
            del_mo1_success = catalog.delete_mythic_object(mo1.id)
            assert del_mo1_success, "Failed to delete MythicObject"
            assert catalog.get_mythic_object(mo1.id) is None, "MythicObject not deleted"
            print(f"Deleted MythicObject: {mo1.id}")

            del_ml1_success = catalog.delete_mythic_link(ml1.id)
            assert del_ml1_success, "Failed to delete MythicLink"
            assert catalog.get_mythic_link(ml1.id) is None, "MythicLink not deleted"
            print(f"Deleted MythicLink: {ml1.id}")
            
            print("Mythic Layer CRUD tests passed conceptually.")
        else:
            print("MythicObject or MythicLink adapter not initialized, skipping their CRUD tests.")

        catalog.close_qdrant_client()
    else:
        print("Qdrant client or one of the adapters not initialized. Skipping DataCatalogService memory tests.") 