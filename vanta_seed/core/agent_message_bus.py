import asyncio
import logging
from collections import defaultdict
from typing import Dict, List, Callable, Awaitable, Any

# Import AgentMessage and BaseAgent for type hints
from .data_models import AgentMessage
# Use a forward reference string for BaseAgent if it causes circular import issues
# from ..agents.base_agent import BaseAgent 

logger = logging.getLogger("Core.AgentMessageBus")

class AgentMessageBus:
    """Handles routing of direct messages between agents within the same process."""

    def __init__(self):
        # Stores registered agents: agent_id -> agent_instance
        self._registry: Dict[str, Any] = {}
        # Stores pending messages if receiver is not immediately available (optional)
        # self._pending_messages: defaultdict[str, List[AgentMessage]] = defaultdict(list)
        logger.info("AgentMessageBus initialized.")

    def register_agent(self, agent_id: str, agent_instance: Any):
        """Registers an agent instance to receive messages."""
        if agent_id in self._registry:
            logger.warning(f"Agent {agent_id} already registered with Message Bus. Overwriting.")
        
        # Check if the agent has the required receive_message method
        if not hasattr(agent_instance, 'receive_message') or not asyncio.iscoroutinefunction(agent_instance.receive_message):
             logger.error(f"Agent {agent_id} cannot be registered: Missing or non-async 'receive_message' method.")
             return
             
        self._registry[agent_id] = agent_instance
        logger.info(f"Agent {agent_id} registered with AgentMessageBus.")
        # Process any pending messages for this agent upon registration (optional)
        # self._process_pending_for_agent(agent_id)

    def unregister_agent(self, agent_id: str):
        """Removes an agent from message routing."""
        if agent_id in self._registry:
            del self._registry[agent_id]
            logger.info(f"Agent {agent_id} unregistered from AgentMessageBus.")
        else:
            logger.warning(f"Attempted to unregister non-existent agent: {agent_id}")

    async def publish_message(self, message: AgentMessage):
        """Routes a message to the receiver agent if registered."""
        receiver_id = message.receiver_id
        receiver_instance = self._registry.get(receiver_id)

        if receiver_instance:
            logger.debug(f"Routing message {message.message_id} from {message.sender_id} to {receiver_id}.")
            try:
                # Call the agent's receive_message method directly
                await receiver_instance.receive_message(message)
            except Exception as e:
                logger.error(f"Error delivering message {message.message_id} to agent {receiver_id}: {e}", exc_info=True)
                # Optionally notify sender of delivery failure?
        else:
            logger.warning(f"Receiver agent {receiver_id} not found or not registered for message {message.message_id}. Message dropped.")
            # Optional: Store message as pending?
            # self._pending_messages[receiver_id].append(message)
            # Optional: Route to orchestrator as fallback?
            # await self._route_to_orchestrator_fallback(message)

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