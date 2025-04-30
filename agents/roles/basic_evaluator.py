from models.trinity_node import TrinityNodeMemory # Import the memory model
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class BasicEvaluator:
    """A simple Evaluator that checks constraints and exploration results."""
    def evaluate(self, memory: TrinityNodeMemory, exploration_result: Optional[Any] = None):
        """Makes a simple decision based on constraints and exploration echoes."""
        logger.info(f"BasicEvaluator: Evaluating...")
        
        # 1. Check Destiny Constraints
        constraint_key = "max_drift_allowed"
        max_drift = memory.get_constraint(constraint_key)
        if max_drift is not None:
            logger.info(f"  Constraint '{constraint_key}' found: {max_drift}")
            # TODO: Compare against actual drift if available in memory echoes
            pass
        else:
             logger.info(f"  No constraint found for '{constraint_key}'.")
             
        # 2. Check Local Echoes from Explorer
        explorer_summary = memory.get_echo("last_exploration_summary")
        if explorer_summary:
            logger.info(f"  Found Explorer echo: '{explorer_summary}'")
            # Simple decision based on exploration result
            if "No results found" in explorer_summary:
                decision = "EXECUTE_DEFAULT_ACTION"
                logger.info(f"  Decision: {decision} (Explorer found nothing)")
                memory.update_echo("last_evaluation_decision", decision)
                return decision
            else:
                 decision = "EXECUTE_BASED_ON_EXPLORATION"
                 logger.info(f"  Decision: {decision} (Explorer found something)")
                 memory.update_echo("last_evaluation_decision", decision)
                 return decision
        else:
             logger.info(f"  No recent Explorer echo found.")
             
        # Default decision if no other logic applies
        default_decision = "EXECUTE_IDLE_MAINTENANCE"
        logger.info(f"  Decision: {default_decision} (Default)")
        memory.update_echo("last_evaluation_decision", default_decision)
        return default_decision 