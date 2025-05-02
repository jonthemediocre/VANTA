from .base_agent import BaseAgent
import requests
import logging
import time
import uuid
from typing import Dict, Any
from vanta_seed.core.data_models import AgentMessage

logger = logging.getLogger(__name__)

class ProxyDeepSeekAgent(BaseAgent):
    """
    Proxy agent that forwards chat completion requests to a local DeepSeek API.
    """

    def __init__(self, name: str, initial_state: Dict[str, Any], settings: Dict[str, Any]):
        """Initialize the proxy agent, storing settings."""
        super().__init__(name, initial_state) # Call BaseAgent init
        self.settings = settings # Store the settings
        logger.info(f"ProxyDeepSeekAgent '{self.name}' initialized with settings: {self.settings}")

    async def perform_task(self, task_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles chat_completion tasks by proxying to DeepSeek.
        
        Args:
            task_data (Dict[str, Any]): The original task data received by the agent.
            current_state (Dict[str, Any]): The current internal state of the agent.

        Returns:
            Dict[str, Any]: A dictionary containing the response or an error.
        """
        # Get relevant data from task_data["payload"]
        payload_data = task_data.get("payload", {})
        messages = payload_data.get("messages", [])
        
        # --- MODIFIED: Get URL and Model from Settings --- 
        # Read from settings passed during initialization (from blueprint)
        default_api_url = "http://127.0.0.1:1337/v1/chat/completions" # Default fallback
        default_model_name = "deepseek-coder" # Default fallback
        
        external_api_url = self.settings.get("api_url", default_api_url)
        # --- Use the DEFAULT model specified in agent settings, NOT the requested_model from payload --- 
        target_model_for_ollama = self.settings.get("default_model", default_model_name)
        # ------------------------------------------------------------------------------------------
        # # Use the model requested in the payload, or fall back to agent default setting, or hardcoded default
        # requested_model = payload_data.get(
        #     "requested_model", 
        #     self.settings.get("default_model", default_model_name)
        # )
        # --- END MODIFIED ---

        # Check intent (should be in task_data directly)
        intent = task_data.get("intent")
        # --- Use the actual target model in the log --- 
        logger.info(f"ProxyDeepSeekAgent '{self.name}' received task with intent: {intent} for model '{target_model_for_ollama}'") # Changed log
        # --------------------------------------------
        if intent != "chat_completion":
            logger.warning(f"Unsupported intent '{intent}' for ProxyDeepSeekAgent.")
            return {"status": "error", "error": f"Unsupported intent '{intent}' for ProxyDeepSeekAgent"}

        if not messages:
             logger.warning("No messages found in payload for chat_completion intent.")
             return {"status": "error", "error": "No messages provided for chat completion"}

        headers = {
            "Content-Type": "application/json",
            # TODO: Add Authorization header from settings if needed
            # api_key = self.settings.get("api_key")
            # if api_key:
            #     headers["Authorization"] = f"Bearer {api_key}"
        }

        # Construct payload for the external API
        external_payload = {
            "model": target_model_for_ollama, # <<< Use the agent's default model setting
            "messages": messages,
            "temperature": self.settings.get("temperature", 0.7),
            "stream": False
            # TODO: Pass other parameters from settings or task_data if desired
        }

        # --- Use the actual target model in the log --- 
        logger.debug(f"Proxying request to DeepSeek endpoint: {external_api_url}") # Changed log
        logger.debug(f"Payload for DeepSeek: {external_payload}") # Changed log
        # --------------------------------------------

        try:
            # Using httpx for async request (ensure httpx is installed: pip install httpx)
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(external_api_url, json=external_payload, headers=headers, timeout=30.0)

            logger.debug(f"Received response from DeepSeek. Status: {response.status_code}")
            response.raise_for_status()

            deepseek_result = response.json()
            logger.debug(f"DeepSeek JSON response: {deepseek_result}")

            # --- Extract the response and format it like OpenAI --- 
            # This part mimics the structure EchoAgent produced, which worked with run.py
            first_choice = deepseek_result.get("choices", [{}])[0]
            message_content = first_choice.get("message", {}).get("content", "")
            
            # Construct the OpenAI-compatible output structure expected by run.py
            output_structure = {
                "id": deepseek_result.get("id", f"chatcmpl-ds-{uuid.uuid4().hex}"),
                "object": "chat.completion",
                "created": deepseek_result.get("created", int(time.time())),
                "model": target_model_for_ollama,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": message_content},
                        "finish_reason": first_choice.get("finish_reason", "stop"),
                    }
                ],
                "usage": deepseek_result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
            }
            # ----------------------------------------------------

            # Return the structured output under the 'output' key for run.py
            return {
                "status": "success",
                "output": output_structure
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API call failed with status {e.response.status_code}: {e.response.text}", exc_info=True)
            return {"status": "error", "error": f"DeepSeek API error ({e.response.status_code})", "details": e.response.text}
        except httpx.RequestError as e:
             logger.error(f"Error connecting to DeepSeek API: {e}", exc_info=True)
             return {"status": "error", "error": f"Could not connect to DeepSeek: {e}"}
        except Exception as e:
            logger.error(f"Exception during DeepSeek call: {e}", exc_info=True)
            return {"status": "error", "error": f"Exception during DeepSeek proxy: {str(e)}"}

    async def receive_message(self, message: AgentMessage, current_state: Dict[str, Any]):
        logger.warning(f"ProxyDeepSeekAgent does not handle direct messages. Message received: {message}")
        pass

    async def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handles state updates and calls perform_task."""
        # This is the standard execute logic from BaseAgent, adapted slightly
        logger.debug(f"ProxyDeepSeekAgent '{self.name}' executing task: {task_data.get('intent')}")
        
        # --- Minimal State Update --- 
        # BaseAgent handles more complex state updates (position, role, energy etc.)
        # For a simple proxy, we might just update last_task_time or similar.
        self.state['last_task_intent'] = task_data.get('intent')
        self.state['last_task_timestamp'] = time.time()
        current_state_dict = self.current_state
        # -------------------------
        
        # --- Call Core Logic --- 
        result = await self.perform_task(task_data, current_state_dict)
        # ---------------------

        logger.debug(f"ProxyDeepSeekAgent '{self.name}' execution finished. Result status: {result.get('status')}")
        return result

# Ensure httpx is installed: pip install httpx 