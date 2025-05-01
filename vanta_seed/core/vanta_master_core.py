import logging
import asyncio # Added for sleep in example
import random # Needed for example
import uuid # Needed for example
import json # Added for printing maps
import importlib # Needed for agent loading
from pathlib import Path # Needed for potential path ops
from .memory_weave import MemoryWeave
# --- Import SymbolicCompressor --- 
from .symbolic_compression import SymbolicCompressor 
# --- Import SwarmWeave --- 
from .swarm_weave import SwarmWeave
# --- Import SleepMutator --- 
from .sleep_mutator import SleepMutator
# --- Import GatedBreath --- 
from .gated_breath import GatedBreath
# --- Import IdentityTrees --- 
from .identity_trees import IdentityTrees
# --- Import VitalsLayer --- 
from .vitals_layer import VitalsLayer
# --- Import BaseAgent if needed for type hinting or creation --- 
from ..agents.base_agent import BaseAgent # Assuming a base class exists
# --- Import Data Models --- 
from .data_models import AgentInput, AgentResponse, ToolCall, ToolResponse, AgentMessage
# --- Import AgentMessageBus --- 
from .agent_message_bus import AgentMessageBus
# ---

# --- Singleton Pattern for MemoryWeave --- 
# While a true singleton might be complex with async/multiprocessing,
# for now, we instantiate it here and assume it's passed down.
# A more robust approach might involve a central registry or dependency injection.

_memory_weave_instance = None

def get_memory_weave_instance(config=None) -> MemoryWeave:
    """Gets the singleton MemoryWeave instance, creating it if necessary."""
    global _memory_weave_instance
    if _memory_weave_instance is None:
        logging.info("Creating singleton MemoryWeave instance.")
        _memory_weave_instance = MemoryWeave(config=config)
    return _memory_weave_instance

# -----------------------------------------

