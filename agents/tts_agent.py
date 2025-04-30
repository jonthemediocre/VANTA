"""
Agent: TTSAgent
Type: domain/audio
"""
import os
import json
import datetime
import logging
import uuid
import httpx # <<< Import httpx
from openai import OpenAI, OpenAIError
# from vanta_nextgen import CrossModalMemory # Remove old import
import constants # <-- Import constants
# from agents.base_tool_agent import BaseToolAgent # Remove old import
from core.base_agent import BaseAgent # <<< Import correct base class
from pathlib import Path

# --- REMOVE module-level logger --- 
# logger = logging.getLogger(__name__)
# ----------------------------------

# Configure basic logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Inherit from BaseAgent ---
class TTSAgent(BaseAgent):
    """Agent that generates speech from text using the OpenAI TTS API."""
    # --- Accept logger_instance --- 
    def __init__(self, agent_name: str, definition: dict, blueprint: dict, **kwargs):
        super().__init__(agent_name, definition, blueprint, **kwargs) # Call correct parent
        # Config, logger, blueprint are now inherited via self
        
        self.default_model = self.config.get('default_model', 'tts-1')
        self.default_voice = self.config.get('default_voice', 'alloy')
        self.default_format = self.config.get('default_format', 'mp3')
        self.save_directory = Path(self.config.get('audio_save_directory', './generated_audio'))
        self.save_directory.mkdir(parents=True, exist_ok=True) # Ensure directory exists
        self.logger.info(f"Audio will be saved to: {self.save_directory.resolve()}")
        
        # --- Initialize OpenAI Client (Similar to MoERouter/ImageGenerator) --- 
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            self.logger.error("OPENAI_API_KEY environment variable not set.")
            self.client = None
        else:
            try:
                custom_http_client = httpx.Client(verify=False)
                self.client = OpenAI(
                    api_key=self.api_key,
                    http_client=custom_http_client
                )
                self.logger.info("OpenAI client initialized successfully (SSL verification disabled).")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
                self.client = None
        # -------------------------------------------------------------------
            
        # --- Memory Interaction Removed --- 
        # self.memory = None # No direct memory access
        # ---------------------------------
        # Base class logs initialization message.

    # --- Update handle to be async --- 
    async def handle(self, task_data: dict):
        """Handle speech generation requests."""
        intent = task_data.get('intent')
        payload = task_data.get('payload', {})
        task_id = task_data.get('task_id', 'unknown')
        self.logger.info(f"{self.agent_name} handling intent: {intent} for task {task_id}")

        if intent == constants.GENERATE_SPEECH:
            if not self.client:
                error_msg = "TTSAgent OpenAI client not initialized (check API key or init errors)."
                self.logger.error(f"Task {task_id}: {error_msg}")
                return {"success": False, "error": error_msg, "task_id": task_id}
                 
            text_input = payload.get('text')
            if not text_input:
                error_msg = "Missing 'text' in payload for generate_speech intent."
                self.logger.error(f"Task {task_id}: {error_msg}")
                return {"success": False, "error": error_msg, "task_id": task_id}
            
            # Prepare API parameters
            model = payload.get('model', self.default_model)
            voice = payload.get('voice', self.default_voice)
            output_format = payload.get('format', self.default_format)
            speed = payload.get('speed', 1.0)
            
            # --- Call OpenAI TTS API --- 
            # Method returns dict with 'audio_bytes' or 'error'
            api_result = self._call_openai_tts_api(text_input, model, voice, output_format, speed)
            # --- ------------------- ---

            if 'error' in api_result:
                 self.logger.error(f"Task {task_id}: TTS generation failed: {api_result['error']}")
                 return {"success": False, "error": api_result['error'], "task_id": task_id}

            audio_bytes = api_result.get('audio_bytes')
            if not audio_bytes:
                 error_msg = "API call returned no audio content."
                 self.logger.error(f"Task {task_id}: {error_msg}")
                 return {"success": False, "error": error_msg, "task_id": task_id}

            # --- Save Audio Locally --- 
            audio_filename = f"generated_{task_id}_{uuid.uuid4().hex[:6]}.{output_format}"
            save_path = self.save_directory / audio_filename
            try:
                # Use response.stream_to_file(save_path) for efficiency if API allows
                # Otherwise, write the bytes manually
                with open(save_path, 'wb') as f:
                    f.write(audio_bytes)
                self.logger.info(f"Task {task_id}: Audio successfully saved to: {save_path.resolve()}")
                return {"success": True, "audio_path": str(save_path.resolve()), "filename": audio_filename, "task_id": task_id}
            except Exception as e:
                 self.logger.error(f"Task {task_id}: Error saving audio to {save_path}: {e}", exc_info=True)
                 return {"success": False, "error": f"Failed to save audio locally: {e}", "task_id": task_id}
            # --- -------------------- ---
        
        else:
            self.logger.warning(f"Task {task_id}: Unsupported intent for {self.agent_name}: {intent}")
            return {"success": False, "error": f"Unsupported intent: {intent}", "task_id": task_id}

    def _call_openai_tts_api(self, text, model, voice, response_format, speed):
        """Calls the OpenAI TTS API and returns raw audio bytes in a dict."""
        # Returns: {"audio_bytes": bytes} or {"error": str}
        if not self.client:
            return {"error": "OpenAI client not initialized."}
        
        self.logger.info(f"Calling OpenAI TTS API. Model: {model}, Voice: {voice}, Format: {response_format}")
        try:
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                response_format=response_format,
                speed=speed
            )
            audio_bytes = response.read()
            self.logger.info("Successfully received audio stream from OpenAI TTS API.")
            return {"audio_bytes": audio_bytes}
            
        except OpenAIError as e:
            error_msg = f"OpenAI API Error: {e}"
            self.logger.error(f"OpenAI API error during TTS generation: {e}")
            return {"error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected API call error: {e}"
            self.logger.error(f"Unexpected error calling OpenAI TTS API: {e}", exc_info=True)
            return {"error": error_msg} 