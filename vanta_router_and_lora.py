# vanta_router_and_lora.py
"""FastAPI router acting as OpenAI compatible gateway to Ollama and OpenAI models.

Handles routing based on prompt content and formats responses.
Requires Ollama service running for local models.
Requires OPENAI_API_KEY environment variable for OpenAI models.
"""

import json # Added for stream error handling
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal, Union
import re, asyncio, os, time, uuid
import ollama # Import ollama
from openai import AsyncOpenAI, OpenAIError # Import OpenAI client and error
from fastapi.responses import StreamingResponse, PlainTextResponse
import yaml # Added for stream error handling
from datetime import datetime # For timestamping entries
import random  # For random drift bonus
import logging # <-- Uncomment
# Add import for the moved helper function
from vanta_seed.core.lot_sh_helper import extract_thought_hierarchy_shorthand

# --- Basic Logging Config --- 
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s') # <-- Uncomment
logger = logging.getLogger(__name__) # <-- Uncomment
# ---------------------------

# --- Load Configuration --- #
CONFIG_PATH = "config.yaml"
PROMPTS_PATH = "prompts.yaml" # <-- Add prompts file path
config = {}
prompts = {} # <-- Add dictionary for prompts

try:
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    print(f"WARNING: {CONFIG_PATH} not found. Using default settings or environment variables.")
except yaml.YAMLError as e:
    print(f"WARNING: Error parsing {CONFIG_PATH}: {e}. Using default settings or environment variables.")

# <-- Load prompts -->
try:
    with open(PROMPTS_PATH, 'r') as f:
        prompts = yaml.safe_load(f)
    if not prompts:
        print(f"WARNING: {PROMPTS_PATH} is empty. Evaluation prompts might be missing.")
        prompts = {} # Ensure it's a dict even if empty
except FileNotFoundError:
    print(f"WARNING: {PROMPTS_PATH} not found. Evaluation prompts will be unavailable.")
    prompts = {}
except yaml.YAMLError as e:
    print(f"WARNING: Error parsing {PROMPTS_PATH}: {e}. Evaluation prompts might be unavailable.")
    prompts = {}
# <-- End loading prompts -->

# Helper function to get config value with fallback
def get_config(key_path: str, default: Any = None):
    keys = key_path.split('.')
    value = config
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        # Fallback to environment variable if top-level key exists (e.g., ollama.host -> OLLAMA_HOST)
        if len(keys) == 2:
            env_var = f"{keys[0].upper()}_{keys[1].upper()}"
            return os.getenv(env_var, default)
        return default

# --- FastAPI Dependency for Logger (Moved Up) ---
def get_logger():
    """FastAPI dependency to provide the logger."""
    # Ensure basic config is called at least once (idempotent)
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)
# -----------------------------------

VISION_PAT = re.compile(r"<img|https?://.*\.(?:png|jpg|jpeg|webp|bmp|gif)", re.I)
CODE_PAT = re.compile(r"(def |class |import |```|#include|<script>|function |return|\{|\}|\(|\))", re.IGNORECASE)
MATH_PAT = re.compile(r"[∑∫√π]|\\frac|\\begin{aligned}")
# New Pattern for Mythogenesis/Storytelling prompts
MYTH_PAT = re.compile(r"(myth|legend|story|narrative|epic|tale|lore|imagine)", re.IGNORECASE)

# --- Configuration for Symbol Index ---
MYTH_INDEX_FILE = "myth_symbol_index.json"
COLLAPSE_SOURCE_LIMIT = 5  # Max number of entries allowed for collapse
NARRATIVE_SNIPPET_LENGTH = 150 # Length of narrative snippet to store

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class ResponseChatMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = None

class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ResponseChatMessage
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter", "function_call"]] = "stop"

class ChatCompletionUsage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionChoice]
    usage: Optional[ChatCompletionUsage] = None

class DeltaMessage(BaseModel):
    role: Optional[Literal["assistant"]] = "assistant"
    content: Optional[str] = None

class ChatCompletionStreamChoice(BaseModel):
    index: int = 0
    delta: DeltaMessage
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter", "function_call"]] = None

class ChatCompletionStreamResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex}")
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[ChatCompletionStreamChoice]
    usage: Optional[ChatCompletionUsage] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None # Can be used to override router choice if desired
    max_tokens: Optional[int] = None # Ollama uses num_predict in options
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1 # Ollama doesn't directly support n>1 in chat API AFAIK
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = None # Ollama uses repeat_penalty in options
    frequency_penalty: Optional[float] = None # Ollama uses repeat_penalty in options
    seed: Optional[int] = None
    # --- VANTA specific ---
    include_reasoning: bool = False

class SymbolSearchRequest(BaseModel):
    query: str = Field(..., description="The symbol or keyword to search for.")
    case_sensitive: Optional[bool] = Field(default=False, description="Perform a case-sensitive search.")
    max_results: Optional[int] = Field(default=10, description="Maximum number of results to return.")

# --- Models for Lineage Tracking ---
class LineageInfo(BaseModel):
    origin_id: str # ID of the initial branch this drift belongs to
    parent_id: Optional[str] = None # ID of the immediate parent entry (None for initial branch)
    drift_step: int # Depth of drift from the origin (0 for initial branch)

class SearchResultItem(BaseModel):
    entry_id: str 
    narrative_snippet: str
    symbols: List[str]
    timestamp: datetime
    model_used: str
    lineage: Optional[LineageInfo] = None # Added lineage field
    type: str # Added type field ('branch' or 'drift')
    # Include other relevant fields from index entry like drift_instruction if type is drift
    original_branch_id: Optional[str] = None # For drift entries
    drift_instruction: Optional[str] = None # For drift entries

class SymbolSearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]

# Model for myth index entry summary
class MythIndexEntrySummary(BaseModel):
    entry_id: str
    symbols: List[str]
    type: str
    timestamp: datetime

# --- LoT-Sh Model (Added) ---
class ThoughtNodeShorthand(BaseModel):
    id: str              # e.g. "T1", "T2"
    shorthand: str       # e.g. '[T1]: CUE("…") -> symbol'
    parent_id: Optional[str] = None

