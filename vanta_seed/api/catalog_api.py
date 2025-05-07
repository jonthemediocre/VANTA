from fastapi import FastAPI, HTTPException, Body, Path, status, APIRouter
from typing import Dict, Any, List, Optional
import sys
import os
import logging
from contextlib import asynccontextmanager # For lifespan manager

# Add the parent directory of 'vanta_seed' to the Python path
# This is to ensure that 'vanta_seed.services' can be imported
# Adjust the number of 'os.path.dirname' calls if catalog_api.py is nested deeper
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VANTA_SEED_DIR = os.path.dirname(SCRIPT_DIR) # Goes up one level from 'api' to 'vanta_seed'
PROJECT_ROOT = os.path.dirname(VANTA_SEED_DIR) # Goes up one level from 'vanta_seed' to project root
sys.path.append(PROJECT_ROOT)

from vanta_seed.services.data_catalog_service import (
    DataCatalogService, 
    DataSourceMetadata, 
    SchemaDefinition,
    SCHEMA_COLLECTION,      # Added import
    ORIGINAL_ID_FIELD       # Added import
)
# Import MemoryAgent schemas
from vanta_seed.schemas.memory_agent_schemas import ContextualData, KnowledgeData, OperationalData

# Configure a logger for this API module
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Global instance of the service
data_catalog_service: Optional[DataCatalogService] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    global data_catalog_service
    logger.info("FastAPI app startup: Initializing DataCatalogService...")
    data_catalog_service = DataCatalogService()
    if not data_catalog_service.client:
        logger.error("CRITICAL: DataCatalogService FAILED to connect to Qdrant during startup. API endpoints will likely fail.")
    else:
        logger.info("DataCatalogService initialized and Qdrant client is available.")
    yield
    # Code to run on shutdown (if any)
    logger.info("FastAPI app shutdown: Cleaning up resources (if any)...")
    if data_catalog_service and hasattr(data_catalog_service, 'close_qdrant_client'):
        data_catalog_service.close_qdrant_client() # Assuming a close method
    data_catalog_service = None

app = FastAPI(
    title="VANTA Data Catalog & Memory API",
    description="API for managing data source metadata, schemas, and agent memory components.",
    version="0.2.0",
    lifespan=lifespan # Use the new lifespan manager
)

# Helper for Qdrant client check and service availability
def get_data_catalog_service() -> DataCatalogService:
    if data_catalog_service is None or not data_catalog_service.client:
        # This check is mostly a safeguard; lifespan should handle initialization.
        logger.error("DataCatalogService not available or Qdrant client not initialized.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data Catalog Service or Qdrant backend not available. Check service logs."
        )
    return data_catalog_service

# --- Metadata API Endpoints ---

@app.post("/metadata/{data_source_id}",
            response_model=Dict[str, Any], 
            status_code=status.HTTP_201_CREATED,
            summary="Register Data Source Metadata", # Simplified summary
            tags=["Metadata"])
async def register_metadata_endpoint(
    data_source_id: str = Path(..., title="The unique identifier for the data source", min_length=1),
    metadata: DataSourceMetadata = Body(...)
) -> Dict[str, Any]:
    """
    Registers metadata for a new data source.
    The `data_source_id` from the path is used as the human-readable original ID.
    If metadata for this ID already exists, it will be effectively overwritten by Qdrant's upsert.
    """
    service = get_data_catalog_service()
    success = service.register_metadata(data_source_id, metadata.model_dump(by_alias=True))
    if not success:
        # Service layer logs details, check those for specific Qdrant errors if this happens.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register metadata for {data_source_id}.")
    return {"message": "Metadata registered successfully", "data_source_id": data_source_id, "metadata": metadata.model_dump(by_alias=True)}

@app.get("/metadata/{data_source_id}", 
           response_model=DataSourceMetadata, 
           summary="Get Data Source Metadata by ID",
           tags=["Metadata"]) 
