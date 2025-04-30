# core/base_agent.py

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class BaseAgent(ABC):
    """Abstract Base Class for all VANTA agents."""
    
    def __init__(
        self, 
        agent_name: str, 
        definition: dict, 
        blueprint: dict, 
        # logger_instance: logging.Logger, # Let agents get their own logger for consistency
        orchestrator_ref: Optional['AgentOrchestrator'] = None, # Optional reference to the orchestrator
        all_definitions_ref: Optional[Dict[str, Any]] = None, # Optional reference to all definitions
        **kwargs # <<< Add **kwargs to accept unexpected arguments
    ):
        """Standard initialization for all agents."""
        self.agent_name = agent_name
        self.definition = definition # The full definition dict from agent_index
        self.blueprint = blueprint
        self.orchestrator = orchestrator_ref # Weak reference? Or direct?
        self.all_definitions = all_definitions_ref
        
        # Get logger instance specific to this agent
        self.logger = logging.getLogger(f"Agent.{self.agent_name}")
        
        # Extract config sub-dictionary
        self.config = definition.get('config', {})
        
        self.logger.info(f"Initialized BaseAgent for '{self.agent_name}'")
        # Subclasses should call super().__init__(...) and then perform their specific setup

    @abstractmethod
    async def handle(self, task_data: dict):
        """
        Abstract method for handling incoming tasks.
        Subclasses MUST implement this method.
        
        Args:
            task_data (dict): The task data dictionary, typically containing 
                              'intent', 'payload', 'task_id', etc.
                              
        Returns:
            dict: A result dictionary, usually including {"success": True/False, ...}
        """
        pass

    # Optional common utility methods can be added here
    def get_capability(self, capability_name: str) -> bool:
        """Checks if the agent has a specific capability listed in its definition."""
        return capability_name in self.definition.get('capabilities', []) 