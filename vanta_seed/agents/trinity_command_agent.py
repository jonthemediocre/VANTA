"""
Trinity Command Agent: Acts as the Master Planner and TriNode Ritual Orchestrator,
interfacing between the VANTA Kernel and the TriNodeController.
"""

import logging
from typing import Dict, Any, Optional
import uuid

from vanta_seed.agents.base_agent import BaseAgent
from vanta_seed.core.models import AgentConfig, TaskData
from vanta_seed.swarm.trinode import TriNodeController # Import the controller

logger = logging.getLogger(__name__)

# Define result status constants specific to this agent if needed
RESULT_RITUAL_ASSIGNED = "RITUAL_ASSIGNED"
RESULT_COLLAPSE_RECEIVED = "COLLAPSE_RECEIVED"
RESULT_ERROR = "ERROR"
RESULT_UNKNOWN_INTENT = "UNKNOWN_INTENT"

class TrinityCommandAgent(BaseAgent):
    """Orchestrates rituals by assigning them to appropriate TriNodes via TriNodeController."""

    def __init__(self, name: str, config: AgentConfig, logger_instance: logging.Logger, trinode_controller: TriNodeController, orchestrator_ref: Optional['VantaMasterCore'] = None):
        """Initializes with a required TriNodeController instance."""
        super().__init__(name, config, logger_instance, orchestrator_ref)
        self.logger.info(f"TrinityCommandAgent '{self._name}' initializing...")
        if not isinstance(trinode_controller, TriNodeController):
             raise TypeError("TrinityCommandAgent requires a valid TriNodeController instance.")
        self.trinode_controller = trinode_controller
        self.logger.info(f"TrinityCommandAgent '{self._name}' initialized with TriNodeController.")

    async def perform_task(self, task_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Receives high-level ritual requests and delegates them to the TriNodeController.
        Also handles the final collapse result reported back from TriNodes.
        """
        intent = task_data.get('intent')
        payload = task_data.get('payload', {})
        self.logger.debug(f"TrinityCommandAgent '{self.name}' received task: {intent}")

        if not self.trinode_controller:
            # This check might be redundant if required in init, but safe
            self.logger.error("TriNodeController not available.")
            return {"status": RESULT_ERROR, "message": "TriNodeController reference missing."}

        if intent == 'initiate_ritual':
            target_trinode = payload.get('target_trinode') # Name/ID of the TriNode
            ritual_name = payload.get('ritual_name')
            ritual_input = payload.get('ritual_input') # Data for the ritual
            task_id = payload.get('task_id', str(uuid.uuid4())) # Generate task ID if not provided

            if not target_trinode or not ritual_name or ritual_input is None:
                self.logger.error("Missing target_trinode, ritual_name, or ritual_input for initiate_ritual.")
                return {"status": RESULT_ERROR, "message": "Invalid payload for initiate_ritual."}

            try:
                self.logger.info(f"Attempting to assign ritual '{ritual_name}' (Task ID: {task_id}) to TriNode '{target_trinode}'...")
                
                # Prepare details for the controller
                ritual_details = {
                    "task_id": task_id,
                    "ritual_name": ritual_name,
                    "input_data": ritual_input
                }
                
                # Delegate to TriNodeController (which handles finding members, communication etc.)
                assignment_result = await self.trinode_controller.assign_ritual_to_trinode(target_trinode, ritual_details)
                
                # Check result from controller (assuming it returns status/message)
                if assignment_result.get("status") == "ASSIGNED":
                    self.logger.info(f"Ritual '{ritual_name}' successfully assigned to TriNode '{target_trinode}'.")
                    # TODO: Track ongoing tasks/rituals to await final collapse?
                    return {"status": RESULT_RITUAL_ASSIGNED, "trinode": target_trinode, "task_id": task_id}
                else:
                     self.logger.error(f"TriNodeController failed to assign ritual: {assignment_result.get('message', 'Unknown error')}")
                     return {"status": RESULT_ERROR, "message": f"Controller assignment failed: {assignment_result.get('message')}"}

            except Exception as e:
                self.logger.error(f"Error assigning ritual '{ritual_name}' to TriNode '{target_trinode}': {e}", exc_info=True)
                return {"status": RESULT_ERROR, "message": f"Error assigning ritual: {e}"}

        elif intent == 'handle_trinode_final_collapse':
             # This intent is likely triggered internally or by the orchestrator 
             # when the TriNodeController reports a final collapse.
             trinode_name = payload.get('trinode_name')
             task_id = payload.get('task_id')
             final_result = payload.get('final_result') # The consolidated output from the TriNode
             status = payload.get('status', 'UNKNOWN') # Status of the ritual (e.g., COMPLETED, FAILED)
             
             if not trinode_name or not task_id or final_result is None:
                 self.logger.error("Missing required fields in handle_trinode_final_collapse payload.")
                 return {"status": RESULT_ERROR, "message": "Invalid collapse payload"}

             self.logger.info(f"Processing final collapse for Task ID '{task_id}' from TriNode '{trinode_name}'. Status: {status}")
             
             # TODO: Implement logic to process the final result:
             # 1. Update Task Status: Mark the original task (if tracked) as completed/failed.
             # 2. Store Result: Save the final_result to appropriate memory (e.g., RelicRepository, Vector Store).
             # 3. Notify Kernel/Orchestrator: Signal completion/failure to the higher level.
             # 4. Trigger Follow-up Actions: Based on the result, initiate next steps in a workflow.
             # 5. Update Plan: Reflect completion in THEPLAN.md or TODO.md if applicable.
             
             self.logger.info(f"Placeholder: Final collapse for task {task_id} processed.")
             
             # Optionally, forward result to CollapseMonitorAgent
             if self.orchestrator: # Assuming orchestrator can route messages
                 monitor_payload = payload.copy()
                 monitor_payload['processed_by'] = self.name
                 await self.orchestrator.route_task_to_agent('CollapseMonitorAgent-01', # Needs config
                                                          'process_ritual_collapse', monitor_payload)

             return {"status": RESULT_COLLAPSE_RECEIVED, "trinode": trinode_name, "task_id": task_id}

        else:
            self.logger.warning(f"TrinityCommandAgent received unhandled intent: {intent}")
            return {"status": RESULT_UNKNOWN_INTENT}

    async def startup(self):
        await super().startup()
        if not self.trinode_controller:
             self.logger.error("CRITICAL: TrinityCommandAgent started without a TriNodeController instance!")
             # Consider preventing full startup or entering a degraded state
        self.logger.info(f"TrinityCommandAgent '{self._name}' specific startup routines complete.")

    async def shutdown(self):
        self.logger.info(f"TrinityCommandAgent '{self._name}' shutting down...")
        await super().shutdown() 