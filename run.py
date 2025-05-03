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

# --- FastAPI Imports ---
from fastapi import FastAPI, HTTPException, Request, Depends
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

# --- FastAPI Lifespan Management ---
async def lifespan(app: FastAPI):
    global orchestrator_instance, plugin_manager_instance
    logger.info("Application startup...")
    
    # --- Initialize Plugin Manager ---
    # Assuming plugins are in vanta_seed/agents
    plugin_dir = config.BASE_DIR / "vanta_seed" / "agents" 
    plugin_manager_instance = PluginManager(plugin_directory=str(plugin_dir))
    plugin_manager_instance.load_plugins()
    logger.info(f"Plugins loaded: {plugin_manager_instance.list_plugins()}")
    # -------------------------------

    # --- Load Configurations ---
    # Assuming blueprint is the core config needed by VantaMasterCore
    core_config = load_yaml_config(BLUEPRINT_PATH) 
    # Agent definitions are loaded inside VantaMasterCore via core_config path now?
    # Let's adjust VantaMasterCore init if needed, or load here if separate.
    # Assuming VantaMasterCore's _load_core_config handles loading agent defs too.
    
    if core_config is None:
        logger.critical("Failed to load core configuration (blueprint). Exiting.")
        # In a real app, maybe raise an exception or handle differently
        return 

    # --- Initialize VantaMasterCore ---
    try:
        # Pass the PATH to the core config, VantaMasterCore loads it internally
        orchestrator_instance = VantaMasterCore(
            core_config_path=str(BLUEPRINT_PATH), # Pass path
            plugin_manager=plugin_manager_instance
        )
        logger.info("VantaMasterCore initialized.")
        # Start the orchestrator's background tasks
        await orchestrator_instance.startup()
        logger.info("VantaMasterCore startup complete.")
    except Exception as e:
         logger.critical(f"Failed to initialize or start VantaMasterCore: {e}", exc_info=True)
         # Prevent app from starting if core fails
         raise RuntimeError("VantaMasterCore failed to start.") from e

    yield # Application runs here

    # --- Shutdown Logic ---
    logger.info("Application shutting down...")
    if orchestrator_instance:
        try:
            await orchestrator_instance.shutdown()
            logger.info("VantaMasterCore shutdown complete.")
        except Exception as e:
            logger.error(f"Error during VantaMasterCore shutdown: {e}", exc_info=True)
    logger.info("Application shutdown complete.")

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
    logger.info("Starting VANTA API Server...")
    # <<< MODIFY Host and Port >>>
    uvicorn.run(
        "run:app", # Point to the FastAPI app instance
        host="127.0.0.1", # Changed from "0.0.0.0"
        port=8888, # Changed from 1337
        reload=True, # Enable auto-reload for development
        log_level=config.LOG_LEVEL.lower() # Use log level from config
    )
    # <<< END MODIFY >>>

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