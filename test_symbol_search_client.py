import requests
import json
import argparse

# Configuration
VANTA_SEARCH_URL = "http://localhost:8002/v1/symbol/search"
TIMEOUT = 30 # Seconds

# Rename function to avoid pytest collection
def _test_symbol_search(query: str, case_sensitive: bool, max_results: int):
    """Calls the VANTA Symbol Search API endpoint."""

    payload = {
        "query": query,
        "case_sensitive": case_sensitive,
        "max_results": max_results
    }

    print("-" * 50)
    print("Attempting to call VANTA Symbol Search API Endpoint")
    print(f"URL: {VANTA_SEARCH_URL}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("Ensure the VANTA FastAPI server is running...")
    print("-" * 50)

    try:
        response = requests.post(VANTA_SEARCH_URL, json=payload, timeout=TIMEOUT)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        print(f"Status Code: {response.status_code}\n")

        response_json = response.json()
        print("VANTA Symbol Search Response (Full JSON):")
        print(json.dumps(response_json, indent=2))
        print("\n" + "-" * 10 + " Highlights " + "-" * 10)
        print(f"Query: {response_json.get('query')}")
        results = response_json.get('results', [])
        print(f"Found {len(results)} results:")
        for i, item in enumerate(results):
            print(f"  Result {i+1}:")
            print(f"    Entry ID: {item.get('entry_id')}")
            print(f"    Timestamp: {item.get('timestamp')}")
            print(f"    Model Used: {item.get('model_used')}")
            print(f"    Symbols: {item.get('symbols')}")
            print(f"    Snippet: {item.get('narrative_snippet')}")
            print("-" * 4)

        print("-" * (20 + len(" Highlights ")))

    except requests.exceptions.ConnectionError as e:
        print(f"\nConnection Error: Could not connect to the VANTA server at {VANTA_SEARCH_URL}.")
        print(f"Please ensure the server is running and accessible. Details: {e}")
    except requests.exceptions.Timeout:
        print(f"\nTimeout Error: The request to {VANTA_SEARCH_URL} timed out after {TIMEOUT} seconds.")
    except requests.exceptions.HTTPError as e:
        print(f"\nHTTP Error: {e.response.status_code} {e.response.reason}")
        try:
            # Try to print the error detail from the response body if available
            error_detail = e.response.json()
            print(f"Response Body: {json.dumps(error_detail, indent=2)}")
        except json.JSONDecodeError:
            print(f"Response Body: {e.response.text}") # Print raw text if not JSON
    except json.JSONDecodeError:
        print("\nJSON Decode Error: Could not decode the response from the server.")
        print(f"Raw Response: {response.text}")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the VANTA Symbol Search API endpoint.")
    parser.add_argument("-q", "--query", required=True, help="The symbol or keyword to search for.")
    parser.add_argument("--case-sensitive", action="store_true", help="Perform a case-sensitive search.")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum number of results to return.")

    args = parser.parse_args()

    # Update function call name
    _test_symbol_search(args.query, args.case_sensitive, args.max_results) 