# --- Task Router Class ---
class TaskRouter:
    # Define default and specialized models available in Ollama
    # Make sure these are pulled in your Ollama instance!
    DEFAULT_OLLAMA_MODEL = get_config("ollama.models.default", "deepseek-llm:latest")
    CODE_OLLAMA_MODEL = get_config("ollama.models.code", "deepseek-coder:latest") # Renamed for clarity
    VISION_OLLAMA_MODEL = get_config("ollama.models.vision", None) # e.g., "llava:latest"

    # Define default OpenAI model
    DEFAULT_OPENAI_MODEL = get_config("openai.models.default_chat", "gpt-4o")
    VISION_OPENAI_MODEL = get_config("openai.models.default_vision", "gpt-4o") # Added for potential OpenAI vision routing

    # Load keywords from config
    OPENAI_IMAGE_KEYWORDS = get_config("routing.openai_image_keywords", ["generate image", "create an image", "make a picture"])

    @staticmethod
    def pick_model(prompt: str, requested_model: Optional[str] = None) -> tuple[str, str, Optional[str]]:
        """Determines the target backend, the model to try first, and a fallback model.

        Returns:
            tuple[str, str, Optional[str]]: 
              (backend, model_to_try, base_model_if_lora_failed)
        """
        # 1. Explicit OpenAI Request?
        if requested_model and requested_model.startswith(("gpt-", "dall-e-")):
            print(f"Routing to OpenAI model (explicit request): {requested_model}")
            return ("openai", requested_model, None) # No fallback needed for OpenAI

        # 2. OpenAI Image Keywords?
        if any(keyword in prompt.lower() for keyword in TaskRouter.OPENAI_IMAGE_KEYWORDS):
            print(f"Routing to OpenAI model (image keywords): {TaskRouter.DEFAULT_OPENAI_MODEL}")
            return ("openai", TaskRouter.DEFAULT_OPENAI_MODEL, None)
        
        # --- Ollama Logic --- 
        ollama_backend = "ollama"
        base_model = None
        lora_model_to_try = None
        
        # 3. Vision Content?
        if TaskRouter.VISION_OLLAMA_MODEL and VISION_PAT.search(prompt):
            model_to_try = TaskRouter.VISION_OLLAMA_MODEL
            # For now, assume vision models don't use LoRA fallbacks in this way
            print(f"Routing to Ollama vision model: {model_to_try}")
            return (ollama_backend, model_to_try, None)

        # 4. Code/Math Content?
        if TaskRouter.CODE_OLLAMA_MODEL and (CODE_PAT.search(prompt) or MATH_PAT.search(prompt)):
            base_model = TaskRouter.CODE_OLLAMA_MODEL # Base for code tasks
            if "python" in prompt.lower():
                lora_model_config_name = get_config("ollama.models.lora_models.python_expert")
                if lora_model_config_name:
                    print(f"Routing attempt: Ollama code model (Python LoRA): {lora_model_config_name}")
                    # Try the LoRA model, specify the base code model as fallback
                    return (ollama_backend, lora_model_config_name, base_model)
            
            # If no specific LoRA matched or configured, use the base code model
            print(f"Routing to Ollama code/math model (standard): {base_model}")
            return (ollama_backend, base_model, None) # No LoRA attempt, no fallback needed

        # 5. Myth/Story Content?
        if MYTH_PAT.search(prompt):
            base_model = TaskRouter.DEFAULT_OLLAMA_MODEL # Base for myth is default
            lora_model_config_name = get_config("ollama.models.lora_models.myth_weaver")
            if lora_model_config_name:
                print(f"Routing attempt: Ollama model (Myth LoRA): {lora_model_config_name}")
                # Try the LoRA model, specify the default model as fallback
                return (ollama_backend, lora_model_config_name, base_model)
            # Fallthrough to default logic if no Myth LoRA configured

        # 6. Fallback: Use Explicitly Requested Model if provided?
        if requested_model:
            # Check if the requested model is actually one of the configured LoRA models
            lora_config_values = list(get_config("ollama.models.lora_models", {}).values())
            if requested_model in lora_config_values:
                # This is tricky - we don't know the intended *base* model easily here.
                # Safest bet is to assume the default model as fallback if a LoRA fails.
                # A better config might map LoRA names back to base models.
                print(f"Routing to Ollama model (LoRA requested directly): {requested_model}")
                return (ollama_backend, requested_model, TaskRouter.DEFAULT_OLLAMA_MODEL)
            else:
                # Assume it's a non-OpenAI, non-LoRA base model requested directly
                 print(f"Routing to Ollama model (Base requested directly): {requested_model}")
                 return (ollama_backend, requested_model, None)

        # 7. Final Default: Use Default Ollama Model
        print(f"Routing to default Ollama model (no match): {TaskRouter.DEFAULT_OLLAMA_MODEL}")
        return (ollama_backend, TaskRouter.DEFAULT_OLLAMA_MODEL, None)

# --- Initialize Clients --- #
# Ollama Client
ollama_host = get_config("ollama.host", "http://localhost:11434")
print(f"--- VANTA: Initializing Ollama client with host: {ollama_host} ---")
ollama_client = ollama.AsyncClient(host=ollama_host)

# OpenAI Client (will be initialized inside the request if needed)
# Ensure OPENAI_API_KEY environment variable is set

router = TaskRouter()
app = FastAPI(title="VANTA Unified API (Ollama + OpenAI + Myth)", version="0.6.0") # Version bump

# --- Streaming Generators ---
async def ollama_stream_generator(request_id: str, created_time: int, model_key: str, ollama_response_stream):
    """Generates OpenAI-compatible SSE chunks from Ollama stream."""
    try:
        async for chunk in ollama_response_stream:
            if chunk.get("error"):
                # Handle errors reported by Ollama within the stream
                error_content = f"\n\nOllama Error: {chunk['error']}"
                error_stream_chunk = ChatCompletionStreamResponse(
                    id=request_id,
                    created=created_time,
                    model=model_key,
                    choices=[ChatCompletionStreamChoice(delta=DeltaMessage(content=error_content), finish_reason="error")]
                )
                yield f"data: {error_stream_chunk.model_dump_json()}\n\n"
                break # Stop streaming on error

            delta_content = chunk['message'].get('content')
            finish_reason = "stop" if chunk.get('done', False) else None

            stream_chunk = ChatCompletionStreamResponse(
                id=request_id,
                created=created_time,
                model=model_key,
                choices=[ChatCompletionStreamChoice(
                    delta=DeltaMessage(content=delta_content),
                    finish_reason=finish_reason
                )]
                # TODO: Add usage stats if available in the final 'done' chunk from Ollama
            )
            yield f"data: {stream_chunk.model_dump_json()}\n\n"

            if finish_reason:
                break # Stop after the final chunk with finish_reason

        yield "data: [DONE]\n\n"

    except Exception as e:
        # Handle exceptions during stream generation/iteration
        print(f"Error during Ollama stream processing: {e}") # Log error server-side
        # Safely convert exception to string
        error_message = str(e)
        error_content = f"\n\nError processing Ollama stream: {error_message}"
        try:
            error_stream_chunk = ChatCompletionStreamResponse(
                id=request_id,
                created=created_time,
                model=model_key,
                choices=[ChatCompletionStreamChoice(delta=DeltaMessage(content=error_content), finish_reason="error")]
            )
            yield f"data: {error_stream_chunk.model_dump_json()}\n\n"
        except Exception as inner_e:
            # Fallback if creating the error chunk fails
            print(f"Error creating error stream chunk: {inner_e}")
            yield f"data: {json.dumps({'error': {'message': error_content}})}\n\n"
        yield "data: [DONE]\n\n"

async def openai_stream_generator(openai_response_stream):
    """Generates OpenAI-compatible SSE chunks directly from OpenAI stream."""
    # OpenAI's stream chunks are already in the correct SSE format
    # We just need to yield them directly
    try:
        async for chunk in openai_response_stream:
            yield f"data: {chunk.model_dump_json()}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        print(f"Error during OpenAI stream processing: {e}")
        # Safely convert exception to string
        error_message = str(e)
        # Attempt to yield a structured error, fallback to simple text
        try:
            # Create a minimal error chunk structure if possible
             error_chunk_data = {
                "object": "chat.completion.chunk",
                "choices": [{"index": 0, "delta": {"content": f"\n\nError processing OpenAI stream: {error_message}"}, "finish_reason": "error"}]
            }
             yield f"data: {json.dumps(error_chunk_data)}\n\n"
        except Exception as inner_e:
            print(f"Error creating OpenAI error stream chunk: {inner_e}")
            yield f"data: {json.dumps({'error': {'message': f'Error processing OpenAI stream: {error_message}'}})}\n\n"
        yield "data: [DONE]\n\n"

# --- Helper Functions for JSON Symbol Index --- 

