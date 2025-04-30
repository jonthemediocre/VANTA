# vanta_seed/agents/dia_tts_agent.py
import logging
import os
import uuid
from pathlib import Path
import concurrent.futures
import time

from core.base_agent import BaseAgent
import constants

# Attempt to import the Dia library
try:
    from dia.model import Dia
    DIA_AVAILABLE = True
except ImportError:
    logging.warning("DiaTTSAgent: Failed to import 'dia' library. Ensure it's installed (pip install git+https://github.com/nari-labs/dia.git). This agent will be non-functional.")
    DIA_AVAILABLE = False
    # Define a dummy Dia class if import fails to prevent NameErrors later
    class Dia:
        @staticmethod
        def from_pretrained(*args, **kwargs):
            raise ImportError("Dia library not installed or import failed.")
        def generate(*args, **kwargs):
            raise ImportError("Dia library not installed or import failed.")
        def save_audio(*args, **kwargs):
            raise ImportError("Dia library not installed or import failed.")

class DiaTTSAgent(BaseAgent):
    """Agent to generate dialogue using the Nari Labs Dia model."""

    def __init__(self, agent_name: str, definition: dict, blueprint: dict, all_agent_definitions: dict, orchestrator_ref=None, **kwargs):
        super().__init__(agent_name, definition, blueprint, all_agent_definitions, orchestrator_ref, **kwargs)
        self.logger = logging.getLogger(f"Agent.{agent_name}")
        self.dia_model = None

        if not DIA_AVAILABLE:
            self.logger.error("Dia library not available. Agent will not function.")
            return # Stop initialization if library missing

        # --- Load Config --- 
        self.model_id = self.config.get('model_id', 'nari-labs/Dia-1.6B')
        self.compute_dtype = self.config.get('compute_dtype', 'float16')
        self.use_torch_compile = self.config.get('use_torch_compile', True)
        save_dir_path = self.config.get('audio_save_directory', './generated_audio_dia')
        self.save_directory = Path(save_dir_path)

        try:
            self.save_directory.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Dialogue audio will be saved to: {self.save_directory.resolve()}")
        except Exception as e:
            self.logger.error(f"Failed to create audio save directory {self.save_directory}: {e}", exc_info=True)
            # Continue initialization but saving might fail

        # --- Load Dia Model --- 
        self.logger.info(f"Attempting to load Dia model: {self.model_id} with dtype: {self.compute_dtype}...")
        self.logger.warning("Dia model loading requires a compatible GPU and CUDA setup.")
        # Use a timeout to prevent silent hangs during model loading
        timeout = self.config.get('load_timeout_seconds', 120)
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(Dia.from_pretrained, self.model_id, compute_dtype=self.compute_dtype)
        try:
            self.dia_model = future.result(timeout=timeout)
            self.logger.info(f"Successfully loaded Dia model: {self.model_id}")
        except concurrent.futures.TimeoutError:
            self.logger.error(f"Dia model loading timed out after {timeout} seconds.")
            self.dia_model = None
        except ImportError as ie:
            # Handles missing library imports
            self.logger.error(f"ImportError during Dia model loading: {ie}.", exc_info=True)
            self.dia_model = None
        except Exception as e:
            # Catch other potential errors (GPU OOM, CUDA issues, download errors)
            self.logger.error(f"Failed to load Dia model {self.model_id}: {e}", exc_info=True)
            self.logger.error("Please ensure you have a compatible GPU, sufficient VRAM, CUDA drivers, and PyTorch installed.")
            self.dia_model = None
        finally:
            executor.shutdown(wait=False)

    async def handle(self, task_data: dict):
        """Handles tasks routed to the DiaTTSAgent."""
        intent = task_data.get('intent')
        payload = task_data.get('payload', {})
        task_id = task_data.get('task_id', 'unknown')

        if not self.dia_model:
            error_msg = "DiaTTSAgent cannot handle task - Model not loaded."
            self.logger.error(f"Task {task_id} ({intent}): {error_msg}")
            return {"success": False, "error": error_msg, "task_id": task_id}

        if intent == constants.GENERATE_DIALOGUE: # Use the new intent
            script = payload.get('script')
            if not script:
                return {"success": False, "error": "No script provided in payload", "task_id": task_id}
            
            # Optional: Validate script format (e.g., contains [S1]/[S2])?
            # For now, assume input script is correctly formatted.
            
            self.logger.info(f"Task {task_id}: Generating dialogue audio for script: '{script[:70]}...' using Dia model.")
            try:
                # Generate audio data
                # Note: Dia's generate might be blocking; consider running in executor if needed
                # For now, assume it's acceptable to block the async worker here.
                output = self.dia_model.generate(script, use_torch_compile=self.use_torch_compile, verbose=True)
                self.logger.info(f"Task {task_id}: Dia model generated audio data.")

                # Save the audio
                filename = f"dia_dialogue_{task_id}_{uuid.uuid4().hex[:6]}.mp3"
                save_path = self.save_directory / filename
                self.dia_model.save_audio(str(save_path), output)
                self.logger.info(f"Task {task_id}: Dialogue audio saved to: {save_path.resolve()}")
                
                return {
                    "success": True, 
                    "audio_path": str(save_path.resolve()), 
                    "filename": filename, 
                    "type": "audio", 
                    "task_id": task_id
                }

            except Exception as e:
                self.logger.error(f"Task {task_id}: Error during Dia generation or saving: {e}", exc_info=True)
                return {"success": False, "error": f"Dia TTS failed: {e}", "task_id": task_id}
        else:
             self.logger.warning(f"DiaTTSAgent received unhandled intent: {intent}")
             return {"success": False, "error": "Unhandled intent for DiaTTSAgent", "task_id": task_id} 