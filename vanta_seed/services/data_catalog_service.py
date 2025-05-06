import logging
import os
import uuid # Added for generating Qdrant point IDs
from typing import Dict, Any, Optional, List
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct, Distance, VectorParams, UpdateStatus
from pydantic import BaseModel, Field, Extra, ValidationError # Added ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

METADATA_COLLECTION = "vanta_metadata_catalog"
SCHEMA_COLLECTION = "vanta_schema_registry"
DUMMY_VECTOR_SIZE = 10 # Required by Qdrant, but not used for primary functionality here

# Field name for storing the user-provided ID within the Qdrant payload
ORIGINAL_ID_FIELD = "_vanta_original_id"

# --- Pydantic Models for Validation ---

class DataSourceMetadata(BaseModel):
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
        try:
            self.client = QdrantClient(url=self.qdrant_url)
            # self.client.heartbeat() # Check connection -- REMOVED as it causes an AttributeError
            # The QdrantClient constructor itself will raise if it cannot connect initially.
            logger.info(f"Successfully connected to Qdrant at {self.qdrant_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant at {self.qdrant_url}: {e}")
            # In a real app, you might want to raise this or have a retry mechanism
            self.client = None # Ensure client is None if connection failed
            return

        self._ensure_collection(METADATA_COLLECTION)
        self._ensure_collection(SCHEMA_COLLECTION)
        logger.info("DataCatalogService initialized with Qdrant.")

    def _ensure_collection(self, collection_name: str):
        if not self.client:
            logger.error("Qdrant client not initialized. Cannot ensure collection.")
            return
        collection_exists = False
        try:
            self.client.get_collection(collection_name=collection_name)
            logger.info(f"Collection '{collection_name}' already exists.")
            collection_exists = True
        except Exception: # Catches collection not found and other potential errors
            logger.info(f"Collection '{collection_name}' not found or error accessing. Attempting to create...")
            try:
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=DUMMY_VECTOR_SIZE, distance=Distance.COSINE)
                )
                logger.info(f"Successfully created collection '{collection_name}'.")
                collection_exists = True
            except Exception as e_create:
                logger.error(f"Failed to create collection '{collection_name}': {e_create}")
                return # If collection creation fails, don't try to create index

        if collection_exists:
            try:
                # Attempt to create a payload index on the ORIGINAL_ID_FIELD for faster lookups
                # field_schema type for keyword/string indexing is models.PayloadSchemaType.KEYWORD
                self.client.create_payload_index(
                    collection_name=collection_name, 
                    field_name=ORIGINAL_ID_FIELD, 
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
                logger.info(f"Ensured payload index exists for '{ORIGINAL_ID_FIELD}' in collection '{collection_name}'.")
            except Exception as e_index:
                # Qdrant might throw an error if the index already exists and is of a different type, 
                # or other specific conditions. For simple keyword index, it's often idempotent or silently ignored if compatible.
                logger.warning(f"Could not explicitly create or verify payload index for '{ORIGINAL_ID_FIELD}' in '{collection_name}'. It might already exist or an error occurred: {e_index}")


    # --- Metadata Management ---

    def register_metadata(self, data_source_id: str, metadata_dict: Dict[str, Any]) -> bool:
        """Registers metadata for a given data source ID after validating it.
        A new UUID is generated for the Qdrant point ID.
        The original data_source_id and validated metadata are stored in the payload.
        """
        if not self.client: return False
        try:
            # Validate the input metadata dictionary
            validated_metadata = DataSourceMetadata(**metadata_dict)
        except ValidationError as ve:
            logger.error(f"Invalid metadata provided for {data_source_id}: {ve}")
            return False
        
        try:
            qdrant_point_id = str(uuid.uuid4())
            
            payload = validated_metadata.model_dump(by_alias=True) # Use model_dump for Pydantic v2
            payload[ORIGINAL_ID_FIELD] = data_source_id

            point = PointStruct(
                id=qdrant_point_id,
                payload=payload,
                vector=[0.0] * DUMMY_VECTOR_SIZE # Dummy vector
            )
            response = self.client.upsert(collection_name=METADATA_COLLECTION, points=[point], wait=True)
            if response.status == UpdateStatus.COMPLETED:
                logger.info(f"Registered/Updated metadata for original ID {data_source_id} (Qdrant ID: {qdrant_point_id})")
                return True
            else:
                logger.error(f"Failed to register metadata for original ID {data_source_id}. Status: {response.status}")
                return False
        except Exception as e:
            logger.error(f"Error registering metadata for original ID {data_source_id}: {e}")
            return False

    def get_metadata(self, data_source_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves metadata by the original data_source_id using a filter."""
        if not self.client: return None
        try:
            search_result = self.client.scroll(
                collection_name=METADATA_COLLECTION,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key=ORIGINAL_ID_FIELD, match=models.MatchValue(value=data_source_id))]
                ),
                limit=1
            )
            if search_result and search_result[0]: # search_result is a tuple (points, next_offset)
                point = search_result[0][0]
                payload = point.payload
                if payload and ORIGINAL_ID_FIELD in payload: # Remove our internal ID field before returning
                    del payload[ORIGINAL_ID_FIELD]
                return payload
            else:
                logger.warning(f"Metadata for original ID {data_source_id} not found.")
                return None
        except Exception as e:
            logger.error(f"Error retrieving metadata for original ID {data_source_id}: {e}")
            return None

    def update_metadata(self, data_source_id: str, updates: Dict[str, Any]) -> bool:
        """Updates existing metadata for a data_source_id.
           Finds the Qdrant point by ORIGINAL_ID_FIELD, updates its payload.
        """
        if not self.client: return False
        try:
            # Find the point by the original data_source_id
            search_result = self.client.scroll(
                collection_name=METADATA_COLLECTION,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key=ORIGINAL_ID_FIELD, match=models.MatchValue(value=data_source_id))]
                ),
                limit=1,
                with_payload=True # Ensure payload is returned
            )

            if not (search_result and search_result[0]):
                logger.error(f"Metadata for original ID {data_source_id} not found. Cannot update.")
                return False
            
            qdrant_point = search_result[0][0]
            current_payload = qdrant_point.payload
            if not current_payload: # Should not happen if point found with payload
                current_payload = {}
            
            # Merge updates into the current payload
            current_payload.update(updates)
            # Ensure our internal ID field is still there
            current_payload[ORIGINAL_ID_FIELD] = data_source_id 

            # Upsert the point with the updated payload using its Qdrant ID
            point_to_update = PointStruct(
                id=qdrant_point.id, 
                payload=current_payload, 
                vector=[0.0] * DUMMY_VECTOR_SIZE
            )
            
            response = self.client.upsert(collection_name=METADATA_COLLECTION, points=[point_to_update], wait=True)
            if response.status == UpdateStatus.COMPLETED:
                logger.info(f"Updated metadata for original ID {data_source_id} (Qdrant ID: {qdrant_point.id})")
                return True
            else:
                logger.error(f"Failed to update metadata for original ID {data_source_id}. Status: {response.status}")
                return False
        except Exception as e:
            logger.error(f"Error updating metadata for original ID {data_source_id}: {e}")
            return False

    def delete_metadata(self, data_source_id: str) -> bool:
        """Deletes metadata by original data_source_id using a filter."""
        if not self.client: return False
        try:
            # Find points to delete by the original data_source_id
            # Note: This could delete multiple points if data_source_id wasn't unique (which it should be conceptually)
            response = self.client.delete(
                collection_name=METADATA_COLLECTION,
                points_selector=models.FilterSelector(filter=models.Filter(
                    must=[models.FieldCondition(key=ORIGINAL_ID_FIELD, match=models.MatchValue(value=data_source_id))]
                )),
                wait=True
            )
            # Delete operation status might be COMPLETED even if no points were found and deleted.
            # We could check the response for details if needed, but for now, this is simpler.
            if response.status == UpdateStatus.COMPLETED:
                logger.info(f"Delete operation for metadata with original ID {data_source_id} completed.")
                # To confirm if anything was actually deleted, one would need to count points before/after or check response op_num
                return True
            else:
                logger.warning(f"Delete operation for metadata with original ID {data_source_id} may not have completed as expected. Status: {response.status}")
                return False
        except Exception as e:
            logger.error(f"Error deleting metadata for original ID {data_source_id}: {e}")
            return False

    def list_data_sources(self) -> List[str]:
        """Lists all registered original data source IDs."""
        if not self.client: return []
        original_ids: List[str] = []
        try:
            next_offset = None
            while True:
                points, next_offset = self.client.scroll(
                    collection_name=METADATA_COLLECTION,
                    limit=100,
                    offset=next_offset,
                    with_payload=True, # We need the payload to get the original ID
                    with_vectors=False
                )
                for point in points:
                    if point.payload and ORIGINAL_ID_FIELD in point.payload:
                        original_ids.append(str(point.payload[ORIGINAL_ID_FIELD]))
                if not next_offset:
                    break
            return list(set(original_ids)) # Use set to ensure uniqueness if multiple Qdrant points somehow had the same original_id
        except Exception as e:
            logger.error(f"Error listing data sources: {e}")
            return []

    # --- Schema Management (similar to metadata) ---

    def register_schema(self, schema_id: str, schema_definition_dict: Dict[str, Any]) -> bool:
        """Registers a schema definition after validating it. Original schema_id stored in payload."""
        if not self.client: return False
        try:
            # Validate the input schema definition dictionary
            validated_schema = SchemaDefinition(**schema_definition_dict)
        except ValidationError as ve:
            logger.error(f"Invalid schema definition provided for {schema_id}: {ve}")
            return False
        
        try:
            qdrant_point_id = str(uuid.uuid4())
            payload = validated_schema.model_dump(by_alias=True) # Use model_dump for Pydantic v2
            payload[ORIGINAL_ID_FIELD] = schema_id

            point = PointStruct(
                id=qdrant_point_id,
                payload=payload,
                vector=[0.0] * DUMMY_VECTOR_SIZE
            )
            response = self.client.upsert(collection_name=SCHEMA_COLLECTION, points=[point], wait=True)
            if response.status == UpdateStatus.COMPLETED:
                logger.info(f"Registered/Updated schema for original ID {schema_id} (Qdrant ID: {qdrant_point_id})")
                return True
            else:
                logger.error(f"Failed to register schema for original ID {schema_id}. Status: {response.status}")
                return False
        except Exception as e:
            logger.error(f"Error registering schema for original ID {schema_id}: {e}")
            return False

    def get_schema(self, schema_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a schema definition by original schema_id using a filter."""
        if not self.client: return None
        try:
            search_result = self.client.scroll(
                collection_name=SCHEMA_COLLECTION,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key=ORIGINAL_ID_FIELD, match=models.MatchValue(value=schema_id))]
                ),
                limit=1
            )
            if search_result and search_result[0]:
                point = search_result[0][0]
                payload = point.payload
                if payload and ORIGINAL_ID_FIELD in payload:
                    del payload[ORIGINAL_ID_FIELD]
                return payload
            else:
                logger.warning(f"Schema for original ID {schema_id} not found.")
                return None
        except Exception as e:
            logger.error(f"Error retrieving schema for original ID {schema_id}: {e}")
            return None

    def delete_schema(self, schema_id: str) -> bool:
        """Deletes a schema definition by original schema_id using a filter."""
        if not self.client: return False
        try:
            response = self.client.delete(
                collection_name=SCHEMA_COLLECTION,
                points_selector=models.FilterSelector(filter=models.Filter(
                    must=[models.FieldCondition(key=ORIGINAL_ID_FIELD, match=models.MatchValue(value=schema_id))]
                )),
                wait=True
            )
            if response.status == UpdateStatus.COMPLETED:
                logger.info(f"Delete operation for schema with original ID {schema_id} completed.")
                return True
            else:
                logger.warning(f"Delete operation for schema with original ID {schema_id} may not have completed as expected. Status: {response.status}")
                return False
        except Exception as e:
            logger.error(f"Error deleting schema for original ID {schema_id}: {e}")
            return False

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
        return self.get_schema(schema_id)