def load_myth_index() -> List[Dict]:
    """Loads the myth index from the JSON file."""
    if not os.path.exists(MYTH_INDEX_FILE):
        return []
    try:
        with open(MYTH_INDEX_FILE, 'r', encoding='utf-8') as f:
            # Handle empty file case
            content = f.read()
            if not content:
                return []
            return json.loads(content)
    except json.JSONDecodeError:
        print(f"Warning: Error decoding {MYTH_INDEX_FILE}. Returning empty index.")
        return [] # Return empty list if file is corrupt
    except Exception as e:
        print(f"Warning: Error loading {MYTH_INDEX_FILE}: {e}. Returning empty index.")
        return []

def append_to_myth_index(entry_data: Dict):
    """Appends a new entry to the myth index JSON file."""
    index = load_myth_index()
    index.append(entry_data)
    try:
        with open(MYTH_INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False, default=str) # Use default=str for datetime
    except Exception as e:
        print(f"Error writing to {MYTH_INDEX_FILE}: {e}")

# --- Symbol Search Endpoint --- 
print("--- VANTA: Attempting to register /v1/symbol/search endpoint ---")

@app.post("/v1/symbol/search", response_model=SymbolSearchResponse)
async def search_symbols(req: SymbolSearchRequest):
    """Searches the myth index for narratives matching symbolic keywords."""
    index_data = load_myth_index()
    query = req.query
    matches = []

    print(f"--- Symbol Search: Query='{query}', CaseSensitive={req.case_sensitive}, MaxResults={req.max_results} ---")

    for entry in index_data:
        # Ensure symbols field exists and is a list
        symbols = entry.get("symbols", [])
        if not isinstance(symbols, list):
            continue # Skip entry if symbols format is unexpected

        found_match = False
        for symbol in symbols:
            if not isinstance(symbol, str):
                continue # Skip non-string symbols
            
            # Perform comparison
            symbol_to_compare = symbol if req.case_sensitive else symbol.lower()
            query_to_compare = query if req.case_sensitive else query.lower()
            
            # Using simple substring containment for now
            if query_to_compare in symbol_to_compare:
                found_match = True
                break # Found a match in this entry's symbols, no need to check further
        
        if found_match:
            # Attempt to parse timestamp robustly
            try:
                timestamp = datetime.fromisoformat(entry.get("timestamp"))
            except (TypeError, ValueError):
                timestamp = datetime.now() # Fallback timestamp
                
            result_item = SearchResultItem(
                entry_id=entry.get("entry_id", "unknown"),
                narrative_snippet=entry.get("narrative_snippet", ""),
                symbols=symbols,
                timestamp=timestamp,
                model_used=entry.get("model_used", "unknown"),
                lineage=entry.get("lineage"),
                type=entry.get("type", "unknown"),
                original_branch_id=entry.get("original_branch_id"),
                drift_instruction=entry.get("drift_instruction")
            )
            matches.append(result_item)

    # Sort matches by timestamp (most recent first)
    matches.sort(key=lambda item: item.timestamp, reverse=True)
    
    # Limit results
    limited_matches = matches[:req.max_results]

    print(f"--- Symbol Search: Found {len(limited_matches)} matches (out of {len(matches)} total) ---")
    
    return SymbolSearchResponse(query=req.query, results=limited_matches)

# --- Unified /v1/chat/completions Endpoint ---
@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    # Determine model and backend using TaskRouter
    # Combine message content for routing analysis
    combined_content = " ".join([msg.content for msg in req.messages if msg.role == 'user'])
    # Get the routing decision: (backend, model_to_try, base_model_if_lora_failed)
    backend, model_to_try, base_model_fallback = router.pick_model(combined_content, req.model)

    # Prepare messages list (common format)
    api_messages = [msg.model_dump() for msg in req.messages]

    # --- Add VANTA specific headers/instructions --- 
    system_message_index = -1
    for i, msg in enumerate(api_messages):
        if msg['role'] == 'system':
            system_message_index = i
            break
    vanta_header = "[(SceneTrigger::START)]\n"
    if req.include_reasoning:
        vanta_header += "Please think step-by-step inside <think> tags. End reasoning with </think> before final answer.\n"
    if system_message_index != -1:
        api_messages[system_message_index]['content'] = vanta_header + api_messages[system_message_index]['content']
    else:
        api_messages.insert(0, {"role": "system", "content": vanta_header})
    # -------------------------------------------

    request_id = f"chatcmpl-{uuid.uuid4().hex}"
    created_time = int(time.time())

    try:
        # --- Route to Ollama --- 
        if backend == "ollama":
            # Map OpenAI parameters to Ollama options
            options = {
                "temperature": req.temperature if req.temperature is not None else 0.7,
                "num_predict": req.max_tokens if req.max_tokens is not None else -1, 
                "top_p": req.top_p if req.top_p is not None else 1.0,
                "stop": [req.stop] if isinstance(req.stop, str) else req.stop, 
                "seed": req.seed,
                "presence_penalty": req.presence_penalty, # Map if needed
                "frequency_penalty": req.frequency_penalty # Map if needed
            }
            options = {k: v for k, v in options.items() if v is not None}

            # --- Attempt Ollama call, with LoRA fallback if needed --- 
            current_model_to_use = model_to_try
            try:
                if req.stream:
                    # INITIAL STREAMING OLLAMA CALL
                    ollama_stream = await ollama_client.chat(
                        model=current_model_to_use,
                        messages=api_messages,
                        stream=True,
                        options=options
                    )
                    # Return stream immediately, fallback happens if initial call fails
                    return StreamingResponse(
                        ollama_stream_generator(request_id, created_time, current_model_to_use, ollama_stream),
                        media_type="text/event-stream"
                    )
                else:
                    # INITIAL NON-STREAMING OLLAMA CALL
                    response = await ollama_client.chat(
                        model=current_model_to_use,
                        messages=api_messages,
                        stream=False,
                        options=options
                    )
            except ollama.ResponseError as e:
                # Check if it's a 404 AND we have a fallback model defined by the router
                if e.status_code == 404 and base_model_fallback:
                    print(f"--- Model '{model_to_try}' not found. Falling back to base model: {base_model_fallback} ---")
                    current_model_to_use = base_model_fallback # Switch to base model
                    # RETRY THE CALL with the base model
                    if req.stream:
                         # RETRY STREAM CALL
                         ollama_stream = await ollama_client.chat(
                             model=current_model_to_use,
                             messages=api_messages,
                             stream=True,
                             options=options
                         )
                         return StreamingResponse(
                             ollama_stream_generator(request_id, created_time, current_model_to_use, ollama_stream),
                             media_type="text/event-stream"
                         )
                    else:
                        # RETRY NON-STREAM CALL
                        response = await ollama_client.chat(
                            model=current_model_to_use,
                            messages=api_messages,
                            stream=False,
                            options=options
                        )
                        # Fallthrough to process response below
                else:
                    # Re-raise other Ollama errors or if no fallback was defined
                    raise e

            # --- Process successful Ollama response (original or fallback, non-streaming only) ---
            if not req.stream:
                if response.get("error"):
                    raise HTTPException(status_code=500, detail=f"Ollama Error in response: {response['error']}")

                final_content = response['message']['content']
                usage = ChatCompletionUsage(
                    prompt_tokens=response.get('prompt_eval_count'),
                    completion_tokens=response.get('eval_count'),
                    total_tokens=response.get('prompt_eval_count', 0) + response.get('eval_count', 0)
                ) if response.get('prompt_eval_count') is not None else None

                return ChatCompletionResponse(
                    id=request_id,
                    created=created_time,
                    model=current_model_to_use, # Report the model actually used
                    choices=[ChatCompletionChoice(
                        message=ResponseChatMessage(content=final_content),
                        finish_reason="stop" 
                    )],
                    usage=usage
                )

        # --- Route to OpenAI --- 
        elif backend == "openai":
            try:
                openai_client = AsyncOpenAI() 
            except Exception as client_err:
                 print(f"Error initializing OpenAI client: {client_err}")
                 raise HTTPException(status_code=500, detail=f"OpenAI Client Initialization Error: {client_err}")

            openai_params = {
                "model": model_to_try, # Use the model determined by router
                "messages": api_messages,
                "temperature": req.temperature,
                # ... (rest of OpenAI parameters as before) ...
                "stream": req.stream,
            }
            openai_params = {k: v for k, v in openai_params.items() if v is not None}

            if req.stream:
                openai_stream = await openai_client.chat.completions.create(**openai_params)
                return StreamingResponse(
                    openai_stream_generator(openai_stream),
                    media_type="text/event-stream"
                )
            else:
                response = await openai_client.chat.completions.create(**openai_params)
                return response

        # --- Unknown Backend --- 
        else:
             raise HTTPException(status_code=501, detail=f"Unsupported backend: {backend}")

    # --- Error Handling --- 
    except ollama.ResponseError as ollama_exc:
        # Handle specific Ollama errors
        print(f"Ollama API Error: {ollama_exc.status_code} - {ollama_exc.error}")
        raise HTTPException(status_code=ollama_exc.status_code, detail=f"Ollama Error: {ollama_exc.error}")
    except OpenAIError as openai_exc:
         # Handle specific OpenAI errors
         print(f"OpenAI API Error: {openai_exc}")
         # You might want to customize the status code based on openai_exc.status_code if available
         raise HTTPException(status_code=getattr(openai_exc, 'status_code', 500), detail=f"OpenAI Error: {openai_exc}")
    except HTTPException as http_exc:
        # Re-raise exceptions we already handled
        raise http_exc
    except Exception as e:
        # Catch-all for other unexpected errors
        print(f"Error processing chat completion request: {e}")
        # Consider logging the full traceback here
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

