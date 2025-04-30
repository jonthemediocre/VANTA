import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion # Or AzureOpenAIChatCompletion if using that pattern
import asyncio
import os # Added to potentially check env var

async def main():
    # --- Kernel Setup ---
    kernel = sk.Kernel()

    # --- Configure the connection to your local VANTA API ---
    vanta_endpoint = "http://localhost:8002/v1" 
    # Provide a dummy key - SK connector might require it, but VANTA doesn't use it
    # You could also read this from an env var like VANTA_API_KEY if preferred
    vanta_api_key = os.getenv("VANTA_API_KEY", "YOUR_VANTA_API_KEY_IF_NEEDED_ELSE_DUMMY") 
    # This can be a specific model VANTA knows, or a generic name your router handles
    vanta_model_id = "routed-model" 

    print(f"Configuring Semantic Kernel to use VANTA endpoint: {vanta_endpoint}")

    # Add the chat service using the OpenAI connector, but point it to VANTA
    # Use OpenAIChatCompletion connector even for a local endpoint
    try:
        kernel.add_chat_service(
            service_id="vanta_chat", # An identifier for this service within the kernel
            service=OpenAIChatCompletion(
                ai_model_id=vanta_model_id,
                api_key=vanta_api_key,
                endpoint=vanta_endpoint # <-- This is the crucial parameter
                # org_id=None # Usually not needed for local endpoint
            )
        )
    except Exception as e:
        print(f"Error configuring Semantic Kernel service: {e}")
        print("Ensure semantic-kernel library is installed (`pip install semantic-kernel`)")
        print("Also check if the VANTA server is running and accessible.")
        return # Exit if configuration fails
    
    print("Kernel configured with VANTA chat service.")

    # --- Example Usage (Optional) ---
    prompt = "What is the capital of France? Explain briefly."
    print(f"\nInvoking kernel for prompt: '{prompt}'")

    try:
        # Create a semantic function or invoke directly
        # Using invoke_prompt for simplicity here
        result = await kernel.invoke_prompt_async(
            prompt, 
            service_id="vanta_chat" # Use the service ID defined above
        )
        
        print(f"\nVANTA Response:\n{result}")

    except Exception as e:
        print(f"\nAn error occurred during kernel invocation: {e}")
        print("Ensure the VANTA server is running and accessible at the specified endpoint.")
        # Add more specific error handling if needed

# --- Run the example ---
if __name__ == "__main__":
    # Make sure your VANTA server (uvicorn vanta_router_and_lora:app...) is running!
    print("-----------------------------------------------------")
    print("Attempting to connect to VANTA API via Semantic Kernel")
    print("Ensure the VANTA FastAPI server is running:")
    print("  python -m uvicorn vanta_router_and_lora:app --reload --port 8002")
    print("-----------------------------------------------------")
    
    asyncio.run(main()) 