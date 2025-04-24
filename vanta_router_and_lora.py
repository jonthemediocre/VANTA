# vanta_router_and_lora.py
"""FastAPI router + LoRA templates for VANTA framework.

See README/oreo_theplan.md for detailed usage and ROI discussion.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
import re, asyncio, os
from vllm import LLM, SamplingParams

MODEL_POOL = {
    "deepseek": {
        "path": os.getenv("DEEPSEEK_PATH", "deepseek-ai/deepseek-llm-r1-32b-chat"),
        "max_tokens": 8192,
    },
    "llama4": {
        "path": os.getenv("LLAMA4_PATH", "meta-llama/Llama-4-70b-maverick"),
        "max_tokens": 1048576,
    },
    "nemotron": {
        "path": os.getenv("NEMO_PATH", "nvidia/nemotron-3.1-253b"),
        "max_tokens": 8192,
    },
}

llm_instances = {
    name: LLM(cfg["path"], tensor_parallel_size=1)
    for name, cfg in MODEL_POOL.items()
}

VISION_PAT = re.compile(r"<img|https?://.*\.(?:png|jpg|jpeg|webp|bmp|gif)", re.I)
CODE_PAT = re.compile(r"```|class |def |import |#include|<script>")
MATH_PAT = re.compile(r"[∑∫√π]|\\frac|\\begin{aligned}")

class ChatRequest(BaseModel):
    messages: List[dict]
    max_tokens: int = 1024
    temperature: float = 0.7
    include_reasoning: bool = False

class ChatResponse(BaseModel):
    content: str
    model_used: str

class TaskRouter:
    @staticmethod
    def pick_model(prompt: str) -> str:
        if VISION_PAT.search(prompt):
            return "llama4"
        if CODE_PAT.search(prompt) or MATH_PAT.search(prompt):
            return "nemotron"
        return "deepseek"

router = TaskRouter()
app = FastAPI(title="VANTA Router", version="0.1.0")

@app.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    raw_prompt = "\n".join([m["content"] for m in req.messages])
    model_key = router.pick_model(raw_prompt)
    llm = llm_instances[model_key]

    system_header = "[(SceneTrigger::START)]\n"
    if req.include_reasoning:
        system_header += "Please think step-by-step inside <think> tags. End reasoning with </think> before final answer.\n"
    prompt = system_header + raw_prompt

    sampling = SamplingParams(max_tokens=req.max_tokens, temperature=req.temperature)
    output = await asyncio.get_event_loop().run_in_executor(
        None, lambda: llm.generate(prompt, sampling_params=sampling)
    )
    text = output[0].outputs[0].text.strip()
    return ChatResponse(content=text, model_used=model_key)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)