# --- New Models for Mythogenesis ---
class MythBranchParams(BaseModel):
    temperature: Optional[float] = 0.9 # Higher temp for creativity
    max_tokens: Optional[int] = 800
    top_p: Optional[float] = 0.9
    # Add other potential generation parameters if needed
    seed: Optional[int] = None

class MythBranchRequest(BaseModel):
    seed_prompt: str
    parameters: Optional[MythBranchParams] = Field(default_factory=MythBranchParams)

class MythBranchResponse(BaseModel):
    branch_id: str = Field(default_factory=lambda: f"mythbranch-{uuid.uuid4().hex[:10]}")
    narrative: str
    model_used: str
    symbolic_nodes: List[str] = [] # Placeholder for future symbol extraction
    thought_shorthand: Dict[str, Optional[str]] = {}  # Changed type
    # Add usage stats later if needed

# --- Symbolic Node Extraction Helper ---
async def extract_symbolic_nodes(narrative: str, model_name: str) -> List[str]:
    """
    Given a narrative, uses the specified model to extract latent symbolic nodes (concepts, motifs, archetypes).
    """
    system_prompt = (
        "You are a Symbolic Distiller. Given a story fragment, you must identify and list between 3 and 7 latent symbolic nodes. "
        "Focus on concepts, motifs, archetypes, and key emotional elements — not just objects or names. "
        "Each node should be concise, evocative, and symbolically meaningful. Output only the list of nodes, each on a new line, optionally prefixed with '- '."
    )
    # Limit narrative length sent for extraction to avoid excessive token usage
    max_narrative_length = 1000 # Adjust as needed
    narrative_snippet = narrative[:max_narrative_length] + ("..." if len(narrative) > max_narrative_length else "")
    
    user_prompt = f"Story fragment:\\n\\n{narrative_snippet}\\n\\nExtract symbolic nodes:"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    print(f"--- Attempting Symbolic Node Extraction using model: {model_name} ---")
    try:
        # Use a reasonable temperature for consistent extraction
        options = {"temperature": 0.5} 
        response = await ollama_client.chat(
            model=model_name,
            messages=messages,
            stream=False,
            options=options
        )
        if response.get("error"):
            print(f"Ollama Error during symbolic node extraction: {response['error']}")
            return []
        
        extracted_text = response['message']['content']
        print(f"--- Raw Symbolic Nodes Extracted:\\n{extracted_text}\\n---")
        
        # Refined Parsing Logic:
        nodes = []
        # Attempt splitting by newline first
        lines = extracted_text.split("\n")
        # Filter out any potential empty lines from multiple newlines
        lines = [line for line in lines if line.strip()]
        
        # If splitting by newline gives multiple lines, assume newline separation
        # Otherwise, if only one line, try splitting by comma
        if len(lines) > 1:
            nodes = [line.strip("- ").strip() for line in lines]
        elif len(lines) == 1:
            # Assume comma separation if only one line was returned
            potential_nodes = lines[0].split(',')
            nodes = [node.strip("- ").strip() for node in potential_nodes]
        # If lines is empty, nodes remains empty []

        # Final filter for any empty strings after stripping
        nodes = [node for node in nodes if node]

        print(f"--- Parsed Symbolic Nodes: {nodes} ---")
        return nodes[:7] # Limit to max 7 nodes
        
    except ollama.ResponseError as e:
         print(f"Ollama API Error during symbolic node extraction: {e.status_code} - {e.error}")
         # Decide if fallback is needed here? For now, return empty on error.
         return []
    except Exception as exc:
        print(f"Unexpected Exception during symbolic node extraction: {exc}")
        import traceback
        traceback.print_exc()
        return []

# --- NEW Mythogenesis Endpoint: /v1/myth/branch --- 
print("--- VANTA: Attempting to register /v1/myth/branch endpoint ---") 

