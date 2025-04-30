# vanta_seed/external/fact_verifier.py
import os
import requests
import logging

class FactVerifier:
    """Verifies factual claims using the WolframAlpha API."""
    def __init__(self, app_id=None):
        # Prioritize passed app_id, then env var, then None
        self.app_id = app_id or os.getenv("WOLFRAM_APP_ID")
        if not self.app_id:
            logging.warning("WOLFRAM_APP_ID not found in environment or arguments. Fact verification disabled.")
        else:
            logging.info("FactVerifier initialized with WolframAlpha App ID.")

    def verify(self, claim: str) -> bool:
        """Checks a claim against WolframAlpha. Returns True if WA understands the query, False otherwise or on error."""
        if not self.app_id:
            logging.debug("Fact verification skipped: No WolframAlpha App ID configured.")
            return True # Default to True if verification is disabled
            
        if not claim or not isinstance(claim, str) or len(claim.strip()) == 0:
            logging.debug("Fact verification skipped: Invalid or empty claim provided.")
            return True # Cannot verify empty claim, assume okay
            
        url = "http://api.wolframalpha.com/v2/query"
        # Parameters for a simple query check
        params = {
            "input": claim,
            "appid": self.app_id,
            "output": "JSON",
            "format": "plaintext", # Get simpler text results
            "scantimeout": "3", # Short timeout
            "podstate": "Step-by-step solution", # Example of controlling pods
            "includepodid": "Result" # Focus on the primary result pod
        }
        
        logging.info(f"Verifying claim with WolframAlpha: '{claim[:100]}...'")
        try:
            res = requests.get(url, params=params, timeout=5) # 5 second timeout
            res.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            data = res.json()
            
            # Check if the query was successful and WolframAlpha understood it
            query_result = data.get('queryresult', {})
            if query_result.get('success') and query_result.get('numpods', 0) > 0:
                 # Check for specific pods like 'Result' or if there are any pods at all
                 pods = query_result.get('pods', [])
                 if pods:
                     logging.info(f"WolframAlpha verification successful for: '{claim[:100]}...'")
                     return True
                 else:
                     logging.warning(f"WolframAlpha success=true but no pods returned for: '{claim[:100]}...'")
                     return False # Technically understood, but no useful result returned
            else:
                 error_info = query_result.get('error')
                 tips = query_result.get('tips')
                 did_you_means = query_result.get('didyoumeans')
                 log_extra = f" Error: {error_info}, Tips: {tips}, DidYouMean: {did_you_means}"
                 logging.warning(f"WolframAlpha verification failed or query not understood for: '{claim[:100]}...'.{log_extra}")
                 return False # Query failed or was not understood

        except requests.exceptions.Timeout:
            logging.error(f"WolframAlpha request timed out for claim: '{claim[:100]}...'")
            return False
        except requests.exceptions.RequestException as e:
            logging.error(f"WolframAlpha request failed for claim '{claim[:100]}...': {e}")
            return False
        except Exception as e:
            # Catch JSONDecodeError or other unexpected errors
            logging.error(f"Error during WolframAlpha verification for claim '{claim[:100]}...': {e}", exc_info=True)
            return False

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Ensure you set WOLFRAM_APP_ID environment variable for this to work
    verifier = FactVerifier()

    print("\n--- Testing Fact Verification --- ")
    claim1 = "What is the capital of France?"
    is_valid1 = verifier.verify(claim1)
    print(f"Claim: '{claim1}' -> Verified: {is_valid1}")

    claim2 = "2 + 2 = 5"
    is_valid2 = verifier.verify(claim2) # WA will likely understand this and potentially refute it
    print(f"Claim: '{claim2}' -> Verified: {is_valid2}")

    claim3 = "sdlkfjsdlkfjsdlfkj"
    is_valid3 = verifier.verify(claim3)
    print(f"Claim: '{claim3}' -> Verified: {is_valid3}")
    
    claim4 = ""
    is_valid4 = verifier.verify(claim4)
    print(f"Claim: '{claim4}' -> Verified: {is_valid4}") 