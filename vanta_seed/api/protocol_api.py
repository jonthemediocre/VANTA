"""
VANTA Kernel - Protocol Trigger API

Exposes an endpoint to receive external events and process them through the
VantaTriggerEngine to generate protocol-driven responses.
"""

from fastapi import APIRouter, HTTPException, Body, Depends, Request
from pydantic import BaseModel, Field
import logging
from typing import Any, Dict, Optional
import uuid
from vanta_seed.core.ritual_executor import RitualExecutor
from vanta_seed.core.vanta_master_core import VantaMasterCore
from datetime import datetime

# Placeholder for engine import - ensure PYTHONPATH allows finding it
# Assuming vanta_trigger_engine.py is at the root or accessible
try:
    # Relative import if api is a package relative to engine's location
    # from ..vanta_trigger_engine import VantaTriggerEngine 
    # Or absolute import if project structure allows
    from vanta_trigger_engine import VantaTriggerEngine
except ImportError:
    logging.error("Failed to import VantaTriggerEngine. Ensure it's accessible via PYTHONPATH.")
    # Define a dummy class so the server can start, but endpoint will fail
    class VantaTriggerEngine:
        def process_event(*args, **kwargs):
            logging.error("VantaTriggerEngine dummy class called - import failed.")
            return {"error": "Trigger engine not loaded"}
            
# Configure logging for the API
logging.basicConfig(level=logging.INFO, format='%(asctime)s - API - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# --- Router Setup --- 
# ADDED: Rituals Router
rituals_router = APIRouter(
    prefix="/rituals",
    tags=["Ritual Engine"],
)

# Existing Protocol Router (ensure it remains)
protocol_router = APIRouter(
    prefix="/protocol",
    tags=["Protocol Engine"],
)

# --- Pydantic Models --- 

# --- ADDED: Ritual Models --- 
class RitualInvocationRequest(BaseModel):
    ritual_id: str = Field(..., description="The unique identifier of the ritual to invoke.")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional parameters to pass to the ritual execution context.")
    # Add correlation_id, user_id, etc. as needed for tracing
    correlation_id: Optional[str] = Field(None, description="Optional ID for tracking the request through the system.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ritual_id": "daily_check_in_prompt",
                    "parameters": {"child_id": "child-alex-123"},
                    "correlation_id": "corr-abc-123"
                }
            ]
        }
    }

class RitualInvocationResponse(BaseModel):
    invocation_id: str = Field(..., description="A unique identifier for this specific ritual invocation attempt.")
    ritual_id: str = Field(..., description="The ID of the ritual that was invoked.")
    status: str = Field(..., description="The status of the invocation (e.g., 'PENDING', 'SUCCESS', 'FAILURE', 'UNKNOWN_RITUAL').")
    # Include timestamp, results summary, or error message as needed
    message: Optional[str] = Field(None, description="Optional message providing details about the status.")
    result_summary: Optional[Dict[str, Any]] = Field(None, description="Optional summary of the ritual's execution result.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "invocation_id": "invoke-zyx-987",
                    "ritual_id": "daily_check_in_prompt",
                    "status": "PENDING",
                    "message": "Ritual invocation submitted to executor."
                }
            ]
        }
    }
# --- END ADDED Ritual Models --- 