@app.post("/v1/myth/branch", response_model=MythBranchResponse)
async def branch_myth(req: MythBranchRequest):
    """Initiates a new narrative branch from a seed prompt."""
    import logging # Define logger locally FIRST
    logger = logging.getLogger(__name__)
    
    # --- Ensure logger is defined before any other logic ---

    # 1. Determine model using TaskRouter (forcing myth context if needed)
    # We can directly use the MYTH_PAT logic or force it
    # Forcing it ensures this endpoint uses myth-intended models
    backend, model_to_try, base_model_fallback = router.pick_model(req.seed_prompt + " story myth legend", None) # Add keywords to ensure myth routing
    
    # Ensure we are using an Ollama model for myth for now
    if backend != "ollama":
        # Or potentially route to a specific OpenAI model if configured for myth
        print("Warning: Myth branching currently configured for Ollama, but router picked OpenAI. Re-routing to default Ollama.")
        backend = "ollama"
        model_to_try = router.DEFAULT_OLLAMA_MODEL
        base_model_fallback = None # Reset fallback if forced to default

    # 2. Prepare messages for the LLM
    # Simple system prompt for narrative generation
    system_prompt = "You are a master storyteller and myth-weaver. Continue the narrative seed provided by the user, expanding it into a compelling and imaginative story fragment. Focus on evocative language and symbolic depth."
    api_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": req.seed_prompt}
    ]
    
    # 3. Prepare Ollama options from request parameters
    req_params = req.parameters if req.parameters else MythBranchParams()
    options = {
        "temperature": req_params.temperature,
        "num_predict": req_params.max_tokens if req_params.max_tokens is not None else -1,
        "top_p": req_params.top_p,
        "seed": req_params.seed
        # Add other mapped parameters if needed
    }
    options = {k: v for k, v in options.items() if v is not None}
    
    # 4. Call Ollama with fallback logic
    current_model_to_use = model_to_try
    try:
        print(f"--- Myth Branch: Attempting model: {current_model_to_use} ---")
        response = await ollama_client.chat(
            model=current_model_to_use,
            messages=api_messages,
            stream=False, # Myth branching is non-streaming for now
            options=options
        )
    except ollama.ResponseError as e:
        if e.status_code == 404 and base_model_fallback:
            print(f"--- Myth Branch: Model '{model_to_try}' not found. Falling back to: {base_model_fallback} ---")
            current_model_to_use = base_model_fallback
            try:
                response = await ollama_client.chat(
                    model=current_model_to_use,
                    messages=api_messages,
                    stream=False,
                    options=options
                )
            except ollama.ResponseError as retry_e:
                print(f"Error during Myth Branch fallback call: {retry_e}")
                raise HTTPException(status_code=retry_e.status_code, detail=f"Ollama Fallback Error: {retry_e.error}")
            except Exception as retry_exc:
                 print(f"Unexpected error during Myth Branch fallback call: {retry_exc}")
                 raise HTTPException(status_code=500, detail=f"Internal Server Error during fallback: {retry_exc}")
        else:
             print(f"Ollama API Error during Myth Branch call: {e}")
             raise HTTPException(status_code=e.status_code, detail=f"Ollama Error: {e.error}")
    except Exception as exc:
         print(f"Unexpected error during Myth Branch call: {exc}")
         raise HTTPException(status_code=500, detail=f"Internal Server Error: {exc}")

    # 5. Process successful response
    if response.get("error"):
        raise HTTPException(status_code=500, detail=f"Ollama Error in Myth Branch response: {response['error']}")

    narrative_content = response['message']['content']
    
    # 6. Extract Symbolic Nodes & LoT-Sh Dictionary
    extracted_symbols = await extract_symbolic_nodes(narrative_content, current_model_to_use)
    # Call the imported helper, passing the client and extraction model
    extraction_model_for_lotsh = TaskRouter.DEFAULT_OLLAMA_MODEL
    shorthand_dict = await extract_thought_hierarchy_shorthand(narrative_content, extraction_model_for_lotsh, ollama_client)

    # --- Append to Symbol Index ---
    branch_response_obj = MythBranchResponse(
        narrative=narrative_content,
        model_used=current_model_to_use,
        symbolic_nodes=extracted_symbols,
        thought_shorthand=shorthand_dict # Assign dict
    )
    entry_data = {
        "entry_id": branch_response_obj.branch_id,
        "narrative_snippet": narrative_content[:NARRATIVE_SNIPPET_LENGTH] + ("..." if len(narrative_content) > NARRATIVE_SNIPPET_LENGTH else ""),
        "symbols": extracted_symbols,
        "timestamp": datetime.now().isoformat(),
        "model_used": current_model_to_use,
        "type": "branch",
        # Add initial lineage info for branch
        "lineage": {
            "origin_id": branch_response_obj.branch_id,
            "parent_id": None,
            "drift_step": 0
        },
        "thought_shorthand": shorthand_dict # Store dict in index
    }
    append_to_myth_index(entry_data)
    logger.info(f"Saved branch {branch_response_obj.branch_id} to index with LoT-Sh.") # Uncomment this call
    SYMBOL_INDEX[branch_response_obj.branch_id] = entry_data

    # 7. Return structured response
    return branch_response_obj # Return the Pydantic object

# --- NEW Models for Myth Drift --- 
class MythDriftParams(BaseModel):
    # Instruction guiding how the narrative should evolve; defaults to a natural drift
    drift_instruction: Optional[str] = "Let the narrative evolve naturally over time."
    # Generation parameters
    temperature: Optional[float] = 0.88
    max_tokens: Optional[int] = 750
    top_p: Optional[float] = 0.9
    seed: Optional[int] = None
    # When true, select a random myth entry as the source for drift
    random_source: Optional[bool] = False  # bonus random drift flag

class MythDriftRequest(BaseModel):
    source_entry_id: str = Field(..., description="The entry_id of the existing narrative to evolve.") 
    parameters: MythDriftParams

class MythDriftResponse(BaseModel):
    drifted_narrative: str
    model_used: str
    original_branch_id: Optional[str] = None
    drift_instruction_used: str
    symbolic_nodes: List[str] = [] # Placeholder for future symbol extraction
    thought_shorthand: Dict[str, Optional[str]] = {}  # Changed type
    # Add usage stats later if needed

# --- Add diagnostic print before Drift Endpoint Definition ---
print("--- VANTA: Attempting to register /v1/myth/drift endpoint ---")

