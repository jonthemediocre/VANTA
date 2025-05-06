"""
Simple registry for managing active agent instances.
Allows decoupling agent instantiation from router/API layer access.
"""
from typing import Dict, Optional, Any, List
import logging

logger = logging.getLogger(__name__)

# Private dictionary to hold agent instances
_agent_registry: Dict[str, Any] = {}

def register_agent(name: str, agent_instance: Any):
    """Registers an instantiated agent by name."""
    if name in _agent_registry:
        logger.warning(f"Agent with name '{name}' already registered. Overwriting.")
    _agent_registry[name] = agent_instance
    logger.info(f"Agent '{name}' registered successfully (Type: {type(agent_instance).__name__}).")

def get_agent(name: str) -> Optional[Any]:
    """Retrieves a registered agent instance by name."""
    agent = _agent_registry.get(name)
    if not agent:
        logger.error(f"Agent with name '{name}' not found in registry.")
        # In a production system, you might raise an error or handle this differently
    return agent

def list_registered_agents() -> List[str]:
    """Returns a list of names of all registered agents."""
    return list(_agent_registry.keys())

def clear_registry():
    """Clears all agents from the registry (useful for testing or shutdown)."""
    global _agent_registry
    _agent_registry = {}
    logger.info("Agent registry cleared.") 