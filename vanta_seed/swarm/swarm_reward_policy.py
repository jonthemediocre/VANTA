"""
Defines reward calculation logic for multi-agent scenarios.

Allows customization beyond individual agent success/failure, considering
swarm goals, ritual alignment, and inter-agent dynamics.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def calculate_swarm_reward(agent_results: Dict[str, Dict[str, Any]], 
                           swarm_context: Dict[str, Any], 
                           policy_config: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculates rewards for multiple agents based on their collective results and context.

    Args:
        agent_results: Dict where keys are agent names and values are their result dicts
                       (e.g., from VantaAgentEnv step or agent execute).
        swarm_context: Shared information available to the swarm (e.g., global goals,
                       current ritual stage, shared observations).
        policy_config: Configuration for the reward calculation (e.g., weights,
                       cooperation bonuses, competition penalties).

    Returns:
        Dict where keys are agent names and values are their calculated float rewards.
    """
    rewards = {}
    mode = policy_config.get("mode", "solo") # e.g., "solo", "cooperative", "competitive"

    if mode == "solo":
        # Basic solo mode: reward based on individual agent success (similar to wrapper)
        for agent_name, result in agent_results.items():
            # Use a refined version of the wrapper's evaluation logic
            status = result.get("status", "ERROR")
            if status == "SUCCESS":
                rewards[agent_name] = policy_config.get("reward_success", 1.0)
            elif status == "PARTIAL":
                rewards[agent_name] = policy_config.get("reward_partial", 0.1)
            elif status == "FAIL":
                rewards[agent_name] = policy_config.get("penalty_fail", -1.0)
            else: # ERROR
                rewards[agent_name] = policy_config.get("penalty_error", -2.0)
                
    elif mode == "cooperative":
        # TODO: Implement cooperative reward logic
        # Example: Shared reward based on overall task completion, bonuses for helping others
        logger.warning("Cooperative swarm reward policy not implemented yet.")
        for agent_name in agent_results:
            rewards[agent_name] = 0.0 # Placeholder
            
    elif mode == "competitive":
        # TODO: Implement competitive reward logic
        # Example: Higher reward for agent achieving goal first/best, penalties for others
        logger.warning("Competitive swarm reward policy not implemented yet.")
        for agent_name in agent_results:
            rewards[agent_name] = 0.0 # Placeholder
            
    else:
        logger.error(f"Unknown swarm reward policy mode: {mode}")
        for agent_name in agent_results:
            rewards[agent_name] = 0.0
            
    logger.debug(f"Calculated swarm rewards (Mode: {mode}): {rewards}")
    return rewards

# Example Policy Config
# swarm_policy_config = {
#     "mode": "solo",
#     "reward_success": 1.0,
#     "reward_partial": 0.1,
#     "penalty_fail": -1.0,
#     "penalty_error": -2.0,
#     # Add cooperative/competitive params later
# } 

class SwarmRewardPolicy:

    @staticmethod
    def calculate(agent_name: str, result: Dict[str, Any], action_taken: int, policy_config: Dict[str, Any] = None) -> float:
        """
        Calculates reward based on result status and policy config.

        Args:
            agent_name: Name of the agent.
            result: The result dictionary from the agent or environment step.
            action_taken: The action taken by the agent.
            policy_config: Optional dictionary containing reward values.

        Returns:
            Calculated reward value.
        """
        config = policy_config or {}
        status = result.get("status", "ERROR")

        # Ritualized reward schema using config values with defaults
        if status == "SUCCESS":
            return config.get("reward_success", 3.0)
        elif status == "PARTIAL":
            return config.get("reward_partial", 1.0)
        elif status == "FAIL":
            return config.get("penalty_fail", -4.0)
        elif status == "ERROR":
            return config.get("penalty_error", -8.0)

        # Default penalty for unknown status
        return config.get("penalty_unknown", -1.0) 