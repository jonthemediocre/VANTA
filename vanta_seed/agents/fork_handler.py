# vanta_seed/agents/fork_handler.py

import logging
import uuid
from core.base_agent import BaseAgent
# --- Import GatingNode ---
from vanta_seed.core.gating_node import GatingNode # Assuming GatingNode is in vanta_seed/core
# --- Import MemoryWeave --- 
from vanta_seed.core.memory_weave import MemoryWeave 

class ForkHandler(BaseAgent):
    """Agent for managing multi-collapse pathways and destiny branch management."""

    def __init__(self, agent_name: str, definition: dict, blueprint: dict, all_agent_definitions: dict, memory_weave: MemoryWeave, orchestrator_ref=None, **kwargs):
        super().__init__(agent_name, definition, blueprint, all_agent_definitions, orchestrator_ref, **kwargs)
        self.logger = logging.getLogger(f"Agent.{agent_name}")
        self.decision_log = [] # Kept for internal logging if needed, but primary log is MemoryWeave
        self.gating_node = GatingNode(config=self.config.get('gating_node_config')) # Pass potential config
        # --- Store MemoryWeave instance --- 
        self.memory_weave = memory_weave 
        if not self.memory_weave:
             # Fallback or error if MemoryWeave wasn't passed
             self.logger.error("MemoryWeave instance was not provided to ForkHandler!")
             # Depending on strictness, could raise error or use a dummy/null object
             # For now, log error and continue; methods using it will fail gracefully
             # self.memory_weave = DummyMemoryWeave() # Example of fallback

    async def handle(self, task_data: dict):
        """Handle fork-related tasks."""
        intent = task_data.get('intent')
        payload = task_data.get('payload', {})
        task_id = task_data.get('task_id')

        if intent == 'evaluate_fork_potential':
             branches = payload.get('branches', [])
             context = payload.get('context', {})
             drift_vector = payload.get('drift_vector')
             cycle_depth = payload.get('cycle_depth', 1)

             # Use GatingNode to decide if fork is needed
             if self.gating_node.evaluate_drift(drift_vector, cycle_depth):
                 selected_branch_data = self.select_branch(branches, context, drift_vector=drift_vector, cycle_depth=cycle_depth)
                 # Decision logging now happens inside select_branch via fork_decision_log
                 if selected_branch_data:
                     return {"success": True, "action": "fork", "selected_branch": selected_branch_data, "task_id": task_id}
                 else:
                     # Handle case where selection failed even after deciding to fork
                     return {"success": False, "message": "Decided to fork, but branch selection failed.", "task_id": task_id}
             else:
                 # Log decision to continue breath via fork_decision_log
                 continue_log_entry = {
                     "decision": "continue_breath",
                     "reason": "Drift within threshold",
                     "drift_vector": drift_vector,
                     "cycle_depth": cycle_depth,
                     "task_id": task_id,
                     # No archetype needed here
                 }
                 self.fork_decision_log(continue_log_entry) # This will now snapshot to MemoryWeave
                 return {"success": True, "action": "continue", "task_id": task_id}

        elif intent == 'merge_forked_branches':
            branch1 = payload.get('branch1')
            branch2 = payload.get('branch2')
            if not branch1 or not branch2:
                return {"success": False, "message": "Missing branch data for merge", "task_id": task_id}
            merged_branch = self.merge_branches(branch1, branch2)
            # Logging/snapshotting happens inside merge_branches
            return {"success": True, "action": "merged", "merged_branch": merged_branch, "task_id": task_id}

        self.logger.warning(f"ForkHandler received unhandled intent: {intent}")
        return {"success": False, "message": f"ForkHandler unhandled intent: {intent}", "task_id": task_id}

    def select_branch(self, branches: list, context: dict, drift_vector=None, cycle_depth=None):
        """Select the best destiny branch and log decision to MemoryWeave."""
        self.logger.debug(f"Selecting branch from {len(branches)} potential branches.")
        # TODO: Implement actual policy-driven branch selection logic
        selected_branch_data = branches[0] if branches else None

        log_entry = {
            "context": context,
            "drift_vector": drift_vector,
            "cycle_depth": cycle_depth
        }

        if selected_branch_data:
            branch_type = selected_branch_data.get('type', 'UNKNOWN').upper()
            semantic_hint = selected_branch_data.get('hint', 'Default')
            token_uuid = uuid.uuid4().hex[:4]
            archetype_token = f"ARCH::{branch_type}::{semantic_hint}::{token_uuid}"
            selected_branch_data['archetype_token'] = archetype_token # Tag branch data

            log_entry.update({
                "decision": "select_branch",
                "selected_branch_id": selected_branch_data.get('id', 'N/A'),
                "archetype_token": archetype_token,
                "reason": "Policy selected highest score (placeholder)" # TODO: Update reason
            })
            self.logger.info(f"Selected branch with archetype: {archetype_token}")
            # Log decision (which now includes snapshotting/registration)
            self.fork_decision_log(log_entry)
            return selected_branch_data
        else:
            self.logger.warning("No branches provided to select_branch.")
            log_entry.update({
                "decision": "no_selection",
                "reason": "No branches available"
                # No archetype needed
            })
            self.fork_decision_log(log_entry)
            return None

    def merge_branches(self, branch1: dict, branch2: dict) -> dict:
        """Merge two collapse paths and log decision to MemoryWeave."""
        self.logger.debug(f"Merging branches: {branch1.get('id', 'N/A')}, {branch2.get('id', 'N/A')}")
        # TODO: Implement merging algorithm
        merged_branch = branch1 or branch2 # Placeholder

        log_entry = {
             "decision": "merge_branches",
             "source_branch1_id": branch1.get('id'),
             "source_branch2_id": branch2.get('id'),
             "reason": "Completed merge operation"
        }

        if merged_branch:
             # Generate archetype for the *result* of the merge
             semantic_hint = f"Merge_{branch1.get('hint','?')}_{branch2.get('hint','?')}"
             merged_archetype_token = f"ARCH::MERGE::{semantic_hint}::{uuid.uuid4().hex[:4]}"
             merged_branch['archetype_token'] = merged_archetype_token
             log_entry['archetype_token'] = merged_archetype_token # Log the *new* token
             log_entry['merged_branch_id'] = merged_branch.get('id', 'N/A')

             # Log decision (which now includes snapshotting/registration)
             self.fork_decision_log(log_entry)
             return merged_branch
        else:
            # Log failure if merge results in None
            log_entry["reason"] = "Merge operation resulted in None"
            self.fork_decision_log(log_entry)
            return None

    def simulate_branches(self, branch_configs: list) -> list:
        """Simulate multiple branch configurations and score them (stubbed)."""
        self.logger.debug(f"Simulating {len(branch_configs)} branch configurations.")
        simulated_results = []
        for config in branch_configs:
            score = 0.0
            simulated_results.append({"branch_config": config, "score": score})
        return simulated_results

    # --- Modified: fork_decision_log now calls MemoryWeave --- 
    def fork_decision_log(self, entry: dict):
        """Record a decision entry locally AND snapshot/register with MemoryWeave."""
        # 1. Local Log (Optional - MemoryWeave is primary)
        # self.decision_log.append(entry)
        self.logger.debug(f"Fork decision event: {entry}")

        # 2. Integrate with MemoryWeave
        if not self.memory_weave:
             self.logger.error("Cannot log fork decision to MemoryWeave: instance is missing.")
             return

        # Extract archetype token if relevant for registration
        token = entry.get('archetype_token')
        decision = entry.get('decision')

        # Register Archetype if a new one was created (select_branch, merge_branches)
        if token and decision in ['select_branch', 'merge_branches']:
             # Construct metadata from the entry
             metadata = {
                 "decision_type": decision,
                 "reason": entry.get('reason'),
                 "source_branch1_id": entry.get('source_branch1_id'), # Only for merge
                 "source_branch2_id": entry.get('source_branch2_id'), # Only for merge
                 # Add any other relevant context from the entry
             }
             # Remove None values from metadata before registration
             metadata_cleaned = {k: v for k, v in metadata.items() if v is not None}
             self.memory_weave.register_archetype(token, metadata_cleaned)

        # Snapshot the state (which is the entire log entry itself)
        # Ensure the entry contains the token if one was relevant
        if token:
            entry['archetype_token'] = token # Ensure it's in the state being snapshotted
        else:
            # Ensure key exists even if None, for consistent snapshot structure?
            # Or handle absence in MemoryWeave.snapshot_drift (current approach)
            pass

        self.memory_weave.snapshot_drift(entry) # Snapshot the full decision context

    # --- Debug method for visualization ---
    def display_drift_history(self, format='ascii', limit=10):
         """Helper to call the visualization methods on the MemoryWeave instance."""
         if not self.memory_weave:
             print("MemoryWeave not available for visualization.")
             return

         if format == 'ascii':
             print("--- ASCII Drift History ---")
             print(self.memory_weave.visualize_drift_history_ascii(limit=limit))
         elif format == 'mermaid':
             print("--- Mermaid Drift History ---")
             print(self.memory_weave.visualize_drift_history_mermaid(limit=limit))
         else:
             print(f"Unknown visualization format: {format}")

# --- Add __init__.py if it doesn't exist ---
# (Ensure vanta_seed/core is a package)
# Create an empty vanta_seed/core/__init__.py if needed. 