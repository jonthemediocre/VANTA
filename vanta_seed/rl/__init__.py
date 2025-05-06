"""
VANTA RL Subsystem → Agent Reinforcement Learning Modules

- agent_wrapper.py → RLAgentWrapper → agent interface adapter + reward logic
- trainer.py → basic trainer loop → future extension for offline training or swarm coordination
- gym_adapter.py → VantaAgentEnv → Gymnasium interface for external RL libraries
"""

from .agent_wrapper import RLAgentWrapper
from .gym_adapter import VantaAgentEnv

from .agent_wrapper import RLAgentWrapper 