# vanta_seed/core/swarm_weave.py
import logging
import json
import uuid
from collections import defaultdict
from .memory_weave import MemoryWeave
from .symbolic_compression import SymbolicCompressor

class SwarmWeave:
    """Manages inter-agent memory circulation and harmonization within VANTA.

    Acts as a mediator between individual agent memory drifts and the collective
    symbolic memory managed by SymbolicCompressor and stored in MemoryWeave.
    """
    def __init__(self, memory_weave: MemoryWeave, symbolic_compressor: SymbolicCompressor, config: dict = None):
        self.logger = logging.getLogger("Core.SwarmWeave")
        self.memory_weave = memory_weave
        self.symbolic_compressor = symbolic_compressor
        self.config = config or {}
        # Use defaultdict for easier initialization of agent buffers
        self.agent_memory_buffers = defaultdict(list) 
        self.registered_agents = set()
        self.logger.info("SwarmWeave initialized.")

    def register_agent(self, agent_id: str):
        """Registers an agent to participate in the swarm."""
        if agent_id in self.registered_agents:
            self.logger.warning(f"Agent '{agent_id}' already registered in SwarmWeave.")
            return
        self.registered_agents.add(agent_id)
        # Initialize buffer explicitly upon registration
        if agent_id not in self.agent_memory_buffers:
             self.agent_memory_buffers[agent_id] = []
        self.logger.info(f"Agent '{agent_id}' registered with SwarmWeave.")

    # --- NEW: Spawn Agent Method --- 
    def spawn_agent(self, parent_agent_id: str, agent_blueprint: dict) -> dict:
        """Creates a new agent ID and initializes its memory buffer linked to a parent.

        Args:
            parent_agent_id: The ID of the agent initiating the spawn.
            agent_blueprint: Configuration or definition for the new agent (structure TBD).

        Returns:
            A dictionary containing the new agent's ID.
        """
        # Generate a unique ID for the child agent
        child_count = sum(1 for agent in self.registered_agents if agent.startswith(f"{parent_agent_id}_child_"))
        new_agent_id = f"{parent_agent_id}_child_{child_count + 1}"
        
        if new_agent_id in self.registered_agents:
             self.logger.warning(f"Generated agent ID '{new_agent_id}' already exists. Attempting retry with UUID.")
             new_agent_id = f"{parent_agent_id}_child_{uuid.uuid4().hex[:6]}"
             if new_agent_id in self.registered_agents:
                 self.logger.error(f"Failed to generate unique child agent ID for parent '{parent_agent_id}'. Aborting spawn.")
                 # Consider raising an exception here?
                 return {"agent_id": None, "error": "Failed to generate unique ID"}
                 
        self.register_agent(new_agent_id) # Register the new agent ID
        # Initialize buffer with spawn information
        spawn_record = {
            "event": "spawn",
            "spawned_from": parent_agent_id,
            "agent_blueprint": agent_blueprint, # Store the blueprint
            "drift_snapshot": None # No drift yet
        }
        self.agent_memory_buffers[new_agent_id].append(spawn_record)
        self.logger.info(f"Initialized memory buffer for spawned agent '{new_agent_id}' from parent '{parent_agent_id}'.")
        
        # --- Potential: Snapshot spawn event to MemoryWeave --- 
        # self.memory_weave.snapshot_drift({ ... spawn event details ... })
        # ---------------------------------------------------
        
        return {"agent_id": new_agent_id}
    # -------------------------------

    def circulate_memory(self, agent_id: str, memory_event: dict):
        """Receives a memory event from an agent and snapshots it to the main weave.

        Args:
            agent_id: The ID of the agent reporting the memory event.
            memory_event: A dictionary containing details of the memory event,
                         including at least 'archetype_token', 'drift_vector', 
                         'decision', and 'reason'.
        """
        if agent_id not in self.registered_agents:
            self.logger.error(f"Attempted to circulate memory for unregistered agent '{agent_id}'. Ignoring.")
            return
        
        # Validate memory_event structure (basic check)
        required_keys = ['archetype_token', 'drift_vector', 'decision', 'reason']
        if not all(key in memory_event for key in required_keys):
            self.logger.error(f"Invalid memory_event received from agent '{agent_id}'. Missing keys: {required_keys}. Event: {memory_event}")
            return

        # Add agent_id to the event for tracking in the main weave
        memory_event['source_agent'] = agent_id
        
        # Snapshot the drift event into the global MemoryWeave
        snapshot_success = self.memory_weave.snapshot_drift(memory_event)

        if snapshot_success:
            self.logger.debug(f"Circulated memory snapshot from agent '{agent_id}' to MemoryWeave. Token: {memory_event.get('archetype_token')}")
            # Optional: Store a local copy in the agent's buffer if needed for harmonization
            # self.agent_memory_buffers[agent_id].append(memory_event)
        else:
             self.logger.error(f"Failed to snapshot drift from agent '{agent_id}' into MemoryWeave.")

    def harmonize_agents(self) -> dict:
        """Periodically compresses the collective drift history to update symbolic maps.
        
        This replaces the direct call to compressor in the orchestrator ritual.
        The SwarmWeave now owns the harmonization process.
        
        Returns:
            The compressed symbolic map.
        """
        self.logger.info("Initiating Swarm Harmonization (Symbolic Compression)...")
        # The compression works on the global MemoryWeave history
        compression_map = self.symbolic_compressor.compress_drift_history()
        # The map itself represents the harmonized state based on collective drift.
        self.logger.info("Swarm Harmonization complete.")
        # Log or return the compression map as the result of harmonization
        return compression_map

    def get_agent_buffer(self, agent_id: str) -> list:
        """Retrieves the local memory buffer for a specific agent."""
        return self.agent_memory_buffers.get(agent_id, [])

    def get_registered_agents(self) -> set:
         """Returns the set of registered agent IDs."""
         return self.registered_agents

    # TODO: Add methods for cross-agent memory sharing based on rules/similarity.
    # TODO: Implement decay or pruning mechanisms for agent buffers. 