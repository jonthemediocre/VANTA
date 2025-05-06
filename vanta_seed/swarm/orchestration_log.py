"""
Logger for Distributed Swarm Orchestration events.

Extends or utilizes the SwarmLogger to capture events specifically related to
the orchestration of tasks across multiple nodes, including task assignments,
node status changes, communication events, and global ritual progression.

Uses JSON Lines format for structured logging.
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Potentially reuse or adapt the existing SwarmLogger
from .swarm_logger import SwarmLogger

logger = logging.getLogger(__name__) # Module-level logger for internal messages

class DistributedLogger:
    def __init__(self, log_dir: str = "logs/orchestration", session_id: Optional[str] = None):
        """Initializes the DistributedLogger instance.

        Args:
            log_dir: Directory to store log files.
            session_id: Optional specific session ID. Defaults to timestamp.
        """
        self.log_dir = log_dir
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(self.log_dir, f"orchestration_log_{self.session_id}.jsonl")
        os.makedirs(self.log_dir, exist_ok=True)
        print(f"DistributedLogger initialized. Logging to: {self.log_file_path}")

        # Setup basic file handler for JSON Lines
        self._file_handler = logging.FileHandler(self.log_file_path, mode='a')
        self._file_handler.setLevel(logging.INFO)
        # No formatter needed, we write JSON directly

    def _log(self, event_type: str, data: Dict[str, Any]):
        """Writes a structured log entry as a JSON line."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "event_type": event_type,
            "data": data
        }
        try:
            json_line = json.dumps(log_entry, ensure_ascii=False)
            self._file_handler.stream.write(json_line + '\n')
            self._file_handler.flush()
        except Exception as e:
            logger.error(f"Failed to write log entry: {e}", exc_info=True)

    def log_node_registration(self, node_id: str, capabilities: list):
        """Logs when a node registers with the orchestrator."""
        self._log("node_registered", {"node_id": node_id, "capabilities": capabilities})

    def log_node_status_change(self, node_id: str, old_status: str, new_status: str):
        """Logs when a node's status changes (e.g., idle -> busy)."""
        self._log("node_status_change", {"node_id": node_id, "old_status": old_status, "new_status": new_status})

    def log_task_assignment(self, task_id: str, node_id: str, task_details: Dict[str, Any]):
        """Logs when a task is assigned to a node."""
        self._log("task_assigned", {"task_id": task_id, "assigned_node": node_id, "task_details": task_details})

    def log_task_completion(self, task_id: str, node_id: str, result_summary: Dict[str, Any]):
        """Logs when a node reports task completion."""
        self._log("task_completed", {"task_id": task_id, "completed_node": node_id, "result_summary": result_summary})

    def log_communication_event(self, source: str, target: str, message_type: str, success: bool, error: Optional[str] = None):
        """Logs a communication attempt between nodes/orchestrator."""
        self._log("communication_event", {
            "source": source,
            "target": target,
            "message_type": message_type,
            "success": success,
            "error": error
        })

    def log_orchestrator_event(self, event_description: str, details: Optional[Dict[str, Any]] = None):
        """Logs general orchestrator state changes or events."""
        self._log("orchestrator_event", {"description": event_description, "details": details or {}})

    def close(self):
        """Closes the log file handler."""
        print(f"Closing DistributedLogger for session {self.session_id}.")
        if self._file_handler:
            self._file_handler.close()

# Example usage (placeholder)
if __name__ == "__main__":
    logger_instance = DistributedLogger()
    logger_instance.log_orchestrator_event("Orchestrator started")
    logger_instance.log_node_registration("node_abc", ['train', 'evaluate'])
    logger_instance.log_task_assignment("task_xyz", "node_abc", {"agent": "Agent_A"})
    logger_instance.log_communication_event("orchestrator", "node_abc", "task_assignment", True)
    logger_instance.log_task_completion("task_xyz", "node_abc", {"status": "SUCCESS", "reward": 2.5})
    logger_instance.close()
    print("Distributed Logger scaffold created. Check logs/orchestration/ for output.") 