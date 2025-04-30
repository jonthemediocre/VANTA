from models.trinity_node import TrinityNodeMemory # Import the memory model
import logging
from typing import Optional, Any
# --- Import global MemoryWeave if needed for direct event pushing ---
# from vanta_seed.core.memory_weave import MemoryWeave # Example
# --- Import BaseAgent or similar if using helper methods ---
# from ..base_agent import BaseAgent # Example if inheriting helper methods
import uuid # For generating tokens

logger = logging.getLogger(__name__)

class BasicExecutor:
    """A simple Executor that acts on the Evaluator's decision and generates a memory event."""
    
    # Assuming it might need orchestrator ref for BaseAgent helpers or direct MemoryWeave access
    # def __init__(self, orchestrator_ref=None):
    #     self.orchestrator = orchestrator_ref 
        
    def execute(self, memory: TrinityNodeMemory, decision: Optional[Any] = None):
        """Performs an action based on the decision and records it globally."""
        logger.info(f"BasicExecutor: Executing...")
        
        # Get decision from memory if not passed directly
        if decision is None:
            decision = memory.get_echo("last_evaluation_decision")
            
        if not decision:
             logger.warning("  No decision provided or found in memory echoes. Performing no action.")
             return "No decision to execute."
             
        logger.info(f"  Executing based on decision: '{decision}'")
        
        # Simulate action based on decision
        action_result_payload = {"decision_executed": decision, "status": "simulated_success"}
        if decision == "EXECUTE_DEFAULT_ACTION":
            logger.info("  Performing default action simulation.")
            action_result_payload["detail"] = "Default action executed."
        elif decision == "EXECUTE_BASED_ON_EXPLORATION":
            logger.info("  Performing action based on exploration simulation.")
            explorer_summary = memory.get_echo("last_exploration_summary")
            action_result_payload["detail"] = f"Action based on exploration: {explorer_summary}"
        elif decision == "EXECUTE_IDLE_MAINTENANCE":
             logger.info("  Performing idle maintenance simulation.")
             action_result_payload["detail"] = "Idle maintenance executed."
        else:
             logger.warning(f"  Unknown decision '{decision}'. Performing generic action simulation.")
             action_result_payload["detail"] = f"Generic action for unknown decision: {decision}"
             
        # --- Generate and Push Memory Event to Global Weave --- 
        global_memory_weave = memory.global_memory # Get reference from TrinityNodeMemory
        if global_memory_weave and hasattr(global_memory_weave, 'snapshot_drift'):
            # Use a simple token generation for now
            token = f"EXEC::{decision[:10].upper()}::BasicExecutor::{uuid.uuid4().hex[:4]}"
            
            memory_event = {
                 "archetype_token": token,
                 "drift_vector": 0.05, # Example drift value
                 "decision": decision, # Record the decision that led to this execution
                 "reason": f"Executed action based on evaluation.",
                 "payload": action_result_payload,
                 "source_agent": "BasicExecutor" # Identify the source role
                 # TODO: Need a way to link this to the Node ID (maybe pass node_id to execute?)
                 # TODO: Need a way to link parent_archetype_token (from evaluator/explorer?)
            }
            
            try:
                # Register the archetype first (important!) 
                if hasattr(global_memory_weave, 'register_archetype'):
                    global_memory_weave.register_archetype(token, memory_event) # Pass full event as metadata for now
                else:
                    logger.warning("MemoryWeave missing register_archetype method.")
                
                # Snapshot the drift event
                global_memory_weave.snapshot_drift(memory_event)
                logger.info(f"  Successfully recorded execution event to global MemoryWeave (Token: {token}).")
                memory.update_echo("last_execution_token", token) # Store token locally if needed
                return f"Execution successful, event {token} recorded."
            except Exception as e:
                 logger.error(f"  Error recording execution event to global MemoryWeave: {e}", exc_info=True)
                 return f"Execution simulated, but failed to record event: {e}"
        else:
            logger.warning("  Global MemoryWeave reference not available. Cannot record execution event.")
            return "Execution simulated, but event not recorded."
        # ---------------------------------------------------- 