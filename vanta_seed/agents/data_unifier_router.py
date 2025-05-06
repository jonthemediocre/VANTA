from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
import logging

from .data_unifier_models import RawRecordInput, UnifiedEntityOutput
# Import the registry and the specific agent type hint
from .agent_registry import get_agent
from .data_unifier_agent import DataUnifierAgent

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Dependency Function using AgentRegistry --- 
def get_data_unifier_dependency() -> DataUnifierAgent:
    """FastAPI dependency function to get the DataUnifierAgent instance from the registry."""
    agent = get_agent("data_unifier") # Use the registered name
    if agent is None:
        # This should ideally not happen if registration is done correctly on startup
        logger.error("DataUnifierAgent not found in registry during request.")
        raise HTTPException(status_code=503, detail="Data Unifier service is unavailable.")
    if not isinstance(agent, DataUnifierAgent):
         logger.error(f"Agent 'data_unifier' in registry is not of type DataUnifierAgent (Type: {type(agent).__name__})")
         raise HTTPException(status_code=500, detail="Internal server configuration error.")
    return agent
# -------------------------------------------

@router.post("/ingest", status_code=202)
async def ingest_record(
    record_input: RawRecordInput,
    agent: DataUnifierAgent = Depends(get_data_unifier_dependency) # Use the registry dependency
) -> Dict[str, Any]:
    """Endpoint to ingest a raw data record for unification."""
    logger.info(f"Received ingest request for source: {record_input.source}")
    try:
        # Prepare task data for the agent's execute method (if using base execute)
        # task_data = {
        #     "intent": "ingest_raw_record",
        #     "payload": record_input.dict()
        # }
        # result = await agent.execute(task_data)
        
        # Or call specific method directly (simpler for direct API mapping)
        result = await agent.ingest_raw_record(record_input.dict())

        if result.get("status") == "accepted":
            return {"message": "Record accepted for processing.", "entity_id": result.get("merged_entity_id")}
        else:
            raise HTTPException(status_code=400, detail=result.get("message", "Processing failed"))

    except ValueError as ve:
        logger.warning(f"Validation error during ingest: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as http_exc:
        raise http_exc # Re-raise FastAPI exceptions
    except Exception as e:
        logger.error(f"Error processing ingest request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during ingestion.")

@router.get("/entity/{entity_id}", response_model=Optional[UnifiedEntityOutput])
async def get_entity(
    entity_id: str,
    agent: DataUnifierAgent = Depends(get_data_unifier_dependency) # Use the registry dependency
) -> Optional[UnifiedEntityOutput]:
    """Endpoint to retrieve a unified entity by its ID."""
    logger.info(f"Received request for entity: {entity_id}")
    try:
        # Prepare task data (if using base execute)
        # task_data = {
        #     "intent": "get_unified_entity",
        #     "payload": {"entity_id": entity_id}
        # }
        # entity_data = await agent.execute(task_data)

        # Call specific method directly
        entity_data = await agent.expose_unified_entity(entity_id)

        if entity_data:
            # Ensure the data matches the response model structure
            # If expose_unified_entity returns the exact structure, this is fine.
            # If not, you might need transformation here before validation.
            return UnifiedEntityOutput(**entity_data)
        else:
            raise HTTPException(status_code=404, detail=f"Entity '{entity_id}' not found.")

    except ValueError as ve:
         logger.warning(f"Input error during entity retrieval: {ve}")
         raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException as http_exc:
        raise http_exc # Re-raise FastAPI exceptions
    except Exception as e:
        logger.error(f"Error retrieving entity {entity_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error retrieving entity {entity_id}.") 