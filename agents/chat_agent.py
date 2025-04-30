# agents/chat_agent.py
import logging
import asyncio
import uuid

class ChatAgent:
    """Handles chat requests, eventually interfacing with an LLM."""
    def __init__(self, agent_name, definition, blueprint, all_agent_definitions, memory_weave, identity_trees, orchestrator_ref):
        self.agent_name = agent_name
        self.definition = definition
        self.blueprint = blueprint
        self.all_agent_definitions = all_agent_definitions
        self.memory_weave = memory_weave
        self.identity_trees = identity_trees
        self.orchestrator = orchestrator_ref
        self.logger = logging.getLogger(f"Agent.{self.agent_name}")
        self.logger.info(f"ChatAgent '{self.agent_name}' initialized.")

    async def handle_chat_request(self, messages: list[dict]) -> dict:
        """
        Processes a list of messages (OpenAI format) and returns a response.
        Placeholder: Returns a hardcoded response.
        Later: Will call OpenAI/Ollama and integrate VANTA memory/context.
        """
        self.logger.info(f"Handling chat request with {len(messages)} messages.")
        last_user_message = "No user message found."
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
        
        # --- Placeholder Response ---
        response_content = f"VANTA acknowledges: '{last_user_message}'. (LLM response pending integration)"
        
        # Simulate some processing time
        await asyncio.sleep(0.1) 
        
        response = {
            "success": True,
            "content": response_content,
            "finish_reason": "stop" 
            # Potential: Add memory event to be circulated?
            # "memory_event": { ... } 
        }
        
        # --- Optional: Generate and circulate a memory event ---
        try:
            memory_event = {
                 "archetype_token": f"CHAT::{self.agent_name}::RESPONSE::{uuid.uuid4().hex[:4]}",
                 "drift_vector": 0.01, # Small drift for chat interaction
                 "decision": "chat_response_generated",
                 "reason": f"Generated response to user prompt ending: ...{last_user_message[-50:]}",
                 "payload": {"response_length": len(response_content)}, 
                 "source_agent": self.agent_name 
            }
            self.memory_weave.register_archetype(memory_event['archetype_token'], memory_event)
            # Use orchestrator's circulation trigger
            self.orchestrator._trigger_circulation(self.agent_name, memory_event)
            self.logger.debug("Chat response memory event circulated.")
        except Exception as e:
            self.logger.error(f"Failed to circulate chat memory event: {e}", exc_info=True)
        # ----------------------------------------------------
            
        return response

    # Optional: Standard handle method if tasks are added via queue
    # async def handle(self, task_data: dict):
    #     messages = task_data.get("payload", {}).get("messages", [])
    #     if messages:
    #         return await self.handle_chat_request(messages)
    #     else:
    #         self.logger.warning(f"Chat task {task_data.get('task_id')} received without messages in payload.")
    #         return {"success": False, "content": "Error: No messages provided.", "finish_reason": "error"} 