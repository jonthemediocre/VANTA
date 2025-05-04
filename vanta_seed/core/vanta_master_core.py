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
# --- ADDED: Import BlueprintConfig --- 
from vanta_seed.core.models import AgentConfig, TaskData, BlueprintConfig 
# ----------------------------------
# Use absolute imports relative to vanta_seed
from vanta_seed.core.memory_weave import MemoryWeave
from vanta_seed.core.symbolic_compression import SymbolicCompressor 
from vanta_seed.core.swarm_weave import SwarmWeave
from vanta_seed.core.sleep_mutator import SleepMutator
from vanta_seed.core.gated_breath import GatedBreath
from vanta_seed.core.identity_trees import IdentityTrees
from vanta_seed.core.vitals_layer import VitalsLayer
from vanta_seed.agents.base_agent import BaseAgent # Keep absolute import for parent package
from vanta_seed.core.data_models import AgentInput, AgentResponse, ToolCall, ToolResponse, AgentMessage 
from vanta_seed.core.models import AgentConfig, TaskData 
from vanta_seed.core.agent_message_bus import AgentMessageBus
from vanta_seed.utils.plugin_manager import PluginManager # Keep absolute import
from vanta_seed.core.swarm_types import NodeStateModel, PurposeVectorModel, SwarmHealthMetricsModel, GlobalBestNodeInfo, TrailSignature, Position, StigmergicFieldPoint
from vanta_seed.core.governance_engine import GovernanceEngine
from vanta_seed.core.procedural_engine import ProceduralEngine
from vanta_seed.core.automutator import Automutator
from vanta_seed.core.autonomous_tasker import AutonomousTasker
from vanta_seed.core.ritual_executor import RitualExecutor
from vanta_seed.core.memory_store import MemoryStore 
from vanta_seed.utils.vector_utils import round_position # Keep absolute import
import yaml 
from vanta_seed.agents.agent_utils import PurposePulse, MythicRole # Keep absolute import
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

        # --- NEW: References to Core Engines ---
        self.memory_store: Optional[MemoryStore] = None
        self.governance_engine: Optional[GovernanceEngine] = None
        self.procedural_engine: Optional[ProceduralEngine] = None
        self.ritual_executor: Optional[RitualExecutor] = None
        self.automutator: Optional[Automutator] = None
        self.autonomous_tasker: Optional[AutonomousTasker] = None
        # ---------------------------------------
        
        # --- NEW: Agent Message Bus --- 
        self.message_bus = AgentMessageBus() # Initialize the message bus
        self.logger.info("AgentMessageBus initialized.")
        # ----------------------------

        # --- Initialization ---
        self._load_core_config() # Load kingdom parameters
        # --- Initialize Core Engines AFTER config is loaded --- 
        self._initialize_core_engines()
        # ----------------------------------------------------
        self._initialize_purpose_vector() # Set the first Dream Pulse (conceptually)
        self._load_pilgrims() # Load agents as Pilgrims

    def _load_core_config(self):
        """Loads the core configuration (kingdom parameters) from the YAML file."""
        self.logger.info(f"Crown: Loading core configuration from: {self.core_config_path}")
        config_data = load_yaml_config(self.core_config_path)
        if config_data is None: # Check if loading failed
            raise ValueError("load_yaml_config returned None, cannot initialize Crown.") # Raise clearer error

        # --- Log the loaded data structure --- 
        self.logger.debug(f"Raw config_data loaded from YAML:\n{json.dumps(config_data, indent=2)}")
        # -------------------------------------

        # --- Validate and Store as Pydantic Object --- 
        try:
            # Ensure BlueprintConfig is imported: from vanta_seed.core.models import BlueprintConfig
            self.core_config = BlueprintConfig(**config_data) # Validate and store Pydantic model
            self.logger.info("Crown: Core configuration validated successfully.")
        except ValidationError as e:
            self.logger.error(f"Crown: Core configuration validation failed: {e}", exc_info=True)
            # Decide handling: raise error or attempt to proceed with partial/raw config?
            # Raising error is safer to prevent unexpected behavior downstream.
            raise ValueError(f"Core configuration validation failed: {e}") from e
        # ---------------------------------------------

        # --- Load dependent parameters AFTER validation ---
        # Access validated config via self.core_config.<attribute>
        # Use getattr for safe access to optional top-level sections
        swarm_cfg = getattr(self.core_config, 'swarm_config', {}) # Safely get potential sub-model or dict
        crown_iface = getattr(self.core_config, 'vanta_crown_interface', {})

        self._stigmergic_resolution = swarm_cfg.get('stigmergic_resolution', 1) if isinstance(swarm_cfg, dict) else getattr(swarm_cfg, 'stigmergic_resolution', 1)
        self._blessing_threshold = crown_iface.get('blessing_threshold', 0.85) if isinstance(crown_iface, dict) else getattr(crown_iface, 'blessing_threshold', 0.85)
        # -------------------------------------------------
        self.logger.info(f"Crown: Stigmergic Res: {self._stigmergic_resolution}, Blessing Threshold: {self._blessing_threshold}")
        # --- Link to Spec ---
        # self.core_config now holds parameters defined in
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

    def _load_pilgrims(self):
        """Loads Pilgrim agents based on the blueprint configuration."""
        self.logger.info(f"Crown: Loading {len(self.core_config.agents)} Pilgrims...")
        self.pilgrims = {} # CHANGE: Use self.pilgrims consistently
        self._pilgrim_states = {} # Initialize state dictionary
        self._model_to_agent_map = {} # Initialize model map
        total_loaded_successfully = 0

        # --- Ritual: Pre-Load Preparation (Placeholder) ---
        self._execute_ritual_if_found('before_pilgrim_load')
        # --------------------------------------------------

        for agent_config_data in self.core_config.agents:
            agent_name = agent_config_data.name
            agent_class_path = agent_config_data.class_path
            agent_enabled = agent_config_data.enabled

            if not agent_enabled:
                self.logger.info(f"Crown: Skipping disabled Pilgrim: {agent_name}")
                continue

            try:
                # --- Step 1: Get Agent Class ---
                AgentClass = self.plugin_manager.get_plugin_class(agent_class_path)
                if not AgentClass:
                    self.logger.error(f"Crown: Agent class not found for path: {agent_class_path}")
                    continue # Skip this agent

                # --- Step 2: Validate Config with Pydantic Model ---
                # agent_config_obj = AgentConfig(**agent_config_data.dict()) # Validate full structure
                # NOTE: agent_config_data is already an AgentConfig instance due to BlueprintConfig validation
                agent_config_obj = agent_config_data

                # --- Step 3: Instantiate Agent --- 
                # Check for specific agent types with different init signatures
                agent_instance: Optional[BaseAgent] = None
                if AgentClass.__name__ == "ProxyDeepSeekAgent":
                    try:
                        proxy_settings = agent_config_obj.settings.model_dump() if agent_config_obj.settings else {}
                        # Proxy needs initial_state as a dict, not TrinityState Pydantic model
                        proxy_initial_state = agent_config_obj.initial_trinity_state.model_dump() if agent_config_obj.initial_trinity_state else {}
                        self.logger.debug(f"Instantiating ProxyDeepSeekAgent '{agent_name}' with specific signature.")
                        # Corrected call matching ProxyDeepSeekAgent __init__ expectations
                        agent_instance = AgentClass(
                            name=agent_name, 
                            settings=proxy_settings, # Pass settings dict as 'settings'
                            initial_state=proxy_initial_state # Pass initial state dict
                        )
                    except Exception as e:
                         self.logger.error(f"Crown: Error instantiating specific agent ProxyDeepSeekAgent '{agent_name}': {e}", exc_info=True)
                         continue # Skip this agent
                # --- ADDED: Specific handling for MemoryAgent ---
                elif AgentClass.__name__ == "MemoryAgent":
                    try:
                        self.logger.debug(f"Instantiating MemoryAgent '{agent_name}' with MemoryStore injection.")
                        agent_instance = AgentClass(
                            name=agent_name,
                            config=agent_config_obj,
                            logger=self.logger,
                            orchestrator_ref=self,
                            memory_store=self.memory_store # Inject the MemoryStore
                        )
                    except Exception as e:
                         self.logger.error(f"Crown: Error instantiating MemoryAgent '{agent_name}': {e}", exc_info=True)
                         continue # Skip this agent
                # ---------------------------------------------
                else:
                    # Default instantiation for other agents derived from BaseAgent
                    try:
                        # --- GET AGENT-SPECIFIC LOGGER and SET LEVEL --- 
                        agent_logger = logging.getLogger(f"Agent.{agent_name}")
                        # Force level based on environment or global config if needed
                        # For now, let's try forcing DEBUG
                        agent_logger.setLevel(logging.DEBUG) 
                        # ----------------------------------------------
                        agent_instance = AgentClass(
                            name=agent_name, 
                            config=agent_config_obj, 
                            logger=agent_logger, # <<< Pass the specific logger 
                            orchestrator_ref=self
                        )
                    except TypeError as te:
                        self.logger.error(f"Crown: TypeError instantiating standard agent '{agent_name}' ({AgentClass.__name__}): {te}. Check __init__ signature.", exc_info=True)
                        continue
                    except Exception as e:
                        self.logger.error(f"Crown: Error instantiating standard agent '{agent_name}' ({AgentClass.__name__}): {e}", exc_info=True)
                        continue
                # ----------------------------------
                
                # Check if instantiation failed (e.g. proxy init failure)
                if agent_instance is None:
                    self.logger.error(f"Crown: Instantiation returned None for Pilgrim: {agent_name}. Skipping further setup.")
                    continue

                self.logger.debug(f"Crown: Successfully instantiated Pilgrim: {agent_name}")

                # --- Step 4: Add to live pilgrims *only if instantiation succeeded* ---
                self.pilgrims[agent_name] = agent_instance

                # --- Step 5: Initialize State *after successful instantiation* ---
                self._initialize_pilgrim_state(agent_name, agent_config_obj)
                
                # --- Step 5.5: Register agent with Message Bus using agent_name --- 
                self.message_bus.register_agent(agent_name, agent_instance) # Use agent_name as ID
                # -----------------------------------------------

                # --- Step 6: Update Model Map *after successful instantiation* ---
                # Safely check for compatible_model_names attribute
                compatible_models = getattr(agent_config_obj, 'compatible_model_names', None)
                if compatible_models:
                    for model_name in compatible_models:
                        if model_name in self._model_to_agent_map:
                            self.logger.warning(f"Model '{model_name}' already mapped to agent '{self._model_to_agent_map[model_name]}'. Overwriting with '{agent_name}'.")
                        self._model_to_agent_map[model_name] = agent_name
                        self.logger.debug(f"Mapped model '{model_name}' to agent '{agent_name}'")

                # --- Step 7: Increment successful load count --- 
                total_loaded_successfully += 1
                # Optional: Run agent-specific startup?
                # asyncio.create_task(agent_instance.startup()) # If startup is async

            except ValidationError as e:
                self.logger.error(f"Crown: Configuration validation failed for Pilgrim '{agent_name}': {e}", exc_info=True)
                continue # Skip this agent
            except Exception as e:
                self.logger.error(f"Crown: Failed to load Pilgrim '{agent_name}': {e}", exc_info=True)
                continue # <<< ADDED: Ensure we skip adding/initializing if instantiation fails

        self.logger.info(f"Crown: Finished loading Pilgrims. Total alive: {total_loaded_successfully}. Model map size: {len(self._model_to_agent_map)}")

        # --- Ritual: Post-Load Finalization (Placeholder) ---
        self._execute_ritual_if_found('after_pilgrim_load')
        # ---------------------------------------------------

    def _initialize_pilgrim_state(self, agent_name: str, agent_config: AgentConfig):
        """Initializes the state dictionary for a given pilgrim."""
        try:
            # Start with the initial trinity state defined in the config
            initial_state_dict = agent_config.initial_trinity_state.model_dump() if agent_config.initial_trinity_state else {}

            # Add other essential base fields (using NodeStateModel structure as guide)
            initial_state_dict['id'] = f"node_{agent_name}_{uuid.uuid4().hex[:4]}" # Assign unique node ID
            initial_state_dict['name'] = agent_name
            # Ensure position/velocity defaults if not in trinity state config
            if 'position' not in initial_state_dict: initial_state_dict['position'] = [random.uniform(-10, 10) for _ in range(3)]
            if 'velocity' not in initial_state_dict: initial_state_dict['velocity'] = [0.0, 0.0, 0.0]
            initial_state_dict['current_role'] = "PILGRIM" # Default role
            initial_state_dict['personal_best_position'] = initial_state_dict['position'][:] # Initialize pBest
            initial_state_dict['personal_best_value'] = float('-inf')
            initial_state_dict['energy_level'] = 1.0 # Default energy
            initial_state_dict['last_updated_timestamp'] = asyncio.get_event_loop().time()
            
            # Incorporate agent settings and symbolic identity into the state dictionary
            initial_state_dict['settings'] = agent_config.settings.model_dump() if agent_config.settings else {}
            initial_state_dict['symbolic_identity'] = agent_config.symbolic_identity.model_dump() if agent_config.symbolic_identity else {}

            # Initialize PurposePulse and MythicRole states within the main state dict
            initial_state_dict['purpose_pulse'] = PurposePulse().to_dict() # Store as dict
            initial_state_dict['mythic_role'] = MythicRole().to_dict() # Store as dict

            # Add swarm params if defined in config settings, else use defaults
            # This structure assumes swarm_params are nested under agent_config.settings
            swarm_params_settings = initial_state_dict['settings'].get('swarm_params', {})
            initial_state_dict['swarm_params'] = {
                'inertia_weight': swarm_params_settings.get('inertia_weight', 0.7),
                'cognitive_weight': swarm_params_settings.get('cognitive_weight', 1.5),
                'social_weight': swarm_params_settings.get('social_weight', 1.5),
                'stigmergic_weight': swarm_params_settings.get('stigmergic_weight', 1.0),
                'max_speed': swarm_params_settings.get('max_speed', 1.0),
                # Add other swarm params with defaults
            }

            # Store the fully constructed initial state
            self._pilgrim_states[agent_name] = initial_state_dict
            self.logger.info(f"Initialized state for Pilgrim '{agent_name}' at position {initial_state_dict['position']}")

        except Exception as e:
            self.logger.error(f"Failed to initialize state for Pilgrim '{agent_name}': {e}", exc_info=True)
            # Ensure state is not partially initialized if error occurs
            if agent_name in self._pilgrim_states:
                del self._pilgrim_states[agent_name]

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
        pilgrim = self.pilgrims.get(agent_name)
        if not pilgrim:
            self.logger.warning(f"Crown: Pilgrim '{agent_name}' not found.")
        return pilgrim

    def _get_pilgrim_state(self, agent_name: str) -> Optional[Dict[str, Any]]: # Changed return type hint
        """Retrieves the current internal state dictionary of a specific Pilgrim."""
        # <<< FIXED: Use the correct state dictionary name >>>
        return self._pilgrim_states.get(agent_name)

    def _update_pilgrim_state(self, agent_name: str, new_state_data: Dict[str, Any]):
        """Updates the internal state of a Pilgrim."""
        # <<< FIXED: Use the correct state dictionary name >>>
        if agent_name not in self._pilgrim_states:
            self.logger.warning(f"Crown: Cannot update state for unknown Pilgrim '{agent_name}'")
            return

        self._pilgrim_states[agent_name].update(new_state_data)
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

        # --- DEBUGGING: Log available pilgrim keys --- 
        self.logger.info(f"Crown: Routing - Available Pilgrim Keys: {list(self.pilgrims.keys())}")
        # -------------------------------------------

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
            if self.pilgrims:
                default_agent_name = list(self.pilgrims.keys())[0] # Example: First agent
                pilgrim_to_run = self.pilgrims[default_agent_name]
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
        """Perform startup tasks for the Crown and Pilgrims.
        MODIFIED: Also starts core engines if they have start methods.
        """
        self.logger.info("VantaMasterCore Crown awakening...")
        # Start background tasks like swarm monitoring if needed
        # self._swarm_monitor_task = asyncio.create_task(self._run_swarm_monitoring())

        # --- Start Core Engines --- 
        core_engine_start_tasks = []
        if self.ritual_executor and hasattr(self.ritual_executor, 'start'):
            self.logger.debug("Starting RitualExecutor...")
            # Assuming start might be async or return a task
            start_op = self.ritual_executor.start()
            if asyncio.iscoroutine(start_op):
                 core_engine_start_tasks.append(start_op)
        if self.autonomous_tasker and hasattr(self.autonomous_tasker, 'start'):
             self.logger.debug("Starting AutonomousTasker...")
             start_op = self.autonomous_tasker.start()
             if asyncio.iscoroutine(start_op):
                  core_engine_start_tasks.append(start_op)
        # Add other engines if they have start methods
        # ------------------------
        
        # Call startup on all Pilgrims
        agent_names_for_startup = list(self._agents.keys())
        pilgrim_startup_tasks = []
        for agent_name in agent_names_for_startup:
            pilgrim = self._agents.get(agent_name) # Re-fetch in case dictionary changes
            if pilgrim and hasattr(pilgrim, 'startup') and asyncio.iscoroutinefunction(pilgrim.startup):
                self.logger.debug(f"Crown: Calling startup for Pilgrim '{agent_name}'")
                pilgrim_startup_tasks.append(pilgrim.startup())
        
        if pilgrim_startup_tasks:
             results = await asyncio.gather(*pilgrim_startup_tasks, return_exceptions=True)
             # Process results/errors - correlate back to agent names more carefully
             for i, result in enumerate(results):
                  agent_name = agent_names_for_startup[i]
                  if isinstance(result, Exception):
                       self.logger.error(f"Error during startup of Pilgrim '{agent_name}': {result}")

        # --- Wait for core engine starts if async --- 
        if core_engine_start_tasks:
            self.logger.debug("Waiting for core engine start tasks...")
            await asyncio.gather(*core_engine_start_tasks, return_exceptions=True)
            # TODO: Check results of engine starts
        # ------------------------------------------

        self.logger.info("VantaMasterCore Crown awake and operational.")

    async def shutdown(self):
        """Perform shutdown tasks for the Crown and Pilgrims.
        MODIFIED: Also shuts down core engines.
        """
        self.logger.info("VantaMasterCore Crown entering rest...")
        # Cancel background tasks
        # if hasattr(self, '_swarm_monitor_task') and self._swarm_monitor_task:
        #     self._swarm_monitor_task.cancel()
        #     try:
        #         await self._swarm_monitor_task
        #     except asyncio.CancelledError:
        #         self.logger.info("Swarm monitor task cancelled.")

        # --- Shutdown Core Engines FIRST --- 
        core_engine_shutdown_tasks = []
        # Call in reverse order of potential dependency? (Tasker -> Automutator -> Engines -> Rituals)
        if self.autonomous_tasker and hasattr(self.autonomous_tasker, 'shutdown'):
             self.logger.debug("Shutting down AutonomousTasker...")
             shutdown_op = self.autonomous_tasker.shutdown()
             if asyncio.iscoroutine(shutdown_op):
                  core_engine_shutdown_tasks.append(shutdown_op)
        if self.automutator and hasattr(self.automutator, 'shutdown'):
             self.logger.debug("Shutting down Automutator...")
             shutdown_op = self.automutator.shutdown()
             if asyncio.iscoroutine(shutdown_op):
                  core_engine_shutdown_tasks.append(shutdown_op)
        if self.ritual_executor and hasattr(self.ritual_executor, 'shutdown'):
            self.logger.debug("Shutting down RitualExecutor...")
            shutdown_op = self.ritual_executor.shutdown()
            if asyncio.iscoroutine(shutdown_op):
                 core_engine_shutdown_tasks.append(shutdown_op)
        # Add other engines if they have shutdown methods
        
        if core_engine_shutdown_tasks:
            self.logger.debug("Waiting for core engine shutdown tasks...")
            await asyncio.gather(*core_engine_shutdown_tasks, return_exceptions=True)
            # TODO: Check results of engine shutdowns
        self.logger.info("Core engines shutdown complete.")
        # --------------------------------

        # Call shutdown on all Pilgrims
        agent_names_for_shutdown = list(self._agents.keys())
        pilgrim_shutdown_tasks = []
        for agent_name in agent_names_for_shutdown:
             pilgrim = self._agents.get(agent_name) # Re-fetch
             if pilgrim and hasattr(pilgrim, 'shutdown') and asyncio.iscoroutinefunction(pilgrim.shutdown):
                 self.logger.debug(f"Crown: Calling shutdown for Pilgrim '{agent_name}'")
                 pilgrim_shutdown_tasks.append(pilgrim.shutdown())
        
        if pilgrim_shutdown_tasks:
             results = await asyncio.gather(*pilgrim_shutdown_tasks, return_exceptions=True)
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

    # --- NEW: Initialize Core Engines Method --- 
    def _initialize_core_engines(self):
        """Initializes core VANTA engines after core config is loaded."""
        self.logger.info("Crown: Initializing core engines...")
        if not self.core_config:
            self.logger.error("Cannot initialize core engines: Core config not loaded.")
            return

        try:
            # Use getattr to safely access optional top-level config sections
            # --- Determine MemoryStore persist path --- 
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # Get VANTA root dir
            default_memory_dir = os.path.join(base_dir, 'memory')
            storage_config = getattr(self.core_config, 'storage', {})
            persist_path_config = storage_config.get('persist_path') # Check if path specified in blueprint
            # ------------------------------------------
            
            # Pass config dict, let MemoryStore handle internal keys
            max_items_config = storage_config.get('max_items', 10000) # Get max_items from blueprint if set
            self.memory_store = MemoryStore(max_items=max_items_config, persist_path=persist_path_config)
            
            self.governance_engine = GovernanceEngine(config=getattr(self.core_config, 'governance', {}))
            self.procedural_engine = ProceduralEngine(config=getattr(self.core_config, 'procedural', {}))
            self.ritual_executor = RitualExecutor(config=getattr(self.core_config, 'rituals', {}), master_core_ref=self)
            self.automutator = Automutator(config=getattr(self.core_config, 'automutator', {}),
                                           procedural_engine=self.procedural_engine,
                                           governance_engine=self.governance_engine)
            self.autonomous_tasker = AutonomousTasker(config=getattr(self.core_config, 'autonomous_tasker', {}),
                                                automutator=self.automutator)
            
            # Load rules/data for engines that need it
            if hasattr(self.governance_engine, 'load_rules'): self.governance_engine.load_rules()
            if hasattr(self.procedural_engine, 'load_rules'): self.procedural_engine.load_rules()
            
            self.logger.info("Crown: Core engines initialized.")
        except Exception as e:
            self.logger.error(f"Crown: Failed to initialize one or more core engines: {e}", exc_info=True)
            # Should we prevent startup if core engines fail?
            # For now, log the error and continue, components will be None
            self.memory_store = None
            self.governance_engine = None
            self.procedural_engine = None
            self.ritual_executor = None
            self.automutator = None
            self.autonomous_tasker = None
    # -----------------------------------------

    # --- NEW: Method to access Message Bus --- 
    def get_message_bus(self) -> Optional[AgentMessageBus]:
        """Returns the instance of the AgentMessageBus."""
        return self.message_bus
    # -----------------------------------------

    # --- NEW: Placeholder for Ritual Execution --- 
    def _execute_ritual_if_found(self, trigger: str):
        """Placeholder method to simulate checking and executing rituals."""
        self.logger.debug(f"Checking for rituals triggered by: {trigger} (Placeholder - No execution)")
        if self.ritual_executor and hasattr(self.ritual_executor, 'trigger_rituals'):
            # In a real implementation, you might call:
            # asyncio.create_task(self.ritual_executor.trigger_rituals(trigger))
            pass # Just log for now
        else:
            self.logger.debug(f"RitualExecutor not available or missing 'trigger_rituals' method.")
    # ---------------------------------------------


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