async def get_metadata_endpoint(
    data_source_id: str = Path(..., title="The original identifier of the data source to retrieve", min_length=1)
) -> DataSourceMetadata:
    """Retrieves metadata for a specific data source by its original ID."""
    service = get_data_catalog_service()
    retrieved_metadata_dict = service.get_metadata(data_source_id)
    if retrieved_metadata_dict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Metadata not found for data source ID: {data_source_id}")
    return DataSourceMetadata(**retrieved_metadata_dict)

@app.get("/metadata/", 
           response_model=List[str], 
           summary="List All Data Source IDs",
           tags=["Metadata"]) 
async def list_metadata_endpoints() -> List[str]:
    """Lists all registered original data source IDs."""
    service = get_data_catalog_service()
    return service.list_data_sources()

@app.put("/metadata/{data_source_id}", 
           response_model=DataSourceMetadata, 
           summary="Update Data Source Metadata",
           tags=["Metadata"]) 
async def update_metadata_endpoint(
    data_source_id: str = Path(..., title="The original identifier of the data source to update", min_length=1),
    updates: Dict[str, Any] = Body(..., example={"owner": "new_team", "tags": ["production", "critical"]}) # Added example
) -> DataSourceMetadata:
    """
    Updates existing metadata for a data source.
    Only fields provided in the request body will be updated.
    If the data source ID does not exist, a 404 error is returned.
    """
    service = get_data_catalog_service()
    
    # Check if metadata exists before attempting update for a clearer 404
    existing_metadata = service.get_metadata(data_source_id)
    if existing_metadata is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Metadata not found for data source ID: {data_source_id}, cannot update.")

    success = service.update_metadata(data_source_id, updates)
    if not success:
        # This would indicate an issue during the Qdrant update operation itself.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update metadata for {data_source_id}.")
    
    updated_metadata_dict = service.get_metadata(data_source_id)
    if updated_metadata_dict is None: # Should ideally not happen if update was successful and ID existed
        logger.error(f"Failed to retrieve metadata for {data_source_id} immediately after a successful update call. This is unexpected.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to retrieve metadata for {data_source_id} after update confirmation.")
    return DataSourceMetadata(**updated_metadata_dict)

@app.delete("/metadata/{data_source_id}", 
              status_code=status.HTTP_204_NO_CONTENT, 
              summary="Delete Data Source Metadata",
              tags=["Metadata"]) 
async def delete_metadata_endpoint(
    data_source_id: str = Path(..., title="The original identifier of the data source to delete", min_length=1)
):
    """
    Deletes metadata for a specific data source by its original ID.
    Returns 204 No Content if successful.
    If the ID does not exist, the operation might still return success from the service layer 
    (as Qdrant delete is idempotent), but we can add a check here for a more explicit 404.
    """
    service = get_data_catalog_service()
    
    # Optional: Check if metadata exists to return a more specific 404
    # if service.get_metadata(data_source_id) is None:
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Metadata not found for data source ID: {data_source_id}, cannot delete.")

    success = service.delete_metadata(data_source_id)
    if not success:
        # This could indicate an issue during the Qdrant delete operation.
        # The service logs more details.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete metadata for {data_source_id}. It might not have existed or an error occurred.")
    return # FastAPI returns 204 No Content by default for None response with this status code

# --- Schema API Endpoints ---

@app.post("/schemas/{schema_id}",
            response_model=Dict[str, Any],
            status_code=status.HTTP_201_CREATED,
            summary="Register Schema Definition",
            tags=["Schemas"])
async def register_schema_endpoint(
    schema_id: str = Path(..., title="The unique identifier for the schema", min_length=1),
    schema_definition: SchemaDefinition = Body(...)
) -> Dict[str, Any]:
    """
    Registers a new schema definition.
    The `schema_id` from the path is used as the human-readable original ID.
    If a schema for this ID already exists, it will be effectively overwritten.
    """
    service = get_data_catalog_service()
    success = service.register_schema(schema_id, schema_definition.model_dump(by_alias=True))
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register schema {schema_id}.")
    return {"message": "Schema registered successfully", "schema_id": schema_id, "schema_definition": schema_definition.model_dump(by_alias=True)}

@app.get("/schemas/{schema_id}",
           response_model=SchemaDefinition,
           summary="Get Schema Definition by ID",
           tags=["Schemas"])
