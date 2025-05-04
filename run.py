# run.py - Main entry point for the VANTA Framework

import os
# --- Remove direct env var/config loading ---
# import yaml 
# import uvicorn 
# from pathlib import Path
# from dotenv import load_dotenv
# import json
# -----------------------------------------
import asyncio
import uuid
import yaml # Keep yaml for blueprint loading
from pathlib import Path # Keep Path
import json # <-- Add json import back
import logging # Added for detailed logging
from typing import Dict, Any, Optional
import sys

# --- Add dotenv import --- 
from dotenv import load_dotenv 
# -----------------------

# --- FastAPI Imports ---
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware # <<< ADD THIS IMPORT
from pydantic import BaseModel, Field # For request body validation
import uvicorn # To run the server
# --- Security Imports ---
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# -----------------------

# --- Import centralized config FIRST --- 
import config # This will load .env, set up logging, define paths, and ALLOWED_API_KEYS
# ---------------------------------------

# --- Import the correct Vanta Master Core ---
from vanta_seed.core.vanta_master_core import VantaMasterCore 
# --- Comment out OLD/Incorrect orchestrator imports ---
# from vanta_seed.core.seed_orchestrator import AgentOrchestrator 
# from orchestrator import AgentOrchestrator 
# ----------------------------------------
# --- Import PluginManager (Assuming location) ---
from vanta_seed.utils.plugin_manager import PluginManager # Try utils
# -------------------------------------------

# --- Configuration Loading (Now handled by config.py) ---

# # --- Set Environment Variables Early --- 
# BASE_DIR = Path(__file__).parent # Defined in config.py
# os.environ["VANTA_LOG_DIR"] = str(BASE_DIR / "logs") # Set in config.py
# print(f"VANTA_LOG_DIR set to: {os.environ['VANTA_LOG_DIR']}") # Printed in config.py
# # -------------------------------------
# 
# # Load environment variables from .env file (can override VANTA_LOG_DIR if present in .env)
# load_dotenv() # Done in config.py

# --- Use paths from config module --- 
# BASE_DIR = Path(__file__).parent
# BLUEPRINT_PATH = BASE_DIR / "blueprint.yaml"
# AGENT_INDEX_PATH = BASE_DIR / "agents.index.mpc.json" 
# -----------------------------------

# Configuration Loading
# --- REMOVE incorrect path construction ---
# CONFIG_DIR = Path(__file__).parent / "config"
# BLUEPRINT_FILE = CONFIG_DIR / "BLUEPRINT.yaml"
# AGENT_INDEX_FILE = CONFIG_DIR / "agents.index.mpc.json"
# --- Use paths from config module --- 
BLUEPRINT_PATH = config.BLUEPRINT_PATH # Use the path defined in config.py
AGENT_INDEX_PATH = config.AGENT_INDEX_PATH # Use the path defined in config.py
# -----------------------------------

# Setup Logging
# Explicitly set agent logger level to DEBUG
# Do this BEFORE loading the main logging config to ensure it takes precedence if needed
logging.getLogger('vanta_seed.agents.proxy_deepseek_agent').setLevel(logging.DEBUG)
# You could add other specific agent loggers here if needed:
# logging.getLogger('vanta_seed.agents.memory_agent').setLevel(logging.DEBUG)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.StreamHandler() # Add file handler later if needed
    ]
)
logger = logging.getLogger(__name__)

def load_yaml_config(file_path: Path) -> dict | None:
    """Loads a YAML configuration file."""
    if not file_path.exists():
        logger.error(f"Configuration file not found: {file_path}")
        return None
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading YAML file {file_path}: {e}", exc_info=True)
        return None

def load_json_config(file_path: Path) -> dict | None:
    """Loads a JSON configuration file."""
    if not file_path.exists():
        logger.error(f"Configuration file not found: {file_path}")
        return None
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading JSON file {file_path}: {e}", exc_info=True)
        return None

