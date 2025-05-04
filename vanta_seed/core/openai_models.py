from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Union
import time

# Based on OpenAI API Reference (Simplified)

# --- Request Models ---

class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: Optional[str] = None
    # Add tool_calls, tool_call_id if needed later

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    # Add other common parameters like top_p, frequency_penalty etc. if needed

# --- Response Models ---

class ResponseMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = None
    # Add tool_calls if needed

class Choice(BaseModel):
    index: int = 0
    message: ResponseMessage
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter"]] = "stop"
    # logprobs: Optional[...] = None # Add if needed

class Usage(BaseModel):
    prompt_tokens: Optional[int] = None # We might not easily calculate these
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{int(time.time())}{random.randint(100,999)}") # Simple ID
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str # Should reflect the model used by VANTA proxy
    choices: List[Choice]
    usage: Optional[Usage] = None # Often omitted in simple implementations
    system_fingerprint: Optional[str] = None

# --- Add imports needed for default factories ---
import random 
# --------------------------------------------- 