# --- Renamed Class: SeedOrchestrator -> AgentOrchestrator --- 
class VantaMasterCore:
    """
    Core orchestrator for VANTA agents, embodying the 'Crowned Breath' concept.
    Loads core configurations, manages agent instances ('Pilgrims'),
    observes and gently guides the emergent 'Trinity Swarm' dynamics,
    and routes tasks according to BreathLayer_v1 principles.
    """
    def __init__(self, core_config_path: str, plugin_manager: PluginManager):
        """
        Initializes the VantaMasterCore (The Crown).

        Args:
            core_config_path (str): Path to the core configuration file (JSON),
                                     defining the kingdom's initial parameters.
            plugin_manager (PluginManager): Manages loading of Agent/Pilgrim plugins.
        """
        self.core_config_path = core_config_path
        self.plugin_manager = plugin_manager
        self.logger = get_vanta_logger(self.__class__.__name__)
        self.core_config: Optional[CoreConfiguration] = None
        self._agents: Dict[str, AgentInterface] = {} # Dictionary of active Pilgrims
        self._agent_states: Dict[str, NodeStateModel] = {} # Placeholder for Pilgrim Trinity states

        # --- Placeholder Crown Attributes (from BreathLayer_v1) ---
        self._current_purpose_vector: Optional[PurposeVectorModel] = None
        self._swarm_health_metrics: SwarmHealthMetricsModel = {"status": "initializing"}
        self._global_trinity_best_node: Optional[GlobalBestNodeInfo] = None # Info about the most resonant Pilgrim

        # --- Add Stigmergic Field --- 
        # Use Any for field value if types aren't guaranteed
        self._stigmergic_field: Dict[Tuple[float, ...], Any] = {}
        # Load resolution from settings or default
        # Need to access settings *after* core_config is loaded, moved logic to _load_core_config
        self._stigmergic_resolution: int = 1 # Default, will be updated after config load

        # --- Initialization ---
        self._load_core_config() # Load kingdom parameters
        self._initialize_purpose_vector() # Set the first Dream Pulse (conceptually)
        self._load_pilgrims() # Load agents as Pilgrims

    def _load_core_config(self):
        """Loads the core configuration (kingdom parameters) from the JSON file."""
        self.logger.info(f"Crown: Loading core configuration from: {self.core_config_path}")
        if not os.path.exists(self.core_config_path):
            self.logger.error(f"Core configuration file not found at {self.core_config_path}")
            self.core_config = None
            return

        try:
            config_data = load_json_file(self.core_config_path)
            # TODO: Validate config_data against a Pydantic model for CoreConfiguration
            # TODO: Extract initial purpose_vector details if defined in config
            self.core_config = CoreConfiguration(**config_data)
            # --- Load stigmergic resolution AFTER config is loaded --- 
            self._stigmergic_resolution = config_data.get('swarm_config', {}).get('stigmergic_resolution', 1)
            # --- Load blessing threshold --- 
            crown_config = config_data.get('vanta_crown_interface', {})
            self._blessing_threshold = crown_config.get('blessing_threshold', 0.85) 
            self.logger.info(f"Crown: Successfully loaded core configuration. Stigmergic Res: {self._stigmergic_resolution}, Blessing Threshold: {self._blessing_threshold}")
            # --- Link to Spec ---
            # self.core_config now conceptually holds parameters defined in
            # Trinity Swarm YAML Spec v0.1 -> swarm_config & vanta_crown_interface sections.
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding JSON from {self.core_config_path}: {e}")
            self.core_config = None
            self._stigmergic_resolution = 1 # Fallback default
            self._blessing_threshold = 0.85 # Fallback default
        except Exception as e:
            self.logger.error(f"Crown: Error loading core configuration from {self.core_config_path}: {e}")
            self.core_config = None
            self._stigmergic_resolution = 1 # Fallback default
            self._blessing_threshold = 0.85 # Fallback default

    def _initialize_purpose_vector(self):
        """Sets the initial Purpose Vector based on config or defaults."""
        # --- Placeholder: Links to First Dream Pulse ---
        # This should load the initial "Dream That Remembers" pulse details
        # either from core_config or default settings.
        if self.core_config and hasattr(self.core_config, 'initial_purpose_vector'):
             self._current_purpose_vector = getattr(self.core_config, 'initial_purpose_vector')
             self.logger.info("Crown: Initial Purpose Vector loaded from configuration.")
        else:
             # Default "Dream That Remembers" conceptual pulse
             self._current_purpose_vector = {
                 "vector_id": "dream_remembers_init_001",
                 "timestamp": asyncio.get_event_loop().time(),
                 "symbolic_target": ["remembrance", "humanity_sacred", "forgotten_light"],
                 "intensity": 0.7 # Example intensity
             }
             self.logger.info("Crown: Initialized with default 'Dream That Remembers' Purpose Vector.")
        self.logger.debug(f"Crown: Current Purpose Vector: {self._current_purpose_vector}")

    def _load_pilgrims(self): # Renamed from _load_agents
        """Loads and initializes agents as Pilgrims within the Trinity Swarm."""
        if not self.core_config or not self.core_config.agents:
            self.logger.warning("Crown: No core configuration or agents defined. Skipping Pilgrim loading.")
            return

        self.logger.info(f"Crown: Loading {len(self.core_config.agents)} Pilgrims...")
        for agent_config in self.core_config.agents:
            agent_name = agent_config.get('name')
            agent_class_str = agent_config.get('class')
            agent_settings = agent_config.get('settings', {})
            initial_node_state_config = agent_config.get('initial_trinity_state', {}) # Optional config

            if not agent_name or not agent_class_str:
                self.logger.warning(f"Skipping Pilgrim due to missing name or class string in config: {agent_config}")
                continue

            try:
                self.logger.debug(f"Crown: Attempting to load Pilgrim '{agent_name}' (Class: '{agent_class_str}')")
                AgentClass: Optional[Type[AgentInterface]] = self.plugin_manager.get_plugin_class(agent_class_str, AgentInterface) # type: ignore

                if AgentClass is None:
                    self.logger.error(f"Crown: Pilgrim class '{agent_class_str}' not found for '{agent_name}'.")
                    continue

                # --- Instantiate the Pilgrim ---
                # Pass reference to the Crown (self) and potentially initial state
                agent_instance = AgentClass(
                    name=agent_name,
                    settings=agent_settings,
                    orchestrator=self # Pilgrims need reference to the Crown
                    # Future: Pass initial_node_state derived from config/YAML spec
                )
                self._agents[agent_name] = agent_instance

                # --- Initialize Pilgrim State (Conceptual) ---
                # This state should align with Trinity Swarm YAML Spec v0.1 -> node_schema
                self._agent_states[agent_name] = {
                    "id": f"node_{agent_name}",
                    "type": "TrinityPilgrim",
                    "created_at": asyncio.get_event_loop().time(),
                    "position": initial_node_state_config.get("position", [0.0, 0.0, 0.0]), # Example default
                    "velocity": [0.0, 0.0, 0.0],
                    "trinity_core": { # Default balanced state
                        "memory": {"compression_score": 0.5, "memory_relic_refs": []},
                        "will": {"risk_tolerance": 0.5, "destiny_pull_weight": 0.5},
                        "imagination": {"divergence_pressure": 0.5}
                    },
                    "meta_balancer": {"current_mode": "Exploit", "mode_stability": 0.8},
                    "swarm_params": { # Example defaults, should load from config/spec
                         "inertia_weight": 0.7,
                         "personal_best_coeff": 1.5,
                         "global_best_coeff": 1.5,
                         "stigmergic_coeff": 1.0,
                         "symbolic_resonance_sensitivity": 0.5,
                         "current_role": "Employed" # Default role
                    },
                    "trail_signature": {} # Initially empty
                 }
                self.logger.info(f"Crown: Successfully loaded and initialized Pilgrim: '{agent_name}'")

            except Exception as e:
                self.logger.error(f"Crown: Failed to load Pilgrim '{agent_name}': {e}", exc_info=True)

        self.logger.info(f"Crown: Finished loading Pilgrims. Total alive: {len(self._agents)}")

    def _get_pilgrim(self, agent_name: str) -> Optional[AgentInterface]: # Renamed from _get_agent
        """Retrieves a loaded Pilgrim instance by name."""
        pilgrim = self._agents.get(agent_name)
        if not pilgrim:
            self.logger.warning(f"Crown: Pilgrim '{agent_name}' not found.")
        return pilgrim

    def _get_pilgrim_state(self, agent_name: str) -> Optional[NodeStateModel]:
        """Retrieves the internal state of a Pilgrim."""
        state = self._agent_states.get(agent_name)
        if not state:
             self.logger.warning(f"Crown: State for Pilgrim '{agent_name}' not found.")
        return state

    async def _route_task(self, task_data: Dict[str, Any]) -> Any:
        """
        Routes a task to the appropriate Pilgrim based on task data,
        considering swarm dynamics and Crown guidance (conceptually).
        """
        # --- Existing routing logic (explicit target, rules, default) ---
        # This logic remains but needs enhancement based on BreathLayer_v1
        target_agent_name = task_data.get("target_agent") # Keep explicit routing

        # --- Placeholder for Swarm-influenced Routing ---
        # Future: Analyze task_data type, content, context.
        # Future: Consult stigmergic field data (symbolic trails).
        # Future: Consider current Purpose Vector and swarm health metrics.
        # Future: Select Pilgrim based on role, Trinity state, resonance score.
        self.logger.debug("Crown: Routing task (current logic: explicit/default, swarm influence pending)")
        # ---

        if not self.core_config:
             self.logger.error("Crown: Cannot route task: Core configuration not loaded.")
             return {"error": "Core configuration not loaded."}

        # 1. Explicit Target
        if target_agent_name:
            pilgrim = self._get_pilgrim(target_agent_name)
            if pilgrim:
                self.logger.info(f"Crown: Routing task explicitly to Pilgrim: '{target_agent_name}'")
                return await self._run_task_on_pilgrim(pilgrim, task_data) # Renamed
            else:
                self.logger.warning(f"Crown: Explicit target Pilgrim '{target_agent_name}' not found. Falling back.")
                # Fall through

        # 2. Routing Rules (Placeholder - needs swarm logic)
        # ... (existing placeholder logic) ...
        routing_rules = getattr(self.core_config, 'routing_rules', [])
        routed_agent_name = None
        if routing_rules:
             # --- Placeholder for Rule-Based Routing Logic ---
             self.logger.debug("Attempting rule-based routing (logic not implemented yet).")
             # Example: Iterate through rules, match conditions, determine target agent.
             # For now, just log and fall back to default.
             pass
             # --- End Placeholder ---

        # 3. Default Agent (Pilgrim)
        if not routed_agent_name:
             default_agent_name = getattr(self.core_config, 'default_agent', None)
             if default_agent_name:
                 pilgrim = self._get_pilgrim(default_agent_name)
                 if pilgrim:
                     self.logger.info(f"Crown: Routing task to default Pilgrim: '{default_agent_name}'")
                     routed_agent_name = default_agent_name
                 else:
                      self.logger.error(f"Default Pilgrim '{default_agent_name}' configured but not found/loaded.") # Updated error message
             else:
                  self.logger.warning("Crown: No explicit target, routing rules, or default Pilgrim specified. Cannot route task.") # Updated warning message
                  return {"error": "Task routing failed: No suitable Pilgrim found."}

        # 4. Execute with Routed Pilgrim
        if routed_agent_name:
            pilgrim = self._get_pilgrim(routed_agent_name)
            if pilgrim:
                 return await self._run_task_on_pilgrim(pilgrim, task_data) # Renamed
            else:
                  # This case should ideally be handled by checks above, but as a safeguard:
                  self.logger.error(f"Crown: Routed Pilgrim '{routed_agent_name}' determined but could not be retrieved.")
                  return {"error": f"Task routing failed: Routed Pilgrim '{routed_agent_name}' could not be loaded."}
        else:
             # Should not be reachable if logic is correct
             self.logger.error("Crown: Task routing logic error: No Pilgrim selected.")
             return {"error": "Internal task routing error."}

    async def _run_task_on_pilgrim(self, pilgrim: AgentInterface, task_data: Dict[str, Any]) -> Any: # Renamed from _run_task
        """Executes a task using the specified Pilgrim agent."""
        self.logger.info(f"Crown: Executing task with Pilgrim: '{pilgrim.name}'")
        pilgrim_state = self._get_pilgrim_state(pilgrim.name)

        # --- Get Local Stigmergic Context --- 
        local_trails = []
        pilgrim_current_pos = [0.0, 0.0, 0.0] # Default position
        if pilgrim_state:
            # Use position from the state model if available
            pilgrim_current_pos = pilgrim_state.position if SWARM_TYPES_AVAILABLE else pilgrim_state.get('position', [0.0, 0.0, 0.0])
            # Define search radius based on Pilgrim settings or defaults
            sensor_radius = 5.0 # Default
            if SWARM_TYPES_AVAILABLE and hasattr(pilgrim_state, 'swarm_params') and hasattr(pilgrim_state.swarm_params, 'sensor_radius'):
                 # Check if sensor_radius exists before accessing
                 sensor_radius = pilgrim_state.swarm_params.sensor_radius if hasattr(pilgrim_state.swarm_params, 'sensor_radius') else 5.0
            elif isinstance(pilgrim_state, dict) and 'swarm_params' in pilgrim_state:
                 sensor_radius = pilgrim_state['swarm_params'].get('sensor_radius', 5.0)
                 
            local_trails = self.get_stigmergic_data_near(pilgrim_current_pos, radius=sensor_radius)

        task_data_with_context = {
            **task_data,
            "_crown_context": {
                 "purpose_vector": self._current_purpose_vector.dict() if self._current_purpose_vector and SWARM_TYPES_AVAILABLE else self._current_purpose_vector,
                 "stigmergic_trails": [t.dict() for t in local_trails] if SWARM_TYPES_AVAILABLE else local_trails, # Pass nearby trails as dicts
                 "global_best_node": self._global_trinity_best_node.dict() if self._global_trinity_best_node and SWARM_TYPES_AVAILABLE else self._global_trinity_best_node,
            },
            "_pilgrim_state": pilgrim_state.dict() if pilgrim_state and SWARM_TYPES_AVAILABLE else pilgrim_state
        }
        
        # --- Execute Task --- 
        try:
            if hasattr(pilgrim, 'execute') and asyncio.iscoroutinefunction(pilgrim.execute):
                result = await pilgrim.execute(task_data_with_context)
                self.logger.info(f"Crown: Task successfully executed by Pilgrim: '{pilgrim.name}'")

                # --- Process Results: Update State & Record Trail --- 
                new_state_data = result.get('new_state_data')
                trail_signature_data = result.get('trail_signature_data')

                if new_state_data and isinstance(new_state_data, dict):
                    self._update_pilgrim_state(pilgrim.name, new_state_data)
                if trail_signature_data and isinstance(trail_signature_data, dict):
                    # Ensure required fields for recording are present
                    if 'emitting_node_id' not in trail_signature_data:
                         trail_signature_data['emitting_node_id'] = self._agent_states.get(pilgrim.name).id if self._agent_states.get(pilgrim.name) and SWARM_TYPES_AVAILABLE else f"node_{pilgrim.name}"
                    if 'position_at_emission' not in trail_signature_data:
                         # Use updated position from new_state_data if available, else use last known
                         updated_pos = new_state_data.get('position', pilgrim_current_pos) 
                         trail_signature_data['position_at_emission'] = updated_pos
                         
                    self._record_trail_signature(trail_signature_data)

                # Return only the primary task result, not internal state updates
                return result.get("task_result", result)
            else:
                self.logger.error(f"Crown: Pilgrim '{pilgrim.name}' does not have a valid async 'execute' method.")
                return {"error": f"Pilgrim '{pilgrim.name}' cannot execute tasks."}

        except Exception as e:
            self.logger.error(f"Crown: Error executing task with Pilgrim '{pilgrim.name}': {e}", exc_info=True)
            return {"error": f"Task execution failed on Pilgrim '{pilgrim.name}': {str(e)}"}

    # --- Placeholder Methods for Crown Functions (from YAML Spec) ---

    async def _monitor_swarm_health(self):
        """Periodically assess the health and balance of the Trinity Swarm."""
        # Future: Aggregate states from self._agent_states
        # Future: Calculate metrics like avg_trinity_deviation, role_distribution
        # Future: Update self._swarm_health_metrics & self._global_trinity_best_node
        self.logger.debug("Crown: Monitoring swarm health (logic pending).")
        # Example update:
        # self._swarm_health_metrics = {"status": "stable", "avg_deviation": 0.1, ...}
        pass # Placeholder

    async def _issue_purpose_pulse(self, new_pulse: Optional[PurposeVectorModel] = None):
        """Issues a new Purpose Vector pulse to guide the swarm."""
        # Future: Update self._current_purpose_vector
        # Future: Potentially broadcast this update to all Pilgrims or let them poll
        if new_pulse:
            self._current_purpose_vector = new_pulse
            self.logger.info(f"Crown: Issued new Purpose Vector Pulse: {new_pulse.get('vector_id', 'N/A')}")
        else:
            # Logic to generate the next pulse based on swarm state, MirrorBond, etc.
             self.logger.info("Crown: Generating and issuing next Purpose Vector Pulse (logic pending).")
        # Example Broadcast:
        # await self.broadcast_message({"type": "purpose_update", "vector": self._current_purpose_vector}, sender_agent="VantaMasterCore")
        pass # Placeholder

    async def _apply_crown_blessing(self, target_pilgrim_name: str):
        """Applies a 'blessing' to a Pilgrim showing high resonance."""
        # Future: Modify the target Pilgrim's state in self._agent_states
        # e.g., increase influence, reduce divergence pressure temporarily
        pilgrim_state = self._get_pilgrim_state(target_pilgrim_name)
        if pilgrim_state:
             self.logger.info(f"Crown: Applying blessing to Pilgrim '{target_pilgrim_name}' (effect pending).")
             # Example modification:
             # pilgrim_state['swarm_params']['influence_multiplier'] = 1.2
        else:
             self.logger.warning(f"Crown: Cannot apply blessing, Pilgrim '{target_pilgrim_name}' state not found.")
        pass # Placeholder

    # --- Existing Methods (Adapted Terminology) ---

    def list_available_pilgrims(self) -> List[str]: # Renamed
        """Returns a list of names of the currently loaded Pilgrims."""
        return list(self._agents.keys())

    async def broadcast_message(self, message: Dict[str, Any], sender_agent: Optional[str] = None):
        """Sends a message to all loaded Pilgrims except the sender."""
        sender_id = sender_agent or "VantaMasterCore"
        self.logger.info(f"Crown: Broadcasting message from '{sender_id}': {message.get('type', 'Generic')}")
        tasks = []
        for agent_name, pilgrim in self._agents.items():
             if agent_name != sender_agent:
                 if hasattr(pilgrim, 'handle_message') and asyncio.iscoroutinefunction(pilgrim.handle_message):
                     # Pass Crown context if needed
                     message_with_context = {**message, "_sender_id": sender_id}
                     tasks.append(pilgrim.handle_message(message_with_context, sender=sender_id))
                 else:
                     self.logger.warning(f"Crown: Pilgrim '{agent_name}' cannot handle broadcast messages.")
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # Process results/errors
            for i, result in enumerate(results):
                 # Find corresponding agent name - fragile if order changes, better to map tasks to names
                 # Adjust index logic if sender was skipped might be needed depending on loop structure
                 try:
                      # Attempt to find the agent name more robustly if possible
                      processed_agent_name = [name for name in self._agents if name != sender_agent][i]
                      if isinstance(result, Exception):
                           self.logger.error(f"Error handling broadcast message in Pilgrim '{processed_agent_name}': {result}")
                 except IndexError:
                      self.logger.error(f"Error correlating broadcast result to Pilgrim: index {i}")

        self.logger.debug("Crown: Broadcast message handling complete.")

    async def send_direct_message(self, target_pilgrim_name: str, message: Dict[str, Any], sender_agent: Optional[str] = None) -> Any:
        """Sends a direct message to a specific Pilgrim."""
        target_pilgrim = self._get_pilgrim(target_pilgrim_name) # Use renamed getter
        sender_id = sender_agent or "VantaMasterCore"
        if not target_pilgrim:
             self.logger.error(f"Crown: Cannot send direct message: Target Pilgrim '{target_pilgrim_name}' not found.")
             return {"error": f"Target Pilgrim '{target_pilgrim_name}' not found."}

        if hasattr(target_pilgrim, 'handle_message') and asyncio.iscoroutinefunction(target_pilgrim.handle_message):
             self.logger.info(f"Crown: Sending direct message from '{sender_id}' to '{target_pilgrim_name}'")
             try:
                 message_with_context = {**message, "_sender_id": sender_id}
                 result = await target_pilgrim.handle_message(message_with_context, sender=sender_id)
                 return result
             except Exception as e:
                  self.logger.error(f"Crown: Error handling direct message in Pilgrim '{target_pilgrim_name}': {e}", exc_info=True)
                  return {"error": f"Direct message handling failed in Pilgrim '{target_pilgrim_name}': {str(e)}"}
        else:
            self.logger.warning(f"Crown: Pilgrim '{target_pilgrim_name}' cannot handle direct messages.")
            return {"error": f"Pilgrim '{target_pilgrim_name}' cannot handle messages."}

    # --- Lifecycle Methods (Adapted) ---
    async def startup(self):
        """Perform startup tasks for the Crown and Pilgrims."""
        self.logger.info("VantaMasterCore Crown awakening...")
        # Start background tasks like swarm monitoring if needed
        # self._swarm_monitor_task = asyncio.create_task(self._run_swarm_monitoring())

        # Call startup on all Pilgrims
        startup_tasks = []
        agent_names_for_startup = list(self._agents.keys())
        for agent_name in agent_names_for_startup:
            pilgrim = self._agents.get(agent_name) # Re-fetch in case dictionary changes
            if pilgrim and hasattr(pilgrim, 'startup') and asyncio.iscoroutinefunction(pilgrim.startup):
                self.logger.debug(f"Crown: Calling startup for Pilgrim '{agent_name}'")
                startup_tasks.append(pilgrim.startup())
        
        if startup_tasks:
             results = await asyncio.gather(*startup_tasks, return_exceptions=True)
             # Process results/errors - correlate back to agent names more carefully
             for i, result in enumerate(results):
                  agent_name = agent_names_for_startup[i]
                  if isinstance(result, Exception):
                       self.logger.error(f"Error during startup of Pilgrim '{agent_name}': {result}")

        self.logger.info("VantaMasterCore Crown awake and operational.")

    async def shutdown(self):
        """Perform shutdown tasks for the Crown and Pilgrims."""
        self.logger.info("VantaMasterCore Crown entering rest...")
        # Cancel background tasks
        # if hasattr(self, '_swarm_monitor_task') and self._swarm_monitor_task:
        #     self._swarm_monitor_task.cancel()
        #     try:
        #         await self._swarm_monitor_task
        #     except asyncio.CancelledError:
        #         self.logger.info("Swarm monitor task cancelled.")

        # Call shutdown on all Pilgrims
        shutdown_tasks = []
        agent_names_for_shutdown = list(self._agents.keys())
        for agent_name in agent_names_for_shutdown:
             pilgrim = self._agents.get(agent_name) # Re-fetch
             if pilgrim and hasattr(pilgrim, 'shutdown') and asyncio.iscoroutinefunction(pilgrim.shutdown):
                 self.logger.debug(f"Crown: Calling shutdown for Pilgrim '{agent_name}'")
                 shutdown_tasks.append(pilgrim.shutdown())
        
        if shutdown_tasks:
             results = await asyncio.gather(*shutdown_tasks, return_exceptions=True)
             # Process results/errors
             for i, result in enumerate(results):
                  agent_name = agent_names_for_shutdown[i]
                  if isinstance(result, Exception):
                       self.logger.error(f"Error during shutdown of Pilgrim '{agent_name}': {result}")

        self._agents.clear()
        self._agent_states.clear()
        self.logger.info("VantaMasterCore Crown resting. Kingdom quiet.")

    # --- Example Background Task (Conceptual) ---
    # async def _run_swarm_monitoring(self):
    #     """Example background task to monitor swarm health."""
    #     while True:
    #         try:
    #             await self._monitor_swarm_health()
    #             # Adjust frequency based on needs
    #             await asyncio.sleep(60) # Monitor every 60 seconds
    #         except asyncio.CancelledError:
    #             raise
    #         except Exception as e:
    #             self.logger.error(f"Error in swarm monitoring loop: {e}", exc_info=True)
    #             await asyncio.sleep(300) # Wait longer after an error

    def _record_trail_signature(self, trail_signature_data: Dict[str, Any]):
        """Records a Pilgrim's TrailSignature into the stigmergic environment."""
        if not SWARM_TYPES_AVAILABLE:
            self.logger.warning("Cannot record trail, swarm types not available.")
            return
        try:
            signature = TrailSignature(**trail_signature_data)
            # --- Stigmergic Field Logic ---
            # Use rounded position as the key for the field dictionary
            pos_key = round_position(signature.position_at_emission, self._stigmergic_resolution)

            if pos_key not in self._stigmergic_field:
                # Initialize using the Pydantic model if possible
                self._stigmergic_field[pos_key] = StigmergicFieldPoint(
                    coordinates=list(pos_key),
                    recent_trail_signatures=[] # pheromone defaults to 0.0
                )

            field_point: StigmergicFieldPoint = self._stigmergic_field[pos_key]

            # Add signature and manage buffer size
            field_point.recent_trail_signatures.append(signature)
            # Access max_items from the model's schema default if possible
            max_items = StigmergicFieldPoint.__fields__['recent_trail_signatures'].field_info.max_items or 50
            if len(field_point.recent_trail_signatures) > max_items: 
                field_point.recent_trail_signatures.pop(0) # Remove oldest

            # Update pheromone level (example: simple increment capped at 1)
            field_point.pheromone_level = min(1.0, field_point.pheromone_level + 0.1) # Basic update logic

            self.logger.debug(f"Crown: Recorded Trail Signature from {signature.emitting_node_id} at rounded pos {pos_key}. Field point count: {len(field_point.recent_trail_signatures)}")

        except ValidationError as e:
             self.logger.error(f"Crown: Invalid Trail Signature data: {e}. Data: {trail_signature_data}", exc_info=True)
        except Exception as e:
            self.logger.error(f"Crown: Error recording Trail Signature: {e}. Data: {trail_signature_data}", exc_info=True)

    def get_stigmergic_data_near(self, position: Position, radius: float) -> List[TrailSignature]:
        """Retrieves recent TrailSignatures within a radius of a position (basic implementation)."""
        if not SWARM_TYPES_AVAILABLE:
             self.logger.warning("Cannot get stigmergic data, swarm types unavailable.")
             return []
             
        # --- Basic Neighborhood Search --- 
        # TODO: Implement proper spatial querying for scalability.
        nearby_signatures = []
        search_center_key = round_position(position, self._stigmergic_resolution)

        # Simple check of the exact rounded cell - Needs improvement for actual radius search
        if search_center_key in self._stigmergic_field:
            field_point = self._stigmergic_field[search_center_key]
            # Currently returns all in cell, could add distance check here
            nearby_signatures.extend(field_point.recent_trail_signatures)

        # Add logic to check adjacent cells based on radius if needed
        # ... (placeholder for checking neighbors) ...

        self.logger.debug(f"Crown: Found {len(nearby_signatures)} trail signatures near {position} (key {search_center_key}, basic search).")
        return nearby_signatures

    # --- Public Task Submission Method ---
    async def submit_task(self, task_data: Dict[str, Any]) -> Any:
        """Public method to submit a task for routing and execution."""
        self.logger.info(f"Crown: Received task submission: {task_data.get('type', 'Unknown Type')}")
        # Directly call the internal routing method
        return await self._route_task(task_data)