# --- FastAPI App Instance ---
# Use context manager for lifespan with FastAPI 0.100+
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan_manager(app: FastAPI):
    # Code to run on startup
    global orchestrator_instance, plugin_manager_instance
    logger.info("Application startup...")
    
    # --- Initialize and Load Plugins FIRST --- 
    plugin_dir = config.BASE_DIR / "vanta_seed" / "agents"
    plugin_manager_instance = PluginManager(plugin_directory=str(plugin_dir))
    plugin_manager_instance.load_plugins() # <<< CALL load_plugins HERE
    logger.info(f"Plugins loaded via PluginManager: {plugin_manager_instance.list_plugins()}")
    # -----------------------------------------

    # --- Load Core Config --- 
    core_config = load_yaml_config(BLUEPRINT_PATH)
    if core_config is None:
        logger.critical("Failed to load core configuration (blueprint). Halting startup.")
        raise RuntimeError("Failed to load core configuration.")

    # --- Initialize VantaMasterCore (NOW uses loaded plugins) --- 
    try:
        orchestrator_instance = VantaMasterCore(
            core_config_path=str(BLUEPRINT_PATH),
            plugin_manager=plugin_manager_instance # Pass the manager with loaded plugins
        )
        logger.info("VantaMasterCore initialized.")
        await orchestrator_instance.startup()
        logger.info("VantaMasterCore startup tasks complete.")
    except Exception as e:
         logger.critical(f"Failed to initialize or start VantaMasterCore: {e}", exc_info=True)
         raise RuntimeError("VantaMasterCore failed to start.") from e

    yield # Application runs

    # Code to run on shutdown
    logger.info("Application shutting down...")
    if orchestrator_instance:
        try:
            await orchestrator_instance.shutdown()
            logger.info("VantaMasterCore shutdown complete.")
        except Exception as e:
            logger.error(f"Error during VantaMasterCore shutdown: {e}", exc_info=True)
    logger.info("Application shutdown complete.")

app = FastAPI(title="VANTA Framework API", lifespan=lifespan_manager)

# --- ADD CORS MIDDLEWARE --- 
origins = [
    "http://localhost",         # Allow local dev environments
    "http://localhost:3000",    # Common React/Next.js dev port
    "http://localhost:5173",    # Common Vite dev port
    "*"                       # Allow all origins (convenient for testing, REMOVE/RESTRICT for production)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],      # Allow all methods
    allow_headers=["*"],      # Allow all headers
)
# --- END ADD CORS MIDDLEWARE ---

# --- Request Models ---
class TaskRequest(BaseModel):
    intent: str
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict)
    target_agent: Optional[str] = None
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

# --- OpenAI-Compatible Models ---
class ChatMessage(BaseModel):
    role: str # Typically "system", "user", or "assistant"
    content: str

class ChatCompletionRequest(BaseModel):
    model: str # Although VANTA handles routing, OpenAI clients expect this
    messages: list[ChatMessage]
    stream: Optional[bool] = False # <<< ADDED: To parse the stream parameter
    # Add other common OpenAI params if needed later (temperature, max_tokens, etc.)
    # temperature: Optional[float] = 1.0 
    # max_tokens: Optional[int] = None

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop" # Simple default

class Usage(BaseModel):
    prompt_tokens: int = 0 # Placeholder
    completion_tokens: int = 0 # Placeholder
    total_tokens: int = 0 # Placeholder

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(asyncio.get_event_loop().time()))
    model: str # Return the model requested, even if VANTA used differently
    choices: list[ChatCompletionChoice]
    usage: Usage = Field(default_factory=Usage)
# ------------------------------

