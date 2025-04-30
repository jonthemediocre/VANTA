import asyncio
import os
from openai import AsyncOpenAI, OpenAIError
import yaml
from typing import Any

# --- Load Configuration (Optional but good practice for defaults) ---
CONFIG_PATH = "config.yaml"
config = {}
try:
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    print(f"WARNING: Client could not find {CONFIG_PATH}. Using hardcoded defaults.")
except yaml.YAMLError as e:
    print(f"WARNING: Client error parsing {CONFIG_PATH}: {e}. Using hardcoded defaults.")

# Helper function to get config value from client side (optional)
def get_config(key_path: str, default: Any = None):
    keys = key_path.split('.')
    value = config
    try:
        for key in keys:
            value = value[key]
        # Ensure we don't return None if default is provided
        return value if value is not None else default 
    except (KeyError, TypeError):
        return default
# --- END ADDED SECTION ---

async def main():
    # --- Configure the connection to your local VANTA API ---
    vanta_base_url = "http://localhost:8002/v1" 
    # The openai library requires an API key, even if your endpoint doesn't.
    # Use a dummy key or read from an env var if you prefer.
    vanta_api_key = os.getenv("VANTA_API_KEY", "DUMMY_KEY_FOR_OPENAI_LIB") 

    print(f"Configuring OpenAI client to use VANTA base URL: {vanta_base_url}")

    try:
        # Initialize the AsyncOpenAI client, pointing it to your VANTA server
        client = AsyncOpenAI(
            base_url=vanta_base_url,
            api_key=vanta_api_key,
        )
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        print("Ensure the openai library is installed (`pip install openai`)")
        return
    
    print("OpenAI client configured for VANTA.\n")

    # --- Test 1: Code Request (targeting Python LoRA fallback) ---
    model_to_request = "deepseek-llm:latest" # Client still requests a base model
    print(f"Sending PYTHON CODE request to VANTA (expecting LoRA routing attempt) using model: '{model_to_request}'")
    prompt_messages = [
        {"role": "system", "content": "You are an expert Python coding assistant."},
        {"role": "user", "content": "Write a Python function using recursion to calculate the nth Fibonacci number."}
    ]
    print(f"Messages: {prompt_messages}\n")

    try:
        # Non-streaming request
        response = await client.chat.completions.create(
            model=model_to_request, # Router should override this based on content
            messages=prompt_messages,
            stream=False
        )
        print("VANTA Response (non-streaming):")
        print(response.model_dump_json(indent=2))

        if response.choices:
            print("\nAssistant's Message:")
            print(response.choices[0].message.content)
        else:
            print("\nNo choices found in response.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")

    # --- (Optional) Add Test 2: Myth Request (targeting Myth LoRA fallback) ---

# --- Run the example --- 
if __name__ == "__main__":
    # Make sure your VANTA server (uvicorn vanta_router_and_lora:app...) is running!
    print("-----------------------------------------------------")
    print("Attempting to connect to VANTA API via OpenAI Library")
    print("Ensure the VANTA FastAPI server is running:")
    print("  python -m uvicorn vanta_router_and_lora:app --reload --port 8002")
    print("-----------------------------------------------------")

    asyncio.run(main()) 