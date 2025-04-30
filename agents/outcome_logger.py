# agents/outcome_logger.py

import logging
import json
from pathlib import Path
import datetime
# --- Import BaseAgent --- 
from core.base_agent import BaseAgent
# -----------------------

# --- Configuration Defaults ---
DEFAULT_LOG_DIR = "logs/outcomes"
DEFAULT_LOG_FILE = "task_outcomes.jsonl"

class OutcomeLogger(BaseAgent): # Inherit from BaseAgent
    """
    Agent responsible for logging the results and metadata of completed tasks 
    to a structured format (e.g., JSON Lines) for analysis and RL.
    (Stub Implementation)
    """
    # --- Updated __init__ signature --- 
    def __init__(self, agent_name: str, definition: dict, blueprint: dict, **kwargs):
        super().__init__(agent_name, definition, blueprint, **kwargs)
        # Config, logger, blueprint available via self
        
        # Configure log path using self.config
        log_dir_path_str = self.config.get("log_directory", DEFAULT_LOG_DIR)
        # Handle relative vs absolute paths potentially using BASE_DIR from config?
        # For now, assume relative to execution dir or absolute
        self.log_file_path = Path(log_dir_path_str) / self.config.get("log_filename", DEFAULT_LOG_FILE)
        
        # Ensure log directory exists
        try:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Outcome log directory set to: {self.log_file_path.parent}")
        except Exception as e:
             self.logger.error(f"Failed to create outcome log directory {self.log_file_path.parent}: {e}", exc_info=True)
             # Potentially fall back or disable?
        
        self.logger.info(f"Initializing OutcomeLogger '{self.agent_name}'. Logging to: {self.log_file_path}")
        # --------------------------------

    async def handle(self, task_data: dict):
        """
        Handles the "log_task_outcome" intent. Writes the outcome payload to 
        the configured JSON Lines file.
        """
        intent = task_data.get('intent')
        payload = task_data.get('payload', {}) 
        task_id = task_data.get('task_id') # This is the ID of the logging task itself
        original_task_id = payload.get('task_id', 'unknown') # ID of the task being logged
        
        if intent != "log_task_outcome":
            self.logger.warning(f"Received task {task_id} with unexpected intent '{intent}'. Ignoring.")
            return {"success": False, "error": "Invalid intent for OutcomeLogger"}

        if not payload:
            self.logger.error(f"Received logging task {task_id} with empty payload for original task {original_task_id}. Cannot log.")
            return {"success": False, "error": "Missing outcome payload"}

        self.logger.debug(f"OutcomeLogger received task {task_id} to log outcome for original task {original_task_id}.")

        # Add timestamp
        payload['log_timestamp_utc'] = datetime.datetime.utcnow().isoformat() + "Z"

        try:
            # Append to JSON Lines file
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                json.dump(payload, f) # Write the payload dict as a JSON object
                f.write('\n') # Add newline for JSON Lines format
            
            self.logger.info(f"Successfully logged outcome for task {original_task_id} to {self.log_file_path}")
            return {"success": True, "task_id": task_id, "agent": self.agent_name}
        
        except Exception as e:
            self.logger.error(f"Failed to write outcome log for task {original_task_id} to {self.log_file_path}: {e}", exc_info=True)
            return {"success": False, "task_id": task_id, "error": f"Failed to write log file: {e}"} 