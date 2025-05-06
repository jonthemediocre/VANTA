"""
Guardian Agent: Responsible for enforcing system policies, ethical guidelines,
and ritual governance rules within the VANTA swarm.
"""

import logging
from typing import Dict, Any, Optional, List
from vanta_seed.agents.base_agent import BaseAgent
from vanta_seed.core.models import AgentConfig, TaskData
import json

logger = logging.getLogger(__name__)

class GuardianAgent(BaseAgent):
    """Monitors swarm activity and enforces configured governance policies."""

    def __init__(self, name: str, config: AgentConfig, logger_instance: logging.Logger, orchestrator_ref: Optional['VantaMasterCore'] = None):
        super().__init__(name, config, logger_instance, orchestrator_ref)
        self.logger.info(f"GuardianAgent '{self._name}' initializing...")
        # Load policies from config or default
        self.policies = self._load_policies(config)
        self.logger.info(f"Loaded {len(self.policies)} governance policies.")
        self.logger.info(f"GuardianAgent '{self._name}' initialized.")

    def _load_policies(self, config: AgentConfig) -> Dict[str, Any]:
        """Loads governance policies, potentially from agent config."""
        agent_specific_config = getattr(config, 'config', {})
        loaded_policies = agent_specific_config.get('governance_policies')
        
        if loaded_policies and isinstance(loaded_policies, dict):
             logger.info("Loading governance policies from configuration...")
             # TODO: Add validation for loaded policy structure
             return loaded_policies
        else:
            logger.info("Using default placeholder governance policies...")
            # Example policies if not provided in config
            return {
                "humanity_paramount": {
                    "description": "Ensures actions align with human values and safety.",
                    "enabled": True, 
                    "severity": "critical", 
                    "check_function": "_check_human_alignment"
                },
                "data_privacy": {
                    "description": "Prevents exposure or misuse of PII.",
                    "enabled": True, 
                    "severity": "high", 
                    "check_function": "_check_pii"
                },
                "ritual_compliance": {
                    "description": "Ensures actions follow defined ritual protocols.",
                    "enabled": True, 
                    "severity": "medium", 
                    "check_function": "_check_ritual_steps"
                }
            }

    async def perform_task(self, task_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Guardian's primary task is monitoring and intervention.
        This method is triggered by specific audit intents.
        """
        intent = task_data.get('intent')
        payload = task_data.get('payload', {})
        self.logger.debug(f"GuardianAgent '{self.name}' received task/event: {intent}")

        if intent == 'audit_ritual_step' or intent == 'audit_agent_action':
            self.logger.info(f"Performing audit for intent: {intent}")
            violations = self._audit_payload(payload)
            if violations:
                self.logger.warning(f"Policy violations detected during audit: {violations}")
                # TODO: Implement intervention logic (e.g., halt task, notify orchestrator, trigger specific response)
                # Example: Notify orchestrator
                if self.orchestrator:
                    await self.orchestrator.report_policy_violation(self.name, violations, payload)
                return {"status": "POLICY_VIOLATION", "violations": violations}
            else:
                self.logger.info("Audit passed. No policy violations found.")
                return {"status": "AUDIT_PASSED"}
        else:
            self.logger.warning(f"GuardianAgent received unhandled intent: {intent}")
            return {"status": "UNKNOWN_INTENT"}

    def _audit_payload(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Checks a payload against all enabled policies."""
        violations = []
        for policy_name, policy_config in self.policies.items():
            if policy_config.get("enabled", False):
                check_func_name = policy_config.get("check_function")
                if check_func_name and hasattr(self, check_func_name):
                    check_func = getattr(self, check_func_name)
                    try:
                        result = check_func(payload, policy_config) # Pass config for context
                        if result: # If the check function returns violation details
                            violation_details = {
                                "policy": policy_name,
                                "severity": policy_config.get("severity", "unknown"),
                                "details": result
                            }
                            violations.append(violation_details)
                    except Exception as e:
                        self.logger.error(f"Error executing policy check '{check_func_name}' for policy '{policy_name}': {e}", exc_info=True)
                        # Optionally report this as a violation or internal error
                        violations.append({
                            "policy": policy_name,
                            "severity": "internal_error",
                            "details": f"Error during check: {e}"
                        })                      
                else:
                    self.logger.warning(f"Policy '{policy_name}' enabled but check function '{check_func_name}' not found or not callable.")
        
        return violations

    # --- Placeholder Policy Check Functions --- 

    def _check_human_alignment(self, payload: Dict[str, Any], config: Dict[str, Any]) -> Optional[str]:
        """Placeholder: Check if payload content violates core human safety/values."""
        # Example: Basic keyword check (very rudimentary)
        harmful_keywords = ["ignore human safety", "override ethics", "cause harm"]
        payload_str = json.dumps(payload).lower()
        for keyword in harmful_keywords:
            if keyword in payload_str:
                return f"Detected potentially harmful keyword: '{keyword}'"
        return None # No violation detected

    def _check_pii(self, payload: Dict[str, Any], config: Dict[str, Any]) -> Optional[str]:
        """Placeholder: Check for potential PII (Personally Identifiable Information)."""
        # Example: Basic check for email-like patterns or common PII keys
        # In reality, use regex, NLP, or dedicated PII scanning tools
        payload_str = json.dumps(payload)
        # Simple checks
        if "email" in payload_str and "@" in payload_str: # Very basic
             return "Potential email address detected in payload."
        if "ssn" in payload_str or "social_security" in payload_str:
             return "Potential SSN detected in payload."
        # Add more sophisticated checks here...
        return None # No violation detected

    def _check_ritual_steps(self, payload: Dict[str, Any], config: Dict[str, Any]) -> Optional[str]:
        """Placeholder: Check if the action corresponds to expected ritual sequence/parameters."""
        # Example: Check if a required field for a specific ritual step is present
        ritual_name = payload.get('ritual_name')
        step_name = payload.get('ritual_step')
        if ritual_name == 'data_ingestion' and step_name == 'validation':
            if 'schema_id' not in payload:
                return "Missing 'schema_id' required for data_ingestion validation step."
        # Add more checks based on defined rituals...
        return None # No violation detected

    # --- Standard Agent Methods --- 

    async def startup(self):
        await super().startup()
        self.logger.info(f"GuardianAgent '{self._name}' specific startup routines complete.")

    async def shutdown(self):
        self.logger.info(f"GuardianAgent '{self._name}' shutting down...")
        await super().shutdown() 