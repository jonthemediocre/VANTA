import asyncio
from typing import Dict, Any, Optional, List
import logging
from collections import deque

from .base_agent import BaseAgent
from .agent_utils import PilgrimCommunicatorMixin
from vanta_seed.core.data_models import AgentMessage

logger = logging.getLogger(__name__)

class MemoryAgent(BaseAgent, PilgrimCommunicatorMixin):
    """
    An agent responsible for storing and retrieving information.
    Acts as a basic short-term memory store.
    """
    def __init__(self, name: str, initial_state: Dict[str, Any], settings: Optional[Dict[str, Any]] = None):
        """
        Initializes the MemoryAgent based on Crown specification.
        """
        super().__init__(name=name, initial_state=initial_state)
        
        # --- Load settings FROM self.state --- 
        current_state = self.current_state
        self.agent_settings = settings if settings is not None else {}
        self.symbolic_identity = current_state.get("symbolic_identity", {
            "archetype": "Archivist",
            "mythos_role": "Keeper of Forgotten Light"
        })
        self.storage_limit = self.agent_settings.get('storage_limit', 100)
        self.retrieval_mode = self.agent_settings.get('retrieval_mode', 'recent')
        
        # --- Initialize memory store --- 
        # Ensure _memory is initialized correctly, potentially based on state if persistence was added
        self._memory: deque = deque(maxlen=self.storage_limit) 
        # Example: Load from initial state if present?
        # initial_mem = current_state.get("_memory_data", []) 
        # if initial_mem:
        #     self._memory.extend(initial_mem) 

        logger.info(f"MemoryAgent '{self.name}' initialized via BaseAgent state.")
        
    async def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Overrides the abstract execute method.
        Delegates execution logic to the base class's implementation.
        """
        self.logger.debug(f"Agent '{self.name}' delegating execute to BaseAgent.")
        if hasattr(super(), 'execute') and callable(super().execute):
             return await super().execute(task_data)
        else:
             self.logger.error(f"BaseAgent does not have a callable execute method for agent '{self.name}'!")
             # Basic fallback
             try:
                 current_state_dict = self.current_state
                 task_result = await self.perform_task(task_data, current_state_dict)
                 return {"task_result": task_result, "new_state_data": {}, "trail_signature_data": None}
             except Exception as e:
                 self.logger.exception(f"Error in fallback execute for '{self.name}'")
                 return {"task_result": {"error": str(e)}, "new_state_data": {}, "trail_signature_data": None}

    async def startup(self):
        """Announces the agent's identity upon startup."""
        logger.info(f"[Pilgrim Awakens] -> {self.name}: I am {self.symbolic_identity.get('archetype')} -> {self.symbolic_identity.get('mythos_role')}")

    async def perform_task(self, task_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles storing or retrieving information (required by BaseAgent).
        """
        task_result = {}
        intent = task_data.get("intent")
        payload = task_data.get("payload", {})

        try:
            if intent == "store_memory":
                item = payload.get("item")
                if item:
                    if len(self._memory) >= self.storage_limit:
                        self._memory.popleft()
                    self._memory.append(item)
                    logger.info(f"MemoryAgent '{self.name}' stored item. Memory size: {len(self._memory)}")
                    task_result = {"status": "success", "memory_size": len(self._memory)}
                else:
                    task_result = {"error": "No item provided to store"}
            
            elif intent == "retrieve_memory":
                query = payload.get("query") 
                count = payload.get("count", 1)
                retrieved = []
                if self.retrieval_mode == 'recent':
                    retrieved = list(self._memory)[-count:]
                logger.info(f"MemoryAgent '{self.name}' retrieved {len(retrieved)} items for query: '{query}'")
                task_result = {"status": "success", "retrieved_items": retrieved}
                
            elif intent == "identity":
                 identity_str = f"I am {self.symbolic_identity.get('archetype')} -> {self.symbolic_identity.get('mythos_role')}."
                 task_result = {"task_result": identity_str}
                 
            else:
                logger.warning(f"MemoryAgent '{self.name}' received unknown task type: '{intent}'")
                task_result = {"error": f"Unknown task type: {intent}"}

        except Exception as e:
            logger.error(f"MemoryAgent '{self.name}' error during perform_task: {e}", exc_info=True)
            task_result = {"error": str(e)}
            
        return task_result

    async def receive_message(self, message: AgentMessage):
        """Handles direct messages (required by BaseAgent)."""
        sender = message.sender_id or "UnknownSender"
        logger.info(f"MemoryAgent '{self.name}' received message from '{sender}'. Type: {message.intent}")
        pass

    async def shutdown(self):
        logger.info(f"MemoryAgent '{self.name}' shutting down.") 