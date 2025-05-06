"""
Basic Trainer Module

- Designed to run agents wrapped in RLAgentWrapper
- Placeholder for future integration with Gymnasium, CleanRL or RLlib
"""

import time
import logging
import asyncio # Import asyncio for async agent calls

from .agent_wrapper import RLAgentWrapper

logger = logging.getLogger(__name__)

class RLTrainer:
    def __init__(self, agent_wrapper: RLAgentWrapper, max_episodes: int = 100):
        self.agent_wrapper = agent_wrapper
        self.max_episodes = max_episodes

    async def train(self, task_data_generator):
        """
        Run training loop asynchronously.
        task_data_generator -> yields task_data dicts to send to agent
        """
        logger.info(f"Starting RL training for agent '{self.agent_wrapper.agent.name}' for {self.max_episodes} episodes.")

        for episode in range(self.max_episodes):
            try:
                task_data = next(task_data_generator)
            except StopIteration:
                logger.info("Task data generator exhausted. Ending training early.")
                break

            logger.info(f"\n[RLTrainer] Episode {episode+1} / {self.max_episodes}")
            
            # Assume perform_task is async, handle potential errors
            try:
                # Pass an empty dict or appropriate placeholder for current_state if needed
                result = await self.agent_wrapper.perform_task(task_data, current_state={})
                
                # Optional: Log result details for debugging
                # logger.debug(f"[RLTrainer] Task Result: {result}")
                
            except Exception as e:
                logger.error(f"[RLTrainer] Error during agent task execution in episode {episode+1}: {e}", exc_info=True)
                # Decide if you want to continue training or break on error
                continue # Continue to next episode

            stats = self.agent_wrapper.get_stats()
            logger.info(f"[RLTrainer] Current Stats: {stats}")

            # Optional pacing
            await asyncio.sleep(0.1) 

        logger.info("\n[RLTrainer] Training complete.")
        final_stats = self.agent_wrapper.get_stats()
        logger.info(f"[RLTrainer] Final Stats: {final_stats}")
        return final_stats 