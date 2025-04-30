import requests
import json

# --- Configuration ---
VANTA_MYTH_URL = "http://localhost:8002/v1/myth/branch"

# --- Test Data ---
seed_prompt = "In the first garden of broken stars, a forgotten lantern flickers."
generation_params = {
    "temperature": 0.85, # Slightly different temp for testing
    "max_tokens": 500
}

request_payload = {
    "seed_prompt": seed_prompt,
    "parameters": generation_params
}

# --- Main Test Function ---
def test_myth_branch():
    print("-----------------------------------------------------")
    print("Attempting to call VANTA Myth Branch API Endpoint")
    print(f"URL: {VANTA_MYTH_URL}")
    print(f"Payload: {json.dumps(request_payload, indent=2)}")
    print("Ensure the VANTA FastAPI server is running...")
    print("-----------------------------------------------------\n")

    try:
        response = requests.post(VANTA_MYTH_URL, json=request_payload)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        print(f"Status Code: {response.status_code}")
        print("\nVANTA Myth Branch Response:")
        try:
            response_data = response.json()
            print(json.dumps(response_data, indent=2))
            
            # Optionally print parts of the response
            if response_data.get("narrative"):
                 print("\nNarrative Received:")
                 print(response_data["narrative"][:200] + "...") # Print first 200 chars
            if response_data.get("symbolic_nodes"):
                 print(f"\nSymbols (Placeholder): {response_data['symbolic_nodes']}")
            if response_data.get("model_used"):
                 print(f"\nModel Used: {response_data['model_used']}")
                 
        except json.JSONDecodeError:
            print("Error: Could not decode JSON response.")
            print(f"Raw Response Text: {response.text}")

    except requests.exceptions.ConnectionError as e:
        print(f"\nConnection Error: Could not connect to VANTA server at {VANTA_MYTH_URL}.")
        print("Please ensure the server is running and accessible.")
        print(f"Error details: {e}")
    except requests.exceptions.Timeout as e:
        print(f"\nTimeout Error: The request to VANTA timed out.")
        print(f"Error details: {e}")
    except requests.exceptions.HTTPError as e:
        print(f"\nHTTP Error: {e.response.status_code} {e.response.reason}")
        print(f"Response Body: {e.response.text}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

# --- Run the Test --- 
if __name__ == "__main__":
    # You might need to install requests: pip install requests
    test_myth_branch() 