from fastapi import FastAPI, HTTPException, Body, Path, status
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

from vanta_seed.services.data_catalog_service import DataCatalogService, DataSourceMetadata, SchemaDefinition

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
    logger.info("FastAPI app shutdown.")

app = FastAPI(
    title="VANTA Data Catalog API",
    description="API for managing data source metadata and schemas in the VANTA ecosystem.",
    version="0.1.0",
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
            summary="Register or Update Data Source Metadata",
            tags=["Metadata"]) # Added tags
async def register_metadata_endpoint(
    data_source_id: str = Path(..., title="The unique identifier for the data source", min_length=1),
    metadata: DataSourceMetadata = Body(...)
) -> Dict[str, Any]:
    """
    Registers metadata for a new data source. If a data source with the same ID already exists, 
    its Qdrant point (identified by a generated UUID) will be updated if found via the original ID filter, 
    or a new point might be created if the old one was manually deleted from Qdrant but not the catalog's view.
    The `data_source_id` from the path is used as the human-readable original ID.
    """
    service = get_data_catalog_service()
    success = service.register_metadata(data_source_id, metadata.model_dump(by_alias=True))
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register metadata for {data_source_id}.")
    return {"message": "Metadata registered successfully", "data_source_id": data_source_id, "metadata": metadata.model_dump(by_alias=True)}

@app.get("/metadata/{data_source_id}", 
           response_model=DataSourceMetadata, 
           summary="Get Data Source Metadata by ID",
           tags=["Metadata"]) 
async def get_metadata_endpoint(
    data_source_id: str = Path(..., title="The original identifier of the data source to retrieve")
) -> DataSourceMetadata:
    """Retrieves metadata for a specific data source by its original ID."""
    service = get_data_catalog_service()
    retrieved_metadata_dict = service.get_metadata(data_source_id)
    if retrieved_metadata_dict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Metadata not found for data source ID: {data_source_id}")
    return DataSourceMetadata(**retrieved_metadata_dict) # Return as Pydantic model

@app.get("/metadata/", 
           response_model=List[str], 
           summary="List All Data Source IDs",
           tags=["Metadata"]) 
async def list_metadata_endpoints() -> List[str]:
    """Lists all registered original data source IDs."""
    ensure_qdrant_client()
    # The Pydantic model 'DataSourceMetadata' has already validated the request body.
    # We pass the dictionary representation to the service.
    success = data_catalog_service.register_metadata(data_source_id, metadata.model_dump(by_alias=True))
    if not success:
        # The service layer logs detailed errors. Here we return a generic server error if registration fails.
        # More specific error handling could be added if the service returned error codes/types.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to register metadata.")
    return {"message": "Metadata registered successfully", "data_source_id": data_source_id, "metadata": metadata}


# Placeholder for other endpoints (to be added progressively)

if __name__ == "__main__":
    import uvicorn
    # This is for local development running this file directly.
    # Production deployments would use a proper ASGI server like Uvicorn or Hypercorn managed externally.
    uvicorn.run(app, host="0.0.0.0", port=8002) 