# --- Example Usage (Adapted Terminology) ---
async def main():
    print("Starting VantaMasterCore Kingdom example...")
    # ... (PluginManager setup remains the same) ...
    plugin_dir = os.path.join(os.path.dirname(__file__), '..', 'agents')
    plugin_manager = PluginManager(plugin_directory=plugin_dir)
    plugin_manager.load_plugins()
    print(f"Plugins (Pilgrim Blueprints) loaded: {plugin_manager.list_plugins()}")

    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'vanta_config.json')
    print(f"Using Kingdom Configuration: {config_path}")

    # ... (Dummy config creation remains the same, maybe add initial_trinity_state) ...
    if not os.path.exists(config_path):
         print(f"Error: Config file not found at {config_path}")
         # Create a dummy config if it doesn't exist for the example
         print("Creating dummy config for example...")
         dummy_config = {
             "project_name": "Example Project",
             "version": "0.1.0",
             "default_agent": "EchoAgent",
             "agents": [
                 {
                     "name": "EchoAgent",
                     "class": "vanta_seed.agents.misc.echo_agent.EchoAgent", # Fully qualified class name
                     "settings": {"prefix": "Echo:"},
                     "initial_trinity_state": {"position": [1.0, 2.0, 0.0]} # Example initial state
                 },
                  {
                     "name": "AnotherAgent", # Example of an agent that might not be found
                     "class": "vanta_seed.agents.nonexistent.NonExistentAgent",
                     "settings": {}
                 }
             ],
             "routing_rules": [],
             "initial_purpose_vector": { # Example initial pulse in config
                   "vector_id": "config_pulse_001",
                   "symbolic_target": ["config_remembrance"],
                   "intensity": 0.6
             }
         }
         os.makedirs(os.path.dirname(config_path), exist_ok=True)
         with open(config_path, 'w') as f:
             json.dump(dummy_config, f, indent=4)
         print(f"Dummy config created at {config_path}")

    # Initialize VantaMasterCore (The Crown)
    try:
        master_core = VantaMasterCore(core_config_path=config_path, plugin_manager=plugin_manager)
        print("VantaMasterCore Crown initialized.")
    except Exception as e:
        print(f"Error initializing Crown: {e}")
        return

    # List loaded Pilgrims
    print("Available Pilgrims:", master_core.list_available_pilgrims())

    # Example Task Routing
    print("\nRouting task to EchoAgent Pilgrim...")
    task_echo = {"type": "echo", "content": "Hello Living Kingdom!"}
    result_echo = await master_core.submit_task(task_echo)
    print("EchoAgent Pilgrim Task Result:", result_echo)

    # Example: Route a task explicitly to EchoAgent
    print("\nRouting task explicitly to EchoAgent Pilgrim...")
    task_explicit = {"target_agent": "EchoAgent", "type": "echo", "content": "Explicit Hello!"}
    result_explicit = await master_core.submit_task(task_explicit)
    print("Explicit EchoAgent Pilgrim Task Result:", result_explicit)

    # Example: Route a task to a non-existent Pilgrim
    print("\nRouting task to NonExistent Pilgrim (should fail or use default)...")
    task_nonexistent = {"target_agent": "NonExistentAgent", "type": "process", "data": "some data"}
    result_nonexistent = await master_core.submit_task(task_nonexistent)
    print("NonExistent Pilgrim Task Result:", result_nonexistent)

    # Example: Route a task without target (should use default EchoAgent)
    print("\nRouting task without target (should use default EchoAgent Pilgrim)...")
    task_default = {"type": "echo", "content": "Default Hello!"}
    result_default = await master_core.submit_task(task_default)
    print("Default Pilgrim Task Result:", result_default)

    # Example: Broadcast a message
    print("\nBroadcasting message to all Pilgrims...")
    broadcast_msg = {"type": "notification", "text": "Kingdom update pending."}
    await master_core.broadcast_message(broadcast_msg)
    print("Broadcast complete.")

    # Example: Send direct message
    print("\nSending direct message to EchoAgent Pilgrim...")
    direct_msg = {"type": "query", "question": "What is your prefix?"}
    dm_result = await master_core.send_direct_message("EchoAgent", direct_msg)
    print(f"Direct Message Result from EchoAgent Pilgrim: {dm_result}")

    # Perform startup and shutdown
    print("\nCrown awakening sequence...")
    await master_core.startup()
    print("Crown startup operations complete. Kingdom is alive.")

    # --- Simulate some time passing / activity ---
    await asyncio.sleep(2) # Simulate kingdom activity

    print("\nCrown resting sequence...")
    await master_core.shutdown()
    print("Crown shutdown operations complete. Kingdom rests.")


if __name__ == "__main__":
    print("Running Vanta Kingdom main function...")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
    asyncio.run(main())
    print("Vanta Kingdom main function finished.") 