@app.post("/v1/myth/drift", response_model=MythDriftResponse)
async def drift_myth(req: MythDriftRequest):
    """Evolves an existing narrative branch based on drift parameters."""
    
    # Random Drift Bonus: choose a random source if requested
    if getattr(req.parameters, "random_source", False):
        all_ids = list(SYMBOL_INDEX.keys())
        if all_ids:
            req.source_entry_id = random.choice(all_ids)
            print(f"--- Random Drift: selected source_entry_id={req.source_entry_id} ---")
    
    # --- Load Parent Entry to get narrative and lineage ---
    print(f"--- Drift Request: Loading parent entry ID: {req.source_entry_id} ---")
    # Load parent entry from in-memory index if available
    parent_entry = SYMBOL_INDEX.get(req.source_entry_id)
    if not parent_entry:
        # Fallback to file in case not loaded
        index_data = load_myth_index()
        parent_entry = next((entry for entry in index_data if entry.get("entry_id") == req.source_entry_id), None)

    if not parent_entry:
        raise HTTPException(status_code=404, detail=f"Source entry ID '{req.source_entry_id}' not found in index.")
        
    source_narrative = parent_entry.get("narrative", "") # Get full narrative if stored, else use snippet (TODO: Store full narrative?)
    if not source_narrative:
         # If full narrative isn't stored, use snippet as fallback (less ideal)
         source_narrative = parent_entry.get("narrative_snippet", "")
         print("Warning: Using narrative snippet as source for drift, full narrative not found in index.")
         if not source_narrative:
             raise HTTPException(status_code=400, detail="Could not retrieve source narrative content from parent entry.")

    parent_lineage = parent_entry.get("lineage")
    current_drift_step = 0
    origin_id = req.source_entry_id # Default origin if parent has no lineage
    if isinstance(parent_lineage, dict):
        current_drift_step = parent_lineage.get("drift_step", 0)
        origin_id = parent_lineage.get("origin_id", origin_id)
    # -----------------------------------------------------
    
    # 1. Determine model using TaskRouter
    routing_prompt = f"{req.parameters.drift_instruction} ... {source_narrative[:100]}" # Use actual narrative snippet
    backend, model_to_try, base_model_fallback = router.pick_model(routing_prompt, None)

    # Ensure Ollama for now (similar to branch)
    if backend != "ollama":
        print("Warning: Myth drift configured for Ollama, re-routing to default Ollama.")
        backend = "ollama"
        model_to_try = router.DEFAULT_OLLAMA_MODEL
        base_model_fallback = None

    # 2. Prepare messages for the LLM - USE LOADED NARRATIVE
    system_prompt = f"You are a master storyteller. Evolve the following narrative according to this instruction: '{req.parameters.drift_instruction}'. Maintain narrative coherence but apply the requested change."
    api_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": source_narrative} # Use the narrative loaded from parent
    ]

    # 3. Prepare Ollama options
    req_params = req.parameters
    options = {
        "temperature": req_params.temperature,
        "num_predict": req_params.max_tokens if req_params.max_tokens is not None else -1,
        "top_p": req_params.top_p,
        "seed": req_params.seed
    }
    options = {k: v for k, v in options.items() if v is not None}

    # 4. Call Ollama with fallback
    current_model_to_use = model_to_try
    try:
        print(f"--- Myth Drift: Attempting model: {current_model_to_use} ---")
        response = await ollama_client.chat(
            model=current_model_to_use,
            messages=api_messages,
            stream=False,
            options=options
        )
    except ollama.ResponseError as e:
        if e.status_code == 404 and base_model_fallback:
            print(f"--- Myth Drift: Model '{model_to_try}' not found. Falling back to: {base_model_fallback} ---")
            current_model_to_use = base_model_fallback
            try:
                response = await ollama_client.chat(
                    model=current_model_to_use,
                    messages=api_messages,
                    stream=False,
                    options=options
                )
            except ollama.ResponseError as retry_e:
                print(f"Error during Myth Drift fallback call: {retry_e}")
                raise HTTPException(status_code=retry_e.status_code, detail=f"Ollama Fallback Error: {retry_e.error}")
            except Exception as retry_exc:
                print(f"Unexpected error during Myth Drift fallback call: {retry_exc}")
                raise HTTPException(status_code=500, detail=f"Internal Server Error during fallback: {retry_exc}")
        else:
            print(f"Ollama API Error during Myth Drift call: {e}")
            raise HTTPException(status_code=e.status_code, detail=f"Ollama Error: {e.error}")
    except Exception as exc:
        print(f"Unexpected error during Myth Drift call: {exc}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {exc}")

    # 5. Process successful response
    if response.get("error"):
        raise HTTPException(status_code=500, detail=f"Ollama Error in Myth Drift response: {response['error']}")

    drifted_content = response['message']['content']

    # 6. Extract Symbolic Nodes & LoT-Sh Dictionary
    extracted_symbols = await extract_symbolic_nodes(drifted_content, current_model_to_use)
    # Call the imported helper, passing the client and extraction model
    extraction_model_for_lotsh = TaskRouter.DEFAULT_OLLAMA_MODEL
    shorthand_dict = await extract_thought_hierarchy_shorthand(drifted_content, extraction_model_for_lotsh, ollama_client)

    # --- Append to Symbol Index with Lineage ---
    drift_entry_id = f"mythdrift-{uuid.uuid4().hex[:10]}"
    new_drift_step = current_drift_step + 1
    
    drift_response_obj = MythDriftResponse(
        drifted_narrative=drifted_content,
        model_used=current_model_to_use,
        original_branch_id=req.source_entry_id,
        drift_instruction_used=req.parameters.drift_instruction,
        symbolic_nodes=extracted_symbols,
        thought_shorthand=shorthand_dict # Assign dict
    )
    entry_data = {
        "entry_id": drift_entry_id,
        "narrative_snippet": drifted_content[:NARRATIVE_SNIPPET_LENGTH] + ("..." if len(drifted_content) > NARRATIVE_SNIPPET_LENGTH else ""),
        "symbols": extracted_symbols,
        "timestamp": datetime.now().isoformat(), 
        "model_used": current_model_to_use,
        "drift_instruction": req.parameters.drift_instruction, 
        "type": "drift",
        # Add calculated lineage info
        "lineage": {
            "origin_id": origin_id,
            "parent_id": req.source_entry_id,
            "drift_step": new_drift_step
        },
        "thought_shorthand": shorthand_dict # Store dict in index
    }
    append_to_myth_index(entry_data)
    logger.info(f"Saved drift {drift_entry_id} to index with LoT-Sh.") # Uncommented
    SYMBOL_INDEX[drift_entry_id] = entry_data
    # ---------------------------------------

    # 7. Return structured response
    return drift_response_obj

# --- Endpoint to retrieve myth index entries summary
@app.get("/v1/myth/index/entries", response_model=List[MythIndexEntrySummary])
async def get_myth_index_entries():
    """Returns summary list of all myth index entries."""
    # Use in-memory symbol index
    index_list = list(SYMBOL_INDEX.values())
    summaries: List[MythIndexEntrySummary] = []
    for entry in index_list:
        try:
            ts = datetime.fromisoformat(entry.get("timestamp"))
        except Exception:
            ts = datetime.now()
        summaries.append(
            MythIndexEntrySummary(
                entry_id=entry.get("entry_id"),
                symbols=entry.get("symbols", []),
                type=entry.get("type", ""),
                timestamp=ts,
            )
        )
    return summaries

# --- Endpoint to return mermaid.js lineage map
@app.get("/v1/myth/lineage/map", response_class=PlainTextResponse)
async def get_myth_lineage_map(origin_id: Optional[str] = None):
    """Returns a mermaid.js flowchart diagram of myth lineage."""
    # Use in-memory symbol index
    index_list = list(SYMBOL_INDEX.values())
    entries = [e for e in index_list if not origin_id or e.get("lineage", {}).get("origin_id") == origin_id]
    lines = ["flowchart LR"]
    for e in entries:
        eid = e.get("entry_id")
        pid = e.get("lineage", {}).get("parent_id")
        if pid:
            lines.append(f"  {pid} --> {eid}")
        else:
            lines.append(f"  {eid}")
    return "\n".join(lines)

# In-memory myth symbol index
SYMBOL_INDEX: Dict[str, Dict[str, Any]] = {}

@app.on_event("startup")
async def load_symbol_index_on_startup():
    """Load or initialize the myth symbol index on startup."""
    if not os.path.exists(MYTH_INDEX_FILE):
        print(f"Warning: {MYTH_INDEX_FILE} not found. Creating empty index.")
        try:
            with open(MYTH_INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error creating empty {MYTH_INDEX_FILE}: {e}")
    index_list = load_myth_index()
    global SYMBOL_INDEX
    SYMBOL_INDEX = {entry["entry_id"]: entry for entry in index_list}
    print(f"Loaded {len(SYMBOL_INDEX)} myth entries into memory.")

# Pydantic models for myth collapse
class MythCollapseRequest(BaseModel):
    entry_ids: List[str] = Field(..., description="List of entry_ids to collapse into an archetype.")

class MythCollapseResponse(BaseModel):
    collapse_narrative: str
    model_used: str
    new_entry_id: str
    symbols: List[str]
    lineage: LineageInfo
    thought_shorthand: Dict[str, Optional[str]] = {}  # Changed type

# Endpoint to collapse multiple myths into an archetype
@app.post("/v1/myth/collapse", response_model=MythCollapseResponse)
async def collapse_myth(req: MythCollapseRequest):
    """Merges multiple myth entries into a single archetype narrative."""
    # Validation Guards
    if not req.entry_ids:
        raise HTTPException(status_code=400, detail="entry_ids cannot be empty.")
    if len(req.entry_ids) > COLLAPSE_SOURCE_LIMIT:
        raise HTTPException(status_code=400, detail=f"Cannot collapse more than {COLLAPSE_SOURCE_LIMIT} entries.")
    for eid in req.entry_ids:
        entry = SYMBOL_INDEX.get(eid)
        if entry and entry.get("type") == "collapse":
            raise HTTPException(status_code=400, detail=f"Cannot collapse archetype entry: {eid}")
        
    # Validate requested entries exist
    missing = [eid for eid in req.entry_ids if eid not in SYMBOL_INDEX]
    if missing:
        raise HTTPException(status_code=404, detail=f"Entries not found: {missing}")
    
    # Gather source narratives
    fragments = []
    for eid in req.entry_ids:
        entry = SYMBOL_INDEX[eid]
        fragments.append(entry.get("narrative", entry.get("narrative_snippet", "")))

    # Prepare LLM prompts
    system_prompt = "You are a master myth synthesizer. Merge the following myth fragments into a coherent archetype narrative."
    api_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n\n".join(fragments)}
    ]

    # Call Ollama
    response = await ollama_client.chat(
        model=TaskRouter.DEFAULT_OLLAMA_MODEL,
        messages=api_messages,
        stream=False,
        options={"temperature": 0.9, "num_predict": 800, "top_p": 0.9}
    )
    if response.get("error"):
        raise HTTPException(status_code=500, detail=f"Ollama Error: {response['error']}")
    collapsed_content = response["message"]["content"]

    # Extract symbols & LoT-Sh Dictionary
    extracted_symbols = await extract_symbolic_nodes(collapsed_content, TaskRouter.DEFAULT_OLLAMA_MODEL)
    # Call the imported helper, passing the client and extraction model
    extraction_model_for_lotsh = TaskRouter.DEFAULT_OLLAMA_MODEL
    shorthand_dict = await extract_thought_hierarchy_shorthand(collapsed_content, extraction_model_for_lotsh, ollama_client)

    # Create new index entry
    collapse_id = f"mythcollapse-{uuid.uuid4().hex[:10]}"
    snippet = collapsed_content[:NARRATIVE_SNIPPET_LENGTH] + ("..." if len(collapsed_content) > NARRATIVE_SNIPPET_LENGTH else "")
    entry_data = {
        "entry_id": collapse_id,
        "narrative_snippet": snippet,
        "symbols": extracted_symbols,
        "timestamp": datetime.now().isoformat(),
        "model_used": TaskRouter.DEFAULT_OLLAMA_MODEL,
        "type": "collapse",
        "lineage": {"origin_id": collapse_id, "parent_id": None, "drift_step": 0},
        "thought_shorthand": shorthand_dict # Store dict in index
    }
    append_to_myth_index(entry_data)
    SYMBOL_INDEX[collapse_id] = entry_data
    logger.info(f"Saved collapse {collapse_id} to index with LoT-Sh.") # Uncommented

    # Return structured response
    return MythCollapseResponse(
        collapse_narrative=collapsed_content,
        model_used=TaskRouter.DEFAULT_OLLAMA_MODEL,
        new_entry_id=collapse_id,
        symbols=extracted_symbols,
        lineage=LineageInfo(origin_id=collapse_id, parent_id=None, drift_step=0),
        thought_shorthand=shorthand_dict # Assign dict
    )

