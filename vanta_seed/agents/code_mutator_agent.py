import logging
import os
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import ast # For basic syntax validation

from vanta_seed.agents.base_agent import BaseAgent
from vanta_seed.utils.mutation_manager import MutationManager # Import the manager

logger = logging.getLogger(__name__)

class CodeMutatorAgent(BaseAgent):
    """
    Agent responsible for applying code modifications to a target instance.
    Relies on MutationManager for logging, backups, and Git ops.
    WARNING: This agent modifies source code and is inherently risky.
    """

    def __init__(self, agent_name: str, definition: Dict[str, Any], blueprint: Dict[str, Any], all_agent_definitions: Dict[str, Any], orchestrator):
        super().__init__(agent_name, definition, blueprint, all_agent_definitions, orchestrator)
        
        # Configuration for this agent
        self.config = definition.get("config", {})
        self.target_instance_name = self.config.get("target_instance_name")
        self.target_instance_path = Path(self.config.get("target_instance_path", "./")) # Path to the OTHER instance
        self.target_log_file = self.target_instance_path / self.config.get("target_log_filename", "mutations.yaml")
        self.archive_dir = Path(self.config.get("archive_directory", "./archive"))
        self.auto_commit = self.config.get("auto_commit_changes", True)
        self.require_approval = self.config.get("require_approval", True) # Safety default

        if not self.target_instance_name or not self.target_instance_path.is_dir():
            raise ValueError("CodeMutatorAgent requires valid 'target_instance_name' and 'target_instance_path' in config.")

        # Initialize MutationManager for the TARGET instance
        self.mutation_manager = MutationManager(
            instance_name=self.target_instance_name,
            instance_root_path=self.target_instance_path,
            log_file=self.target_log_file,
            archive_dir=self.archive_dir
        )

        logger.info(f"CodeMutatorAgent '{agent_name}' initialized. Target: {self.target_instance_name} at {self.target_instance_path}")

    async def handle_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handles incoming code modification tasks."""
        intent = task_data.get("intent")
        payload = task_data.get("payload", {})
        context = task_data.get("context", {})
        mutation_id = f"mut_{uuid.uuid4().hex[:8]}" # Generate a unique ID

        logger.info(f"CodeMutatorAgent received task '{mutation_id}' with intent: {intent}")

        if intent == "modify_code":
            target_file = payload.get("target_file") # Relative path within target instance
            modification_description = payload.get("modification_description") # e.g., "add import logging"
            code_changes = payload.get("code_changes") # Can be diff, specific lines, etc.
            requester = context.get("source_agent", "Unknown")

            if not target_file or not (modification_description or code_changes):
                return {"status": "error", "message": "Missing target_file or modification details.", "mutation_id": mutation_id}

            # Log the request
            self.mutation_manager.log_mutation_event({
                'id': mutation_id,
                'type': 'request_received',
                'requester': requester,
                'target_file': target_file,
                'description': modification_description
            })

            # --- Backup --- 
            backup_path = self.mutation_manager.create_backup(mutation_id)
            if not backup_path:
                msg = "Failed to create pre-mutation backup."
                self.mutation_manager.log_mutation_event({'id': mutation_id, 'type': 'error', 'message': msg})
                return {"status": "error", "message": msg, "mutation_id": mutation_id}
            
            # --- Branching (Optional but Recommended) ---
            branch_name = f"mutation/{mutation_id}"
            branch_created = self.mutation_manager.create_branch(branch_name)
            if not branch_created:
                 # Log warning but potentially proceed without branching if repo not setup
                 self.mutation_manager.log_mutation_event({'id': mutation_id, 'type': 'warning', 'message': f"Failed to create git branch {branch_name}."})

            # --- Apply Changes --- 
            # ** THIS IS THE CRITICAL/RISKY PART **
            # Needs robust implementation: parse request, read file, modify content, write file
            success, message = self._apply_code_changes(target_file, code_changes, modification_description)

            if not success:
                self.mutation_manager.log_mutation_event({'id': mutation_id, 'type': 'error', 'message': f"Failed to apply changes: {message}", 'backup': str(backup_path)})
                # TODO: Add revert logic here? (e.g., git checkout HEAD~1 or restore from zip)
                return {"status": "error", "message": f"Failed to apply changes: {message}", "mutation_id": mutation_id, "backup_path": str(backup_path)}

            # --- Commit Changes (Optional) --- 
            commit_hash = None
            if self.auto_commit:
                commit_message = f"Apply mutation {mutation_id}: {modification_description}"
                commit_hash = self.mutation_manager.commit_changes(commit_message, files_to_add=[target_file])
                if not commit_hash:
                     # Log warning but don't necessarily fail the whole operation
                     self.mutation_manager.log_mutation_event({'id': mutation_id, 'type': 'warning', 'message': "Failed to auto-commit changes."}) 

            # --- Log Completion --- 
            self.mutation_manager.log_mutation_event({
                'id': mutation_id,
                'type': 'changes_applied',
                'target_file': target_file,
                'commit': commit_hash,
                'branch': branch_name if branch_created else None,
                'backup': str(backup_path),
                'status': 'pending_reload_and_approval' # Or 'complete' if no approval needed
            })
            
            # --- Signal Target Instance Reload (Via Queue/API?) --- 
            # This part is external to this agent's direct capability.
            # It needs to trigger the mechanism that tells Instance B to reload.
            logger.info(f"Code changes applied for {mutation_id}. Target instance requires reload.")
            # Example: self.orchestrator.submit_task({"intent": "signal_reload", "target_agent": "InstanceBControlPlane", "payload": {...}})
            
            return {
                "status": "success", 
                "message": f"Code changes applied to {target_file} in branch {branch_name}. Target requires reload.", 
                "mutation_id": mutation_id,
                "commit_hash": commit_hash,
                "branch_name": branch_name if branch_created else None,
                "backup_path": str(backup_path)
            }

        else:
            logger.warning(f"Intent '{intent}' not handled by CodeMutatorAgent.")
            return {"status": "ignored", "message": f"Intent '{intent}' not handled."}

    def _apply_code_changes(self, relative_target_file: str, code_changes: Any, description: str) -> tuple[bool, str]:
        """
        Applies the code changes to the target file within the target instance.
        
        Args:
            relative_target_file: Path relative to the target instance root.
            code_changes: The description or data representing the changes.
            description: Text description of the change.
            
        Returns:
            tuple (success: bool, message: str)
        """
        absolute_target_path = self.target_instance_path / relative_target_file
        logger.info(f"Attempting to apply changes to: {absolute_target_path}")

        if not absolute_target_path.exists():
            return False, f"Target file does not exist: {absolute_target_path}"
        if not absolute_target_path.is_file():
             return False, f"Target path is not a file: {absolute_target_path}"
             
        # --- Basic Syntax Check (Example) ---
        try:
            with open(absolute_target_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            ast.parse(source_code)
            logger.debug(f"Existing code syntax OK: {absolute_target_path}")
        except Exception as e:
             logger.warning(f"Syntax error in existing code {absolute_target_path}: {e}. Proceeding with caution.")
             # Decide whether to proceed or fail if existing code is broken

        # --- !! DANGER ZONE !! --- 
        # This is where the actual file modification logic goes.
        # It needs to be implemented carefully based on the format of `code_changes`.
        # Options:
        # 1. Simple search/replace (fragile)
        # 2. Diff patching (using `patch` library or similar)
        # 3. AST modification (robust but complex, requires understanding Python grammar)
        # 4. Using LLM to generate the full modified file (requires validation)
        # 
        # For this placeholder, we will just append a comment.
        try:
            with open(absolute_target_path, 'a', encoding='utf-8') as f:
                f.write(f"\n# Mutation applied by CodeMutatorAgent: {description}\n")
            logger.info(f"Placeholder: Appended comment to {absolute_target_path}")
            
            # --- Post-Change Syntax Check (Example) ---
            # Re-read and parse to see if the *change* broke syntax
            # with open(absolute_target_path, 'r', encoding='utf-8') as f:
            #     modified_code = f.read()
            # ast.parse(modified_code) 
            # logger.debug(f"Modified code syntax OK: {absolute_target_path}")
            
            return True, "Placeholder comment appended successfully."
            
        except Exception as e:
             logger.error(f"Failed to write changes to {absolute_target_path}: {e}", exc_info=True)
             return False, f"Error writing to file: {e}"
        # --- !! END DANGER ZONE !! --- 


</rewritten_file> 