# --- Dependency to get Orchestrator ---
# Ensures orchestrator is initialized before endpoint is called
async def get_orchestrator() -> VantaMasterCore:
    if orchestrator_instance is None:
        # This shouldn't happen if lifespan event completes successfully
        logger.error("Orchestrator not initialized!")
        raise HTTPException(status_code=503, detail="Service Unavailable: Orchestrator not ready.")
        
    # --- DEBUGGING: Log pilgrim keys from the instance being returned --- 
    pilgrim_keys = []
    if hasattr(orchestrator_instance, 'pilgrims') and isinstance(orchestrator_instance.pilgrims, dict):
        pilgrim_keys = list(orchestrator_instance.pilgrims.keys())
    logger.info(f"get_orchestrator: Returning instance {id(orchestrator_instance)} with pilgrim keys: {pilgrim_keys}")
    # ------------------------------------------------------------------
    
    return orchestrator_instance

# --- Security Scheme Definition ---
api_key_scheme = HTTPBearer()

# --- API Key Verification Function ---
async def verify_api_key(credentials: Optional[HTTPAuthorizationCredentials] = Depends(api_key_scheme, use_cache=False)):
    """Dependency function to verify the provided API key."""
    # --- Explicitly skip check if no keys are configured --- 
    if not config.ALLOWED_API_KEYS:
        logger.debug("API key check skipped: VANTA_ALLOWED_API_KEYS is not set.")
        return None # Allow access
    # -------------------------------------------------------

    # --- Proceed with check only if keys ARE configured --- 
    if not credentials:
        # This case handles requests missing the Authorization header entirely when keys ARE required
        raise HTTPException(
            status_code=403,
            detail="Not authenticated: Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"}, # Standard practice
        )
        
    if credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=403,
            detail="Invalid authentication scheme. Use Bearer token.",
        )
        
    if credentials.credentials not in config.ALLOWED_API_KEYS:
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key",
        )
        
    # Key is valid
    logger.debug(f"API key verified successfully.") # Add debug log for success
    return credentials.credentials
# --------------------------------- 

# --- API Endpoints ---
@app.get("/")
async def root():
    # Access blueprint version via orchestrator's loaded config if available
    version = "N/A"
    # This check is needed because orchestrator_instance might not be ready immediately
    # A dependency approach is safer for endpoints needing the orchestrator.
    if orchestrator_instance and orchestrator_instance.core_config:
         version = getattr(orchestrator_instance.core_config, 'version', 'N/A')
    return {"message": "VANTA Framework API running...", "version": version}