async def get_schema_endpoint(
    schema_id: str = Path(..., title="The original identifier of the schema to retrieve", min_length=1)
) -> SchemaDefinition:
    """Retrieves a specific schema definition by its original ID."""
    service = get_data_catalog_service()
    retrieved_schema_dict = service.get_schema(schema_id)
    if retrieved_schema_dict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Schema not found for ID: {schema_id}")
    return SchemaDefinition(**retrieved_schema_dict)

@app.get("/schemas/",
           response_model=List[str],
           summary="List All Schema IDs",
           tags=["Schemas"])
async def list_schemas_endpoint() -> List[str]:
    """Lists all registered original schema IDs."""
    service = get_data_catalog_service()
    # Assuming the service layer has a list_schemas() method similar to list_data_sources()
    # If not, this method would need to be added to DataCatalogService first.
    # For now, let's assume it exists or we'll add it if there's an AttributeError.
    # Let's check DataCatalogService for a list_schemas() method or similar.
    # Based on DataCatalogService, it does not have list_schemas yet.
    # We need to add list_schemas to DataCatalogService.py first.
    # For now, this API endpoint will be a placeholder or we can implement list_data_sources equivalent.
    # To keep moving with API layer, let's use a placeholder/comment it out and add list_schemas in service later.
    # Actually, let's add a simple list_schemas to the service now for completeness of this step.
    # This will require an edit to data_catalog_service.py as well.
    
    # For now, we will assume list_schemas will be similar to list_data_sources and call it.
    # If DataCatalogService.list_schemas() is not implemented, this will fail at runtime.
    # We will add it in the next step to the service if not present.
    schema_ids = []
    # Temporarily, if service doesn't have list_schemas, return empty or raise not implemented
    if hasattr(service, 'list_schemas'):
        schema_ids = service.list_schemas() # Placeholder if you add it to service
    elif hasattr(service, 'list_schema_ids'): # Alternative naming
        schema_ids = service.list_schema_ids()
    else:
        # For now, to make API testable, let's query all schemas and extract original_ids like in list_data_sources
        # This is a simplified version that should exist in the service layer.
        # Replicating the logic from list_data_sources for schemas:
        if service.client:
            try:
                next_offset = None
                while True:
                    points, next_offset = service.client.scroll(
                        collection_name=SCHEMA_COLLECTION, # Uses the constant from data_catalog_service
                        limit=100,
                        offset=next_offset,
                        with_payload=True,
                        with_vectors=False
                    )
                    for point in points:
                        if point.payload and ORIGINAL_ID_FIELD in point.payload:
                            schema_ids.append(str(point.payload[ORIGINAL_ID_FIELD]))
                    if not next_offset:
                        break
                return list(set(schema_ids))
            except Exception as e:
                logger.error(f"API error listing schemas: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to list schemas.")
        else:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Qdrant client not available.")
    return list(set(schema_ids)) # Ensure uniqueness

@app.delete("/schemas/{schema_id}",
              status_code=status.HTTP_204_NO_CONTENT,
              summary="Delete Schema Definition",
              tags=["Schemas"])
async def delete_schema_endpoint(
    schema_id: str = Path(..., title="The original identifier of the schema to delete", min_length=1)
):
    """Deletes a schema definition by its original ID."""
    service = get_data_catalog_service()
    success = service.delete_schema(schema_id)
    if not success:
        # Could check service.get_schema(schema_id) to return 404 if not found before delete attempt
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete schema {schema_id}, or it was not found.")
    return

# --- MemoryAgent API Endpoints (New) ---
memory_router = APIRouter(prefix="/memory", tags=["MemoryAgent - Agent Lifecycle Data"])

# -------- ContextualData Routes --------
@memory_router.post("/contextual", response_model=ContextualData, status_code=status.HTTP_201_CREATED)
async def create_contextual(data: ContextualData) -> ContextualData:
    service = get_data_catalog_service()
    # Assuming register_contextual will return the full object or its ID for confirmation
    # For now, let's make it return the object if successful, matching response_model
    # The service method will need to be adapted for this if it currently returns only ID
    registered_data = service.register_contextual(data) # Placeholder for actual return value
    if not registered_data: # Or check specific error from service
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register contextual data.")
    return registered_data # Return the created/retrieved data

