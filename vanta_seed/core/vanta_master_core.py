import logging
import asyncio # Added for sleep in example
import random # Needed for example
import uuid # Needed for example
import json # Added for printing maps
import importlib # Needed for agent loading
from pathlib import Path # Needed for potential path ops
import os # <<< Added import os
# --- Add typing imports --- 
from typing import Optional, Dict, List, Tuple, Any, Type # Added Optional and others
# --- Import Pydantic ValidationError --- 
from pydantic import ValidationError
# --------------------------
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
# --- Import PluginManager (Assuming location) --- 
# Try importing from utils
from vanta_seed.utils.plugin_manager import PluginManager # <<< Changed to absolute import
# from ..runtime.plugin_manager import PluginManager # Previous attempt
# --- Import necessary types from swarm_types (Corrected) --- #
from .swarm_types import NodeStateModel, PurposeVectorModel, SwarmHealthMetricsModel, GlobalBestNodeInfo, TrailSignature, Position, StigmergicFieldPoint # Removed round_position
# ---

# --- Utility Imports (Corrected) ---
# from vanta_seed.utils.file_utils import load_json_file # <<< Ensure this REMOVED incorrect import
# from vanta_seed.logging import get_vanta_logger # <<< REMOVE this incorrect import
from vanta_seed.utils.vector_utils import round_position # <<< Added round_position import
# --- Import YAML loader from run.py --- # This is now defined locally
import yaml 
from vanta_seed.agents.agent_utils import PurposePulse, MythicRole # <<< Import PurposePulse and MythicRole
# ---------------------------------- #