if __name__ == '__main__':
    # Example usage/basic test
    # Ensure Qdrant is running (e.g., via Docker: docker run -p 6333:6333 qdrant/qdrant)
    
    catalog = DataCatalogService()

    if catalog.client: # Proceed only if client connection was successful
        # Register Metadata
        meta1_orig_id = "user_profiles_db_v3"
        meta1_payload_dict = {"description": "Main user profile database (Validated)", "type": "PostgreSQL", "owner": "auth_team", "tags": ["users", "pii"]}
        catalog.register_metadata(meta1_orig_id, meta1_payload_dict)

        meta2_orig_id = "clickstream_kafka_v3"
        meta2_payload_dict = {"description": "Real-time user clicks (Validated)", "type": "KafkaTopic", "custom_field": "example"}
        catalog.register_metadata(meta2_orig_id, meta2_payload_dict)

        # Attempt to register invalid metadata
        invalid_meta_payload = {"name": "missing_description_and_type"} # Missing required fields
        logger.info(f"Attempting to register invalid metadata for '{invalid_meta_payload.get('name', 'unknown_id')}'...")
        catalog.register_metadata("invalid_meta_source", invalid_meta_payload)

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
        catalog.register_schema(schema1_orig_id, user_schema_payload_dict)
        
        # Attempt to register invalid schema (e.g., property type missing)
        invalid_schema_payload = {
            "type": "object",
            "properties": {"bad_prop": {"description": "missing type"}}
        }
        logger.info(f"Attempting to register invalid schema for 'invalid_schema_test'...")
        catalog.register_schema("invalid_schema_test", invalid_schema_payload)
        
        retrieved_schema_payload = catalog.get_schema(schema1_orig_id)
        print(f"Schema for {schema1_orig_id}: {retrieved_schema_payload}")
        expected_schema1 = SchemaDefinition(**user_schema_payload_dict).model_dump(by_alias=True)
        assert retrieved_schema_payload == expected_schema1 if retrieved_schema_payload else False, f"Expected {expected_schema1}, got {retrieved_schema_payload}"

        # Get Schema for Memory Agent (Example)
        memory_topic = "user profiles v3" # Example topic
        schema_for_memory_orig_id = f"schema_for_{memory_topic.replace(' ', '_').lower()}"
        schema_for_memory_payload = {"type": "object", "properties": {"userId": {"type": "string"}, "email": {"type": "string"}}, "required": ["userId"]}
        catalog.register_schema(schema_for_memory_orig_id, schema_for_memory_payload)
        
        retrieved_schema_for_memory = catalog.get_schema_for_memory(memory_topic)
        print(f"Schema for '{memory_topic}' topic: {retrieved_schema_for_memory}")
        assert retrieved_schema_for_memory is not None

        # Update metadata example
        catalog.update_metadata(meta1_orig_id, {"status": "active_v2", "region": "us-west-2"})
        updated_meta = catalog.get_metadata(meta1_orig_id)
        print(f"Updated metadata for {meta1_orig_id}: {updated_meta}")
        assert updated_meta and updated_meta.get("status") == "active_v2", f"Update failed, status is {updated_meta.get('status') if updated_meta else None}"

        # Delete
        catalog.delete_metadata(meta1_orig_id)
        catalog.delete_metadata(meta2_orig_id)
        catalog.delete_schema(schema1_orig_id)
        catalog.delete_schema("invalid_schema_test") # Clean up example schema
        
        print(f"Data sources after all deletes: {catalog.list_data_sources()}")
        assert meta1_orig_id not in catalog.list_data_sources()
        print(f"Schema {schema1_orig_id} after delete: {catalog.get_schema(schema1_orig_id)}")
        assert catalog.get_schema(schema1_orig_id) is None
    else:
        print("Qdrant client not initialized. Skipping example usage.") 