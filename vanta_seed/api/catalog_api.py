from fastapi import FastAPI, HTTPException, Body, Path, status
from typing import Dict, Any, List, Optional
import sys
import os
import logging

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

app = FastAPI(
    title="VANTA Data Catalog API",
    description="API for managing data source metadata and schemas in the VANTA ecosystem.",
    version="0.1.0"
)

# Initialize the DataCatalogService instance
# This instance will be shared across all API requests to this worker/process.
# For Qdrant, the client inside the service handles connections.
data_catalog_service = DataCatalogService()

@app.on_event("startup")
async def startup_event():
    # This event is a good place to check critical dependencies like the Qdrant client.
    if not data_catalog_service.client:
        logger.error("CRITICAL: DataCatalogService did NOT connect to Qdrant. API endpoints will likely fail.")
        # Depending on desired behavior, you could raise an exception here to stop the app from starting,
        # or allow it to start and have individual requests fail with 503.
        # For now, we log an error, and individual requests will fail via ensure_qdrant_client().
    else:
        logger.info("DataCatalogService reports Qdrant client is available on startup.")

# Helper for Qdrant client check
def ensure_qdrant_client():
    if not data_catalog_service.client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Qdrant service not available. Check service logs."
        )

# --- Metadata API Endpoints ---

@app.post("/metadata/{data_source_id}", status_code=status.HTTP_201_CREATED)
async def register_metadata_endpoint(
    data_source_id: str = Path(..., title="The unique identifier for the data source"),
    metadata: DataSourceMetadata = Body(...)
) -> Dict[str, Any]:
    """
    Registers metadata for a new data source or updates existing metadata.
    The `data_source_id` in the path will be used as the original ID.
    """
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