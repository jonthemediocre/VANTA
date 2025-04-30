# vanta_seed/logging/outcome_logger.py
import logging
import json
import os
from datetime import datetime
from pathlib import Path

class OutcomeLogger:
    """Logs task outcomes to a structured log file (JSONL)."""
    def __init__(self, agent_name: str, definition: dict, blueprint: dict, all_agent_definitions: dict, orchestrator_ref=None, **kwargs):
        self.config = definition.get('config', {})
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"Agent.{agent_name}")
        # Determine log file path from config or default
        log_dir = Path(self.config.get('log_directory', './logs')) # Default to ./logs relative to execution dir
        log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file_path = log_dir / self.config.get('outcome_log_file', 'task_outcomes.jsonl')
        self.logger.info(f"OutcomeLogger Initialized. Logging outcomes to: {self.log_file_path}")

    def record(self, prompt, output, task_id="unknown", success=True, error=None):
        """Records the outcome of a task/prompt."""
        # Basic structure matching orchestrator's finally block
        outcome_record = {
            "timestamp": datetime.now().isoformat(),
            "task_id": task_id,
            "prompt_preview": str(prompt)[:100] if prompt else None, # Log preview
            "output_preview": str(output)[:100] if output else None, # Log preview
            "success": success,
            "error": str(error) if error else None,
            # Add more context if needed (e.g., agent used, duration)
        }
        self._write_log(outcome_record)

    def _write_log(self, record_dict):
        """Appends a JSON record to the log file."""
        try:
            json_line = json.dumps(record_dict, ensure_ascii=False)
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(json_line + '\n')
            self.logger.debug(f"Successfully logged outcome for task {record_dict.get('task_id')}")
        except (TypeError, ValueError) as json_e:
            self.logger.error(f"Failed to serialize outcome record to JSON: {json_e}. Record: {record_dict}")
        except Exception as e:
            self.logger.error(f"Failed to write outcome log to {self.log_file_path}: {e}")
            
    async def handle(self, task_data):
        """Handles tasks specifically routed to the OutcomeLogger, primarily for logging."""
        self.logger.debug(f"Handling task via handle method: {task_data.get('intent')}")
        if task_data.get('intent') == 'log_task_outcome':
            payload = task_data.get('payload', {})
            # Use payload fields, falling back to None
            record = {
                "timestamp": datetime.now().isoformat(),
                "task_id": payload.get('task_id'),
                "task_intent": payload.get('task_intent'),
                "target_agent": payload.get('target_agent'),
                "success": payload.get('success'),
                "result_preview": str(payload.get('result'))[:150],
                "error": payload.get('error'),
                "execution_time_ms": payload.get('execution_time_ms')
            }
            self._write_log(record)
            return {"success": True, "message": f"Outcome logged for task {payload.get('task_id')}"}
        else:
             self.logger.warning(f"Received unhandled intent: {task_data.get('intent')}")
             return {"success": False, "error": "Unhandled intent"} 