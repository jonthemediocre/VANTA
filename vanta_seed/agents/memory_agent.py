import asyncio
from typing import Dict, Any, Optional, List
import logging
from collections import deque

from .base_agent import BaseAgent
from .agent_utils import PilgrimCommunicatorMixin
from vanta_seed.core.models import AgentConfig, TaskData
from vanta_seed.core.data_models import AgentMessage
from vanta_seed.core.memory_store import MemoryStore

logger = logging.getLogger(__name__)

class MemoryAgent(BaseAgent, PilgrimCommunicatorMixin):
    """
    An agent responsible for storing and retrieving information.
    Acts as a basic short-term memory store.
    """
    def __init__(self, name: str, config: AgentConfig, logger: logging.Logger, orchestrator_ref: Optional[Any] = None, memory_store: Optional[MemoryStore] = None):
        """
        Initializes the MemoryAgent.
        Uses the BaseAgent __init__ for standard setup.
        """
        super().__init__(name=name, config=config, logger=logger, orchestrator_ref=orchestrator_ref)

        # Config values are now in self.config
        # Use direct attribute access for Pydantic models, provide default if attribute might be missing
        self.storage_limit = getattr(self.config.settings, 'storage_limit', 100)
        self.retrieval_mode = getattr(self.config.settings, 'retrieval_mode', 'recent')
        
        # --- Initialize memory store --- 
        # Ensure _memory is initialized correctly, potentially based on state if persistence was added
        self._memory: deque = deque(maxlen=self.storage_limit)
        # Example: Load from initial state if present?
        # initial_mem = self.config.initial_state.get("_memory_data", []) # Access via config if needed
        # if initial_mem:
        #     self._memory.extend(initial_mem)

        # --- Store the injected MemoryStore --- 
        if memory_store is None:
            # Log an error or raise if MemoryStore is absolutely required
            self.logger.error(f"MemoryStore not injected into MemoryAgent '{self.name}'. Memory functions will fail.")
            # Or raise ValueError("MemoryStore instance is required for MemoryAgent")
        self.memory_store = memory_store
        # --------------------------------------

        self.logger.info(f"MemoryAgent '{self.name}' initialized. Limit: {self.storage_limit}")
        
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
        Stores or retrieves memory items using the injected MemoryStore.
        Handles intents: 'store_memory' and 'request_memory_retrieval'.
        """
        intent = task_data.get("intent")
        payload = task_data.get("payload", {})
        agent_id = current_state.get('id', self.name) # Use node ID if available, else agent name
        task_result = {}

        if not self.memory_store:
            self.logger.error(f"MemoryStore not available for MemoryAgent '{self.name}'. Cannot perform task '{intent}'.")
            return {"error": "MemoryStore not configured"}

        try:
            if intent == "store_memory":
                memory_type = payload.get("type", "generic")
                memory_content = payload.get("content")
                originating_agent = payload.get("source_agent", agent_id) # Use source if provided

                if not memory_content or not isinstance(memory_content, dict):
                    task_result = {"status": "failure", "error": "Invalid or missing 'content' dictionary in payload"}
                else:
                    # --- Add logging around add_item --- 
                    self.logger.debug(f"Attempting to add item to MemoryStore. Agent: {originating_agent}, Type: {memory_type}")
                    success = self.memory_store.add_item(originating_agent, memory_type, memory_content)
                    self.logger.debug(f"MemoryStore.add_item returned: {success}")
                    # -----------------------------------
                    if success:
                        task_result = {"status": "success", "message": "Memory stored."}
                        # --- ADDED: Explicitly save after adding --- 
                        # --- Add logging around save --- 
                        self.logger.debug(f"Attempting to save MemoryStore to YAML.")
                        save_success = self.memory_store.save()
                        self.logger.debug(f"MemoryStore.save returned: {save_success}")
                        # -------------------------------
                        if not save_success:
                             self.logger.warning(f"Failed to save memory store to YAML after adding item for {originating_agent}")
                        # -------------------------------------------
                    else:
                        task_result = {"status": "failure", "error": "Failed to add item to memory store."}
            
            elif intent == "request_memory_retrieval":
                query = payload.get("query") # e.g., "last_item", "search_term", or complex filter dict
                query_type = payload.get("type") # Optional filter by type
                limit = payload.get("count", 5)
                query_agent_id = payload.get("agent_id") # Optional filter by agent
                query_tags = payload.get("tags") # Optional filter by tags (list)
                query_start_time = payload.get("start_time") # Optional filter by time
                query_end_time = payload.get("end_time") # Optional filter by time
                
                retrieved_items = []
                # --- Use get_items_filtered for richer queries --- 
                if query == "search_term" and isinstance(payload.get("search_query"), str):
                     # Handle specific search intent
                     search_query_str = payload.get("search_query")
                     retrieved_items = self.memory_store.search_items(
                         query=search_query_str, 
                         agent_id=query_agent_id, 
                         limit=limit
                     )
                     self.logger.info(f"Retrieved {len(retrieved_items)} items via search ('{search_query_str}') from store based on payload: {payload}")
                elif query == "last_item" or not query: 
                    # Default to filtered retrieval, passing all relevant filters
                    retrieved_items = self.memory_store.get_items_filtered(
                        agent_id=query_agent_id, 
                        type=query_type, 
                        tags=query_tags,
                        start_time=query_start_time,
                        end_time=query_end_time,
                        limit=limit
                    )
                    self.logger.info(f"Retrieved {len(retrieved_items)} items using filtered get from store based on payload: {payload}")
                # --- End Filtered Get --- 
                # Remove old simple search logic
                # elif isinstance(query, str):
                #     retrieved_items = self.memory_store.search_items(query=query, agent_id=query_agent_id, limit=limit)
                #     self.logger.info(f"Retrieved {len(retrieved_items)} items via search ('{query}') from store based on payload: {payload}")
                else:
                    task_result = {"status": "failure", "error": "Invalid 'query' parameter or missing 'search_query' for search intent."}
                    return task_result

                task_result = {"status": "success", "retrieved_items": retrieved_items, "query": payload}

            elif intent == "identity":
                 archetype = self.symbolic_identity.archetype if hasattr(self.symbolic_identity, 'archetype') else 'UnknownArchetype'
                 mythos_role = self.symbolic_identity.mythos_role if hasattr(self.symbolic_identity, 'mythos_role') else 'UnknownRole'
                 identity_str = f"I am {archetype} -> {mythos_role}. I guard memories."
                 task_result = {"status": "success", "output": identity_str, "summary": "Returned symbolic identity.", "store_size": self.memory_store.get_store_size()}

            else:
                logger.warning(f"MemoryAgent '{self.name}' received unknown task intent: '{intent}'")
                task_result = {"status": "failure", "error": f"Unknown intent: {intent}"}

        except Exception as e:
            self.logger.error(f"MemoryAgent '{self.name}' error during perform_task for intent '{intent}': {e}", exc_info=True)
            task_result = {"status": "failure", "error": str(e)}

        return task_result

    async def receive_message(self, message: AgentMessage):
        """Handles direct messages, specifically memory retrieval requests."""
        sender_node_id = message.sender_id # e.g., node_SymbolicAgent_98a4
        correlation_id = message.correlation_id
        
        # Default response
        response_payload = {"status": "failure", "error": "Could not process message"}
        response_intent = "message_processing_failed"

        # Check MemoryStore availability
        if not self.memory_store:
            self.logger.error(f"MemoryStore not available for MemoryAgent '{self.name}'. Cannot process message intent '{message.intent}'.")
            response_payload["error"] = "Internal MemoryStore error."
        elif message.intent == "request_memory_retrieval":
            try:
                payload = message.payload or {}
                query = payload.get("query")
                query_type = payload.get("type")
                limit = payload.get("count", 5)
                query_agent_id = payload.get("agent_id")
                query_tags = payload.get("tags")
                query_start_time = payload.get("start_time")
                query_end_time = payload.get("end_time")

                retrieved_items = []
                # --- Use get_items_filtered for richer queries --- 
                if query == "search_term" and isinstance(payload.get("search_query"), str):
                     search_query_str = payload.get("search_query")
                     retrieved_items = self.memory_store.search_items(
                         query=search_query_str, 
                         agent_id=query_agent_id, 
                         limit=limit
                     )
                     self.logger.info(f"[A2A] Retrieved {len(retrieved_items)} items via search ('{search_query_str}') for {sender_node_id}")
                elif query == "last_item" or not query:
                    retrieved_items = self.memory_store.get_items_filtered(
                        agent_id=query_agent_id, 
                        type=query_type, 
                        tags=query_tags,
                        start_time=query_start_time,
                        end_time=query_end_time,
                        limit=limit
                    )
                    self.logger.info(f"[A2A] Retrieved {len(retrieved_items)} items using filtered get for {sender_node_id}")
                # --- End Filtered Get --- 
                # Remove old simple search logic
                # elif isinstance(query, str):
                #     retrieved_items = self.memory_store.search_items(query=query, agent_id=query_agent_id, limit=limit)
                #     self.logger.info(f"[A2A] Retrieved {len(retrieved_items)} items via search ('{query}') for {sender_node_id}")
                else:
                     response_payload = {"status": "failure", "error": "Invalid 'query' or missing 'search_query' in message payload"}
                     response_intent = "invalid_request"
                     # Go directly to sending response below

                # If retrieval was attempted and didn't error out immediately above
                if response_intent != "invalid_request":
                    response_payload = {"status": "success", "retrieved_items": retrieved_items, "query": payload}
                    response_intent = "memory_retrieval_response"
                    
            except Exception as e:
                self.logger.error(f"Error processing A2A request_memory_retrieval from {sender_node_id}: {e}", exc_info=True)
                response_payload = {"status": "failure", "error": f"Error retrieving memory: {str(e)}"}
                response_intent = "memory_retrieval_failed"
        
        elif message.intent == "store_memory": # Allow storing via message too
             try:
                payload = message.payload or {}
                memory_type = payload.get("type", "message")
                memory_content = payload.get("content")
                originating_agent = message.sender_id # Attribute storage to sender

                if not memory_content or not isinstance(memory_content, dict):
                    response_payload = {"status": "failure", "error": "Invalid or missing 'content' dictionary in payload"}
                    response_intent = "invalid_request"
                else:
                    success = self.memory_store.add_item(originating_agent, memory_type, memory_content)
                    if success:
                        response_payload = {"status": "success", "message": "Memory stored via message."}
                        response_intent = "memory_stored_confirmation"
                    else:
                        response_payload = {"status": "failure", "error": "Failed to add item to memory store via message."}
                        response_intent = "memory_store_failed"
             except Exception as e:
                self.logger.error(f"Error processing A2A store_memory from {sender_node_id}: {e}", exc_info=True)
                response_payload = {"status": "failure", "error": f"Error storing memory: {str(e)}"}
                response_intent = "memory_store_failed"
        else:
            self.logger.warning(f"MemoryAgent received unhandled message intent '{message.intent}' from {sender_node_id}")
            response_payload = {"status": "failure", "error": f"Unsupported intent: {message.intent}"}
            response_intent = "message_not_understood" # Use a different intent for clarity

        # Send response back to the original sender if required
        if message.requires_response:
             # --- Extract simple name from sender_id --- 
             sender_node_id = message.sender_id # e.g., node_SymbolicAgent_98a4
             sender_name_parts = sender_node_id.split('_')
             sender_simple_name = sender_name_parts[1] if len(sender_name_parts) > 1 else sender_node_id # Fallback to full ID if format unexpected
             # -------------------------------------------
             self.logger.debug(f"Sending '{response_intent}' response to {sender_simple_name} (correlation: {correlation_id}) based on sender ID {sender_node_id}")
             # --- Ensure we are using the correlation ID from the *incoming* message --- 
             incoming_correlation_id = message.correlation_id # Explicitly capture
             # ----------------------------------------------------------------------
             # --- Construct Response Message Object --- 
             response_message = AgentMessage(
                 sender_id=self.node_id, # MemoryAgent is the sender
                 receiver_id=sender_simple_name, # Target the original sender by name
                 intent=response_intent,
                 payload=response_payload,
                 requires_response=False,
                 correlation_id=incoming_correlation_id # Link back to the original request
             )
             # --------------------------------------
             await self.send_message(response_message) # <<< Send the constructed message object
        else:
            self.logger.debug(f"Not sending response for message {message.message_id} as requires_response is False.")

    async def shutdown(self):
        logger.info(f"MemoryAgent '{self.name}' shutting down.") 