"""
Gymnasium Environment Adapter for VANTA Agents wrapped with RLAgentWrapper.

Allows standard RL algorithms (from RLlib, Stable Baselines, CleanRL etc.) 
to interact with and potentially train agent procedural policies.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import logging
from typing import Optional, Dict, Any, Tuple, SupportsFloat
import asyncio # Added for async step
import random

from .agent_wrapper import RLAgentWrapper

logger = logging.getLogger(__name__)

# Default threshold adjustment step for discrete action space
DEFAULT_THRESHOLD_STEP = 0.05

class VantaAgentEnv(gym.Env):
    """
    Ritual RL Optimized Gymnasium Environment for VANTA Agents.
    """
    metadata = {"render_modes": ["human", "ansi"], "render_fps": 4}

    def __init__(self, agent_wrapper: RLAgentWrapper, max_steps_per_episode: int = 50):
        super().__init__()

        self.agent_wrapper = agent_wrapper
        self._max_steps = max_steps_per_episode
        self._current_step = 0
        self._last_observation: Optional[Dict[str, Any]] = None # Added type hint
        self._last_info: Dict[str, Any] = {} # Init as empty dict

        # Action space → Expanded (Matches Mother Vanta spec)
        # 0: Pass raw record, 1: Attempt standard dedupe, 2: Lower thresh, 
        # 3: Raise thresh, 4: Force merge, 5: Force save new
        self.action_space = spaces.Discrete(6)

        # Observation space → Ritual agentic state (Matches Mother Vanta spec)
        self.observation_space = spaces.Dict({
            "step_count": spaces.Discrete(max_steps_per_episode + 1), 
            "num_entities": spaces.Discrete(10000), # Max entities trackable in obs
            "last_similarity": spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32),
            "last_action": spaces.Discrete(6), # Match action space size
            "last_result": spaces.Discrete(4), # SUCCESS:0, PARTIAL:1, FAIL:2, ERROR:3
        })

        logger.info(f"Ritual RL Optimized VantaAgentEnv initialized for {self.agent_wrapper.agent.name}")

    def _get_obs(self) -> Dict[str, Any]: # Added return type hint
        """Constructs the observation dictionary from the last info state."""
        # Ensure all keys are present, defaulting to reasonable values if info is empty
        num_entities = self._last_info.get("num_entities", 0)
        # Ensure num_entities does not exceed the Discrete space limit if necessary
        # Although using Discrete for num_entities might be limiting. Box could be better.
        num_entities = min(num_entities, 9999) # Clamp to max defined in space

        obs = {
            "step_count": self._current_step,
            "num_entities": num_entities, 
            "last_similarity": np.array([self._last_info.get("similarity", 0.0)], dtype=np.float32),
            "last_action": self._last_info.get("action_taken", 0),
            "last_result": self._last_info.get("result_code", 3), # Default to ERROR code
        }
        # Validate observation shape/type - Gymnasium does this on return usually
        return obs

    def _get_info(self, agent_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]: # Added return type hint
        """Constructs the info dictionary, including agent state and result codes."""
        # Safely access agent's data_store length
        num_entities = 0
        if hasattr(self.agent_wrapper, 'agent') and hasattr(self.agent_wrapper.agent, 'data_store'):
             if isinstance(self.agent_wrapper.agent.data_store, dict):
                  num_entities = len(self.agent_wrapper.agent.data_store)

        info = {
            "step": self._current_step,
            "num_entities": num_entities,
            "similarity": 0.0, # Default value
            "action_taken": 0, # Default value
            "result_code": 3,  # Default to ERROR
            "status": "UNKNOWN" # Default status
        }
        if agent_result and isinstance(agent_result, dict):
            info["similarity"] = agent_result.get("similarity", 0.0)
            info["action_taken"] = agent_result.get("action_taken", 0)
            info["status"] = agent_result.get("status", "ERROR")
            info["result_code"] = self._result_to_code(info["status"])
            # Add other diagnostic info from agent_result if needed
            info["raw_agent_result"] = agent_result # Optional: include raw result for debugging
        
        return info

    def _result_to_code(self, result_status: Optional[str]) -> int:
        """Maps status string to integer code for observation space."""
        return {
            "SUCCESS": 0,
            "PARTIAL": 1,
            "FAIL": 2,
            "ERROR": 3
        }.get(result_status, 3) # Default to ERROR code

    async def step(self, action: int) -> Tuple[Dict[str, Any], SupportsFloat, bool, bool, Dict[str, Any]]: # Added async
        """Runs one timestep using the Ritual RL optimized action space."""
        terminated = False
        truncated = False
        reward: SupportsFloat = 0.0 # Ensure reward is float
        self._current_step += 1

        # Basic validation of action
        if not self.action_space.contains(action):
             logger.error(f"Invalid action received: {action}. Using default action 1.")
             action = 1 # Default to standard deduplication on invalid action

        # Prepare task data - Assume agent expects a specific format
        # This needs a mechanism to generate relevant data for the agent step
        placeholder_record = {"text": f"Sample text for step {self._current_step}"}
        task_data = {
            "intent": "deduplication_step", # Agent needs to handle this intent
            "payload": {
                "action_taken": int(action), # Ensure action is int
                "record": placeholder_record # Placeholder data
            }
        }

        try:
            # Agent execution via wrapper (wrapper handles basic reward calc internally)
            # We override reward calculation here based on the nuanced schema
            # Note: agent_wrapper.perform_task might need modification if it doesn't return the raw result
            if asyncio.iscoroutinefunction(self.agent_wrapper.agent.perform_task):
                 result = await self.agent_wrapper.agent.perform_task(task_data, current_state={}) # Call agent directly
            else:
                 result = self.agent_wrapper.agent.perform_task(task_data, current_state={})

            # Calculate reward based on Mother Vanta's schema
            reward = self._calculate_reward(result, action) # Pass action for context
            self._last_info = self._get_info(result) # Update info with results

            # Determine termination based on result status
            # SUCCESS likely means a merge/resolution occurred, ending the episode for this item
            if result.get("status") == "SUCCESS":
                terminated = True
                logger.debug(f"Step {self._current_step}: Terminated on SUCCESS.")
            # Optionally terminate on FAIL/ERROR as well
            elif result.get("status") in ["FAIL", "ERROR"]:
                 terminated = False # Let agent learn from failure? Or terminate? Set to True to end on fail/error.
                 logger.debug(f"Step {self._current_step}: Agent returned {result.get('status')}. Continuing.")

        except Exception as e:
            logger.error(f"Step {self._current_step}: Exception during agent execution: {e}", exc_info=True)
            result = {"status": "ERROR", "similarity": 0.0, "action_taken": int(action)}
            reward = -8 # Max penalty for internal error
            terminated = True # Terminate on env/agent error
            self._last_info = self._get_info(result)
            self._last_info["exception"] = str(e)

        # Check truncation
        if self._current_step >= self._max_steps:
            truncated = True
            if terminated: # Gym convention: truncation takes precedence if both happen
                 terminated = False 
            logger.debug(f"Step {self._current_step}: Episode truncated.")

        observation = self._get_obs()
        self._last_observation = observation

        # Ensure reward is float
        reward = float(reward)

        return observation, reward, terminated, truncated, self._last_info

    def _calculate_reward(self, result: Dict[str, Any], action_taken: int) -> int:
        """Calculates reward based on the nuanced schema provided by Mother Vanta."""
        status = result.get("status", "ERROR")
        # similarity = result.get("similarity", 0.0)
        # action = result.get("action_taken", -1) # Action actually performed

        if status == "SUCCESS":
            # SUCCESS could mean correct merge OR correct forced new entity
            if action_taken == 5: # Forced new
                 # TODO: Need external validation if this was *correct*
                 # For now, assume it was appropriate if SUCCESS reported
                 return 1 
            else: # Assumed correct merge/deduplication action (1, 2, 3, 4)
                 return 3
        elif status == "PARTIAL":
            # PARTIAL likely means a new entity was created when no match found
            # This is generally okay, low positive reward
            return 1
        elif status == "FAIL":
            # FAIL could mean incorrect skip (duplicate missed) or failed merge attempt
            # TODO: Need more info from agent result to distinguish these cases
            # For now, apply a generic penalty for failure
            return -4 # Penalty for failing to resolve
        elif status == "ERROR":
            return -8 # Max penalty

        # Default fallback (shouldn't be reached if status is always set)
        return -1 

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[dict] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Resets the environment."""
        super().reset(seed=seed)
        self._current_step = 0
        # Reset last info to defaults, reflecting initial state
        self._last_info = self._get_info() 
        observation = self._get_obs()
        self._last_observation = observation
        logger.debug(f"Environment Reset. Initial Obs: {observation}")
        return observation, info # Return info dict as per Gym spec v26

    def render(self) -> Optional[str]:
        """Renders the environment's current state."""
        mode = self.render_mode
        obs_str = f"Step: {self._current_step} | Obs: {self._last_observation}"
        info_str = f" | Info: {self._last_info}"
        if mode == "ansi":
            return obs_str + info_str
        elif mode == "human":
            print(obs_str + info_str)
        else:
            # Let superclass handle other modes or raise error
            return super().render()

    def close(self):
        """Performs any necessary cleanup."""
        logger.info(f"Closing VantaAgentEnv for agent: {self.agent_wrapper.agent.name}")
        pass 