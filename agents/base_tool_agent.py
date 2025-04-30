"""
Base class for Agents that interact with external tools/APIs.
"""
import os
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseToolAgent(ABC):
    """Abstract Base Class for agents interacting with external tools/APIs.

    Handles common initialization like reading config and API keys.
    Subclasses should implement the specific API interaction logic.
    """
    def __init__(self, config: dict = None, default_api_key_env: str = None, logger_instance=None):
        self.config = config or {}
        self.agent_name = self.__class__.__name__ # Get subclass name
        
        # Store the passed logger
        self.logger = logger_instance or logging.getLogger(self.agent_name) # Use passed logger or create specific one
        
        # API Key Handling
        self.api_key_env = self.config.get('api_key_env', default_api_key_env)
        if not self.api_key_env:
            self.logger.error(f"{self.agent_name}: Configuration must provide 'api_key_env' or a default must be set.")
            self.api_key = None
        else:
            self.api_key = os.getenv(self.api_key_env)
            if not self.api_key:
                self.logger.warning(f"{self.agent_name}: Environment variable '{self.api_key_env}' not set. Agent may fail.")
        
        # Memory Path Handling (Optional - subclasses can override if needed)
        self.memory_path = self.config.get('memory_path')
        if self.memory_path:
            # Could initialize memory here, or let subclasses do it.
            # from vanta_nextgen import CrossModalMemory 
            # self.memory = CrossModalMemory(self.memory_path)
            self.logger.info(f"{self.agent_name}: Memory path configured to '{self.memory_path}'. Subclass should initialize memory component.")
        else:
            self.logger.info(f"{self.agent_name}: No memory path configured.")

        self.logger.info(f"{self.agent_name} initialized.")

    @abstractmethod
    def handle(self, context: dict):
        """Main entry point for handling tasks.
        Subclasses must implement this method.
        """
        pass

    # Optional: Define standard helper methods subclasses might use
    # def _make_request(self, method, url, headers=None, json_payload=None, params=None, timeout=30):
    #     """Standard way to make HTTP requests with error handling."""
    #     # Implementation using requests library...
    #     pass 