# --- Updated Endpoint for Shorthand Dictionary --- 
@app.get("/v1/thought/{entry_id}/shorthand", response_model=Dict[str, Optional[str]])
async def get_thought_shorthand(entry_id: str):
    """Retrieves the LoT-Sh dictionary for a given myth entry."""
    logger.debug(f"Request received for shorthand of entry: {entry_id}") # Uncommented
    entry = SYMBOL_INDEX.get(entry_id)
    if not entry:
        logger.warning(f"Shorthand requested for non-existent entry: {entry_id}") # Uncommented
        raise HTTPException(status_code=404, detail="Entry not found")
        
    # Retrieve the dictionary stored under the 'thought_shorthand' key
    shorthand_data = entry.get("thought_shorthand") 
    
    # --- Return the dictionary directly, or a default if missing/malformed --- 
    if isinstance(shorthand_data, dict):
         # Ensure all expected keys are present, adding None if missing
         expected_keys = ["T1_CUE", "T2_MAP", "T3_EVAL", "T4_PLAN"]
         # Create a new dict to avoid modifying the original potentially cached data
         result_dict = {key: shorthand_data.get(key) for key in expected_keys}
         logger.debug(f"Returning shorthand dict for {entry_id}: {result_dict}") # Uncommented
         return result_dict # RETURN THE DICTIONARY DIRECTLY
    else:
         logger.warning(f"Shorthand data for {entry_id} is missing or not a dict: {shorthand_data}. Returning default.") # Uncommented
         # Return the default structure if data is missing or malformed
         return {"T1_CUE": None, "T2_MAP": None, "T3_EVAL": None, "T4_PLAN": None}

# --- Models for Narrative Evaluation --- 
class MythEvalRequest(BaseModel):
    entry_id: str
    criteria: Optional[List[str]] = ["coherence", "novelty", "depth"]

class MythEvalResponse(BaseModel):
    scores: Dict[str, float]
    notes: Dict[str, str]

# --- Narrative Evaluation Endpoint --- 
print("--- VANTA: Attempting to register /v1/myth/evaluate endpoint ---")

