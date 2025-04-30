"""
Agent: ImageGenerator
Type: domain/creative
"""
import os
import json
import datetime
import logging
import uuid
import requests
import httpx
from openai import OpenAI, OpenAIError
import constants
from core.base_agent import BaseAgent
from pathlib import Path

# --- Add module-level logger ---
logger = logging.getLogger(__name__)
# -------------------------------

# Logging setup (can likely be removed if basicConfig is set elsewhere)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Inherit from BaseAgent ---
class ImageGeneratorAgent(BaseAgent):
    """Agent that generates images based on prompts using the OpenAI DALL-E 3 API."""
    
    # --- Update __init__ to standard signature --- 
    def __init__(self, agent_name: str, definition: dict, blueprint: dict, **kwargs):
        super().__init__(agent_name, definition, blueprint, **kwargs) # Call correct parent
        # Config, logger, blueprint are now inherited via self
        
        self.default_model = self.config.get('default_model', 'dall-e-3') 
        self.default_size = self.config.get('default_size', '1024x1024')
        self.default_quality = self.config.get('default_quality', 'standard') 
        self.default_style = self.config.get('default_style', 'vivid') 
        self.save_directory = Path(self.config.get('image_save_directory', './generated_images'))
        self.save_directory.mkdir(parents=True, exist_ok=True) # Ensure directory exists
        self.logger.info(f"Images will be saved to: {self.save_directory.resolve()}")

        # --- Initialize OpenAI Client (Similar to MoERouter) --- 
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            self.logger.error("OPENAI_API_KEY environment variable not set.")
            self.client = None # Indicate client is not available
        else:
            try:
                # Use custom httpx client to disable SSL verification
                custom_http_client = httpx.Client(verify=False)
                self.client = OpenAI(
                    api_key=self.api_key,
                    http_client=custom_http_client
                )
                self.logger.info("OpenAI client initialized successfully (SSL verification disabled).")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
                self.client = None # Indicate failure
        # ----------------------------------------------------
        
        # --- Memory Interaction Removed for Simplicity --- 
        # self.memory = None # No direct memory access for now
        # -------------------------------------------------
        # Base class logs initialization message.

    # --- Update handle to be async --- 
    async def handle(self, task_data: dict):
        """Handle image generation requests."""
        intent = task_data.get('intent')
        payload = task_data.get('payload', {})
        task_id = task_data.get('task_id', 'unknown')
        self.logger.info(f"{self.agent_name} handling intent: {intent} for task {task_id}")

        if intent == constants.GENERATE_IMAGE:
            if not self.client:
                error_msg = "ImageGeneratorAgent OpenAI client not initialized (check API key or init errors)."
                self.logger.error(f"Task {task_id}: {error_msg}")
                return {"success": False, "error": error_msg, "task_id": task_id}
                 
            prompt = payload.get('prompt')
            if not prompt:
                error_msg = "Missing 'prompt' in payload for generate_image intent."
                self.logger.error(f"Task {task_id}: {error_msg}")
                return {"success": False, "error": error_msg, "task_id": task_id}
            
            # --- Call Image API --- 
            # Method returns dict with 'image_bytes' or 'error'
            api_result = self._call_openai_image_api(prompt, payload)
            # --- -------------- --- 

            if 'error' in api_result:
                self.logger.error(f"Task {task_id}: Image generation failed: {api_result['error']}")
                return {"success": False, "error": api_result['error'], "task_id": task_id}
            
            image_bytes = api_result.get('image_bytes')
            if not image_bytes:
                 error_msg = "API call returned no image content."
                 self.logger.error(f"Task {task_id}: {error_msg}")
                 return {"success": False, "error": error_msg, "task_id": task_id}

            # --- Save Image Locally Instead of Memory --- 
            image_filename = f"generated_{task_id}_{uuid.uuid4().hex[:6]}.png"
            save_path = self.save_directory / image_filename
            try:
                with open(save_path, 'wb') as f:
                    f.write(image_bytes)
                self.logger.info(f"Task {task_id}: Image successfully saved to: {save_path.resolve()}")
                return {"success": True, "image_path": str(save_path.resolve()), "filename": image_filename, "task_id": task_id}
            except Exception as e:
                 self.logger.error(f"Task {task_id}: Error saving image to {save_path}: {e}", exc_info=True)
                 return {"success": False, "error": f"Failed to save image locally: {e}", "task_id": task_id}
            # --- ------------------------------------ ---
        
        else:
            self.logger.warning(f"Task {task_id}: Unsupported intent for {self.agent_name}: {intent}")
            return {"success": False, "error": f"Unsupported intent: {intent}", "task_id": task_id}

    def _call_openai_image_api(self, prompt, params):
        """Calls the OpenAI Image API (DALL-E 3), downloads the image, and returns raw bytes in a dict."""
        # Returns: {"image_bytes": bytes} or {"error": str}
        if not self.client:
            # Logger already logged error during init
            return {"error": "OpenAI client not initialized."}
        
        model = params.get('model', self.default_model)
        size = params.get('size', self.default_size)
        quality = params.get('quality', self.default_quality)
        style = params.get('style', self.default_style)
        n = 1 # Request only one image

        self.logger.info(f"Calling OpenAI Image API. Model: {model}, Size: {size}, Quality: {quality}, Style: {style}")
        try:
            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                n=n,
                response_format="url"
            )
            
            if not response.data or not response.data[0].url:
                error_msg = "OpenAI API response did not contain an image URL."
                self.logger.error(error_msg)
                return {"error": error_msg}
                
            image_url = response.data[0].url
            self.logger.info(f"Received image URL from OpenAI: {image_url}")

            # --- Download the image from the URL --- 
            try:
                # Use stream=True for potentially large images
                # Disable SSL verification for the download request as well
                with requests.Session() as session:
                    session.verify = False # Disable SSL verification for this session
                    image_response = session.get(image_url, stream=True, timeout=30) 
                    image_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                
                # Read the content into bytes
                image_bytes = image_response.content
                self.logger.info(f"Successfully downloaded image ({len(image_bytes)} bytes) from URL.")
                return {"image_bytes": image_bytes}
                
            except requests.exceptions.RequestException as e:
                error_msg = f"Failed to download image from URL {image_url}: {e}"
                self.logger.error(error_msg)
                return {"error": error_msg}
            # --- ------------------------------- --- 

        except OpenAIError as e:
            error_msg = f"OpenAI API Error: {e}"
            self.logger.error(f"OpenAI API error during image generation: {e}")
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected API call error: {e}"
            self.logger.error(f"Unexpected error calling OpenAI Image API: {e}", exc_info=True)
            return {"error": error_msg} 