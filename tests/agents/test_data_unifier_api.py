import pytest
from fastapi.testclient import TestClient
import logging

# Import the FastAPI app instance
# Assuming web_server.py is structured to allow importing 'app'
# This might require adjustments in web_server.py if it runs uvicorn directly under if __name__ == '__main__'
# A common pattern is to have a create_app() function.
# For now, we assume direct import works for testing.
from vanta_seed.web_server import app

# Disable noisy logging during tests if desired
# logging.disable(logging.CRITICAL)

@pytest.fixture(scope="module")
def client() -> TestClient:
    """Create a TestClient instance for the FastAPI app."""
    # We might need to handle agent registration differently for tests,
    # perhaps by mocking the registry or running the startup event logic.
    # For now, assume the app startup within TestClient handles it.
    with TestClient(app) as c:
        yield c

# --- Test Cases --- 

def test_health_check(client: TestClient):
    """Test the /health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_ingest_record_success(client: TestClient):
    """Test successful ingestion via /ingest endpoint."""
    test_payload = {
        "data": {"name": "Test Record", "value": 123},
        "source": "test_suite",
        "record_id": "test-001"
    }
    response = client.post("/v1/agents/data-unifier/ingest", json=test_payload)
    assert response.status_code == 202 # Check for Accepted status
    response_data = response.json()
    assert "message" in response_data
    assert response_data["message"] == "Record accepted for processing."
    assert "entity_id" in response_data # Check if placeholder ID is returned
    # Example: assert response_data["entity_id"].startswith("unified_")

def test_ingest_record_missing_data(client: TestClient):
    """Test ingestion failure when 'data' field is missing."""
    test_payload = {
        # Missing 'data'
        "source": "test_suite_invalid",
        "record_id": "test-invalid-001"
    }
    response = client.post("/v1/agents/data-unifier/ingest", json=test_payload)
    # FastAPI/Pydantic usually returns 422 for validation errors
    assert response.status_code == 422 
    # Or check for 400 if the agent raises ValueError before Pydantic catches it
    # assert response.status_code == 400
    # assert "detail" in response.json()

def test_get_entity_not_found(client: TestClient):
    """Test retrieving a non-existent entity."""
    response = client.get("/v1/agents/data-unifier/entity/non-existent-id-12345")
    assert response.status_code == 404
    assert "detail" in response.json()
    assert "not found" in response.json()["detail"]

# TODO: Add test_get_entity_success
# This test is slightly more complex because the agent's data_store is in-memory
# and resets with the TestClient. Options:
# 1. Mock the `get_data_unifier_dependency` to return an agent with pre-populated data.
# 2. Perform an /ingest first within the test, then retrieve the generated ID.
# 3. Modify the agent/registry for easier test data injection.
# Option 2 is often the simplest for basic integration testing:
def test_get_entity_success_after_ingest(client: TestClient):
    """Test retrieving an entity after ingesting it."""
    ingest_payload = {
        "data": {"name": "Retrieve Me", "value": 999},
        "source": "test_retrieve",
        "record_id": "retrieve-001"
    }
    ingest_response = client.post("/v1/agents/data-unifier/ingest", json=ingest_payload)
    assert ingest_response.status_code == 202
    entity_id = ingest_response.json().get("entity_id")
    assert entity_id is not None

    # Now retrieve the entity
    get_response = client.get(f"/v1/agents/data-unifier/entity/{entity_id}")
    assert get_response.status_code == 200
    entity_data = get_response.json()
    assert entity_data["entity_id"] == entity_id
    assert entity_data["unified_data"] == ingest_payload["data"] # Check if data matches (based on placeholder logic)
    assert ingest_payload["source"] in entity_data["sources"] 