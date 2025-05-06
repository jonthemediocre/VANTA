import uvicorn
from fastapi import FastAPI
import logging
from typing import Dict, Any

# VANTA Imports
from vanta_seed.agents.agent_registry import register_agent, get_agent, clear_registry # Import registry functions
from vanta_seed.agents.data_unifier_agent import DataUnifierAgent
from vanta_seed.agents.data_unifier_router import router as data_unifier_router
from vanta_seed.core.models import AgentConfig # Assuming AgentConfig is needed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VANTA Agent API Server",
    version="0.1.0",
    description="Provides API access to VANTA agents."
)

@app.on_event("startup")
async def startup_event():
    """Event handler for application startup."""
    logger.info("API Server starting up... Registering agents.")
    # Instantiate and register agents here
    # TODO: Load agent configurations dynamically (e.g., from agents.index.mpc.json)
    try:
        # --- Instantiate DataUnifierAgent --- 
        # Placeholder config - replace with actual loading mechanism
        placeholder_config_dict = {
            "name": "data_unifier",
            "class_path": "vanta_seed.agents.data_unifier_agent.DataUnifierAgent",
            "symbolic_identity": {"archetype": "unifier", "mythos_role": "scribe"},
            "deduplication_threshold": 0.9,
            "merge_strategy": "recency"
        }
        data_unifier_config = AgentConfig(**placeholder_config_dict)
        data_unifier_agent_instance = DataUnifierAgent(
            name="data_unifier_instance_01", 
            config=data_unifier_config, 
            logger=logging.getLogger("DataUnifierAgent"),
            orchestrator_ref=None # TODO: Pass orchestrator if needed
        )
        await data_unifier_agent_instance.startup() # Run agent-specific startup
        register_agent("data_unifier", data_unifier_agent_instance)
        # ----------------------------------
        
        # --- Register other agents as needed --- 
        # ...

        logger.info("Agent registration complete.")
    except Exception as e:
        logger.error(f"Error during agent registration: {e}", exc_info=True)
        # Decide if the app should fail to start if registration fails
        raise RuntimeError(f"Failed to initialize agents: {e}") from e

@app.on_event("shutdown")
async def shutdown_event():
    """Event handler for application shutdown."""
    logger.info("API Server shutting down... Performing agent cleanup.")
    # TODO: Implement graceful shutdown for registered agents if needed
    # Example:
    # data_unifier = get_agent("data_unifier")
    # if data_unifier:
    #     await data_unifier.shutdown()
    clear_registry()
    logger.info("Agent cleanup complete.")


# Mount agent routers
app.include_router(
    data_unifier_router, # Pass the router object directly
    prefix="/v1/agents/data-unifier", 
    tags=["DataUnifierAgent"]
)
# Mount other agent routers here...

@app.get("/health", tags=["System"])
async def health_check() -> Dict[str, str]:
    """Basic health check endpoint."""
    # logger.info("Health check requested.") # Reduce noise for health checks
    return {"status": "healthy"}

if __name__ == "__main__":
    logger.info("Starting VANTA Agent API Server...")
    # TODO: Load host/port from config
    uvicorn.run(app, host="127.0.0.1", port=8000) 