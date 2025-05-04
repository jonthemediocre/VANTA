import asyncio
from typing import Dict, Any, Optional
import logging
import uuid
import time

from .base_agent import BaseAgent
from .agent_utils import PilgrimCommunicatorMixin, PurposePulse
from vanta_seed.core.models import AgentConfig, TaskData
from vanta_seed.core.data_models import AgentMessage

logger = logging.getLogger(__name__)

class EchoAgent(BaseAgent, PilgrimCommunicatorMixin):
    """
    A simple agent that echoes back the content it receives,
    potentially with a prefix defined in settings.
    Inherits communication abilities from PilgrimCommunicatorMixin.
    """
    def __init__(self, name: str, config: AgentConfig, logger: logging.Logger, orchestrator_ref: Optional[Any] = None):
        """
        Initializes the EchoAgent.
        Uses the BaseAgent __init__ for standard setup.
        """
        super().__init__(name=name, config=config, logger=logger, orchestrator_ref=orchestrator_ref)
        
        # --- Load settings FROM self.state --- 
        # The base __init__ populates self.state from initial_state
        current_state = self.current_state # Use property to get state dict
        agent_settings = current_state.get("settings", {}) # Settings might be nested
        self.symbolic_identity = current_state.get("symbolic_identity", {
            "archetype": "Reflection", 
            "mythos_role": "Voice of Crown"
        })
        self.prefix = agent_settings.get('prefix', '') # Get prefix from settings within state
        self.max_repeat = agent_settings.get('max_repeat', 1) # Get max_repeat from settings within state
        
        # --- Remove orchestrator assignment (handled by base or not needed) --- 
        # self.orchestrator = orchestrator 
        
        # We don't currently use settings in EchoAgent, but accept it for compatibility
        self.agent_settings = config.settings if config.settings is not None else {}
        
        # Use direct attribute access for Pydantic models, provide default if attribute might be missing
        self.echo_prefix = getattr(self.config.settings, 'echo_prefix', "Echo")
        self.greeting_message = getattr(self.config.settings, 'greeting', "EchoAgent ready.")
        
        # Symbolic identity is now loaded by BaseAgent into self.symbolic_identity
        # Make logging access safer
        archetype = self.symbolic_identity.get('archetype', 'UnknownArchetype')
        logger.info(f"EchoAgent '{self.name}' initialized. Archetype: {archetype}")

    async def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Overrides the abstract execute method.
        Delegates execution logic to the base class's implementation.
        """
        # Assuming BaseAgent provides a concrete execute implementation despite the decorator
        # If this fails, we might need to replicate the base logic here.
        self.logger.debug(f"Agent '{self.name}' delegating execute to BaseAgent.")
        # --- Check if super().execute exists before calling --- #
        if hasattr(super(), 'execute') and callable(super().execute):
             return await super().execute(task_data)
        else:
             # Fallback if super().execute is somehow not available/callable
             self.logger.error(f"BaseAgent does not have a callable execute method for agent '{self.name}' to delegate to!")
             # Attempt to call perform_task directly as a basic fallback
             try:
                 # We need the 'current_state' which execute *should* calculate.
                 # This fallback is imperfect as state won't be updated first.
                 current_state_dict = self.current_state
                 task_result = await self.perform_task(task_data, current_state_dict)
                 # Package minimally
                 return {"task_result": task_result, "new_state_data": {}, "trail_signature_data": None}
             except Exception as e:
                 self.logger.exception(f"Error in fallback execute calling perform_task for '{self.name}'")
                 return {"task_result": {"error": str(e)}, "new_state_data": {}, "trail_signature_data": None}

    async def perform_task(self, task_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handles tasks: echo or identity request.
        This is the core logic implementation required by BaseAgent.
        The base class's execute method handles state updates and calls this.
        
        Args:
            task_data (Dict[str, Any]): The original task data received by the agent.
            current_state (Dict[str, Any]): The current internal state of the agent AFTER 
                                            potential updates calculated by the base execute method.

        Returns:
            Dict[str, Any]: A dictionary containing the primary result of the task.
        """
        logger.info(f"EchoAgent '{self.name}': Entering perform_task. Task Type: {task_data.get('intent')}")
        # --- Pulse logic is handled by the base execute method --- #
        
        task_result = {}
        intent = task_data.get("intent")
        payload = task_data.get("payload", {})

        try:
            logger.debug(f"EchoAgent '{self.name}': Processing intent '{intent}'")
            # --- Handle Identity Request --- 
            if intent == "identity":
                archetype = self.symbolic_identity.get('archetype', 'Unknown Archetype')
                mythos_role = self.symbolic_identity.get('mythos_role', 'Unknown Mythos')
                identity_str = f"I am {archetype} -> {mythos_role}."
                logger.info(f"EchoAgent '{self.name}' performing identity task.")
                task_result = {"status": "success", "output": identity_str, "summary": "Returned symbolic identity."}
            
            # --- Handle OpenAI Chat Completion Request --- 
            elif intent == "chat_completion":
                logger.debug(f"EchoAgent '{self.name}': Handling chat_completion intent.")
                messages = payload.get("messages", [])
                logger.debug(f"EchoAgent '{self.name}': Received {len(messages)} messages.")
                last_user_message = "No user message found."
                if messages and isinstance(messages, list):
                    for msg in reversed(messages):
                        if isinstance(msg, dict) and msg.get("role") == "user":
                            last_user_message = msg.get("content", "User message content empty.")
                            logger.debug(f"EchoAgent '{self.name}': Found last user message: '{last_user_message[:50]}...'")
                            break
                else:
                    logger.warning(f"EchoAgent '{self.name}': No messages found or messages is not a list.")
                    
                response_text = f"{self.prefix}You said: {last_user_message}"
                logger.info(f"EchoAgent '{self.name}' echoing last user message for chat_completion.")

                pulse_state = current_state.get('purpose_pulse', {}).get('state', 'Dormant')
                if pulse_state == 'Active':
                    response_text = f"[PULSE ACTIVE] {response_text}"
                    logger.info(f"EchoAgent '{self.name}': Pulse is active, modifying echo.")
                
                response_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
                created_time = int(time.time())
                response_structure = {
                    "id": response_id,
                    "object": "chat.completion",
                    "created": created_time,
                    "model": payload.get("requested_model", "echo-model-unknown"),
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_text,
                            },
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
                }
                logger.debug(f"EchoAgent '{self.name}': Prepared response structure.")
                task_result = {
                    "status": "success",
                    "output": response_structure,
                    "summary": "Echoed last message in chat completion format."
                }
            
            # --- Handle Original Echo Task --- 
            elif intent == "echo": 
                content_to_echo = payload.get("content", "Nothing provided to echo.")
                repeated_content = ' '.join([content_to_echo] * self.max_repeat)
                echo_response = f"{self.prefix}{repeated_content}"
                logger.info(f"EchoAgent '{self.name}' performing echo task for 'echo' intent.")
                task_result = {"status": "success", "output": echo_response, "summary": "Default echo performed."}

            # --- Default/Unknown Task Handling --- 
            else:
                logger.warning(f"EchoAgent '{self.name}' received unknown intent for perform_task: '{intent}'")
                task_result = {"status": "error", "error": f"Unknown intent: {intent}", "summary": "Unknown intent received."}

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"EchoAgent '{self.name}' exception during perform_task (Intent: '{intent}'): {error_type} - {error_msg}", exc_info=True)
            task_result = {"status": "error", "error": f"{error_type}: {error_msg}", "summary": "Agent execution failed."}

        logger.info(f"EchoAgent '{self.name}': Exiting perform_task. Result status: {task_result.get('status', 'unknown')}")
        # --- Base class handles returning the final package --- #
        return task_result # Return only the core result

    async def receive_message(self, message: AgentMessage):
        """Handles direct messages sent to this agent (required by BaseAgent)."""
        sender = message.sender_id or "UnknownSender"
        logger.info(f"EchoAgent '{self.name}' received message from '{sender}'. Type: {message.intent}")
        # BaseAgent doesn't specify a return type, so just log/process
        pass 
        
    # --- Lifecycle Methods --- 
    async def startup(self):
        """Announces the agent's identity upon startup."""
        logger.info(f"[Pilgrim Awakens] -> {self.name}: I am {self.symbolic_identity.get('archetype')} -> {self.symbolic_identity.get('mythos_role')}")
        # No call to super().startup() as BaseAgent doesn't define it as async or implement it

    async def shutdown(self):
        """Optional shutdown logic for the agent."""
        logger.info(f"EchoAgent '{self.name}' shutting down.")
        # No call to super().shutdown() as BaseAgent doesn't define it as async or implement it 