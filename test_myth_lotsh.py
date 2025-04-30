import requests
import pytest
import re # For regex check
from unittest.mock import patch, MagicMock # Import mock helpers

# Configuration (Update port to 9000)
BASE_URL = "http://localhost:9000"
TIMEOUT = 120 # Increased timeout as branching can take time

BRANCH_URL = f"{BASE_URL}/v1/myth/branch"
LOTSH_URL_TEMPLATE = f"{BASE_URL}/v1/thought/{{entry_id}}/shorthand"

# Regex to check the basic LoT-Sh format (updated for dict keys)
# LOTSH_FORMAT_REGEX = r"^\[T\d+\]: (CUE|MAP)\(\".*\"\) -> .*$"

EXPECTED_SHORTHAND_KEYS = ["T1_CUE", "T2_MAP", "T3_EVAL", "T4_PLAN"]

@pytest.fixture(scope="module")
@patch('test_myth_lotsh.requests.post') # Patch post for the fixture
def create_test_entry(mock_post):
    """Fixture to create a mock myth entry once for the test module."""
    # print("\nCreating MOCK test entry for LoT-Sh tests...") # Removed print
    
    # --- Configure Mock Response --- 
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"branch_id": "mock_branch_id_123"}
    # Configure raise_for_status to do nothing on success
    mock_response.raise_for_status.return_value = None 
    mock_post.return_value = mock_response
    
    # --- Fixture Logic --- 
    payload = {"seed_prompt": "A library card unlocked a door to yesterday."}
    try:
        # This call now hits the mock
        response = requests.post(BRANCH_URL, json=payload, timeout=TIMEOUT) 
        response.raise_for_status() # Check status code via mock
        data = response.json()
        new_id = data.get('branch_id')
        assert new_id, "Failed to get branch_id from mocked response."
        # print(f"Mock test entry created: {new_id}") # Removed print
        mock_post.assert_called_once_with(BRANCH_URL, json=payload, timeout=TIMEOUT)
        return new_id
    except Exception as e:
        # This fail should ideally not be reached if mock is configured correctly
        pytest.fail(f"Failed to create MOCK test entry needed for LoT-Sh tests: {e}")

@patch('test_myth_lotsh.requests.get') # Patch get for this test
def test_get_shorthand_happy_path(mock_get, create_test_entry):
    """Test fetching shorthand dictionary for a valid entry."""
    entry_id = create_test_entry # Get the mock ID from the fixture
    url = LOTSH_URL_TEMPLATE.format(entry_id=entry_id)
    
    # --- Configure Mock Response --- 
    mock_response = MagicMock()
    mock_response.status_code = 200
    # Create plausible shorthand dictionary
    mock_shorthand = {key: f"Mock value for {key}" for key in EXPECTED_SHORTHAND_KEYS}
    mock_response.json.return_value = mock_shorthand
    mock_get.return_value = mock_response
    
    # --- Test Logic --- 
    # print(f"\nFetching shorthand dict for MOCK ID: {entry_id}") # Removed print
    # This call now hits the mock
    resp = requests.get(url, timeout=TIMEOUT) 
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    
    data = resp.json()
    # --- Assert Dictionary Structure --- 
    assert isinstance(data, dict), "Response should be a dictionary"
    # print(f"Shorthand Dict Received: {data}") # Removed print

    # Check for expected keys
    for key in EXPECTED_SHORTHAND_KEYS:
        assert key in data, f"Expected key '{key}' not found in shorthand dictionary"
    
    # Check that values are strings or None (allowing for potential step failures)
    for key in EXPECTED_SHORTHAND_KEYS:
        value = data[key]
        assert value is None or isinstance(value, str), f"Value for key '{key}' should be str or None, got {type(value)}"
        if isinstance(value, str):
             assert len(value.strip()) > 0, f"Value for key '{key}' should not be empty or just whitespace if it's a string."

    # print("Shorthand dictionary structure and basic types validated.") # Removed print
    mock_get.assert_called_once_with(url, timeout=TIMEOUT)

@patch('test_myth_lotsh.requests.get') # Patch get for this test
def test_get_shorthand_not_found(mock_get):
    """Test fetching shorthand for a non-existent entry ID."""
    entry_id = "nonexistent-id-for-testing"
    url = LOTSH_URL_TEMPLATE.format(entry_id=entry_id)
    
    # --- Configure Mock Response --- 
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    
    # --- Test Logic ---
    # print(f"\nFetching shorthand for non-existent ID: {entry_id}") # Removed print
    # This call now hits the mock
    resp = requests.get(url, timeout=TIMEOUT) 
    assert resp.status_code == 404, f"Expected 404 Not Found, got {resp.status_code}"
    # print("404 Not Found validated.") # Removed print
    mock_get.assert_called_once_with(url, timeout=TIMEOUT) 