@memory_router.get("/contextual/{session_id}", response_model=ContextualData)
async def get_contextual(session_id: str = Path(..., min_length=1)) -> ContextualData:
    service = get_data_catalog_service()
    data = service.get_contextual(session_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ContextualData not found for session_id: {session_id}")
    return data

@memory_router.put("/contextual/{session_id}", response_model=ContextualData)
async def update_contextual(session_id: str = Path(..., min_length=1), data_update: ContextualData = Body(...)) -> ContextualData:
    service = get_data_catalog_service()
    updated_data = service.update_contextual(session_id, data_update)
    if not updated_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ContextualData not found for session_id: {session_id} or update failed.")
    return updated_data

@memory_router.delete("/contextual/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contextual(session_id: str = Path(..., min_length=1)):
    service = get_data_catalog_service()
    success = service.delete_contextual(session_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"ContextualData not found for session_id: {session_id} or delete failed.")
    return

# -------- KnowledgeData Routes --------
@memory_router.post("/knowledge", response_model=KnowledgeData, status_code=status.HTTP_201_CREATED)
async def create_knowledge(data: KnowledgeData) -> KnowledgeData:
    service = get_data_catalog_service()
    registered_data = service.register_knowledge(data)
    if not registered_data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register knowledge data.")
    return registered_data

@memory_router.get("/knowledge/{knowledge_id}", response_model=KnowledgeData)
async def get_knowledge(knowledge_id: str = Path(..., min_length=1)) -> KnowledgeData:
    service = get_data_catalog_service()
    data = service.get_knowledge(knowledge_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"KnowledgeData not found for knowledge_id: {knowledge_id}")
    return data

@memory_router.put("/knowledge/{knowledge_id}", response_model=KnowledgeData)
async def update_knowledge(knowledge_id: str = Path(..., min_length=1), data_update: KnowledgeData = Body(...)) -> KnowledgeData:
    service = get_data_catalog_service()
    updated_data = service.update_knowledge(knowledge_id, data_update)
    if not updated_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"KnowledgeData not found for knowledge_id: {knowledge_id} or update failed.")
    return updated_data

@memory_router.delete("/knowledge/{knowledge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(knowledge_id: str = Path(..., min_length=1)):
    service = get_data_catalog_service()
    success = service.delete_knowledge(knowledge_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"KnowledgeData not found for knowledge_id: {knowledge_id} or delete failed.")
    return

# -------- OperationalData Routes --------
@memory_router.post("/operational", response_model=OperationalData, status_code=status.HTTP_201_CREATED)
async def create_operational(data: OperationalData) -> OperationalData:
    service = get_data_catalog_service()
    registered_data = service.register_operational(data)
    if not registered_data:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register operational data.")
    return registered_data

@memory_router.get("/operational/{operation_id}", response_model=OperationalData)
async def get_operational(operation_id: str = Path(..., min_length=1)) -> OperationalData:
    service = get_data_catalog_service()
    data = service.get_operational(operation_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OperationalData not found for operation_id: {operation_id}")
    return data

@memory_router.put("/operational/{operation_id}", response_model=OperationalData)
async def update_operational(operation_id: str = Path(..., min_length=1), data_update: OperationalData = Body(...)) -> OperationalData:
    service = get_data_catalog_service()
    updated_data = service.update_operational(operation_id, data_update)
    if not updated_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OperationalData not found for operation_id: {operation_id} or update failed.")
    return updated_data

@memory_router.delete("/operational/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_operational(operation_id: str = Path(..., min_length=1)):
    service = get_data_catalog_service()
    success = service.delete_operational(operation_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OperationalData not found for operation_id: {operation_id} or delete failed.")
    return

app.include_router(memory_router) # Include the new router

if __name__ == "__main__":
    import uvicorn
    # This is for local development running this file directly.
    # Production deployments would use a proper ASGI server like Uvicorn or Hypercorn managed externally.
    uvicorn.run(app, host="0.0.0.0", port=8002) 