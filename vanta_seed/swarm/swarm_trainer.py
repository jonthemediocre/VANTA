"""
Core Swarm Trainer for Multi-Agent RL within VANTA.

Coordinates training episodes involving multiple agents, potentially
interacting within a shared environment or tackling cooperative/competitive tasks.
Integrates with the VantaAgentEnv and Swarm Reward Policies.
Placeholder for integration with Ray RLlib or PettingZoo.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
import yaml
import importlib

# Assuming agents are wrapped and environments are created based on registry
# from ..agents.agent_registry import get_agent 
# from ..rl.agent_wrapper import RLAgentWrapper
# from ..rl.gym_adapter import VantaAgentEnv
# from .swarm_reward_policy import calculate_swarm_reward
# from .swarm_logger import SwarmLogger

logger = logging.getLogger(__name__)

class SwarmTrainer:
    def __init__(self, registry_path="vanta_seed/swarm/agent_registry.yaml", max_steps=50, log_dir="logs/swarm"):
        """
        Initializes the Swarm Trainer.

        Args:
            registry_path: Path to the agent registry YAML file.
            max_steps: Default maximum steps per episode.
            log_dir: Directory for swarm logs.
        """
        self.registry_path = registry_path
        self.registry = self._load_registry()
        self.max_steps = max_steps
        self.swarm_logger = SwarmLogger(log_dir=log_dir) # Instantiate the logger class

    def _load_registry(self):
        """Loads the agent registry from the YAML file."""
        try:
            with open(self.registry_path, "r") as f:
                data = yaml.safe_load(f)
                if "agents" not in data or not isinstance(data["agents"], list):
                    logger.error(f"Invalid format in registry file: {self.registry_path}. Expected top-level 'agents' list.")
                    return []
                return data["agents"]
        except FileNotFoundError:
            logger.error(f"Agent registry file not found: {self.registry_path}")
            return []
        except yaml.YAMLError as e:
            logger.error(f"Error parsing agent registry file {self.registry_path}: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading registry {self.registry_path}: {e}", exc_info=True)
            return []

    async def run(self):
        """Runs the training loop for all enabled agents in the registry."""
        logger.info(f"Starting swarm training run for {len(self.registry)} configured agents.")
        tasks = []
        for agent_meta in self.registry:
            if not agent_meta.get("rl_enabled"):
                logger.debug(f"Skipping agent {agent_meta.get('name', 'Unknown')} as rl_enabled is not true.")
                continue

            # Schedule the training task for each enabled agent
            tasks.append(self._run_agent_training(agent_meta))
        
        if tasks:
            await asyncio.gather(*tasks)
            logger.info("Swarm training run completed for all scheduled agents.")
        else:
            logger.warning("No RL-enabled agents found in the registry to run training.")

    async def _run_agent_training(self, agent_meta: dict):
        """Runs the training loop for a single agent based on its metadata."""
        agent_name = agent_meta.get("name", "UnnamedAgent")
        agent_mode = agent_meta.get("mode", "solo") # Get agent mode
        episode_num = 0 # Simple episode counter for now

        logger.info(f"Initiating training for agent: {agent_name} in mode: {agent_mode}")

        try:
            agent_cls = self._load_agent(agent_meta["module"], agent_meta["class"])
            # Pass agent config if available in registry, otherwise agent uses its defaults
            agent_config = agent_meta.get("agent_config", {}) 
            agent = agent_cls(**agent_config) 
            # Pass wrapper config if available
            wrapper_config = agent_meta.get("wrapper_config", {})
            wrapper = RLAgentWrapper(agent, **wrapper_config)
            # Pass env config if available, else use trainer default max_steps
            env_config = agent_meta.get("env_config", {})
            max_steps = env_config.get("max_steps_per_episode", self.max_steps)
            env = VantaAgentEnv(agent_wrapper=wrapper, max_steps_per_episode=max_steps, **env_config)
            # Get policy config if available
            policy_config = agent_meta.get("policy_config", {})

        except KeyError as e:
            logger.error(f"Agent {agent_name}: Missing required key in registry: {e}", exc_info=True)
            return
        except ImportError as e:
            logger.error(f"Agent {agent_name}: Failed to import module {agent_meta.get('module','?')}: {e}", exc_info=True)
            return
        except Exception as e:
            logger.error(f"Agent {agent_name}: Failed to initialize agent/env: {e}", exc_info=True)
            return
        
        self.swarm_logger.log_episode_start(episode_num, agent_meta)

        try:
            obs, info = env.reset()
            done = False
            current_step = 0

            # --- Ritual Mode Logic Placeholder --- 
            # Future: Based on agent_mode ('solo', 'cooperative', 'competitive'),
            # different logic/coordination might happen here or involve shared state.
            # For now, this loop runs independently per agent ('solo' effectively).

            while not done and current_step < max_steps: # Ensure max_steps is respected
                # Future: Action selection might involve a learned policy
                action = env.action_space.sample() # Simple random action for now

                # Step the environment
                obs, reward_raw, terminated, truncated, info = await env.step(action)
                current_step = info.get("step", current_step + 1) # Update step from info

                # Calculate reward using the policy (passing specific config)
                calculated_reward = SwarmRewardPolicy.calculate(agent_name, info, action, policy_config)

                # Log the step using the structured logger
                self.swarm_logger.log_step(
                    episode=episode_num,
                    step=current_step,
                    agent_name=agent_name,
                    observation=obs, # Consider summarizing obs
                    action=action,
                    reward=calculated_reward,
                    terminated=terminated,
                    truncated=truncated,
                    info=info
                )

                done = terminated or truncated

            # Log episode end
            # Future: Aggregate stats might come from env or trainer
            final_stats = info # Use last info dict as placeholder stats
            self.swarm_logger.log_episode_end(episode_num, final_stats)

        except Exception as e:
            logger.error(f"Error during training loop for agent {agent_name}: {e}", exc_info=True)
            # Optionally log an error event
            self.swarm_logger.log_ritual_event("training_error", {"agent": agent_name, "error": str(e)})
        finally:
            env.close()
            logger.info(f"Training finished for agent: {agent_name}")

    def _load_agent(self, module_path, class_name):
        """Dynamically loads an agent class from a module path."""
        logger.debug(f"Loading agent class '{class_name}' from module '{module_path}'")
        module = importlib.import_module(module_path)
        return getattr(module, class_name)

# Example of how to run this (conceptual)
# async def main():
#     trainer = SwarmTrainer()
#     await trainer.run()
#
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.INFO)
#     asyncio.run(main()) 