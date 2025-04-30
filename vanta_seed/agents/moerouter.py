# vanta_seed/agents/moerouter.py
import logging
import random
import os
import httpx # <<< Import httpx
import json # <<< Add json import for tool arguments
import requests # <<< Add requests for downloading image URL
import uuid # <<< Add uuid for filenames
from pathlib import Path # <<< Add Path for saving images
from openai import OpenAI, APIError # Import OpenAI and specific errors if needed
import constants # <<< Add constants import

# Load environment variables (ensure dotenv is loaded in your main script, e.g., run.py)
# from dotenv import load_dotenv
# load_dotenv() # Typically done once at startup

class MoERouter:
    """Routes prompts to appropriate LLMs and handles tool calls like image generation."""
    def __init__(self, agent_name: str, definition: dict, blueprint: dict, all_agent_definitions: dict, orchestrator_ref=None, **kwargs):
        # --- Extract config from definition --- 
        self.config = definition.get('config', {}) 
        self.agent_name = agent_name # Store agent name if needed
        # -------------------------------------
        self.logger = logging.getLogger(f"Agent.{agent_name}") # Use agent_name in logger
        
        # --- OpenAI Client Initialization ---
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            self.logger.error("OPENAI_API_KEY environment variable not set.")
            raise ValueError("OPENAI_API_KEY must be set.")
            
        try:
            # --- Create custom httpx client to disable SSL verification --- 
            # WARNING: Disabling SSL verification is insecure for production.
            #          Use only if necessary for local dev or specific network issues.
            custom_http_client = httpx.Client(verify=False)
            # ------------------------------------------------------------
            
            # Pass the custom client to OpenAI constructor
            self.openai_client = OpenAI(
                api_key=self.openai_api_key, 
                http_client=custom_http_client # <<< Pass configured client
            )
            self.logger.info("OpenAI client initialized successfully (SSL verification disabled).")
        except Exception as e:
            self.logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
            raise
            
        # --- Model Configuration ---
        # Get model from env, with fallback (Step 6 from plan)
        self.primary_model = os.getenv("OPENAI_MODEL", "gpt-4o") # Default fallback to gpt-4o
        self.logger.info(f"Primary OpenAI model set to: {self.primary_model}")
        
        # --- Image Generation Config --- 
        self.image_model = self.config.get('image_model', 'dall-e-3')
        self.image_size = self.config.get('image_size', '1024x1024')
        self.image_quality = self.config.get('image_quality', 'standard')
        self.image_style = self.config.get('image_style', 'vivid')
        self.save_directory = Path(self.config.get('image_save_directory', './generated_images'))
        self.save_directory.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Images generated via tool calls will be saved to: {self.save_directory.resolve()}")
        # ---------------------------

        # Simplified: Assume only one primary OpenAI LLM for now
        self.available_llms = [
            {
                "name": f"openai_{self.primary_model}", 
                "model_id": self.primary_model,
                "client": self.openai_client,
                "call": self.call_openai_chat # Reference the actual call method
            }
            # TODO: Add logic to load other LLMs (e.g., Ollama) if needed
        ]
        
        self.logger.info(f"MoERouter Initialized. Available LLMs: {[llm['name'] for llm in self.available_llms]}")

    def select(self, prompt: str):
        """Selects an LLM based on the prompt content or routing rules."""
        self.logger.debug(f"Selecting LLM for prompt: {prompt[:50]}...")
        # TODO: Implement actual routing logic
        # Placeholder: always select the first (primary OpenAI) LLM for now
        selected_llm_config = self.available_llms[0] 
        self.logger.info(f"Selected LLM: {selected_llm_config['name']} (Default selection)")
        return selected_llm_config # Return the chosen LLM config/client

    def call_openai_chat(self, prompt: str, model_id: str):
        """Calls the OpenAI Chat Completion API."""
        self.logger.info(f"Calling OpenAI model '{model_id}'...")
        self.logger.debug(f"Prompt (first 100 chars): {prompt[:100]}...")
        
        # Basic message format - assuming a user prompt
        messages = [{"role": "user", "content": prompt}] 
        
        try:
            response = self.openai_client.chat.completions.create(
                model=model_id,
                messages=messages
            )
            # Extract the text content from the response
            # Accessing the message content correctly
            if response.choices and response.choices[0].message:
                content = response.choices[0].message.content
                self.logger.info(f"Received response from {model_id}.")
                self.logger.debug(f"Response content (first 100 chars): {content[:100]}...")
                return content.strip() if content else "[No content received]"
            else:
                 self.logger.warning(f"OpenAI response structure unexpected or empty: {response}")
                 return "[Error: Unexpected response structure]"

        except APIError as e:
            self.logger.error(f"OpenAI API Error calling model {model_id}: {e.status_code} - {e.message}", exc_info=True)
            return f"[Error: OpenAI API Error - {e.message}]"
        except Exception as e:
            self.logger.error(f"Generic error calling OpenAI model {model_id}: {e}", exc_info=True)
            return f"[Error: Could not contact OpenAI - {e}]"

    # --- NEW: Chat Call WITH Image Tool --- 
    def call_chat_with_image_tool(self, prompt: str, model_id: str, task_id: str):
        """Calls Chat Completions API with an image generation tool definition."""
        self.logger.info(f"Task {task_id}: Calling OpenAI model '{model_id}' with image tool...")
        messages = [{"role": "user", "content": prompt}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "Generates an image based on a textual description.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The detailed textual description of the image to generate."
                            },
                            "style": {
                                "type": "string",
                                "enum": ["vivid", "natural"],
                                "description": "The style of the generated image. Defaults to vivid."
                            },
                            "quality": {
                                "type": "string",
                                "enum": ["standard", "hd"],
                                "description": "The quality of the generated image. Defaults to standard."
                            } 
                        },
                        "required": ["prompt"]
                    }
                }
            }
        ]

        try:
            response = self.openai_client.chat.completions.create(
                model=model_id,
                messages=messages,
                tools=tools,
                tool_choice="auto" # Let the model decide whether to use the tool
            )

            response_message = response.choices[0].message

            # Check if the model wants to call the tool
            if response_message.tool_calls:
                self.logger.info(f"Task {task_id}: Model requested tool call: {response_message.tool_calls[0].function.name}")
                tool_call = response_message.tool_calls[0]
                if tool_call.function.name == "generate_image":
                    # --- Execute the Image Generation --- 
                    function_args = json.loads(tool_call.function.arguments)
                    image_prompt = function_args.get("prompt")
                    image_style = function_args.get("style", self.image_style) # Use arg or default
                    image_quality = function_args.get("quality", self.image_quality)
                    
                    if not image_prompt:
                        return {"success": False, "error": "Tool call for generate_image missing required prompt argument.", "task_id": task_id}
                        
                    self.logger.info(f"Task {task_id}: Extracted image prompt from tool call: '{image_prompt[:50]}...'")
                    
                    # Use internal method to generate/save image (copied logic)
                    image_result = self._generate_and_save_image(image_prompt, {
                        "style": image_style,
                        "quality": image_quality,
                        # Use defaults for size/model from MoERouter config
                        "size": self.image_size, 
                        "model": self.image_model
                    }, task_id)
                    
                    # Return the result from the image generation attempt
                    return image_result 
                else:
                     # Should not happen if only one tool is defined
                     self.logger.warning(f"Task {task_id}: Model called unexpected tool: {tool_call.function.name}")
                     return {"success": False, "error": f"Unexpected tool call: {tool_call.function.name}", "task_id": task_id}
            else:
                # Model didn't use the tool, return its text response
                self.logger.info(f"Task {task_id}: Model did not use tool, returning text response.")
                content = response_message.content
                return {"success": True, "result": content.strip() if content else "[No text content received]", "type": "text", "task_id": task_id}

        except APIError as e:
            self.logger.error(f"Task {task_id}: OpenAI API Error calling model {model_id} with tool: {e.status_code} - {e.message}", exc_info=True)
            return {"success": False, "error": f"OpenAI API Error - {e.message}", "task_id": task_id}
        except Exception as e:
            self.logger.error(f"Task {task_id}: Generic error calling OpenAI model {model_id} with tool: {e}", exc_info=True)
            return {"success": False, "error": f"Could not contact OpenAI - {e}", "task_id": task_id}
    # --------------------------------------

    # --- NEW: Internal Image Generation Logic (Adapted from ImageGeneratorAgent) --- 
    def _generate_and_save_image(self, prompt, params, task_id):
        """Generates, downloads, and saves image locally."""
        # Returns: {"success": True/False, ...} including image path or error
        model = params.get('model', self.image_model)
        size = params.get('size', self.image_size)
        quality = params.get('quality', self.image_quality)
        style = params.get('style', self.image_style)
        n = 1

        self.logger.info(f"Task {task_id}: Calling OpenAI Image API via MoERouter. Model: {model}, Size: {size}, Quality: {quality}, Style: {style}")
        try:
            response = self.openai_client.images.generate(
                model=model, prompt=prompt, size=size, quality=quality, style=style, n=n, response_format="url"
            )
            
            if not response.data or not response.data[0].url:
                error_msg = "OpenAI API response did not contain an image URL."
                self.logger.error(f"Task {task_id}: {error_msg}")
                return {"success": False, "error": error_msg, "task_id": task_id}
                
            image_url = response.data[0].url
            self.logger.info(f"Task {task_id}: Received image URL from OpenAI: {image_url}")

            # Download the image
            try:
                with requests.Session() as session:
                    session.verify = False
                    image_response = session.get(image_url, stream=True, timeout=60) # Increased timeout
                    image_response.raise_for_status()
                image_bytes = image_response.content
                self.logger.info(f"Task {task_id}: Successfully downloaded image ({len(image_bytes)} bytes) from URL.")
            except requests.exceptions.RequestException as e:
                error_msg = f"Failed to download image from URL {image_url}: {e}"
                self.logger.error(f"Task {task_id}: {error_msg}")
                return {"success": False, "error": error_msg, "task_id": task_id}
            
            # Save the image
            image_filename = f"tool_generated_{task_id}_{uuid.uuid4().hex[:6]}.png"
            save_path = self.save_directory / image_filename
            try:
                with open(save_path, 'wb') as f:
                    f.write(image_bytes)
                self.logger.info(f"Task {task_id}: Image successfully saved to: {save_path.resolve()}")
                # Return success with path info
                return {"success": True, "image_path": str(save_path.resolve()), "filename": image_filename, "type": "image", "task_id": task_id}
            except Exception as e:
                 self.logger.error(f"Task {task_id}: Error saving image to {save_path}: {e}", exc_info=True)
                 return {"success": False, "error": f"Failed to save image locally: {e}", "task_id": task_id}

        except APIError as e:
            error_msg = f"OpenAI API Error: {e}"
            self.logger.error(f"Task {task_id}: OpenAI API error during image generation: {e}")
            return {"success": False, "error": error_msg, "task_id": task_id}
        except Exception as e:
            error_msg = f"Unexpected API call error: {e}"
            self.logger.error(f"Task {task_id}: Unexpected error calling OpenAI Image API: {e}", exc_info=True)
            return {"success": False, "error": error_msg, "task_id": task_id}
    # -------------------------------------------------------------------------

    async def handle(self, task_data: dict):
        """Handles tasks specifically routed to the MoERouter."""
        self.logger.info(f"Handling task via MoERouter: {task_data.get('intent')}")
        intent = task_data.get('intent')
        payload = task_data.get('payload', {})
        task_id = task_data.get('task_id', 'unknown') # Get task_id for context

        if intent == 'get_primary_model':
             return {"success": True, "model": self.primary_model, "task_id": task_id}
             
        # --- Add handling for generate_text --- 
        elif intent == 'generate_text':
            prompt = payload.get('prompt')
            if not prompt:
                self.logger.error(f"Task {task_id} ({intent}): No prompt provided in payload.")
                return {"success": False, "error": "No prompt provided", "task_id": task_id}
            
            # Select the LLM configuration (currently always selects primary)
            selected_llm_config = self.select(prompt)
            
            if selected_llm_config and 'call' in selected_llm_config and 'model_id' in selected_llm_config:
                self.logger.info(f"Task {task_id} - Using selected LLM: {selected_llm_config['name']} for intent '{intent}'")
                try:
                    # Call the actual LLM function (e.g., call_openai_chat)
                    llm_output = selected_llm_config['call'](prompt, selected_llm_config['model_id'])
                    
                    # Check if the output indicates an error from the call method itself
                    if isinstance(llm_output, str) and llm_output.startswith("[Error:"):
                         self.logger.error(f"Task {task_id} - LLM call failed: {llm_output}")
                         return {"success": False, "error": f"LLM call failed: {llm_output}", "task_id": task_id}
                    else:
                         self.logger.info(f"Task {task_id} - LLM call successful.")
                         return {"success": True, "result": llm_output, "task_id": task_id}
                except Exception as e:
                    self.logger.error(f"Task {task_id} - Exception during LLM call via MoERouter handle: {e}", exc_info=True)
                    return {"success": False, "error": f"Exception during LLM call: {e}", "task_id": task_id}
            else:
                self.logger.error(f"Task {task_id} - MoERouter.select did not return a valid LLM configuration.")
                return {"success": False, "error": "LLM selection failed within MoERouter", "task_id": task_id}
        # -----------------------------------------
        elif intent == constants.GENERATE_IMAGE: # <<< Handle generate_image intent
            # Use the chat endpoint WITH the image tool
            prompt = payload.get('prompt')
            if not prompt:
                return {"success": False, "error": "No prompt provided for image generation", "task_id": task_id}
            
            selected_llm_config = self.select(prompt)
            if selected_llm_config and 'model_id' in selected_llm_config:
                # Call the method that includes the tool definition
                result = self.call_chat_with_image_tool(prompt, selected_llm_config['model_id'], task_id)
                return result # Return the dict from the tool call method
            else:
                 return {"success": False, "error": "LLM selection failed for image generation", "task_id": task_id}
                 
        else:
            self.logger.warning(f"MoERouter received unhandled intent: {intent}")
            return {"success": False, "error": "Unhandled intent for MoERouter", "task_id": task_id} 