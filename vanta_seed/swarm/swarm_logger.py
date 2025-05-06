"""
Logger specifically for Swarm RL training sessions.

Captures multi-agent states, actions, rewards, and context for analysis
and potential offline training or replay. Uses JSON Lines format.
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__) # Keep a module-level logger for internal messages

class SwarmLogger:
    def __init__(self, log_dir: str = "logs/swarm", session_id: Optional[str] = None):
        """Initializes the SwarmLogger instance.

        Args:
            log_dir: Directory to store log files.
            session_id: Optional specific session ID. Defaults to timestamp.
        """
        self.log_dir = log_dir
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(self.log_dir, f"swarm_log_{self.session_id}.jsonl")
        self._setup_logging()

    def _setup_logging(self):
        """Sets up the log directory and file for JSON Lines logging."""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            # Basic check if file can be opened
            with open(self.log_file_path, 'a') as f:
                pass
            logger.info(f"SwarmLogger initialized. Logging to: {self.log_file_path}")
        except OSError as e:
            logger.error(f"Failed to create log directory or file for SwarmLogger: {e}", exc_info=True)
            self.log_file_path = None # Disable logging if setup fails

    def log_episode_start(self, episode: int, config: Dict[str, Any]):
        """Logs the start of a swarm training episode."""
        self._log_entry("episode_start", {"episode": episode, "config": config})

    def log_step(self,
                 episode: int,
                 step: int,
                 agent_name: str, # Added agent_name for clarity
                 observation: Any, # Keep observation potentially summarised
                 action: Any,
                 reward: float,
                 terminated: bool,
                 truncated: bool,
                 info: Dict[str, Any]):
        """Logs a single step for a specific agent within a swarm episode."""
        # Consider summarizing observation/info if they become too large
        entry_data = {
            "episode": episode,
            "step": step,
            "agent_name": agent_name,
            "action": action,
            "reward": reward,
            "terminated": terminated,
            "truncated": truncated,
            "info": info, # Include full info dict for now
            # "observation": observation, # Optional: log observation summary
        }
        self._log_entry("step", entry_data)

    def log_episode_end(self, episode: int, aggregated_stats: Dict[str, Any]):
        """Logs the end of a swarm training episode."""
        self._log_entry("episode_end", {"episode": episode, "final_stats": aggregated_stats})

    def log_ritual_event(self, event_name: str, details: Dict[str, Any]):
         """Logs specific ritual events occurring during swarm interaction."""
         self._log_entry("ritual_event", {"event_name": event_name, "details": details})

    def _log_entry(self, event_type: str, data: Dict[str, Any]):
        """Writes a structured log entry to the JSON Lines file."""
        if not self.log_file_path:
            logger.warning("SwarmLogger file path not set, cannot log entry.")
            return

        log_record = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "event_type": event_type,
            "data": data
        }
        try:
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                json.dump(log_record, f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to write to swarm log file '{self.log_file_path}': {e}", exc_info=True)

# Example Usage (Conceptual)
# if __name__ == "__main__":
#     swarm_log = SwarmLogger()
#     swarm_log.log_episode_start(0, {"mode": "cooperative"})
#     # ... log steps for different agents ...
#     swarm_log.log_step(0, 1, "DataUnifierAgent", {"state":1}, 2, 3.5, False, False, {"status":"SUCCESS"})
#     swarm_log.log_episode_end(0, {"total_reward": 10.5})
#     swarm_log.log_ritual_event("consensus_reached", {"threshold": 0.8}) 