import random
import logging # Added logging

logger = logging.getLogger(__name__) # Added logger instance

class RLAgentWrapper:
    """
    Wraps a BaseAgent to enable simple reinforcement learning feedback.

    - Automatically evaluates result success/failure
    - Tracks cumulative reward
    - Can be extended to integrate with RL frameworks (Gymnasium, CleanRL, etc)
    """

    def __init__(self, agent, reward_threshold=0.8):
        self.agent = agent
        self.reward_threshold = reward_threshold # Threshold not used in basic evaluate_result yet
        self.reward_total = 0
        self.episode_count = 0
        # Use agent's logger if available, otherwise use module logger
        self.logger = getattr(agent, 'logger', logger) 

    async def perform_task(self, task_data, current_state):
        """ Wraps the agent's perform_task and applies reward logic. """
        # Ensure the wrapped agent's perform_task is awaited if it's async
        if asyncio.iscoroutinefunction(self.agent.perform_task):
            result = await self.agent.perform_task(task_data, current_state)
        else:
            result = self.agent.perform_task(task_data, current_state)

        success = self.evaluate_result(result)
        reward = 1 if success else -1
        self.reward_total += reward
        self.episode_count += 1

        self.logger.info(f"[RLAgentWrapper({self.agent.name})] Episode {self.episode_count} | Reward: {reward} | Total Reward: {self.reward_total}")

        return result

    def evaluate_result(self, result):
        """
        Basic success criteria:
        - Non-empty result
        - Result dict has success flag OR no error key/message
        """
        if not result:
            return False
        if isinstance(result, dict):
            if result.get("status") == "error" or "error" in result or "message" in result.get("error", {}):
                 return False # Explicit error signal
            # Consider successful if it's not explicitly an error
            # Or check for a specific success key if convention dictates
            # return result.get("status") == "success" 
            return True # Assume success if no error found
        # Fallback for non-dict results (consider them successful if not None/empty)
        return True 

    def get_stats(self):
        return {
            "agent_name": self.agent.name,
            "total_reward": self.reward_total,
            "episodes": self.episode_count,
            "avg_reward": self.reward_total / self.episode_count if self.episode_count > 0 else 0,
        }

    # Allow accessing attributes of the wrapped agent directly
    def __getattr__(self, name):
        return getattr(self.agent, name) 