@app.post("/submit_task")
async def submit_task_endpoint(
    task_request: TaskRequest, 
    orchestrator: VantaMasterCore = Depends(get_orchestrator),
    api_key: str = Depends(verify_api_key) # <<< Apply API key check
):
    """Submits a task to the VANTA Orchestrator."""
    try:
        # Construct the task_data dictionary expected by submit_task
        task_data = {
            "intent": task_request.intent,
            "payload": task_request.payload,
            "context": task_request.context if task_request.context else {},
            # Add source if not provided in context
        }
        if "source" not in task_data["context"]:
             task_data["context"]["source"] = "api"
             
        if task_request.target_agent:
            task_data["target_agent"] = task_request.target_agent

        logger.info(f"API received task: {task_data}")
        
        # --- DEBUGGING: Log pilgrim keys from orchestrator instance used by endpoint ---
        pilgrim_keys = []
        if hasattr(orchestrator, 'pilgrims') and isinstance(orchestrator.pilgrims, dict):
            pilgrim_keys = list(orchestrator.pilgrims.keys())
        logger.info(f"/submit_task endpoint: Using orchestrator {id(orchestrator)} with pilgrim keys: {pilgrim_keys}")
        # -----------------------------------------------------------------------------
        
        # Submit the task to the orchestrator
        result = await orchestrator.submit_task(task_data)
        
        # Return the result from the agent
        # Check if result is an error (simple check)
        if isinstance(result, dict) and result.get("error"):
             raise HTTPException(status_code=500, detail=f"Task execution failed: {result['error']}")
             
        return result # Return the successful result

    except HTTPException as http_exc:
        raise http_exc # Re-raise known HTTP exceptions
    except Exception as e:
        logger.error(f"Error processing /submit_task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# --- OpenAI Compatible Endpoint ---
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def openai_chat_completions(
    request: ChatCompletionRequest,
    orchestrator: VantaMasterCore = Depends(get_orchestrator),
    # --- Temporarily comment out API key check for debugging --- 
    # api_key: str = Depends(verify_api_key) 
    # -------------------------------------------------------
):
    """Handles requests formatted like OpenAI's chat completions endpoint."""
    logger.info(f"Received OpenAI-style request for model: {request.model}")

    # --- ADDED: Check for streaming request --- 
    if hasattr(request, 'stream') and request.stream:
        logger.warning("Streaming chat completions requested, but not yet supported.")
        raise HTTPException(
            status_code=400, 
            detail="Streaming responses are not supported by this VANTA endpoint yet."
        )
    # --- END ADDED ---
    
    # --- Translate OpenAI request to VANTA task ---
    # Define the VANTA intent for chat
    vanta_intent = "chat_completion"
    
    # Pass the messages directly in the payload
    # A dedicated VANTA chat agent would know how to handle this structure
    vanta_payload = {
        "messages": [msg.dict() for msg in request.messages],
        "requested_model": request.model 
        # TODO: Potentially translate/pass other params like temperature if needed
    }
    
    # Construct the task data for VANTA's submit_task
    task_data = {
        "intent": vanta_intent,
        "payload": vanta_payload,
        "context": {"source": "openai_api_compat"}
        # Decide if we need to target a specific agent or use default routing
        # "target_agent": "ChatAgent" 
    }

    try:
        logger.debug(f"Submitting translated task to VANTA orchestrator: {task_data}")
        vanta_result = await orchestrator.submit_task(task_data)
        logger.debug(f"Received raw result from VANTA orchestrator: {vanta_result}") 

        # --- Translate VANTA result back to OpenAI response --- 
        if isinstance(vanta_result, dict) and vanta_result.get("status") == "error": # Check for VANTA error status
            # Handle errors reported by VANTA
            error_detail = vanta_result.get("error", "Unknown VANTA error")
            logger.error(f"VANTA task execution failed: {error_detail}") # Log the error
            raise HTTPException(status_code=500, detail=f"VANTA task execution failed: {error_detail}")

        # --- MODIFIED START: Extract response structure from 'output' key --- 
        chat_completion_output = vanta_result.get("output")
        logger.debug(f"Extracted chat_completion_output: {chat_completion_output}")

        # Validate the structure received
        if not chat_completion_output or not isinstance(chat_completion_output, dict) or not chat_completion_output.get("choices"):
             logger.error(f"VANTA agent did not return the expected OpenAI structure under 'output' for intent '{vanta_intent}'. Received: {vanta_result}")
             raise HTTPException(status_code=500, detail="Agent response format error: Invalid structure.")
             
        # Directly use the validated structure from the agent
        try:
            logger.debug(f"Attempting to create ChatCompletionResponse from: {chat_completion_output}")
            response = ChatCompletionResponse(**chat_completion_output)
            logger.debug(f"Successfully created ChatCompletionResponse object: {response}")
            response.model = request.model 
        except ValidationError as e:
             logger.error(f"Failed to validate/parse agent response structure: {e}. Output received: {chat_completion_output}", exc_info=True)
             raise HTTPException(status_code=500, detail="Agent response format error: Validation failed.")
        # --- END MODIFIED ---

        # --- ADDED: Log the final response object --- 
        logger.debug(f"Sending response to client: {response.model_dump_json(indent=2)}") # Use model_dump_json for clarity
        # -------------------------------------------

        return response

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error processing /v1/chat/completions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
# ------------------------------

# --- Main Entry Point --- 
if __name__ == "__main__":
    # --- Load .env before anything else --- 
    dotenv_path = Path(__file__).resolve().parent / '.env'
    print(f"Loading environment variables from: {dotenv_path}")
    loaded = load_dotenv(dotenv_path=dotenv_path, override=True, verbose=True)
    print(f"Dotenv loaded: {loaded}")
    # --------------------------------------
    
    # Setup logging ONLY if running as main script
    logger = logging.getLogger(__name__)
    logger.info("Starting VANTA API Server...")
    
    # Use environment variable for host/port or defaults
    host = os.getenv("VANTA_HOST", "127.0.0.1")
    port = int(os.getenv("VANTA_PORT", 8888)) # <<< CHANGED BACK to 8888

    # Run the Uvicorn server
    uvicorn.run(
        "run:app", # Point to the FastAPI app instance
        host=host,
        port=port,
        reload=False, # <<< Disable auto-reload for testing
        log_level="info"
    )

# --- Main Execution ---

# async def main_async():
#     """Main async entry point to load config and run framework."""
#     # Config loading and logging setup happens when config.py is imported
#     # print("Starting VANTA (async)...") # Already printed in config.py maybe?
#     blueprint = load_blueprint()
# 
#     if blueprint:
#         agent_definitions = load_agent_definitions()
# 
#         if agent_definitions:
#             orchestrator = run_framework(blueprint, agent_definitions)
#             if orchestrator:
#                 # Keep the event loop running until orchestrator stops or is interrupted
#                 print("Framework initialized. Orchestrator starting task loop...")
#                 # Start the processing loop within the main async function
#                 processing_task = asyncio.create_task(orchestrator.run_processing_loop())
#                 # Start the scheduler in the background
#                 # Check if scheduler exists before starting (it might have been commented out)
#                 if hasattr(orchestrator, 'scheduler') and not orchestrator.scheduler.running:
#                     orchestrator.scheduler.start()
#                     # Use orchestrator's logger
#                     orchestrator.logger.info("Background scheduler started from main_async.") 
#                 
#                 # --- Add a simple initial task for testing ---
#                 initial_task_data = {
#                     "intent": "prompt_creation", 
#                     "payload": {"topic": "hello world"},
#                     "task_id": f"init_task_{uuid.uuid4().hex[:6]}", 
#                     "source_agent": "SystemStartup"
#                 }
#                 await orchestrator.add_task(initial_task_data)
#                 # Use orchestrator's logger
#                 orchestrator.logger.info(f"Added initial test task {initial_task_data['task_id']} to queue.") 
#                 # -------------------------------------------
#                 
#                 try:
#                     # Keep running - wait for the processing task or external shutdown
#                     await processing_task 
#                 except KeyboardInterrupt:
#                     print("\nKeyboardInterrupt received. Shutting down...")
#                 finally:
#                     # Graceful shutdown
#                     await orchestrator.stop()
#                     print("Framework shutdown complete.")
#             else:
#                  print("Orchestrator initialization failed.")
#         else:
#             print("Exiting due to missing or invalid agent definitions.")
#     else:
#         print("Exiting due to missing or invalid blueprint.")

# if __name__ == "__main__":
#     # --- Use asyncio.run to manage the event loop ---
#     # config.py is imported first, setting everything up
#     try:
#         asyncio.run(main_async())
#     except KeyboardInterrupt:
#         print("\nShutdown requested by user (Ctrl+C).")
#     # --- Removed old synchronous call ---
#     # print("Starting VANTA...")
#     # blueprint = load_blueprint()
#     # 
#     # if blueprint:
#     #     # --- Load definitions from JSON instead of configs from YAML ---
#     #     agent_definitions = load_agent_definitions()
#     # 
#     #     if agent_definitions: # Proceed only if definitions were loaded
#     #          # Option 1: Run as a background process/loop (example)
#     #         run_framework(blueprint, agent_definitions)
#     # 
#     #         # Option 2: Run as a FastAPI server (example)
#     #         # print("Starting API server...")
#     #         # uvicorn.run(app, host="0.0.0.0", port=8000) # Match port in vanta_router_and_lora.py?
#     #     else:
#     #         print("Exiting due to missing or invalid agent definitions.")
#     # else:
#     #     print("Exiting due to missing or invalid blueprint.") 

# --- REMOVED Security Scheme Definition from here --- 
# api_key_scheme = HTTPBearer()

# --- REMOVED API Key Verification Function from here ---
# async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(api_key_scheme)):
#     """Dependency function to verify the provided API key."""
#     # Only enforce key check if ALLOWED_API_KEYS is populated
#     if config.ALLOWED_API_KEYS:
#         if credentials.scheme != "Bearer":
#             raise HTTPException(
#                 status_code=403,
#                 detail="Invalid authentication scheme. Use Bearer token.",
#             )
#         if credentials.credentials not in config.ALLOWED_API_KEYS:
#             raise HTTPException(
#                 status_code=403,
#                 detail="Invalid API Key",
#             )
#         # Key is valid
#         return credentials.credentials
#     else:
#         # No keys configured, allow access
#         logger.warning("API key check skipped: VANTA_ALLOWED_API_KEYS is not set.")
#         return None # Indicate no key was checked/needed
# --------------------------------- 

# Ensure VantaMasterCore is globally accessible or passed appropriately
master_core: Optional[VantaMasterCore] = None
plugin_manager: Optional[PluginManager] = None # Add global ref for plugin manager

# --- Pydantic Models for API ---
class TaskInput(BaseModel):
    intent: str
    payload: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    target_agent: Optional[str] = None

class ApiResponse(BaseModel):
    status: str = "success"
    data: Optional[Any] = None
    error: Optional[str] = None
# ----------------------------

# --- Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    """Application startup logic."""
    global master_core, plugin_manager # <<< Declare global
    logger.info("Application startup...")
    
    # --- Initialize Plugin Manager --- 
    plugin_dir = config.get_vanta_path("vanta_seed/agents")
    logger.info(f"Initializing PluginManager for directory: {plugin_dir}")
    plugin_manager = PluginManager(plugin_directory=str(plugin_dir))
    plugin_manager.load_plugins()
    logger.info(f"Plugins loaded via PluginManager: {plugin_manager.list_plugins()}")
    # -------------------------------
    
    # --- Initialize VantaMasterCore --- 
    blueprint_path = config.get_vanta_path(config.VANTA_BLUEPRINT_FILE)
    if not blueprint_path.exists():
         logger.error(f"CRITICAL: Blueprint file not found at {blueprint_path}. Cannot start Master Core.")
         # Exit or raise? For now, log and continue but core won't function
         master_core = None 
    else:
         try:
              master_core = VantaMasterCore(
                   core_config_path=str(blueprint_path), # Pass path as string
                   plugin_manager=plugin_manager # Pass the initialized manager
              )
              logger.info("VantaMasterCore initialized.")
              # Run Crown startup tasks
              await master_core.startup()
              logger.info("VantaMasterCore startup tasks complete.")
         except Exception as e:
              logger.exception(f"CRITICAL: Failed to initialize VantaMasterCore: {e}")
              master_core = None # Ensure it's None on failure
    # -------------------------------
    logger.info("Application startup complete.")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown logic."""
    global master_core
    logger.info("Application shutdown...")
    if master_core and hasattr(master_core, 'shutdown'):
        await master_core.shutdown()
        logger.info("VantaMasterCore shutdown complete.")
    logger.info("Application shutdown complete.")
# -----------------------

# --- API Endpoints ---
@app.get("/")
async def read_root():
    return {"message": "Welcome to VANTA"}

# --- NEW: General Task Submission Endpoint --- 
@app.post("/submit_task", response_model=ApiResponse)
async def submit_task_endpoint(task: TaskInput):
    """Receives a task and submits it to the VantaMasterCore."""
    global master_core
    if not master_core:
        logger.error("Submit Task request failed: VantaMasterCore not initialized.")
        raise HTTPException(status_code=503, detail="Core service unavailable")
        
    task_dict = task.model_dump() # Use model_dump for Pydantic v2
    logger.info(f"API received task submission via /submit_task: Intent '{task.intent}'")
    
    try:
        result = await master_core.submit_task(task_dict)
        return ApiResponse(status="success", data=result)
    except Exception as e:
        logger.exception(f"Error processing task via /submit_task: {e}")
        # Consider returning a more structured error
        return ApiResponse(status="error", error=f"Internal server error: {str(e)}")
# ------------------------------------------

# --- Existing OpenAI Compatible Endpoint --- 
@app.post("/v1/chat/completions")
async def chat_completions(request: Request, authorization: str = Header(None)):
    pass # Replace placeholder with pass to avoid syntax error
    # Original logic for this endpoint should be preserved here
    # Example start:
    # logger.info("Received request on /v1/chat/completions")
    # api_key = get_api_key(authorization)
    # if not is_api_key_valid(api_key):
    #     raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    # ... rest of the OpenAI endpoint logic ...

# --- Health Check Endpoint --- 
@app.get("/health")
async def health_check(): # Added function definition
    # Placeholder logic, should check core components like Master Core status
    return {"status": "ok"}
    # pass # Replace placeholder with pass

# --- Plugin Listing Endpoint --- 
@app.get("/plugins")
async def list_plugins():
    # Placeholder logic, should return a list of available plugins
    return {"plugins": ["PlaceholderPlugin1", "PlaceholderPlugin2"]}

# --- NEW: OpenAI Compatible Chat Completions Endpoint --- 
@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def handle_chat_completions(
    request: ChatCompletionRequest,
    orchestrator: VantaMasterCore = Depends(get_orchestrator),
    api_key: str = Depends(verify_api_key) # <<< CORRECTED: Use verify_api_key
):
    """Handles OpenAI-compatible chat completion requests."""
    logger.info(f"Received /v1/chat/completions request for model: {request.model}")
    if not orchestrator:
        logger.error("Orchestrator not initialized during chat completion request.")
        raise HTTPException(status_code=503, detail="Service Temporarily Unavailable: Orchestrator not ready.")

    # --- Translate OpenAI request to VANTA task --- 
    vanta_task_payload = {
        "requested_model": request.model,
        "messages": [msg.model_dump() for msg in request.messages],
        # Pass common parameters if the proxy agent supports them
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        # "stream": request.stream, # Add stream handling later if needed
    }
    
    task_data = {
        "intent": "chat_completion",
        "payload": vanta_task_payload,
        "context": {"source": "openai_api"}
        # target_agent will be determined by VantaMasterCore based on requested_model
    }

    try:
        logger.debug(f"Submitting translated task to orchestrator: {task_data}")
        # Assuming submit_task returns a dict, potentially with 'response_text'
        core_result = await orchestrator.submit_task(task_data)
        logger.debug(f"Orchestrator returned: {core_result}")

        if isinstance(core_result, dict) and core_result.get("response_text"):
            response_text = core_result["response_text"]
            # --- Format VANTA result into OpenAI response --- 
            response_message = ResponseMessage(content=response_text)
            choice = Choice(message=response_message)
            openai_response = ChatCompletionResponse(
                model=request.model, # Reflect back the requested model (or actual model used if known)
                choices=[choice]
                # usage can be added if token counts are available
            )
            logger.info(f"Successfully processed chat completion for model {request.model}")
            return openai_response
        elif isinstance(core_result, dict) and core_result.get("error"):
             # Propagate errors from the core
             logger.error(f"Error from VANTA core during chat completion: {core_result['error']}")
             raise HTTPException(status_code=500, detail=f"Agent execution failed: {core_result['error']}")
        else:
            # Handle unexpected result format from VANTA core
            logger.error(f"Unexpected result format from VANTA core: {core_result}")
            raise HTTPException(status_code=500, detail="Internal Server Error: Unexpected response format from agent.")

    except HTTPException as http_exc:
        raise http_exc # Re-raise known HTTP exceptions
    except Exception as e:
        logger.exception(f"Unexpected error processing chat completion request: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
# ------------------------------------------------------