from fastapi import FastAPI, HTTPException, Body, Path, status, APIRouter
from typing import Dict, Any, List, Optional, Literal
import sys
import os
import uuid # Import UUID
import logging
from contextlib import asynccontextmanager

# Correct path adjustments (assuming catalog_api.py is in vanta_seed/api/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VANTA_SEED_DIR = os.path.dirname(SCRIPT_DIR)
PROJECT_ROOT = os.path.dirname(VANTA_SEED_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from vanta_seed.services.data_catalog_service import (
    DataCatalogService, 
    DataSourceMetadata, # Locally defined model in service file (ok for now)
    SchemaDefinition,   # Locally defined model in service file (ok for now)
)
# Import updated schemas including BaseMemoryRecord implicitly
from vanta_seed.schemas.memory_agent_schemas import ContextualData, KnowledgeData, OperationalData
from vanta_seed.schemas.mythic_schemas import MythicObject, MythicLink

# Import custom exceptions for handling
from vanta_seed.exceptions import (
    NotFound, 
    ValidationError, 
    StorageFailure, 
    ConnectionFailure, 
    OperationFailure,
    ConfigurationError
)

# Configure a logger for this API module
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Global instance of the service
data_catalog_service: Optional[DataCatalogService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... (lifespan function remains the same) ...
    global data_catalog_service
    logger.info("FastAPI app startup: Initializing DataCatalogService...")
    try:
        data_catalog_service = DataCatalogService()
        if not data_catalog_service.client:
            logger.error("CRITICAL: DataCatalogService FAILED to connect to Qdrant during startup. API endpoints will likely fail.")
        else:
            logger.info("DataCatalogService initialized and Qdrant client is available.")
    except (ConnectionFailure, ConfigurationError, OperationFailure) as e:
        logger.critical(f"FATAL: Failed to initialize DataCatalogService during startup: {e}")
        # Optional: could raise exception here to prevent FastAPI starting if service init fails critically
        data_catalog_service = None # Ensure service is None if init failed
    except Exception as e:
        logger.critical(f"FATAL: Unexpected error during DataCatalogService initialization: {e}", exc_info=True)
        data_catalog_service = None # Ensure service is None
    
    yield
    
    logger.info("FastAPI app shutdown: Cleaning up resources (if any)...")
    if data_catalog_service and hasattr(data_catalog_service, 'close_qdrant_client'):
        data_catalog_service.close_qdrant_client()
    data_catalog_service = None

app = FastAPI(
    title="VANTA Unified Memory & Catalog API", # Updated Title
    description="API for VANTA's universal memory store (Contextual, Knowledge, Operational, Mythic) and Data Catalog.", # Updated Desc
    version="1.3.0", # Updated Version
    lifespan=lifespan
)

# Helper for Qdrant client check and service availability
def get_data_catalog_service() -> DataCatalogService:
    if data_catalog_service is None:
        logger.error("DataCatalogService was not successfully initialized during startup.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data Catalog Service is not available. Check service logs for initialization errors."
        )
    return data_catalog_service

# --- API Routers ---
metadata_router = APIRouter(prefix="/metadata", tags=["Metadata"])
schema_router = APIRouter(prefix="/schemas", tags=["Schemas"])
memory_router = APIRouter(prefix="/memory", tags=["Memory"])

# --- Metadata API Endpoints ---

# NOTE: Using the locally defined DataSourceMetadata from service for now.
# If this needs BaseMemoryRecord fields later, it should be moved to schemas/

@metadata_router.post("/{data_source_id}", 
                      response_model=DataSourceMetadata, # Return the created/updated object
                      status_code=status.HTTP_201_CREATED,
                      summary="Register or Update Data Source Metadata")
async def register_or_update_metadata(
    data_source_id: str = Path(..., title="The unique identifier for the data source", min_length=1),
    metadata_in: DataSourceMetadata = Body(...)
) -> DataSourceMetadata:
    """
    Registers metadata for a new data source or updates an existing one.
    The `data_source_id` in the path **must** match `data_source_id` in the body.
    Uses Qdrant's upsert logic.
    """
    service = get_data_catalog_service()
    if metadata_in.data_source_id != data_source_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Path ID '{data_source_id}' does not match payload ID '{metadata_in.data_source_id}'."
        )
    try:
        success = service.register_metadata(metadata_in) # Pass the validated model
        if not success:
            # Should ideally be caught by specific exceptions below, but as fallback
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register metadata for {data_source_id}.")
        # Fetch the potentially updated record to return it
        result = service.get_metadata(data_source_id)
        if result is None:
             # This is unlikely if upsert succeeded but possible in edge cases
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve metadata {data_source_id} after registration.")
        return result
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except StorageFailure as sf:
        logger.error(f"Storage failure registering metadata {data_source_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error registering metadata {data_source_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@metadata_router.get("/{data_source_id}", 
                     response_model=DataSourceMetadata, 
                     summary="Get Data Source Metadata by ID") 
async def get_metadata(
    data_source_id: str = Path(..., title="The identifier of the data source to retrieve", min_length=1)
) -> DataSourceMetadata:
    service = get_data_catalog_service()
    try:
        result = service.get_metadata(data_source_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Metadata not found for data source ID: {data_source_id}")
        return result
    except StorageFailure as sf:
        logger.error(f"Storage failure getting metadata {data_source_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error getting metadata {data_source_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@metadata_router.get("/", 
                     response_model=List[str], 
                     summary="List All Data Source IDs") 
async def list_metadata() -> List[str]:
    service = get_data_catalog_service()
    try:
        return service.list_data_sources()
    except StorageFailure as sf:
        logger.error(f"Storage failure listing data sources: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error listing data sources: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

# PUT is less ideal than POST for upsert, changing register_or_update_metadata to handle both is better
# Removing PUT for metadata for now to rely on POST for create/update.

@metadata_router.delete("/{data_source_id}", 
                        status_code=status.HTTP_204_NO_CONTENT, 
                        summary="Delete Data Source Metadata") 
async def delete_metadata(
    data_source_id: str = Path(..., title="The identifier of the data source to delete", min_length=1)
):
    service = get_data_catalog_service()
    try:
        # Optionally check existence first for a 404, but delete is idempotent
        if service.get_metadata(data_source_id) is None:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Metadata not found for data source ID: {data_source_id}")
        
        success = service.delete_metadata(data_source_id)
        if not success:
            # This might happen if the item was deleted between the GET and DELETE, or storage error
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete metadata for {data_source_id}. Check logs.")
        return # Return None for 204
    except NotFound: # Catch if service.get raises NotFound
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Metadata not found for data source ID: {data_source_id}")
    except StorageFailure as sf:
        logger.error(f"Storage failure deleting metadata {data_source_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error deleting metadata {data_source_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

# --- Schema API Endpoints ---

@schema_router.post("/{schema_id}",
                      response_model=SchemaDefinition,
                      status_code=status.HTTP_201_CREATED,
                      summary="Register or Update Schema Definition")
async def register_or_update_schema(
    schema_id: str = Path(..., title="The unique identifier for the schema", min_length=1),
    schema_in: SchemaDefinition = Body(...)
) -> SchemaDefinition:
    service = get_data_catalog_service()
    if schema_in.schema_id != schema_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Path ID '{schema_id}' does not match payload ID '{schema_in.schema_id}'."
        )
    try:
        success = service.register_schema(schema_in)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register schema {schema_id}.")
        result = service.get_schema(schema_id)
        if result is None:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve schema {schema_id} after registration.")
        return result
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except StorageFailure as sf:
        logger.error(f"Storage failure registering schema {schema_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error registering schema {schema_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@schema_router.get("/{schema_id}",
                   response_model=SchemaDefinition,
                   summary="Get Schema Definition by ID")
async def get_schema(
    schema_id: str = Path(..., title="The identifier of the schema to retrieve", min_length=1)
) -> SchemaDefinition:
    service = get_data_catalog_service()
    try:
        result = service.get_schema(schema_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Schema not found for ID: {schema_id}")
        return result
    except StorageFailure as sf:
        logger.error(f"Storage failure getting schema {schema_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error getting schema {schema_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@schema_router.get("/",
                   response_model=List[str],
                   summary="List All Schema IDs") 
async def list_schemas() -> List[str]:
    service = get_data_catalog_service()
    try:
        return service.list_schemas()
    except StorageFailure as sf:
        logger.error(f"Storage failure listing schemas: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error listing schemas: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@schema_router.delete("/{schema_id}",
                      status_code=status.HTTP_204_NO_CONTENT,
                      summary="Delete Schema Definition")
async def delete_schema(
    schema_id: str = Path(..., title="The identifier of the schema to delete", min_length=1)
):
    service = get_data_catalog_service()
    try:
        if service.get_schema(schema_id) is None:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Schema not found for ID: {schema_id}")
        
        success = service.delete_schema(schema_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete schema {schema_id}. Check logs.")
        return
    except NotFound:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Schema not found for ID: {schema_id}")
    except StorageFailure as sf:
        logger.error(f"Storage failure deleting schema {schema_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error deleting schema {schema_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

# --- Memory API Endpoints ---

# Contextual Data
@memory_router.post("/contextual", response_model=ContextualData, status_code=status.HTTP_201_CREATED)
async def create_contextual(data: ContextualData = Body(...)) -> ContextualData:
    """Registers or updates contextual data for a session (identified by session_id in the body)."""
    service = get_data_catalog_service()
    try:
        result = service.register_contextual(data)
        if result is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register contextual data.")
        return result
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except StorageFailure as sf:
        logger.error(f"Storage failure registering contextual data: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error registering contextual data: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.get("/contextual/{session_id}", response_model=ContextualData)
async def get_contextual(session_id: uuid.UUID = Path(..., description="UUID of the session")) -> ContextualData:
    """Retrieves contextual data for a specific session UUID."""
    service = get_data_catalog_service()
    try:
        result = service.get_contextual(str(session_id)) # Service method expects string ID
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Contextual data not found for session ID: {session_id}")
        return result
    except StorageFailure as sf:
        logger.error(f"Storage failure getting contextual data {session_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error getting contextual data {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

# PUT for contextual doesn't make sense if POST is upsert based on session_id in body.

@memory_router.delete("/contextual/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contextual(session_id: uuid.UUID = Path(..., description="UUID of the session to delete")):
    """Deletes contextual data for a specific session UUID."""
    service = get_data_catalog_service()
    try:
        if service.get_contextual(str(session_id)) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Contextual data not found for session ID: {session_id}")
        success = service.delete_contextual(str(session_id))
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete contextual data {session_id}.")
        return
    except NotFound:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Contextual data not found for session ID: {session_id}")
    except StorageFailure as sf:
        logger.error(f"Storage failure deleting contextual data {session_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error deleting contextual data {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

# Knowledge Data
@memory_router.post("/knowledge", response_model=KnowledgeData, status_code=status.HTTP_201_CREATED)
async def create_knowledge(data: KnowledgeData = Body(...)) -> KnowledgeData:
    """Registers a new knowledge data item. A unique knowledge_id will be generated."""
    service = get_data_catalog_service()
    try:
        # ID is generated by default factory in Pydantic model
        result = service.register_knowledge(data)
        if result is None:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register knowledge data.")
        return result # Return the data with the generated ID
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except StorageFailure as sf:
        logger.error(f"Storage failure registering knowledge data: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error registering knowledge data: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.get("/knowledge/{knowledge_id}", response_model=KnowledgeData)
async def get_knowledge(knowledge_id: uuid.UUID = Path(..., description="UUID of the knowledge item")) -> KnowledgeData:
    """Retrieves a specific knowledge data item by its UUID."""
    service = get_data_catalog_service()
    try:
        result = service.get_knowledge(str(knowledge_id))
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge data not found for ID: {knowledge_id}")
        return result
    except StorageFailure as sf:
        logger.error(f"Storage failure getting knowledge data {knowledge_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error getting knowledge data {knowledge_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.put("/knowledge/{knowledge_id}", response_model=KnowledgeData)
async def update_knowledge(knowledge_id: uuid.UUID = Path(..., description="UUID of the knowledge item to update"), 
                           data_update: KnowledgeData = Body(...)) -> KnowledgeData:
    """Updates an existing knowledge data item. knowledge_id in path must match body."""
    service = get_data_catalog_service()
    if data_update.knowledge_id != knowledge_id:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Path ID '{knowledge_id}' does not match payload ID '{data_update.knowledge_id}'.")
    try:
        result = service.update_knowledge(str(knowledge_id), data_update)
        if result is None:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge data not found for ID: {knowledge_id} (or update failed).")
        return result
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except NotFound: # Service might raise NotFound if ID doesn't exist for update
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge data not found for ID: {knowledge_id}")
    except StorageFailure as sf:
        logger.error(f"Storage failure updating knowledge data {knowledge_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error updating knowledge data {knowledge_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.delete("/knowledge/{knowledge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(knowledge_id: uuid.UUID = Path(..., description="UUID of the knowledge item to delete")):
    """Deletes a specific knowledge data item by its UUID."""
    service = get_data_catalog_service()
    try:
        if service.get_knowledge(str(knowledge_id)) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge data not found for ID: {knowledge_id}")
        success = service.delete_knowledge(str(knowledge_id))
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete knowledge data {knowledge_id}.")
        return
    except NotFound:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Knowledge data not found for ID: {knowledge_id}")
    except StorageFailure as sf:
        logger.error(f"Storage failure deleting knowledge data {knowledge_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error deleting knowledge data {knowledge_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

# Operational Data (using operational_id as UUID)
@memory_router.post("/operational", response_model=OperationalData, status_code=status.HTTP_201_CREATED)
async def create_operational(data: OperationalData = Body(...)) -> OperationalData:
    """Registers a new operational data item. A unique operational_id will be generated."""
    service = get_data_catalog_service()
    try:
        result = service.register_operational(data)
        if result is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register operational data.")
        return result
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except StorageFailure as sf:
        logger.error(f"Storage failure registering operational data: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error registering operational data: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.get("/operational/{operational_id}", response_model=OperationalData)
async def get_operational(operational_id: uuid.UUID = Path(..., description="UUID of the operational item")) -> OperationalData:
    """Retrieves a specific operational data item by its UUID."""
    service = get_data_catalog_service()
    try:
        result = service.get_operational(str(operational_id))
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Operational data not found for ID: {operational_id}")
        return result
    except StorageFailure as sf:
        logger.error(f"Storage failure getting operational data {operational_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error getting operational data {operational_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.put("/operational/{operational_id}", response_model=OperationalData)
async def update_operational(operational_id: uuid.UUID = Path(..., description="UUID of the operational item to update"), 
                           data_update: OperationalData = Body(...)) -> OperationalData:
    """Updates an existing operational data item. operational_id in path must match body."""
    service = get_data_catalog_service()
    if data_update.operational_id != operational_id:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Path ID '{operational_id}' does not match payload ID '{data_update.operational_id}'.")
    try:
        result = service.update_operational(str(operational_id), data_update)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Operational data not found for ID: {operational_id} (or update failed).")
        return result
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except NotFound:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Operational data not found for ID: {operational_id}")
    except StorageFailure as sf:
        logger.error(f"Storage failure updating operational data {operational_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error updating operational data {operational_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.delete("/operational/{operational_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_operational(operational_id: uuid.UUID = Path(..., description="UUID of the operational item to delete")):
    """Deletes a specific operational data item by its UUID."""
    service = get_data_catalog_service()
    try:
        if service.get_operational(str(operational_id)) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Operational data not found for ID: {operational_id}")
        success = service.delete_operational(str(operational_id))
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete operational data {operational_id}.")
        return
    except NotFound:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Operational data not found for ID: {operational_id}")
    except StorageFailure as sf:
        logger.error(f"Storage failure deleting operational data {operational_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error deleting operational data {operational_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


# --- Mythic Layer API Endpoints ---

@memory_router.post("/mythic_object", response_model=MythicObject, status_code=status.HTTP_201_CREATED,
                    summary="Create Mythic Object")
async def create_mythic_object(data: MythicObject = Body(...)) -> MythicObject:
    """Registers a new Mythic Object. A unique mythic_object_id will be generated."""
    service = get_data_catalog_service()
    try:
        success = service.register_mythic_object(data)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register Mythic Object.")
        # We might need to fetch the object again if the ID isn't known beforehand or if we want to return the full object with defaults
        # For now, assume the input data (with generated ID) is sufficient if upsert works.
        # If ID generation or other defaults are crucial, fetch after register.
        return data # Assuming data includes the generated mythic_object_id
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except StorageFailure as sf:
        logger.error(f"Storage failure registering Mythic Object: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error registering Mythic Object: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.get("/mythic_object/{mythic_object_id}", response_model=MythicObject,
                   summary="Get Mythic Object by ID")
async def get_mythic_object(mythic_object_id: uuid.UUID = Path(..., description="UUID of the Mythic Object")) -> MythicObject:
    """Retrieves a specific Mythic Object by its UUID."""
    service = get_data_catalog_service()
    try:
        result = service.get_mythic_object(str(mythic_object_id))
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mythic Object not found for ID: {mythic_object_id}")
        return result
    except StorageFailure as sf:
        logger.error(f"Storage failure getting Mythic Object {mythic_object_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error getting Mythic Object {mythic_object_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.put("/mythic_object/{mythic_object_id}", response_model=MythicObject,
                   summary="Update Mythic Object by ID")
async def update_mythic_object(mythic_object_id: uuid.UUID = Path(..., description="UUID of the Mythic Object to update"), 
                           data_update: MythicObject = Body(...)) -> MythicObject:
    """Updates an existing Mythic Object. mythic_object_id in path must match body."""
    service = get_data_catalog_service()
    if data_update.mythic_object_id != mythic_object_id:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Path ID '{mythic_object_id}' does not match payload ID '{data_update.mythic_object_id}'.")
    try:
        result = service.update_mythic_object(str(mythic_object_id), data_update)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mythic Object not found for ID: {mythic_object_id} (or update failed).")
        return result
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except NotFound:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mythic Object not found for ID: {mythic_object_id}")
    except StorageFailure as sf:
        logger.error(f"Storage failure updating Mythic Object {mythic_object_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error updating Mythic Object {mythic_object_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.delete("/mythic_object/{mythic_object_id}", status_code=status.HTTP_204_NO_CONTENT,
                      summary="Delete Mythic Object by ID")
async def delete_mythic_object(mythic_object_id: uuid.UUID = Path(..., description="UUID of the Mythic Object to delete")):
    """Deletes a specific Mythic Object by its UUID."""
    service = get_data_catalog_service()
    try:
        if service.get_mythic_object(str(mythic_object_id)) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mythic Object not found for ID: {mythic_object_id}")
        success = service.delete_mythic_object(str(mythic_object_id))
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete Mythic Object {mythic_object_id}.")
        return
    except NotFound:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mythic Object not found for ID: {mythic_object_id}")
    except StorageFailure as sf:
        logger.error(f"Storage failure deleting Mythic Object {mythic_object_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error deleting Mythic Object {mythic_object_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


# --- MythicLink Endpoints ---

@memory_router.post("/mythic_link", response_model=MythicLink, status_code=status.HTTP_201_CREATED,
                    summary="Create Mythic Link")
async def create_mythic_link(data: MythicLink = Body(...)) -> MythicLink:
    """Registers a new Mythic Link between Mythic Objects. A unique mythic_link_id will be generated."""
    service = get_data_catalog_service()
    try:
        success = service.register_mythic_link(data)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register Mythic Link.")
        # Assuming input data contains the generated ID after successful registration
        return data 
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except StorageFailure as sf:
        logger.error(f"Storage failure registering Mythic Link: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error registering Mythic Link: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.get("/mythic_link/{mythic_link_id}", response_model=MythicLink,
                   summary="Get Mythic Link by ID")
async def get_mythic_link(mythic_link_id: uuid.UUID = Path(..., description="UUID of the Mythic Link")) -> MythicLink:
    """Retrieves a specific Mythic Link by its UUID."""
    service = get_data_catalog_service()
    try:
        result = service.get_mythic_link(str(mythic_link_id))
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mythic Link not found for ID: {mythic_link_id}")
        return result
    except StorageFailure as sf:
        logger.error(f"Storage failure getting Mythic Link {mythic_link_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error getting Mythic Link {mythic_link_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.put("/mythic_link/{mythic_link_id}", response_model=MythicLink,
                   summary="Update Mythic Link by ID")
async def update_mythic_link(mythic_link_id: uuid.UUID = Path(..., description="UUID of the Mythic Link to update"), 
                         data_update: MythicLink = Body(...)) -> MythicLink:
    """Updates an existing Mythic Link. mythic_link_id in path must match body."""
    service = get_data_catalog_service()
    if data_update.mythic_link_id != mythic_link_id:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Path ID '{mythic_link_id}' does not match payload ID '{data_update.mythic_link_id}'.")
    try:
        result = service.update_mythic_link(str(mythic_link_id), data_update)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mythic Link not found for ID: {mythic_link_id} (or update failed).")
        return result
    except ValidationError as ve:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except NotFound:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mythic Link not found for ID: {mythic_link_id}")
    except StorageFailure as sf:
        logger.error(f"Storage failure updating Mythic Link {mythic_link_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error updating Mythic Link {mythic_link_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@memory_router.delete("/mythic_link/{mythic_link_id}", status_code=status.HTTP_204_NO_CONTENT,
                      summary="Delete Mythic Link by ID")
async def delete_mythic_link(mythic_link_id: uuid.UUID = Path(..., description="UUID of the Mythic Link to delete")):
    """Deletes a specific Mythic Link by its UUID."""
    service = get_data_catalog_service()
    try:
        if service.get_mythic_link(str(mythic_link_id)) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mythic Link not found for ID: {mythic_link_id}")
        success = service.delete_mythic_link(str(mythic_link_id))
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete Mythic Link {mythic_link_id}.")
        return
    except NotFound:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Mythic Link not found for ID: {mythic_link_id}")
    except StorageFailure as sf:
        logger.error(f"Storage failure deleting Mythic Link {mythic_link_id}: {sf}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Storage backend error.")
    except Exception as e:
        logger.error(f"Unexpected error deleting Mythic Link {mythic_link_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


# --- Forget Me Endpoint ---
@memory_router.delete("/forget/{identifier_type}/{identifier_value}",
                      status_code=status.HTTP_200_OK, # 200 because we return a report
                      response_model=Dict[str, bool],
                      summary="Delete Memory Records by Identifier (Forget Me)")
async def forget_memory_records(
    identifier_type: Literal["session_id", "source"] = Path(..., description="Type of identifier to use for deletion: 'session_id' or 'source'."),
    identifier_value: str = Path(..., description="The session_id (as UUID string) or source string to delete records for.")
) -> Dict[str, bool]:
    """
    Initiates deletion of memory records (Contextual, Knowledge, Operational, MythicObject, MythicLink)
    based on a specified session_id or source identifier.

    Returns a dictionary indicating submission success for each relevant collection.
    Note: Deletion in the backend might be asynchronous.
    """
    service = get_data_catalog_service()
    try:
        # Basic validation for session_id format if specified
        if identifier_type == "session_id":
            try:
                uuid.UUID(identifier_value) # Check if it's a valid UUID string
            except ValueError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session_id format. Must be a valid UUID string.")
        
        # Call the service method
        deletion_results = service.delete_memory_records_by_identifier(
            identifier_value=identifier_value,
            identifier_type=identifier_type
        )
        
        # Check if any operations failed (indicated by False in the results)
        if not all(deletion_results.values()):
             logger.warning(f"Some delete operations failed or were not submitted for {identifier_type}='{identifier_value}'. Results: {deletion_results}")
             # Still return 200 with the results, but log a warning.
             # Alternatively, could return a different status code like 207 Multi-Status.
        
        return deletion_results

    except (ConnectionFailure, OperationFailure, StorageFailure) as e:
        logger.error(f"Service error during forget operation for {identifier_type}='{identifier_value}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Forget operation failed due to backend service error: {type(e).__name__}")
    except Exception as e:
        logger.error(f"Unexpected error during forget operation for {identifier_type}='{identifier_value}': {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during the forget operation.")


# Include routers in the main app
app.include_router(metadata_router)
app.include_router(schema_router)
app.include_router(memory_router)


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server directly for VANTA Catalog API...")
    uvicorn.run("vanta_seed.api.catalog_api:app", host="0.0.0.0", port=8002, reload=True)
    # Changed port to 8002 to avoid potential conflicts

# End of file, ensuring the invalid tag is gone. 