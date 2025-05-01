# server_a.py - FastAPI server entry point for VANTA Instance A

import logging
import asyncio
import os
import yaml
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel, Field
import uvicorn
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Add project root to sys path for imports
import sys
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

# Core VANTA imports (adjust paths if necessary)
import config as global_config # Load shared config first (logging, .env)
from vanta_seed.core.vanta_master_core import VantaMasterCore
from vanta_seed.core.plugin_manager import PluginManager

# --- Instance Specific Config ---
INSTANCE_NAME = "instance_a"
INSTANCE_ROOT = Path(__file__).parent.resolve()
CONFIG_FILE = INSTANCE_ROOT / "config_a.yaml"

logger = logging.getLogger(f"VANTA_{INSTANCE_NAME.upper()}_API")

# --- Load Instance Config --- 
def load_instance_config(file_path: Path) -> dict:
    if not file_path.exists():
        logger.error(f"Instance configuration file not found: {file_path}")
        return {}
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error loading instance config {file_path}: {e}")
        return {}

instance_config = load_instance_config(CONFIG_FILE)
INSTANCE_IDENTITY = instance_config.get("identity", {})

# --- Globals for Lifespan --- 
orchestrator_instance: Optional[VantaMasterCore] = None
plugin_manager_instance: Optional[PluginManager] = None

# --- Security --- 
api_key_scheme = HTTPBearer()
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(api_key_scheme)):
    # Using shared ALLOWED_API_KEYS from global config.py
    if global_config.ALLOWED_API_KEYS:
        if credentials.scheme != "Bearer" or credentials.credentials not in global_config.ALLOWED_API_KEYS:
            raise HTTPException(status_code=403, detail="Invalid API Key")
        return credentials.credentials
    else:
        logger.warning("API key check skipped: VANTA_ALLOWED_API_KEYS not set.")
        return None

# --- FastAPI Lifespan --- 
@asynccontextmanager
async def lifespan_manager(app: FastAPI):
    global orchestrator_instance, plugin_manager_instance
    logger.info(f"Starting up {INSTANCE_NAME}...")

    # Init Plugin Manager (using shared agent code path)
    plugin_dir = project_root / "vanta_seed" / "agents"
    plugin_manager_instance = PluginManager(plugin_directory=str(plugin_dir))
    plugin_manager_instance.load_plugins()
    logger.info(f"Plugins loaded: {plugin_manager_instance.list_plugins()}")

    # Load core blueprint (shared)
    core_blueprint_path = global_config.get_blueprint_path()
    if not core_blueprint_path.exists():
        logger.critical(f"Core blueprint not found at {core_blueprint_path}. Halting.")
        raise RuntimeError("Core blueprint configuration missing.")

    # Init Orchestrator
    try:
        # VantaMasterCore uses the blueprint path to load its own config
        orchestrator_instance = VantaMasterCore(
            core_config_path=str(core_blueprint_path),
            plugin_manager=plugin_manager_instance
            # TODO: Consider passing instance_name/config to orchestrator if needed
        )
        logger.info(f"VantaMasterCore initialized for {INSTANCE_NAME}.")
        await orchestrator_instance.startup()
        logger.info(f"VantaMasterCore startup tasks complete for {INSTANCE_NAME}.")
    except Exception as e:
        logger.critical(f"Failed to start VantaMasterCore for {INSTANCE_NAME}: {e}", exc_info=True)
        raise RuntimeError(f"VantaMasterCore failed to start for {INSTANCE_NAME}.") from e

    yield # App runs

    logger.info(f"Shutting down {INSTANCE_NAME}...")
    if orchestrator_instance:
        await orchestrator_instance.shutdown()
    logger.info(f"{INSTANCE_NAME} shutdown complete.")

# --- FastAPI App --- 
app = FastAPI(title=f"VANTA API - {INSTANCE_NAME}", lifespan=lifespan_manager)

# --- Request Models (Shared with run.py potentially, redefined here for clarity) ---
class TaskRequest(BaseModel):
    intent: str
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict)
    target_agent: Optional[str] = None
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ChatMessage(BaseModel): role: str; content: str
class ChatCompletionRequest(BaseModel): model: str; messages: list[ChatMessage]
class ChatCompletionChoice(BaseModel): index: int; message: ChatMessage; finish_reason: str = "stop"
class Usage(BaseModel): prompt_tokens: int = 0; completion_tokens: int = 0; total_tokens: int = 0
class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: str = "chat.completion"; created: int = Field(default_factory=lambda: int(asyncio.get_event_loop().time()))
    model: str; choices: list[ChatCompletionChoice]; usage: Usage = Field(default_factory=Usage)

