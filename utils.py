"""
Utility functions for the VANTA framework.
"""

import uuid
import datetime
import logging
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def load_agent_definitions(file_path="agents.index.mpc.json") -> dict:
    """Loads agent definitions from the specified JSON file."""
    definitions_path = Path(file_path)
    logger.info(f"Attempting to load agent definitions from: {definitions_path.resolve()}")
    if not definitions_path.is_file():
        logger.error(f"Agent definitions file not found at {definitions_path.resolve()}")
        raise FileNotFoundError(f"Agent definitions file not found: {definitions_path.resolve()}")
    
    try:
        with open(definitions_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Basic validation: check if 'agents' key exists and is a dict
        if isinstance(data, dict) and isinstance(data.get('agents'), dict):
             logger.info(f"Successfully loaded definitions for {len(data['agents'])} agents.")
             return data['agents'] # Return only the 'agents' dictionary
        else:
            logger.error(f"Invalid format in {definitions_path}: Missing 'agents' dictionary.")
            raise ValueError(f"Invalid format in {definitions_path}: Missing 'agents' dictionary.")
            
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {definitions_path}: {e}")
        raise ValueError(f"Could not parse {definitions_path} as JSON.") from e
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading {definitions_path}: {e}", exc_info=True)
        raise

def create_task_data(intent: str, payload: dict = None, source_agent: str = None, context: dict = None, priority: int = 0) -> dict:
    """Creates a standardized task data dictionary.

    Args:
        intent: The primary goal or action for the task.
        payload: Task-specific data required by the handling agent.
        source_agent: ID/Name of the agent creating this task.
        context: Additional contextual information (e.g., source task ID, file path).
        priority: Task priority (higher value means higher priority).

    Returns:
        A dictionary conforming to the task_data schema.
    """
    task_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat() + 'Z'
    status = "queued"
    
    task = {
        "task_id": task_id,
        "intent": intent,
        "payload": payload or {},
        "context": context or {},
        "source_agent": source_agent,
        "timestamp": timestamp,
        "priority": priority,
        "status": status
    }
    
    logger.debug(f"Created task data: ID={task_id}, Intent={intent}")
    # TODO: Add schema validation here before returning?
    return task 