class TriggerEvent(BaseModel):
    """Schema for incoming trigger events."""
    event_type: str = Field(..., description="The type of event (e.g., 'behavior_log', 'context_change') matching trigger_type in registry.")
    payload: Dict[str, Any] = Field(..., description="The detailed data payload of the event, used for matching trigger criteria.")
    app_context: str = Field(..., description="The application context sending the event (e.g., 'guardian', 'innercircle').")
    child_id: Optional[str] = Field(None, description="Optional identifier for the child related to the event.")
    # Optional field to link this event if it's part of a sequence or requires specific lookup
    event_id: Optional[str] = Field(None, description="Optional unique ID for this specific event instance.") 
    timestamp: Optional[str] = Field(None, description="Optional ISO 8601 timestamp of when the event occurred.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "event_type": "behavior_log",
                    "payload": {
                        "behavior_category": "aggression",
                        "behavior_specific": "throwing_object",
                        "intensity": "high",
                        "details": "Child threw a toy car at the wall."
                    },
                    "app_context": "guardian",
                    "child_id": "child-alex-123",
                    "event_id": "evt-ix9z-pq7r",
                    "timestamp": "2023-10-27T10:30:00Z"
                },
                {
                    "event_type": "child_context_change",
                    "payload": {
                         "context_variable": "supervision_level_dogs",
                         "new_value": "unsupervised",
                         "details": "Child entered area with dogs alone."
                    },
                    "app_context": "innercircle",
                    "child_id": "child-bailey-456",
                    "event_id": "evt-om3a-jy2k",
                    "timestamp": "2023-10-27T11:00:00Z"
                }
            ]
        }
    }

# --- Placeholder Data --- 

# Mock child profile retrieval - Replace with actual data source lookup
MOCK_CHILD_PROFILES = {
    "child-alex-123": {"name": "Alex", "known_triggers": ["transitions"], "preferred_calming_strategies": ["deep breathing", "using a fidget toy"], "tags":[]},
    "child-bailey-456": {"name": "Bailey", "tags": ["dog_safety_risk"], "preferred_calming_strategies":["listening to music"]},
    "child-sam-789": {"name": "Sam"}
}

def get_child_profile(child_id: str) -> dict | None:
    log.info(f"Attempting to retrieve profile for child_id: {child_id} (Mock)")
    return MOCK_CHILD_PROFILES.get(child_id)

# --- Engine Instantiation --- 

# Instantiate the engine here. For more complex apps, use FastAPI's dependency injection or lifespan events.
# Ensure VantaTriggerEngine() can find trigger_registry.py
try:
    trigger_engine_instance = VantaTriggerEngine()
    log.info("VantaTriggerEngine instantiated successfully.")
except Exception as e:
    log.exception("Failed to instantiate VantaTriggerEngine! API endpoints will likely fail.", exc_info=True)
    # Create a dummy instance to prevent FastAPI from crashing on startup if import failed earlier too
    if 'trigger_engine_instance' not in locals():
         trigger_engine_instance = VantaTriggerEngine() # Will use the dummy class if import failed

# --- Dependency Injection Functions --- 

def get_ritual_executor(request: Request) -> RitualExecutor:
    """FastAPI dependency function to get the RitualExecutor instance."""
    if not hasattr(request.app.state, 'ritual_executor') or request.app.state.ritual_executor is None:
        log.error("RitualExecutor not found in app state. Ensure it's added during startup.")
        raise HTTPException(status_code=503, detail="Ritual Executor service not available") # 503 Service Unavailable
    return request.app.state.ritual_executor

def get_master_core(request: Request) -> VantaMasterCore:
    """FastAPI dependency function to get the VantaMasterCore instance."""
    if not hasattr(request.app.state, 'master_core') or request.app.state.master_core is None:
        log.error("VantaMasterCore not found in app state. Ensure it's added during startup.")
        raise HTTPException(status_code=503, detail="Core Orchestrator service not available") # 503 Service Unavailable
    return request.app.state.master_core

# --- END Dependency Injection Functions --- 

# --- API Endpoints --- 