# --- Dependencies --- 
async def get_orchestrator() -> VantaMasterCore:
    if orchestrator_instance is None:
        raise HTTPException(status_code=503, detail=f"Service Unavailable: {INSTANCE_NAME} orchestrator not ready.")
    return orchestrator_instance

# --- Endpoints --- 
@app.get("/")
async def root():
    return {"message": f"VANTA API ({INSTANCE_NAME}) running..."}

@app.post("/submit_task")
async def submit_task_endpoint(task_request: TaskRequest, orchestrator: VantaMasterCore = Depends(get_orchestrator), api_key: str = Depends(verify_api_key)):
    try:
        task_data = task_request.dict()
        if "source" not in task_data.get("context", {}):
            task_data["context"] = task_data.get("context", {}) # ensure context exists
            task_data["context"]["source"] = f"api_{INSTANCE_NAME}"
        logger.info(f"API {INSTANCE_NAME} received task: {task_data}")
        result = await orchestrator.submit_task(task_data)
        if isinstance(result, dict) and result.get("error"):
             raise HTTPException(status_code=500, detail=f"Task execution failed: {result['error']}")
        return result
    except Exception as e:
        logger.error(f"Error processing /submit_task on {INSTANCE_NAME}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def openai_chat_completions(request: ChatCompletionRequest, orchestrator: VantaMasterCore = Depends(get_orchestrator), api_key: str = Depends(verify_api_key)):
    vanta_intent = "chat_completion"
    vanta_payload = {"messages": [msg.dict() for msg in request.messages], "requested_model": request.model}
    task_data = {"intent": vanta_intent, "payload": vanta_payload, "context": {"source": f"openai_api_compat_{INSTANCE_NAME}"}}
    try:
        vanta_result = await orchestrator.submit_task(task_data)
        if isinstance(vanta_result, dict) and vanta_result.get("error"):
            raise HTTPException(status_code=500, detail=f"VANTA task execution failed: {vanta_result['error']}")
        assistant_response_text = vanta_result.get("response_text")
        if not assistant_response_text:
             raise HTTPException(status_code=500, detail="Agent response format error (missing 'response_text')")
        assistant_message = ChatMessage(role="assistant", content=assistant_response_text)
        choice = ChatCompletionChoice(index=0, message=assistant_message)
        response = ChatCompletionResponse(model=request.model, choices=[choice])
        return response
    except Exception as e:
        logger.error(f"Error processing /v1/chat/completions on {INSTANCE_NAME}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# --- Janus System Endpoints (Placeholders) --- 

@app.post("/mutate_peer")
async def mutate_peer(request: Request, api_key: str = Depends(verify_api_key)):
    # TODO: Implement security check (e.g., check sender identity/token)
    # TODO: Parse mutation request body
    # TODO: Queue task for CodeMutatorAgent (needs RQ setup)
    logger.warning("Endpoint /mutate_peer received request (not implemented)")
    return {"status": "received", "message": "Mutation task queued (placeholder)"}

@app.post("/approve_sync")
async def approve_sync(request: Request, api_key: str = Depends(verify_api_key)):
    # TODO: Implement security check
    # TODO: Parse approval request (mutation_id, commit_hash, etc.)
    # TODO: Trigger MutationManager.merge_branch (potentially via RQ)
    logger.warning("Endpoint /approve_sync received request (not implemented)")
    return {"status": "received", "message": "Sync approval task queued (placeholder)"}

# Add /request_diff, /reload_signal etc. as needed

# --- Uvicorn Runner --- 
if __name__ == "__main__":
    port = int(os.getenv("PORT_A", 8000)) # Use INSTANCE_A specific port
    host = os.getenv("HOST", "127.0.0.1")
    log_level_str = global_config.LOG_LEVEL.lower()
    print(f"--- Starting VANTA API Server ({INSTANCE_NAME} on {host}:{port}) ---")
    uvicorn.run(f"server_a:app", host=host, port=port, log_level=log_level_str, reload=True) 