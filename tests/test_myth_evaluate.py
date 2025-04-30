# tests/test_myth_evaluate.py
import pytest
import sys
import os
# Remove httpx import, add requests and mock
# import httpx
import requests 
from unittest.mock import MagicMock, patch, AsyncMock
from urllib.parse import urlparse
from io import BytesIO
from fastapi.testclient import TestClient
from typing import Any
import logging 
import ollama # Import ollama for patching
import re # Need re for checking prompt content
# Remove unused typing import
# from typing import Any

# --- Add parent directory to sys.path ---
# This allows importing from vanta_router_and_lora.py in the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
# ----------------------------------------

# Import app AND the actual route handler function for dependency override
from vanta_router_and_lora import app, branch_myth 

# --- Remove MODULE-LEVEL logger mock ---
# mock_logger = logging.getLogger("vanta_test_module_mock")
# mock_logger.setLevel(logging.CRITICAL + 1) # Effectively disable it unless needed
# -----------------------------------------------------------------------

# --- Global Test Variables ---
# Shared client for making requests to the FastAPI app during tests
client = TestClient(app)

# --- Fixtures ---
@pytest.fixture(autouse=True)
def stub_services(monkeypatch):
    """
    Stub external dependencies using monkeypatch, focusing on underlying calls.
    """
    # --- Define Fake Functions --- 
    # No longer need fake_branch_myth
    # async def fake_branch_myth(req: Any): ...

    async def fake_extract_shorthand(narrative: str, extraction_model: str, ollama_client: Any):
        return {"T1_CUE": "mock_cue", "T2_MAP": "mock_map", "T3_EVAL": "mock_eval", "T4_PLAN": "mock_plan"}

    # We will mock retrieve_entry inside the tests now
    # def fake_retrieve_entry(entry_id): ...
            
    async def fake_call_llm_for_evaluation(narrative: str, criteria: list):
        scores = {c: 0.75 for c in criteria}
        notes = {c: f"Mock evaluation notes for {c}." for c in criteria}
        return {"scores": scores, "notes": notes} 
        
    # --- Define Mock for ollama.AsyncClient.chat --- 
    async def mock_ollama_chat(self, model: str, messages: list, options: dict = None, **kwargs):
        is_evaluation_call = False
        user_prompt = ""
        for msg in messages:
            if msg.get('role') == 'user':
                user_prompt = msg.get('content', '').lower()
                # Use the actual phrase from prompts.yaml
                if "analyze the following narrative snippet based on the requested criteria" in user_prompt:
                   is_evaluation_call = True
                   break
        
        response_content = f'Default mock narrative response for {model}'
        if is_evaluation_call:
            requested_criteria = [c.strip() for c in re.findall(r"-\s*(coherence|novelty|depth)", user_prompt, re.IGNORECASE)]
            if not requested_criteria: 
                requested_criteria = ["coherence", "novelty", "depth"]
                
            response_parts = []
            for crit in requested_criteria:
                score = 0.91 
                note = f"Mock notes for {crit}." 
                response_parts.append(f"Criterion: {crit}\nScore: {score:.2f}\nNotes: {note}")
            response_content = "\n---\n".join(response_parts) 
            
        # Return the structured response mimicking Ollama output
        return {
            'model': model,
            'created_at': 'mock_time',
            'message': {
                'role': 'assistant',
                'content': response_content
            },
            'done': True,
            'total_duration': 12345,
            'load_duration': 123,
            'prompt_eval_count': 10,
            'prompt_eval_duration': 456,
            'eval_count': 20,
            'eval_duration': 789
        }

    # --- Apply Mocks --- 
    # Remove dependency override
    # app.dependency_overrides[branch_myth] = fake_branch_myth
    
    # Patch the underlying ollama client method
    monkeypatch.setattr("ollama.AsyncClient.chat", mock_ollama_chat)
    
    # Patch other functions needed by real routes (if not calling mocks directly)
    monkeypatch.setattr(
        "vanta_router_and_lora.extract_thought_hierarchy_shorthand",
        fake_extract_shorthand 
    )
    # Don't patch retrieve_entry here anymore
    # monkeypatch.setattr("vanta_router_and_lora.retrieve_entry", fake_retrieve_entry)
    monkeypatch.setattr("vanta_router_and_lora.call_llm_for_evaluation", fake_call_llm_for_evaluation)

    yield # Allow tests to run
    # No cleanup needed for dependency override
    # app.dependency_overrides = {}