# --- Ritual Invocation Endpoint (Implemented) --- 
@rituals_router.post("/invoke", response_model=RitualInvocationResponse)
async def invoke_ritual_endpoint(
    request_data: RitualInvocationRequest = Body(...),
    ritual_executor: RitualExecutor = Depends(get_ritual_executor), 
    master_core: VantaMasterCore = Depends(get_master_core)
):
    """
    Invokes a specified ritual with given parameters, logs the request,
    and emits an MCP signal to potentially trigger a cascade.
    """
    invocation_id = f"invoke-{uuid.uuid4().hex[:8]}"
    correlation_id = request_data.correlation_id or str(uuid.uuid4()) # Ensure correlation ID exists
    
    log.info(f"Received ritual invocation request (ID: {invocation_id}). Ritual: {request_data.ritual_id}, CorrID: {correlation_id}")

    # Log API request receipt to agentic replay log via master_core helper
    # (Assuming master_core._log_to_agentic_replay is accessible or we use a signal)
    # For now, we rely on the signal processing in master_core to log

    status = "UNKNOWN"
    message = ""
    ritual_result_summary = None

    try:
        # Prepare parameters, adding invocation and correlation IDs for context
        parameters_for_executor = request_data.parameters or {}
        parameters_for_executor['_invocation_id'] = invocation_id
        parameters_for_executor['_correlation_id'] = correlation_id
        parameters_for_executor['_api_source'] = "/rituals/invoke" # Add source info

        # --- Execute the Ritual --- 
        # The execute_ritual method itself is async and currently placeholder
        # We assume it runs the ritual asynchronously. For now, we just await it.
        # A production system might return PENDING immediately and handle completion via webhook/polling.
        # Let's assume execute_ritual returns None on success for now (or raises error)
        await ritual_executor.execute_ritual(
            ritual_name=request_data.ritual_id,
            parameters=parameters_for_executor
        )
        
        # If execute_ritual completes without error, assume it was submitted/successful
        status = "SUCCESS" # Or PENDING depending on executor's actual behavior
        message = f"Ritual '{request_data.ritual_id}' submitted for execution."
        log.info(f"Invocation {invocation_id} for ritual '{request_data.ritual_id}' submitted. Status: {status}")

    except ValueError as ve: # Specific error for ritual not found potentially
        log.warning(f"Ritual '{request_data.ritual_id}' not found or invalid parameters (ID: {invocation_id}): {ve}", exc_info=True)
        status = "UNKNOWN_RITUAL" # Or BAD_REQUEST?
        message = f"Ritual '{request_data.ritual_id}' not found or parameters invalid."
        raise HTTPException(status_code=404, detail=message) # 404 Not Found seems appropriate
    except Exception as e:
        log.exception(f"Error submitting ritual '{request_data.ritual_id}' to executor (ID: {invocation_id}): {e}", exc_info=True)
        status = "FAILURE"
        message = f"Internal server error during ritual submission: {str(e)}"
        # Don't re-raise here, return failure response below
        # Consider raising HTTPException(status_code=500, detail=message) depending on desired API behavior

    # --- Emit MCP Signal (If submission was successful/pending) --- 
    if status in ["SUCCESS", "PENDING"]:
        try:
            mcp_payload = {
                "ritual_id": request_data.ritual_id,
                "parameters_submitted": request_data.parameters, # Log what was sent
                "api_invocation_id": invocation_id,
                "status_at_signal": status # Log status when signal was sent
            }
            signal_data = {
                "signal_id": str(uuid.uuid4()), # Unique ID for the signal itself
                "timestamp_iso": datetime.utcnow().isoformat() + "Z",
                "source_agent_id": "API:/rituals/invoke", # Identify the source
                "signal_type": "INITIATE_CASCADE",
                "target_entity": {
                    "type": "CASCADE_PROFILE_ID",
                    "id": "ritual_invocation_submitted_cascade" # Use a relevant cascade profile ID
                },
                "payload": mcp_payload,
                "metadata": {
                    "correlation_id": correlation_id
                }
            }
            
            # Send the signal to the orchestrator
            log.info(f"Sending MCP Signal for cascade '{signal_data['target_entity']['id']}'. Invocation: {invocation_id}, CorrID: {correlation_id}")
            signal_response = await master_core.receive_signal(signal_data)
            log.info(f"MCP Signal submission response: {signal_response}")
            
            # Log signal emission via master_core helper
            # await master_core._log_to_agentic_replay(...) # Rely on master_core logging internally

        except Exception as signal_error:
            log.exception(f"Failed to send MCP Signal for invocation {invocation_id} (Ritual: {request_data.ritual_id}): {signal_error}", exc_info=True)
            # Don't change the primary status, but log the error clearly
            # Potentially add a note to the response message? 
            message += " (Warning: Failed to trigger post-invocation cascade)"

    # --- Prepare and Return Response --- 
    response_payload = RitualInvocationResponse(
        invocation_id=invocation_id,
        ritual_id=request_data.ritual_id,
        status=status,
        message=message,
        result_summary=ritual_result_summary # Populate if execute_ritual returns data
    )

    # Raise HTTP error if status indicates failure occurred during execution phase
    if status == "FAILURE":
         raise HTTPException(status_code=500, detail=message)
         
    return response_payload

