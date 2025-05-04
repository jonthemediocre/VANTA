import asyncio
from typing import Dict, Any, Optional, List
import logging
import json # For potential serialization

from .base_agent import BaseAgent
from .agent_utils import PilgrimCommunicatorMixin
from vanta_seed.core.models import AgentConfig, TaskData
from vanta_seed.core.data_models import AgentMessage

logger = logging.getLogger(__name__)

class SymbolicAgent(BaseAgent, PilgrimCommunicatorMixin):
    """
    An agent focused on symbolic manipulation, like compression or summarization.
    (Basic implementation for now).
    """
    def __init__(self, name: str, config: AgentConfig, logger: logging.Logger, orchestrator_ref: Optional[Any] = None):
        """
        Initializes the SymbolicAgent.
        Uses the BaseAgent __init__ for standard setup.
        """
        super().__init__(name=name, config=config, logger=logger, orchestrator_ref=orchestrator_ref)

        # Access settings via self.config
        # Use direct attribute access for Pydantic models, provide default if attribute might be missing
        self.compression_level = getattr(self.config.settings, 'compression_level', 0.8)
        self.target_domains = getattr(self.config.settings, 'target_domains', ['identity', 'dream fragments'])

        # Symbolic identity is now loaded by BaseAgent into self.symbolic_identity
        # self.symbolic_identity = config.symbolic_identity

        # --- Add dictionary for pending responses --- 
        self._pending_responses: Dict[str, asyncio.Future] = {}
        # ------------------------------------------

        self.logger.info(f"SymbolicAgent '{self.name}' initialized. Level: {self.compression_level}, Target: {self.target_domains}")

    async def startup(self):
        """Announces the agent's identity upon startup."""
        logger.info(f"[Pilgrim Awakens] -> {self.name}: I am {self.symbolic_identity.get('archetype')} -> {self.symbolic_identity.get('mythos_role')}")
        # No super().startup()

    async def perform_task(self, task_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs symbolic compression. 
        MODIFIED: Sends A2A request to MemoryAgent first, then uses placeholder data.
        """
        task_result = {}
        intent = task_data.get("intent")
        payload = task_data.get("payload", {})
        task_id = task_data.get("task_id", "unknown_task") # Get task_id if available
        
        try:
            if intent == "compress_symbolic":
                data_to_compress = payload.get("data") # Original data if provided
                retrieved_data = None
                correlation_id = None # Initialize correlation_id

                # --- A2A Request to MemoryAgent --- 
                memory_agent_name = "MemoryAgent" # Use simple name
                self.logger.info(f"SymbolicAgent '{self.name}' requesting memory from '{memory_agent_name}' for task {task_id}.")
                request_payload = {"query": "last_item", "count": 1} # Example request
                
                # Create a future to wait for the response
                future = asyncio.get_running_loop().create_future()
                
                # --- Create the message object FIRST ---
                request_message = AgentMessage(
                    sender_id=self.node_id,
                    receiver_id=memory_agent_name, # Use simple name
                    intent="request_memory_retrieval",
                    payload=request_payload,
                    requires_response=True
                    # message_id is auto-generated
                )
                # --- Set correlation ID to the message ID ---
                request_message.correlation_id = request_message.message_id # Link request to potential response
                correlation_id = request_message.message_id # Store for future lookup key
                # -----------------------------------------

                # Store the future *before* sending the message
                if correlation_id:
                    self._pending_responses[correlation_id] = future
                    self.logger.debug(f"Stored future for correlation ID: {correlation_id}")
                else:
                    self.logger.error("Failed to generate correlation ID (message_id). Cannot wait for response.")
                    # Handle error appropriately - maybe don't proceed?
                    future.set_exception(ValueError("Failed to generate message_id for correlation"))


                # Send the message *using the constructed message object*
                # message_sent_id = await self.send_message_obj(request_message) # Use a potentially new method
                message_sent_id = await self.send_message(request_message) # <<< CORRECTED: Use send_message
                
                # Check if sending succeeded before waiting
                if message_sent_id and correlation_id and not future.done():
                    self.logger.info(f"Memory request message ({correlation_id}) sent to {memory_agent_name}. Waiting for response...")
                    try:
                        # Wait for the future to be resolved by receive_message
                        retrieved_data = await asyncio.wait_for(future, timeout=5.0)
                        self.logger.info(f"Received response for {correlation_id}: {retrieved_data}")
                    except asyncio.TimeoutError:
                        self.logger.warning(f"Timeout waiting for response from MemoryAgent for message {correlation_id}.")
                        retrieved_data = None # Indicate timeout
                    except Exception as e:
                         self.logger.error(f"Error waiting for future for message {correlation_id}: {e}", exc_info=True)
                         retrieved_data = None
                    finally:
                        # Clean up the pending response entry *after* waiting or timeout
                        self._pending_responses.pop(correlation_id, None)
                elif not message_sent_id:
                     self.logger.error(f"Failed to send message {correlation_id} to {memory_agent_name}. Aborting wait.")
                     # Ensure future is cleaned up if send fails
                     if correlation_id:
                          self._pending_responses.pop(correlation_id, None)
                          if not future.done(): future.set_exception(RuntimeError("Message sending failed"))
                     retrieved_data = None # <<< Ensure retrieved_data is None if send failed
                # --- End A2A Request ---
                
                # --- ADDED: Explicitly check future state AFTER wait_for block --- 
                if future.done() and not future.cancelled():
                    try:
                        final_future_result = future.result() # Get the actual result stored in the future
                        self.logger.debug(f"After wait_for block - Future is DONE. Result type: {type(final_future_result)}, value: {final_future_result}")
                        # <<< Re-assign retrieved_data based on the future's actual result >>>
                        retrieved_data = final_future_result 
                    except Exception as e:
                         self.logger.error(f"After wait_for block - Future is DONE but getting result failed: {e}")
                         retrieved_data = {"error": "Future result retrieval failed"} # Indicate error
                elif future.cancelled():
                     self.logger.debug("After wait_for block - Future was CANCELLED.")
                     # retrieved_data should already be None from the TimeoutError block
                else:
                    # This case (future not done, not cancelled) should ideally not happen here
                     self.logger.warning("After wait_for block - Future is NOT DONE and NOT CANCELLED. State is unexpected.")
                     # retrieved_data might be None from assignment failure or error block
                # -----------------------------------------------------------------
                
                # --- Use retrieved data in Compression Logic --- 
                # --- ADDED: Debug log before check --- 
                self.logger.debug(f"Before check - retrieved_data type: {type(retrieved_data)}, value: {retrieved_data}")
                # -------------------------------------
                # Use retrieved_data if available and successful, otherwise fallback
                data_used_for_compression = None
                retrieval_outcome_status = "unknown"
                # --- CORRECTED: Check retrieved_data structure --- 
                if isinstance(retrieved_data, dict) and retrieved_data.get('status') == 'success':
                    retrieval_outcome_status = "success"
                # -------------------------------------------------
                    # Assuming the payload structure from MemoryAgent's response
                    items = retrieved_data.get('retrieved_items', [])
                    # --- Use first item's content if exists --- 
                    if items and isinstance(items[0], dict):
                         data_used_for_compression = items[0].get('content') # Get the content dict
                         self.logger.info(f"Using retrieved data for compression: {data_used_for_compression}")
                    else:
                         self.logger.warning("Retrieval success, but no items or invalid item structure found in response. Using placeholder.")
                         data_used_for_compression = data_to_compress or {"placeholder": "Retrieval successful but no items found"}
                    # ------------------------------------------
                elif retrieved_data is None:
                    # Handle timeout or send failure cases explicitly
                    retrieval_outcome_status = "timeout_or_send_failed"
                    data_used_for_compression = data_to_compress or {"placeholder": "No data retrieved (timeout/send failure)"}
                else: # Handle explicit failure responses from MemoryAgent
                    retrieval_outcome_status = retrieved_data.get('status', 'failure')
                    self.logger.warning(f"Using original/placeholder data for compression due to memory retrieval failure ({retrieval_outcome_status}). Original: {data_to_compress}")
                    data_used_for_compression = data_to_compress or {"placeholder": f"No data retrieved ({retrieval_outcome_status})"}
                # -----------------------------------------------------------------
                
                # Ensure we have *some* data to compress, even if it's just a placeholder
                if data_used_for_compression is None:
                    data_used_for_compression = {"placeholder": "Fallback - No data available"}
                    
                symbolic_representation = f"[Compressed:{self.compression_level}]{json.dumps(data_used_for_compression)[:50]}..."
                logger.info(f"SymbolicAgent '{self.name}' performed symbolic compression. Task: {task_id}")
                # Correct the retrieval status passed back
                task_result = {"status": "success", "symbolic_form": symbolic_representation, "retrieval_status": retrieval_outcome_status}
                # -----------------------------------------------------------------

            elif intent == "identity":
                 archetype = self.symbolic_identity.archetype if hasattr(self.symbolic_identity, 'archetype') else 'UnknownArchetype'
                 mythos_role = self.symbolic_identity.mythos_role if hasattr(self.symbolic_identity, 'mythos_role') else 'UnknownRole'
                 identity_str = f"I am {archetype} -> {mythos_role}."
                 task_result = {"status": "success", "output": identity_str, "summary": "Returned symbolic identity."}
                 
            else:
                logger.warning(f"SymbolicAgent '{self.name}' received unknown task type: '{intent}'")
                task_result = {"error": f"Unknown task type: {intent}"}
                
        except Exception as e:
            logger.error(f"SymbolicAgent '{self.name}' error during perform_task: {e}", exc_info=True)
            task_result = {"error": str(e)}
            
        return task_result # Return only core result

    async def receive_message(self, message: AgentMessage):
        """Handles direct messages (required by BaseAgent).
           Specifically looks for responses correlated to pending requests.
        """
        sender = message.sender_id or "UnknownSender"
        correlation_id = message.correlation_id
        
        self.logger.info(f"SymbolicAgent '{self.name}' received message from '{sender}'. Intent: {message.intent}, CorrID: {correlation_id}")
        
        # Attempt to get the future *first*
        future = self._pending_responses.get(correlation_id)

        if future: # Check if we found a future for this ID
            if not future.done():
                self.logger.info(f"Found pending future for correlation ID: {correlation_id}. Setting result.")
                response_payload = message.payload or {}
                try:
                    # Attempt to set the result. This might fail if the future
                    # was *just* cancelled by a timeout, but it's worth trying.
                    future.set_result(response_payload)
                except asyncio.InvalidStateError:
                    self.logger.warning(f"Could not set result for future {correlation_id}, likely already cancelled by timeout.")
                # We don't remove the future here; the finally block in perform_task handles cleanup.
            elif future.done():
                self.logger.warning(f"Received response for already completed/cancelled future: {correlation_id}")
        elif correlation_id:
            # If we have a correlation ID but no matching future, it likely timed out
            # and was removed by the finally block.
            self.logger.warning(f"Received response for {correlation_id}, but no pending future found (likely timed out).")
        else:
            # Handle messages that are not responses to our requests
            self.logger.warning(f"Received uncorrelated message from {sender}. Intent: {message.intent}. Ignoring.")

        # No 'pass' needed, we've handled the logic.

    async def shutdown(self):
        logger.info(f"SymbolicAgent '{self.name}' shutting down.")
        # No super().shutdown() 

    # <<< ADD Concrete execute method to satisfy ABC check >>>
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
    # <<< END ADDED execute method >>> 