@app.post("/v1/myth/evaluate", response_model=MythEvalResponse)
async def evaluate_myth(req: MythEvalRequest):
    entry_id = req.entry_id
    # Use defaults if None or empty list provided
    criteria = req.criteria if req.criteria else ["coherence", "novelty", "depth"]

    logger.info(f"Evaluating myth entry {entry_id} with criteria: {criteria}") # Uncommented

    # 1. Find the narrative snippet from the in-memory index
    narrative_snippet = None
    source_entry = None # Store the whole entry if found
    for entry in SYMBOL_INDEX.values():
        if entry.get("entry_id") == entry_id:
            source_entry = entry
            # Use full narrative if available, otherwise snippet
            narrative_snippet = entry.get("narrative", entry.get("narrative_snippet", "No narrative found."))
            break

    if not narrative_snippet:
        logger.warning(f"Evaluation failed: Entry ID {entry_id} not found in SYMBOL_INDEX.") # Uncommented
        raise HTTPException(status_code=404, detail=f"Entry ID {entry_id} not found")

    # Limit snippet size for the prompt if needed (e.g., first 1000 chars)
    if len(narrative_snippet) > 1000: # Limit prompt context
         narrative_snippet = narrative_snippet[:1000] + "..."
         logger.info(f"Truncated narrative snippet for evaluation prompt for entry {entry_id}.") # Uncommented

    # 2. Build the prompt from loaded file
    eval_prompt_template = prompts.get('myth_evaluation')
    if not eval_prompt_template:
        logger.error("Myth evaluation prompt template missing from prompts.yaml!") # Uncommented
        raise HTTPException(status_code=500, detail="Server configuration error: Evaluation prompt missing.")

    criteria_str = "\n".join([f"- {c}" for c in criteria])
    prompt = eval_prompt_template.format(
        narrative_snippet=narrative_snippet,
        criteria_list=criteria_str
    )

    # 3. Call LLM using TaskRouter's default model
    try:
        # <<< REMOVING TEMPORARY SKIP >>>

        # --- Original LLM Call Block (Restored) ---
        # Use the router to get the default model and backend
        # Combine message content for routing analysis (use criteria as hint)
        routing_hint = f"Evaluate narrative based on {', '.join(criteria)}."
        backend, model_to_use, _ = router.pick_model(routing_hint, None) # Use default model selection
        logger.info(f"Using model '{model_to_use}' via backend '{backend}' for evaluation.") # Uncommented
        
        # Prepare messages for the chat API
        eval_messages = [
            {"role": "system", "content": "You are a narrative analysis assistant. Evaluate the provided text based on the criteria using the specified format."},
            {"role": "user", "content": prompt}
        ]
        
        # Make the API call (simplified - assumes non-streaming for eval)
        # TODO: Refactor to use a unified internal call function later
        llm_response_content = ""
        if backend == "ollama":
            options = {"temperature": 0.3} # Low temp for deterministic eval
            try:
                response_data = await ollama_client.chat(
                    model=model_to_use,
                    messages=eval_messages,
                    stream=False,
                    options=options
                )
                llm_response_content = response_data.get("message", {}).get("content", "")
            except ollama.ResponseError as e:
                 logger.error(f"Ollama API error during evaluation for {entry_id}: {e}") # Uncommented
                 raise HTTPException(status_code=502, detail=f"Ollama API error: {e}")
        
        elif backend == "openai":
             # Placeholder for OpenAI call - adapt if needed
             logger.warning("OpenAI backend for evaluation is not fully implemented yet.") # Uncommented
             # Example structure (replace with actual call):
             # try:
             #     response = await openai_async_client.chat.completions.create(
             #         model=model_to_use,
             #         messages=eval_messages,
             #         temperature=0.3,
             #         stream=False
             #     )
             #     llm_response_content = response.choices[0].message.content or ""
             # except Exception as e:
             #     logger.error(f"OpenAI API error during evaluation for {entry_id}: {e}") # Uncommented
             #     raise HTTPException(status_code=502, detail=f"OpenAI API error: {e}")
             llm_response_content = "OpenAI evaluation not fully implemented yet." # Placeholder
        
        else:
             logger.error(f"Unknown backend '{backend}' selected for evaluation.") # Uncommented
             raise HTTPException(status_code=501, detail=f"Evaluation not supported for backend: {backend}")
        
        logger.debug(f"LLM Raw Response for evaluation of {entry_id}:\\n{llm_response_content}") # Uncommented
        # --- End of Original LLM Call Block ---

    except Exception as e:
        # This block catches errors during the LLM call or setup
        logger.error(f"LLM call failed during evaluation for {entry_id}: {e}", exc_info=True) # Uncommented
        raise HTTPException(status_code=500, detail=f"LLM call failed during evaluation: {e}")

    # 4. Parse the response - Revised Strategy
    scores = {}
    notes = {}
    parsing_errors = []
    parsed_criteria = set()
    
    # Split the response into blocks based on the separator
    response_blocks = llm_response_content.split("\n---\n")
    
    for block in response_blocks:
        if not block.strip():
            continue # Skip empty blocks
            
        criterion_name_raw = None
        score_str = None
        note_str = None

        # Use simpler regex/searches within each block
        crit_match = re.search(r"Criterion:\s*(.*?)\n", block, re.IGNORECASE)
        if crit_match:
            criterion_name_raw = crit_match.group(1).strip()
        else:
            parsing_errors.append(f"Criterion Missing: Could not find 'Criterion:' line in block: {block[:50]}...")
            continue # Cannot proceed without criterion

        score_match = re.search(r"Score:\s*([-+]?\d*\.?\d+)", block, re.IGNORECASE)
        if score_match:
            score_str = score_match.group(1)
        # else: score is optional, do nothing

        # Find Notes: and capture everything after it until end of block
        notes_match = re.search(r"Notes:\s*(.*)", block, re.IGNORECASE | re.DOTALL)
        if notes_match:
            note_str = notes_match.group(1).strip()
        # else: notes are optional, do nothing
            
        # --- Process the extracted parts (similar to before) --- 
        matched_criterion = None
        if criterion_name_raw:
            for req_crit in criteria:
                if req_crit.lower() == criterion_name_raw.lower():
                    matched_criterion = req_crit
                    break

        if not matched_criterion:
            parsing_errors.append(f"Criterion Mismatch: Parsed '{criterion_name_raw}' but expected one of {criteria}.")
            continue

        if matched_criterion in parsed_criteria:
            parsing_errors.append(f"Duplicate Criterion: '{matched_criterion}' found more than once.")
            continue
        parsed_criteria.add(matched_criterion)

        # Parse Score
        if score_str:
            try:
                parsed_score = float(score_str)
                scores[matched_criterion] = max(0.0, min(1.0, parsed_score))
            except (ValueError, TypeError):
                parsing_errors.append(f"Score Parse Error: Could not parse '{score_str}' as float for '{matched_criterion}'.")
                scores[matched_criterion] = None # Assign None on error
        else:
            parsing_errors.append(f"Score Missing: Score field was empty or missing for '{matched_criterion}'.")
            scores[matched_criterion] = None # Assign None if missing

        # Parse Notes
        if note_str is not None: # Check explicitly for None, as empty string is valid
            notes[matched_criterion] = note_str
        else:
            parsing_errors.append(f"Notes Missing: Notes field was empty or missing for '{matched_criterion}'.")
            notes[matched_criterion] = None # Assign None if missing

    # Check for any requested criteria that were *not* found/parsed
    missing_criteria = set(criteria) - parsed_criteria
    for crit in missing_criteria:
        parsing_errors.append(f"Criterion Missing: Requested '{crit}' not parsed from LLM response.")
        if crit not in scores: scores[crit] = None
        if crit not in notes: notes[crit] = None

    if parsing_errors:
        logger.warning(f"Parsing issues encountered during evaluation of {entry_id}:\n" + "\n".join([f"  - {e}" for e in parsing_errors]))
        # Decide if parsing errors should halt processing or just result in None values
        # Current logic proceeds with None values

    # 5. Format output (with error handling added previously)
    try:
        # Ensure all expected keys exist, even if they are None (Pydantic will validate types)
        final_scores = {c: scores.get(c) for c in criteria}
        final_notes = {c: notes.get(c) for c in criteria}
        eval_response = MythEvalResponse(scores=final_scores, notes=final_notes)
        return eval_response
    except Exception as pydantic_error:
        logger.error(f"Pydantic validation error during evaluation response creation for {entry_id}: {pydantic_error}")
        logger.error(f"Data passed: scores={scores}, notes={notes}")
        raise pydantic_error 

# --- Helper function placeholders for testing ---
def create_branch_entry(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Placeholder for creating a new branch entry."""
    logger.debug(f"PLACEHOLDER: create_branch_entry called with payload: {payload}") # Uncommented
    # Simulate behavior needed for tests (specifically stub_services)
    branch_id = f"placeholder-branch-{uuid.uuid4().hex[:10]}"
    content = payload.get("seed_prompt", "Placeholder content")
    # We might need to interact with SYMBOL_INDEX here if tests rely on it post-monkeypatch
    return {"branch_id": branch_id, "content": content}

def retrieve_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    """Placeholder for retrieving an entry."""
    logger.debug(f"PLACEHOLDER: retrieve_entry called for entry_id: {entry_id}") # Uncommented
    # Return a structure similar to what evaluate_myth expects
    # Check SYMBOL_INDEX if tests rely on the monkeypatch adding to it
    if entry_id in SYMBOL_INDEX:
         logger.debug(f"PLACEHOLDER: Found entry {entry_id} in SYMBOL_INDEX from monkeypatch?") # Uncommented
         # Ensure it has 'narrative' key expected by evaluate_myth
         entry = SYMBOL_INDEX[entry_id]
         if "content" in entry and "narrative" not in entry:
             entry["narrative"] = entry["content"]
         return entry
    elif entry_id == "test-branch-id": # From test fixture
         return {"entry_id": entry_id, "narrative": "Placeholder narrative for test-branch-id"}
    return None

def call_llm_for_evaluation(narrative: str, criteria: List[str]) -> Dict:
    """Placeholder for calling an LLM for evaluation."""
    logger.debug(f"PLACEHOLDER: call_llm_for_evaluation called with criteria: {criteria}") # Uncommented
    # Return a structure matching MythEvalResponse
    scores = {c: round(random.uniform(0.5, 0.9), 2) for c in criteria}
    notes = {c: f"Placeholder evaluation notes for {c}." for c in criteria}
    return {"scores": scores, "notes": notes}
# --- End Placeholder definitions ---

if __name__ == "__main__":
    import uvicorn
    # Recommend running on a specific port, e.g., 8002, if 8000 is busy
    default_port = int(os.getenv("VANTA_PORT", 8002)) 
    # Run with reload for development: python -m uvicorn vanta_router_and_lora:app --reload --port 8002
    uvicorn.run(app, host="0.0.0.0", port=default_port)