@pytest.fixture
def test_entry():
    """
    Creates a real test myth entry via the branch endpoint (using mocked LLM calls).
    Returns the *actual* generated entry ID.
    """
    response = client.post(
        "/v1/myth/branch", json={"seed_prompt": "Once upon a time in a symbolic realm..."}
    )
    assert response.status_code == 200, f"LLM mock failed: {response.text}"
    data = response.json()
    assert "branch_id" in data, "LLM mock fixture failed: branch_id not in response"
    entry_id = data["branch_id"]
    return entry_id # Return the real ID

# Use patch context manager inside tests needing retrieve_entry mock
def test_evaluate_happy_path(test_entry, monkeypatch):
    """
    Happy path: evaluate an existing narrative with explicit criteria.
    """
    # --- Mock retrieve_entry specifically for this test --- 
    def fake_retrieve_entry_happy(entry_id):
        if entry_id == test_entry: # Use the actual ID from the fixture
             return {"entry_id": entry_id, "narrative": f"Mock narrative for {entry_id}"}
        return None # Should not happen in happy path
    monkeypatch.setattr("vanta_router_and_lora.retrieve_entry", fake_retrieve_entry_happy)
    # ----------------------------------------------------- 
    
    request_body = {
        "entry_id": test_entry,
        "criteria": ["coherence", "novelty", "depth"]
    }
    response = client.post("/v1/myth/evaluate", json=request_body)
    assert response.status_code == 200
    result = response.json()
    assert "scores" in result
    assert "notes" in result
    for crit in request_body["criteria"]:
        assert crit in result["scores"]
        assert isinstance(result["scores"][crit], float)
        # Check the score value from the refined mock
        assert result["scores"][crit] == 0.91 
        assert crit in result["notes"]
        assert isinstance(result["notes"][crit], str)
        # Check notes content
        assert result["notes"][crit] == f"Mock notes for {crit}."

def test_evaluate_default_criteria(test_entry, monkeypatch):
    """
    Without specifying criteria, defaults should apply.
    """
    # --- Mock retrieve_entry specifically for this test --- 
    def fake_retrieve_entry_default(entry_id):
        if entry_id == test_entry:
             return {"entry_id": entry_id, "narrative": f"Mock narrative for {entry_id}"}
        return None
    monkeypatch.setattr("vanta_router_and_lora.retrieve_entry", fake_retrieve_entry_default)
    # ----------------------------------------------------- 

    request_body = {"entry_id": test_entry}
    response = client.post("/v1/myth/evaluate", json=request_body)
    assert response.status_code == 200
    result = response.json()
    default_criteria = ["coherence", "novelty", "depth"]
    for crit in default_criteria:
        assert crit in result["scores"]
        assert result["scores"][crit] == 0.91
        assert crit in result["notes"]
        assert result["notes"][crit] == f"Mock notes for {crit}."

def test_evaluate_not_found(monkeypatch): # Add monkeypatch here too
    """
    Evaluating a non-existent entry should return 404.
    """
    # --- Mock retrieve_entry specifically for this test --- 
    def fake_retrieve_entry_notfound(entry_id):
        if entry_id == "nonexistent-id": 
            return None # Simulate not found
        pytest.fail(f"fake_retrieve_entry_notfound called with unexpected ID: {entry_id}")
    monkeypatch.setattr("vanta_router_and_lora.retrieve_entry", fake_retrieve_entry_notfound)
    # ----------------------------------------------------- 
    
    request_body = {
        "entry_id": "nonexistent-id", 
        "criteria": ["coherence"]
    }
    response = client.post("/v1/myth/evaluate", json=request_body)
    assert response.status_code == 404, f"Expected 404 Not Found, got {response.status_code}"
    print("404 Not Found validated for non-existent entry.") 