# Existing Protocol Trigger Endpoint
@protocol_router.post("/trigger", response_model=Optional[Dict[str, Any]])
async def process_trigger_event(event_data: TriggerEvent = Body(...)):
    """
    Receives an event, processes it through the VantaTriggerEngine,
    and returns the resulting protocol response (e.g., a visual prompt).
    """
    log.info(f"Received trigger event request. Type: {event_data.event_type}, Context: {event_data.app_context}, ChildID: {event_data.child_id}")
    
    child_profile = None
    if event_data.child_id:
        child_profile = get_child_profile(event_data.child_id)
        if not child_profile:
            log.warning(f"Child profile not found for ID: {event_data.child_id}. Proceeding without profile.")
            # Decide if this should be an error or just proceed without profile
            # For now, proceed without profile data
            child_profile = {} # Pass empty dict
        else:
             log.info(f"Retrieved profile for child: {child_profile.get('name')}")
             
    # Construct the event dictionary expected by the engine (type + payload)
    # Modify this if VantaTriggerEngine expects a different structure
    engine_event = {
        "type": event_data.event_type,
        # Pass the full payload dictionary directly
        **event_data.payload 
        # Add other top-level event details if needed by engine/match criteria
        # "event_id": event_data.event_id, 
        # "timestamp": event_data.timestamp
    }

    log.debug(f"Processing event with engine. Event: {engine_event}, Context: {event_data.app_context}, Profile: {child_profile}")
    
    try:
        response = trigger_engine_instance.process_event(
            event=engine_event,
            current_app_context=event_data.app_context,
            child_profile=child_profile
        )
        
        if response is None:
            log.info("Trigger engine returned no matching response for the event.")
            # Return HTTP 204 No Content or a specific message?
            # Returning None results in a 200 OK with `null` body based on response_model=Optional[...]
            return None 
        elif response.get("error"):
             log.error(f"Trigger engine reported an error: {response['error']}")
             # Decide on appropriate HTTP error
             if "not found" in response["error"].lower():
                 raise HTTPException(status_code=404, detail=response["error"]) # e.g., Module not found
             else:
                 raise HTTPException(status_code=500, detail=response["error"]) # General internal error
        else:
            log.info(f"Trigger engine returned a successful response. Protocol: {response.get('protocol_applied')}")
            # TODO: Add detailed ritual tracing here
            # Log: event_id, trigger_id, protocol_applied, response_summary
            return response
            
    except Exception as e:
        log.exception(f"Unhandled exception during trigger processing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error during trigger processing: {str(e)}")

# --- Basic Test Block (Optional - for running this file directly if needed) ---
# Usually, testing is done via FastAPI test client or tools like curl/Postman
# if __name__ == "__main__":
#     import uvicorn
#     # This would require creating a full FastAPI app instance here
#     # from fastapi import FastAPI
#     # app = FastAPI()
#     # app.include_router(router)
#     # uvicorn.run(app, host="0.0.0.0", port=8003) # Use a different port
#     print("To test this API, run the main FastAPI application (e.g., using run.py) and send POST requests to /protocol/trigger") 