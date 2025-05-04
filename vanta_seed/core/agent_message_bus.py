import asyncio
import logging
from collections import defaultdict, deque
from typing import Dict, List, Callable, Awaitable, Optional, TYPE_CHECKING

# Use TYPE_CHECKING to avoid circular import issues at runtime
if TYPE_CHECKING:
    from vanta_seed.core.data_models import AgentMessage
    from vanta_seed.agents.base_agent import BaseAgent # For type hint

logger = logging.getLogger(__name__)

# Type Alias for the handler
MessageHandler = Callable[['AgentMessage'], Awaitable[None]]

class AgentMessageBus:
    """Handles routing messages between agents."""

    def __init__(self):
        # Stores agent_id -> agent_instance mapping for direct calls
        self._agent_registry: Dict[str, 'BaseAgent'] = {}
        # Fallback queue for messages to unregistered agents (optional)
        self._undelivered_messages: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("AgentMessageBus initialized.")

    def register_agent(self, agent_id: str, agent_instance: 'BaseAgent'):
        """Registers an agent instance with the message bus."""
        if agent_id in self._agent_registry:
            self.logger.warning(f"Agent ID '{agent_id}' is already registered. Overwriting.")
        if not hasattr(agent_instance, 'receive_message') or not asyncio.iscoroutinefunction(agent_instance.receive_message):
             self.logger.error(f"Agent '{agent_id}' ({type(agent_instance).__name__}) cannot be registered: Missing or non-async 'receive_message' method.")
             return
             
        self._agent_registry[agent_id] = agent_instance
        self.logger.info(f"Agent '{agent_id}' ({type(agent_instance).__name__}) registered with message bus.")
        # Optionally, try delivering queued messages upon registration
        # self._deliver_queued_messages(agent_id)

    def unregister_agent(self, agent_id: str):
        """Removes an agent from the registry."""
        if agent_id in self._agent_registry:
            del self._agent_registry[agent_id]
            self.logger.info(f"Agent '{agent_id}' unregistered from message bus.")
        else:
            self.logger.warning(f"Attempted to unregister non-existent agent ID: '{agent_id}'")

    async def publish_message(self, message: 'AgentMessage'):
        """Publishes a message to the target agent."""
        target_agent_id = message.receiver_id # The simple name or ID used for registration
        target_agent = self._agent_registry.get(target_agent_id)

        # --- ADDED: Log correlation ID upon receiving message in bus --- 
        self.logger.debug(f"BUS RECEIVED message {message.message_id} for '{target_agent_id}'. Intent: {message.intent}. CorrID: {message.correlation_id}")
        # -------------------------------------------------------------

        if target_agent:
            if hasattr(target_agent, 'receive_message') and asyncio.iscoroutinefunction(target_agent.receive_message):
                try:
                    # Directly await the receive_message coroutine
                    self.logger.debug(f"Found registered agent '{target_agent_id}'. Calling receive_message for {message.message_id}.")
                    await target_agent.receive_message(message)
                    self.logger.debug(f"Successfully delivered message {message.message_id} to '{target_agent_id}'.")
                except Exception as e:
                    self.logger.error(f"Error calling receive_message for agent '{target_agent_id}' (Message ID: {message.message_id}): {e}", exc_info=True)
                    # Optionally queue if delivery fails?
            else:
                # Handle unregistered agent
                self.logger.warning(f"Receiver agent {target_agent_id} not found or not registered for message {message.message_id}. Message dropped.")
                # Optionally queue the message
                # self._undelivered_messages[target_agent_id].append(message)
                # self.logger.info(f"Message {message.message_id} queued for later delivery to {target_agent_id}.")
        else:
            # Handle unregistered agent
            self.logger.warning(f"Receiver agent {target_agent_id} not found or not registered for message {message.message_id}. Message dropped.")
            # Optionally queue the message
            # self._undelivered_messages[target_agent_id].append(message)
            # self.logger.info(f"Message {message.message_id} queued for later delivery to {target_agent_id}.")

    # Optional: Method to deliver queued messages
    # async def _deliver_queued_messages(self, agent_id: str):
    #     if agent_id in self._undelivered_messages and agent_id in self._agent_registry:
    #         queued = self._undelivered_messages.pop(agent_id)
    #         self.logger.info(f"Delivering {len(queued)} queued messages to newly registered agent '{agent_id}'.")
    #         for message in queued:
    #             await self.publish_message(message) # Re-publish to trigger delivery

    # --- Optional: Pending message handling --- 
    # def _process_pending_for_agent(self, agent_id: str):
    #     if agent_id in self._pending_messages:
    #         messages_to_deliver = self._pending_messages.pop(agent_id)
    #         logger.info(f"Processing {len(messages_to_deliver)} pending message(s) for newly registered agent {agent_id}.")
    #         for msg in messages_to_deliver:
    #             asyncio.create_task(self.publish_message(msg)) # Re-publish now that agent is registered
    # -----------------------------------------
    
    # --- Optional: Orchestrator fallback --- 
    # async def _route_to_orchestrator_fallback(self, message: AgentMessage):
    #     # Requires orchestrator reference passed during init or set later
    #     if hasattr(self, 'orchestrator') and self.orchestrator:
    #         logger.debug(f"Routing undelivered message {message.message_id} to orchestrator fallback.")
    #         # Adapt message format if needed for orchestrator task queue
    #         fallback_task = {
    #             "task_id": f"fallback_{message.message_id}",
    #             "intent": "handle_undelivered_message",
    #             "payload": message.__dict__ # Send whole message data
    #         }
    #         await self.orchestrator.add_task(fallback_task)
    #     else:
    #         logger.error("Cannot route message to orchestrator fallback: Orchestrator reference missing.")
    # --------------------------------------- 