# --- Define local helper functions --- 
def load_json_file(file_path: str | Path) -> Optional[Dict[str, Any]]:
    """Loads a JSON file, returning None on error."""
    log = logging.getLogger(__name__) # Get logger specific to this module
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        log.error(f"JSON file not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        log.error(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        log.error(f"Error loading JSON file {file_path}: {e}", exc_info=True)
        return None

def load_yaml_config(file_path: str | Path) -> Optional[Dict[str, Any]]: # ADDED Function
    """Loads a YAML file, returning None on error."""
    log = logging.getLogger(__name__)
    if not os.path.exists(file_path):
        log.error(f"YAML configuration file not found: {file_path}")
        return None
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        log.error(f"Error parsing YAML from {file_path}: {e}")
        return None
    except Exception as e:
        log.error(f"Error loading YAML file {file_path}: {e}", exc_info=True)
        return None
# ----------------------------------

# --- Check if Swarm Types are actually available (for conditional logic) ---
SWARM_TYPES_AVAILABLE = True # Assume available for now, adjust if imports fail
# NOTE: Removed the try/except block for SWARM_TYPES_AVAILABLE as requested for now.
# ----------------------------------------------------------------------------

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
        # Use standard logging.getLogger
        self.logger = logging.getLogger(self.__class__.__name__) 
        self.core_config: Optional[Any] = None
        self._agents: Dict[str, BaseAgent] = {} # <<< Changed AgentInterface to BaseAgent
        self._agent_states: Dict[str, NodeStateModel] = {} # Placeholder for Pilgrim Trinity states
        self._model_to_agent_map: Dict[str, str] = {} # <<< ADDED: Map model names to agent names

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
        """Loads the core configuration (kingdom parameters) from the YAML file.""" 
        self.logger.info(f"Crown: Loading core configuration from: {self.core_config_path}")
        # Use the locally defined load_yaml_config
        config_data = load_yaml_config(self.core_config_path)
        # ---------------------------
        if config_data is None: # Check if loading failed
            raise ValueError("load_yaml_config returned None")
            
        # Temporarily store raw dict
        self.core_config = config_data # Store raw dict for now
        # --- Load stigmergic resolution AFTER config is loaded --- 
        self._stigmergic_resolution = config_data.get('swarm_config', {}).get('stigmergic_resolution', 1)
        # --- Load blessing threshold --- 
        crown_config = config_data.get('vanta_crown_interface', {})
        self._blessing_threshold = crown_config.get('blessing_threshold', 0.85) 
        self.logger.info(f"Crown: Successfully loaded core configuration. Stigmergic Res: {self._stigmergic_resolution}, Blessing Threshold: {self._blessing_threshold}")
        # --- Link to Spec ---
        # self.core_config now conceptually holds parameters defined in
        # Trinity Swarm YAML Spec v0.1 -> swarm_config & vanta_crown_interface sections.

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
        # Use dictionary access (.get) because self.core_config is currently a dict
        agent_list = self.core_config.get('agents') if self.core_config else None # Changed from self.core_config.agents
        if not self.core_config or not agent_list:
            self.logger.warning("Crown: No core configuration or agents list found. Skipping Pilgrim loading.") # Updated log message
            return

        self.logger.info(f"Crown: Loading {len(agent_list)} Pilgrims...")
        self._model_to_agent_map.clear() # Clear map before reloading

        for agent_config in agent_list:
            agent_name = agent_config.get('name')
            agent_class_str = agent_config.get('class')
            agent_settings = agent_config.get('settings', {})
            initial_node_state_config = agent_config.get('initial_trinity_state', {}) # Optional config
            compatible_model_names = agent_config.get('compatible_model_names', []) # <<< GET MODEL NAMES

            if not agent_name or not agent_class_str:
                self.logger.warning(f"Skipping Pilgrim due to missing name or class string in config: {agent_config}")
                continue

            try:
                self.logger.debug(f"Crown: Attempting to load Pilgrim '{agent_name}' (Class: '{agent_class_str}')")
                AgentClass: Optional[Type[BaseAgent]] = self.plugin_manager.get_plugin_class(agent_class_str, BaseAgent) # type: ignore

                if AgentClass is None:
                    self.logger.error(f"Crown: Pilgrim class '{agent_class_str}' not found for '{agent_name}'.")
                    continue

                # --- Construct initial_state dictionary --- #
                initial_state_dict = {
                    "name": agent_name,
                    "node_id": f"node_{agent_name}", # Ensure node_id consistency
                    "settings": agent_settings, # Pass settings nested inside state
                    "symbolic_identity": agent_config.get("symbolic_identity", {}),
                    "swarm_params": agent_config.get("swarm_params", {}),
                    "position": initial_node_state_config.get("position", [0.0, 0.0, 0.0]),
                    # Add other potential initial state fields from trinity_state or blueprint
                    "velocity": initial_node_state_config.get("velocity", [0.0, 0.0, 0.0]),
                    "energy_level": initial_node_state_config.get("energy_level", 1.0),
                    "current_role": initial_node_state_config.get("current_role", "Pilgrim"), # Default role
                    # Initialize purpose/mythic state placeholders if used by base init
                    "purpose_pulse": {"state": "Dormant", "intensity": 0.0}, # Default pulse
                    "mythic_role": {"current": "Pilgrim", "escalation": 0.0} # Default mythic role
                    # Add personal_best_position if needed, or let base init handle
                }
                # ------------------------------------------ #

                # --- Instantiate the Pilgrim ---
                # Pass reference to the Crown (self) and potentially initial state
                agent_instance = AgentClass(
                    name=agent_name,
                    initial_state=initial_state_dict,
                    settings=agent_settings # <<< ADDED: Pass the agent-specific settings
                )
                self._agents[agent_name] = agent_instance

                # --- Initialize Pilgrim State (Conceptual) ---
                # This state should align with Trinity Swarm YAML Spec v0.1 -> node_schema
                initial_pulse_state = initial_node_state_config.get("initial_pulse_state", "Dormant") # Get initial state or default
                initial_mythic_role = initial_node_state_config.get("initial_mythic_role", "Pilgrim") # <<< Get initial role
                self._agent_states[agent_name] = {
                    "id": f"node_{agent_name}",
                    "type": "TrinityPilgrim",
                    "created_at": asyncio.get_event_loop().time(),
                    "position": initial_node_state_config.get("position", [0.0, 0.0, 0.0]), # Example default
                    "velocity": [0.0, 0.0, 0.0],
                    "purpose_pulse": PurposePulse(initial_state=initial_pulse_state).to_dict(), # <<< Add PurposePulse state
                    "mythic_role": MythicRole(initial_role=initial_mythic_role).to_dict(), # <<< Add MythicRole state
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

                # --- Populate the model-to-agent map ---
                if compatible_model_names:
                    for model_name in compatible_model_names:
                        if model_name in self._model_to_agent_map:
                            self.logger.warning(f"Crown: Model name '{model_name}' conflict. Already mapped to '{self._model_to_agent_map[model_name]}'. Pilgrim '{agent_name}' will NOT overwrite.")
                        else:
                            self.logger.info(f"Crown: Mapping model name '{model_name}' to Pilgrim '{agent_name}'.")
                            self._model_to_agent_map[model_name] = agent_name
                # -----------------------------------------

                self.logger.info(f"Crown: Successfully loaded and initialized Pilgrim: '{agent_name}' with Pulse: {initial_pulse_state}, Role: {initial_mythic_role}")

                # --- ADDED: Trigger agent startup explicitly after loading --- 
                asyncio.create_task(self._run_agent_startup(agent_instance))
                # -----------------------------------------------------------

            except Exception as e:
                self.logger.error(f"Crown: Failed to load Pilgrim '{agent_name}': {e}", exc_info=True)

        self.logger.info(f"Crown: Finished loading Pilgrims. Total alive: {len(self._agents)}. Model map size: {len(self._model_to_agent_map)}") # Log map size

    async def _run_agent_startup(self, agent_instance: BaseAgent):
        """Safely runs the agent's startup method if it exists."""
        if hasattr(agent_instance, 'startup') and callable(agent_instance.startup):
            try:
                self.logger.debug(f"Running startup for agent: {agent_instance.name}")
                await agent_instance.startup()
            except Exception as e:
                self.logger.error(f"Error during startup for agent {agent_instance.name}: {e}", exc_info=True)

    def _get_pilgrim(self, agent_name: str) -> Optional[BaseAgent]: # Renamed from _get_agent, corrected type hint to BaseAgent
        """Retrieves a loaded Pilgrim instance by name."""
        pilgrim = self._agents.get(agent_name)
        if not pilgrim:
            self.logger.warning(f"Crown: Pilgrim '{agent_name}' not found.")
        return pilgrim

    def _get_pilgrim_state(self, agent_name: str) -> Optional[NodeStateModel]:
        """Retrieves the current internal state of a specific Pilgrim."""
        return self._agent_states.get(agent_name)

    def _update_pilgrim_state(self, agent_name: str, new_state_data: Dict[str, Any]):
        """Updates the internal state of a Pilgrim."""
        if agent_name not in self._agent_states:
            self.logger.warning(f"Crown: Cannot update state for unknown Pilgrim '{agent_name}'")
            return

        self._agent_states[agent_name].update(new_state_data)
        self.logger.info(f"Crown: Updated state for Pilgrim '{agent_name}'.")

    async def _route_task(self, task_data: Dict[str, Any]) -> Any:
        """
        Routes a task to the appropriate Pilgrim based on intent, payload,
        or explicit target. This now incorporates routing based on 'requested_model'
        for 'chat_completion' intents.

        Args:
            task_data (Dict[str, Any]): The task dictionary, including intent, payload, context.

        Returns:
            Any: The result from the executed Pilgrim.
        """
        intent = task_data.get("intent")
        payload = task_data.get("payload", {})
        context = task_data.get("context", {})
        target_agent_name = task_data.get("target_agent")
        requested_model = payload.get("requested_model") if isinstance(payload, dict) else None

        pilgrim_to_run: Optional[BaseAgent] = None

        self.logger.debug(f"Crown: Routing task. Intent: '{intent}', Target: '{target_agent_name}', Requested Model: '{requested_model}'")

        # --- Priority 1: Explicit Target --- 
        if target_agent_name:
            pilgrim_to_run = self._get_pilgrim(target_agent_name)
            if not pilgrim_to_run:
                self.logger.warning(f"Crown: Explicit target Pilgrim '{target_agent_name}' not found.")
                # Fall through to other routing methods or return error?
                # For now, let's fall through
            else:
                self.logger.info(f"Crown: Routing to explicitly targeted Pilgrim: {target_agent_name}")

        # --- Priority 2: OpenAI Model Routing (Optimized) ---
        # Only apply if no explicit target was found or valid
        elif intent == "chat_completion" and requested_model: # <<< Changed to elif
            self.logger.info(f"Crown: Attempting to route via requested model: '{requested_model}' using precomputed map.")
            target_agent_name_from_map = self._model_to_agent_map.get(requested_model)

            if target_agent_name_from_map:
                pilgrim_to_run = self._get_pilgrim(target_agent_name_from_map)
                if pilgrim_to_run:
                    self.logger.info(f"Crown: Found matching Pilgrim '{target_agent_name_from_map}' for model '{requested_model}' via map.")
                else:
                    # This case is unlikely if map is built correctly, but good to handle
                    self.logger.error(f"Crown: Model map pointed to '{target_agent_name_from_map}' for model '{requested_model}', but Pilgrim not loaded.")
                    # Fall through to default routing
            else:
                 self.logger.warning(f"Crown: No Pilgrim found mapped to requested model '{requested_model}'. Falling back.")
                 # Fall through to default routing

        # --- Priority 3: Default Routing (Placeholder - based on intent?) --- 
        if not pilgrim_to_run:
            # Basic fallback: Use the first available agent or a designated default
            # A more sophisticated router would analyze intent/payload here.
            if self._agents:
                default_agent_name = list(self._agents.keys())[0] # Example: First agent
                pilgrim_to_run = self._agents[default_agent_name]
                self.logger.info(f"Crown: No specific route found. Falling back to default Pilgrim: {default_agent_name}")
            else:
                 self.logger.error("Crown: Routing failed. No Pilgrims available.")
                 return {"error": "No agents available to handle the task."}

        # --- Execute Task on Selected Pilgrim --- 
        if pilgrim_to_run:
            return await self._run_task_on_pilgrim(pilgrim_to_run, task_data)
        else:
            # This case should ideally be handled above, but as a safeguard:
            self.logger.error("Crown: Routing logic failed to select a Pilgrim.")
            return {"error": "Task routing failed internally."}

    async def _run_task_on_pilgrim(self, pilgrim: BaseAgent, task_data: Dict[str, Any]) -> Any:
        """Executes a task using the specified Pilgrim agent, handling state updates including Pulse/Role."""
        self.logger.info(f"Crown: Executing task with Pilgrim: '{pilgrim.name}'")
        pilgrim_full_state = self._get_pilgrim_state(pilgrim.name)

        if not pilgrim_full_state:
            self.logger.error(f"Crown: Cannot run task, state not found for Pilgrim '{pilgrim.name}'")
            return {"error": f"State not found for Pilgrim '{pilgrim.name}'"}

        # --- Get Local Stigmergic Context (existing logic) --- 
        local_trails = []
        pilgrim_current_pos = [0.0, 0.0, 0.0] # Default position
        # Extract position safely
        if SWARM_TYPES_AVAILABLE:
             # Assuming NodeStateModel structure is used if SWARM_TYPES_AVAILABLE is True
             pilgrim_current_pos = pilgrim_full_state.position if hasattr(pilgrim_full_state, 'position') else [0.0, 0.0, 0.0]
             sensor_radius = pilgrim_full_state.swarm_params.sensor_radius if hasattr(pilgrim_full_state, 'swarm_params') and hasattr(pilgrim_full_state.swarm_params, 'sensor_radius') else 5.0
        else:
             # Use dictionary access if not using Pydantic models
             pilgrim_current_pos = pilgrim_full_state.get('position', [0.0, 0.0, 0.0])
             sensor_radius = pilgrim_full_state.get('swarm_params', {}).get('sensor_radius', 5.0)
        
        local_trails = self.get_stigmergic_data_near(pilgrim_current_pos, radius=sensor_radius)
        # --- End Stigmergic Context ---

        task_data_with_context = {
            **task_data,
            "_crown_context": { 
                # --- MODIFIED START: Safe dict conversion for purpose vector ---
                "purpose_vector": self._current_purpose_vector.model_dump(mode='json') if SWARM_TYPES_AVAILABLE and hasattr(self._current_purpose_vector, 'model_dump') 
                                  else (self._current_purpose_vector.dict() if SWARM_TYPES_AVAILABLE and hasattr(self._current_purpose_vector, 'dict') 
                                  else (self._current_purpose_vector.copy() if isinstance(self._current_purpose_vector, dict) 
                                  else self._current_purpose_vector)), # Fallback to original if not model or dict
                # --- END MODIFIED ---
                
                # --- MODIFIED START: Safe dict conversion for local trails ---
                "stigmergic_trails": [(t.model_dump(mode='json') if SWARM_TYPES_AVAILABLE and hasattr(t, 'model_dump') 
                                     else (t.dict() if SWARM_TYPES_AVAILABLE and hasattr(t, 'dict') 
                                     else (t.copy() if isinstance(t, dict) 
                                     else t))) 
                                    for t in local_trails],
                # --- END MODIFIED ---
                
                # --- MODIFIED START: Safe dict conversion for global best node ---
                "global_best_node": (self._global_trinity_best_node.model_dump(mode='json') if SWARM_TYPES_AVAILABLE and hasattr(self._global_trinity_best_node, 'model_dump') 
                                    else (self._global_trinity_best_node.dict() if SWARM_TYPES_AVAILABLE and hasattr(self._global_trinity_best_node, 'dict') 
                                    else (self._global_trinity_best_node.copy() if isinstance(self._global_trinity_best_node, dict) 
                                    else self._global_trinity_best_node))) if self._global_trinity_best_node else None,
                # --- END MODIFIED ---
            },
            # Pass the full state dict, including pulse and role
            # --- MODIFIED START: Safe dict conversion for pilgrim state ---
            "_pilgrim_state": (pilgrim_full_state.model_dump(mode='json') if SWARM_TYPES_AVAILABLE and hasattr(pilgrim_full_state, 'model_dump') 
                              else (pilgrim_full_state.dict() if SWARM_TYPES_AVAILABLE and hasattr(pilgrim_full_state, 'dict') 
                              else (pilgrim_full_state.copy() if isinstance(pilgrim_full_state, dict) 
                              else pilgrim_full_state)))
            # --- END MODIFIED ---
        }
        
        task_successful = False
        result = {}
        # --- Execute Task --- 
        try:
            if hasattr(pilgrim, 'execute') and asyncio.iscoroutinefunction(pilgrim.execute):
                result = await pilgrim.execute(task_data_with_context)
                self.logger.info(f"Crown: Task successfully executed by Pilgrim: '{pilgrim.name}'")
                task_successful = True # Mark task as successful
            else:
                self.logger.error(f"Crown: Pilgrim '{pilgrim.name}' does not have a valid async 'execute' method.")
                result = {"error": f"Pilgrim '{pilgrim.name}' cannot execute tasks."}

        except Exception as e:
            self.logger.error(f"Crown: Error executing task with Pilgrim '{pilgrim.name}': {e}", exc_info=True)
            result = {"error": f"Task execution failed on Pilgrim '{pilgrim.name}': {str(e)}"}
            task_successful = False # Mark task as failed
            
        # --- Process Results: Update State (including Pulse/Role) & Record Trail --- 
        # Get potential state updates from the agent's result
        agent_state_updates = result.get('new_state_data', {}) 
        
        # --- Mythic Role Escalation/De-escalation Logic (Orchestrator part) --- 
        current_mythic_role_dict = pilgrim_full_state.get('mythic_role', {"current_role": "Pilgrim"})
        mythic_role = MythicRole.from_dict(current_mythic_role_dict)
        original_role = mythic_role.get_role()
        
        # Basic Trigger Logic (Refine Later):
        if task_successful: 
            mythic_role.escalate_role() # Escalate on success (simple example)
        else: # De-escalate on error
             mythic_role.deescalate_role()
             
        if mythic_role.get_role() != original_role:
             self.logger.info(f"Crown: Mythic Role for '{pilgrim.name}' changed: {original_role} -> {mythic_role.get_role()}")
             # Ensure role update is included in state changes
             agent_state_updates['mythic_role'] = mythic_role.to_dict()
        # ---------------------------------------------------------------------
        
        # --- Update Full State if changes occurred --- 
        if agent_state_updates: # This now includes agent updates AND potential role update
            self._update_pilgrim_state(pilgrim.name, agent_state_updates)
        
        # --- Record Trail Signature (existing logic) --- 
        trail_signature_data = result.get('trail_signature_data')
        if trail_signature_data and isinstance(trail_signature_data, dict):
            # Ensure required fields are present
            if 'emitting_node_id' not in trail_signature_data:
                 # Use node ID from potentially updated state if available
                 updated_state = self._get_pilgrim_state(pilgrim.name) # Get potentially updated state
                 node_id = f"node_{pilgrim.name}" # Default
                 if updated_state:
                      node_id = updated_state.id if SWARM_TYPES_AVAILABLE and hasattr(updated_state, 'id') else updated_state.get('id', node_id)
                 trail_signature_data['emitting_node_id'] = node_id
                 
            if 'position_at_emission' not in trail_signature_data:
                 # Use updated position if agent provided it, else use last known
                 updated_pos = agent_state_updates.get('position', pilgrim_current_pos) 
                 trail_signature_data['position_at_emission'] = updated_pos
                 
            self._record_trail_signature(trail_signature_data)
        # ----------------------------------------------

        # Return only the primary task result part of the agent's response
        return result.get("task_result", result) 

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

            # --- MODIFIED START: Hardcode max_items --- 
            max_items = 50 # Hardcoded buffer size for simplicity
            # --- END MODIFIED ---

            # Access max_items using modern Pydantic approach (model_fields)
            # try:
            #     # Pydantic v2+ approach
            #     max_items = StigmergicFieldPoint.model_fields['recent_trail_signatures'].metadata.get('max_length', 50) # Check metadata first
            #     if not max_items:
            #          # Fallback check constraints if metadata missing max_length
            #          if hasattr(StigmergicFieldPoint.model_fields['recent_trail_signatures'], 'max_length'):
            #               max_items = StigmergicFieldPoint.model_fields['recent_trail_signatures'].max_length
            #          else:
            #               max_items = 50 # Default if not found
            # except (AttributeError, KeyError):
            #      # Fallback for older Pydantic or unexpected structure
            #      try:
            #           # Pydantic v1 approach
            #           field_info = StigmergicFieldPoint.__fields__['recent_trail_signatures'].field_info
            #           max_items = getattr(field_info, 'max_items', 50) # Check field_info directly
            #      except (AttributeError, KeyError):
            #          # Absolute fallback
            #          max_items = 50
            #          self.logger.warning("Could not determine max_items for trail signatures. Falling back to default.")

            # Trim the buffer if it exceeds the limit
            if len(field_point.recent_trail_signatures) > max_items:
                field_point.recent_trail_signatures = field_point.recent_trail_signatures[-max_items:]

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