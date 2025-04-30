import requests
import json
import argparse

# Configuration
VANTA_DRIFT_URL = "http://localhost:8002/v1/myth/drift"
TIMEOUT = 60 # Increased timeout slightly for potentially longer drift calls

# Rename function to avoid pytest collection
def _test_myth_drift(source_entry_id: str, instruction: str, temperature: float, max_tokens: int):
    """Calls the VANTA Myth Drift API endpoint with lineage tracking structure."""

    # Construct the payload according to MythDriftRequest model
    payload = {
        "source_entry_id": source_entry_id,
        "parameters": {
            "drift_instruction": instruction,
            "temperature": temperature,
            "max_tokens": max_tokens
            # Add other parameters like top_p, seed if needed
        }
    }

    print("-" * 50)
    print("Attempting to call VANTA Myth Drift API Endpoint")
    print(f"URL: {VANTA_DRIFT_URL}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("Ensure the VANTA FastAPI server is running...")
    print("-" * 50)

    try:
        response = requests.post(VANTA_DRIFT_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        print(f"Status Code: {response.status_code}\n")

        response_json = response.json()
        print("VANTA Myth Drift Response (Full JSON):")
        print(json.dumps(response_json, indent=2))

        # --- Highlights --- 
        print("\n" + "-" * 10 + " Highlights " + "-" * 10)
        print("Drifted Narrative:")
        print(response_json.get('drifted_narrative', 'N/A'))
        print("\nModel Used:", response_json.get('model_used', 'N/A'))
        print("Symbols:", response_json.get('symbolic_nodes', []))
        print("Drift Instruction Used:", response_json.get('drift_instruction_used', 'N/A'))
        print("Original Branch ID:", response_json.get('original_branch_id', 'N/A'))
        # We might want to add lineage info display here later if it gets added to the response model
        print("-" * (20 + len(" Highlights ")))

    except requests.exceptions.ConnectionError as e:
        print(f"\nConnection Error: Could not connect to the VANTA server at {VANTA_DRIFT_URL}.")
        print(f"Please ensure the server is running and accessible. Details: {e}")
    except requests.exceptions.Timeout:
        print(f"\nTimeout Error: The request to {VANTA_DRIFT_URL} timed out after {TIMEOUT} seconds.")
    except requests.exceptions.HTTPError as e:
        print(f"\nHTTP Error: {e.response.status_code} {e.response.reason}")
        try:
            error_detail = e.response.json()
            print(f"Response Body: {json.dumps(error_detail, indent=2)}")
        except json.JSONDecodeError:
            print(f"Response Body: {e.response.text}")
    except json.JSONDecodeError:
        print("\nJSON Decode Error: Could not decode the response from the server.")
        print(f"Raw Response: {response.text}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the VANTA Myth Drift API endpoint with lineage.")
    parser.add_argument("-sid", "--source-id", required=True, help="The entry_id of the source narrative to drift from.")
    parser.add_argument("-i", "--instruction", required=True, help="The instruction for how the narrative should drift.")
    parser.add_argument("--temp", type=float, default=0.9, help="Generation temperature.")
    parser.add_argument("--max-tokens", type=int, default=500, help="Maximum tokens for the drifted narrative.")

    args = parser.parse_args()

    # Update function call name
    _test_myth_drift(args.source_id, args.instruction, args.temp, args.max_tokens) 