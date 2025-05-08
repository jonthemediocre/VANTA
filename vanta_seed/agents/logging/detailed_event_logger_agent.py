import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

# Assuming BaseAgent is in vanta_seed.agents.base_agent
from vanta_seed.agents.base_agent import BaseAgent
import vanta_seed.config as config # For base directory

# Configure a dedicated logger for this agent
agent_logger = logging.getLogger("DetailedEventLoggerAgent")

class DetailedEventLoggerAgent(BaseAgent):
    """
    VANTA Agent responsible for logging structured event details passed via cascades
    or direct task submission. Logs to a dedicated JSONL file.
    """
    
    def __init__(self, name: str, config, logger, orchestrator_ref, **kwargs):
        super().__init__(name, config, logger, orchestrator_ref, **kwargs)
        self.log_file_path: Optional[Path] = None
        self._setup_logging()

    def _setup_logging(self):
        """Sets up the dedicated file logging."""
        try:
            # Get log path from agent settings in blueprint.yaml or use default
            log_dir_path = config.BASE_DIR / "logs" / "structured_events"
            log_dir_path.mkdir(parents=True, exist_ok=True)
            
            # Example setting lookup (adjust key based on blueprint.yaml structure for this agent)
            log_filename = self.config.settings.get("log_filename", "detailed_events.log.jsonl") if self.config and self.config.settings else "detailed_events.log.jsonl"
            
            self.log_file_path = log_dir_path / log_filename
            self.logger.info(f"Detailed event logger will write to: {self.log_file_path}")
            
            # Optional: Could set up a dedicated FileHandler here if needed,
            # but appending directly might be sufficient for JSONL.

        except Exception as e:
            self.logger.error(f"Failed to configure structured event logging path: {e}", exc_info=True)
            self.log_file_path = None # Disable logging if setup fails

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a task to log event details.
        Expects payload to contain the structured data to log.
        Uses input mapping from cascade definition (e.g., log_event_type, invocation_id etc.)
        """
        payload = task_data.get("payload", {})
        context = task_data.get("context", {})
        correlation_id = context.get("correlation_id")
        cascade_instance_id = context.get("cascade_instance_id")
        
        self.logger.info(f"Received task to log event. Type: {payload.get('log_event_type')}, CorrID: {correlation_id}")
        
        if not self.log_file_path:
            msg = "Structured event logging is disabled due to setup failure."
            self.logger.error(msg)
            return {"status": "FAILURE", "error_message": msg}

        try:
            log_entry = {
                "log_id": str(uuid.uuid4()),
                "timestamp_iso": datetime.utcnow().isoformat() + "Z",
                "event_source_agent": self.agent_id, # Log that this agent wrote the entry
                "correlation_id": correlation_id,
                "cascade_instance_id": cascade_instance_id,
                # Pass through all fields from the payload (mapped by cascade)
                **payload 
            }
            
            # Filter out None values potentially
            log_entry_filtered = {k: v for k, v in log_entry.items() if v is not None}

            # Append as JSON line
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry_filtered) + "\n")

            self.logger.info(f"Successfully logged event {payload.get('log_event_type')} to {self.log_file_path}. Log ID: {log_entry['log_id']}")
            return {"status": "SUCCESS", "output": {"log_id": log_entry['log_id'], "log_file": str(self.log_file_path)}}
            
        except Exception as e:
            self.logger.error(f"Failed to write to structured event log {self.log_file_path}: {e}", exc_info=True)
            return {"status": "FAILURE", "error_message": f"Failed to write to log: {str(e)}"}

    async def startup(self):
        await super().startup() # Call base class startup if needed
        self.logger.info(f"DetailedEventLoggerAgent '{self.name}' started.")

    async def shutdown(self):
        await super().shutdown() # Call base class shutdown if needed
        self.logger.info(f"DetailedEventLoggerAgent '{self.name}' shutting down.") 