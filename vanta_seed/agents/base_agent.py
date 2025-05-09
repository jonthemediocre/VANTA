import logging
import asyncio
import json
import random
import time
from abc import ABC, abstractmethod
from typing import Optional, List, Any, Dict, Type, Union, Tuple
from vanta_seed.core.data_models import AgentInput, AgentResponse, AgentMessage # Use absolute import
from vanta_seed.core.swarm_types import (
    NodeStateModel, TrailSignature, Position, PurposeVectorModel,
    GlobalBestNodeInfo, NodeRole
) # Use actual types if available

# Import Pydantic models
from ..core.models import AgentConfig, TaskData
import uuid # <<< Added uuid import

# --- Constants (Defaults) --- # ADDED Defaults block
DEFAULT_MAX_SPEED = 1.0
DEFAULT_INERTIA_WEIGHT = 0.7
DEFAULT_COGNITIVE_WEIGHT = 1.5
DEFAULT_SOCIAL_WEIGHT = 1.5
DEFAULT_STIGMERGIC_WEIGHT = 1.0 # Weight for trail influence
DEFAULT_ROLE_SWITCH_THRESHOLD = 0.6 # Example threshold

# --- Inherit directly from ABC --- 
class BaseAgent(ABC):
    """
    BaseAgent defines the minimal interface and core structure for all Trinity Pilgrim agents
    operating within the Breath Kingdom swarm. (Incorporating user's provided structure)
    """

    def __init__(self, name: str, config: AgentConfig, logger: logging.Logger, orchestrator_ref: Optional['VantaMasterCore'] = None):
        """
        Initialize the BaseAgent.

        Args:
            name (str): The unique name of the agent instance.
            config (AgentConfig): The Pydantic model containing the agent's validated configuration.
            logger (logging.Logger): The injected logger instance.
            orchestrator_ref (Optional[VantaMasterCore]): Reference to the core orchestrator.
        """
        # Assign basic attributes
        self._name = name 
        self.config = config # Store the validated Pydantic config model
        self.logger = logger # Store the injected logger
        self.orchestrator = orchestrator_ref # Store the orchestrator reference
        self.symbolic_identity = config.symbolic_identity # Loaded from validated config
        
        # --- Initialize Node ID --- 
        self.node_id = f"node_{name}_{uuid.uuid4().hex[:4]}" # Assign node_id here
        # ------------------------
        
        # --- Initialize State --- 
        self.state: Union[Dict[str, Any], NodeStateModel] = {} # Define the attribute first
        self._initialize_default_state() # Call state initializer
        # ------------------------
        
        self.logger.info(f"BaseAgent {self._name} (ID: {self.node_id}) initialized with archetype: {self.symbolic_identity.archetype}") # Added node_id to log

    def startup(self):
        """Optional method called once when the core starts up."""
        self.logger.info(f"Agent {self._name} ({self.symbolic_identity.mythos_role}) starting up.")
        # Announce identity
        self.logger.info(f" >> {self._name} Online. Archetype: {self.symbolic_identity.archetype}, Role: {self.symbolic_identity.mythos_role} <<")

    def shutdown(self):
        """Optional method called once when the core shuts down."""
        self.logger.info(f"Agent {self._name} shutting down.")

    @abstractmethod
    def execute(self, task: TaskData) -> Any:
        """
        Execute a given task.

        Args:
            task (TaskData): The Pydantic model containing task details.

        Returns:
            Any: The result of the task execution. Structure depends on the task intent.
                 Should be serializable (e.g., dict, list, str, int, float, bool).
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """Return the current status of the agent."""
        # Basic status, subclasses can override for more detail
        return {
            "name": self._name,
            "status": "running", # Or more specific status if tracked
            "config": self.config.dict() # Return dict representation of config
        }

    # --- Core Abstract Methods (Pilgrim Lifecycle) ---

    @abstractmethod
    async def execute(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution loop for the Pilgrim. Receives task data potentially including
        Crown context and the latest known state for this Pilgrim.

        Steps:
        1. Update internal state if newer state provided by Crown.
        2. Process context from Crown (purpose, trails, global best).
        3. Determine primary goal for this cycle.
        4. Calculate state updates (movement, role, energy) based on context and goals.
           -> This step now internally applies the calculated updates to self.state.
        5. Perform the core task logic specific to the agent subclass.
           -> Passes the *updated* state from step 4 to the subclass method.
        6. Generate a TrailSignature based on the outcome.
        7. Package results (task outcome, new state data dict, trail signature data dict) for the Crown.
        """
        self.logger.debug(f"Pilgrim '{self._name}': Execute cycle starting. Task keys: {list(task_data.keys())}")
        crown_context = task_data.get("_crown_context", {})
        # Get latest state data provided by Crown, defaults to current internal state if not provided
        latest_state_from_crown = task_data.get("_pilgrim_state", self.current_state)

        # --- Step 1: Update internal state if necessary ---
        # Compare dict versions to handle potential Pydantic objects
        if latest_state_from_crown != self.current_state:
             self.logger.debug(f"Pilgrim '{self._name}': Received updated state from Crown. Applying...")
             self._update_internal_state(latest_state_from_crown)
        else:
             self.logger.debug(f"Pilgrim '{self._name}': Crown state matches internal state.")

        # --- Step 2: Process Crown Context ---
        purpose_vector = crown_context.get("purpose_vector")
        stigmergic_trails = crown_context.get("stigmergic_trails", [])
        global_best_node = crown_context.get("global_best_node")
        self.logger.debug(f"Pilgrim '{self._name}': Context received. Trails: {len(stigmergic_trails)}, Purpose: {bool(purpose_vector)}, gBest: {bool(global_best_node)}")

        # --- Step 3: Determine Primary Goal ---
        primary_goal_for_cycle = task_data.get('primary_goal', purpose_vector)
        if not primary_goal_for_cycle:
            self.logger.warning(f"Pilgrim '{self._name}': No primary goal or purpose vector. Defaulting to hold position.")
            current_position = self.current_state.get('position', [0.0]*3)
            primary_goal_for_cycle = current_position # Use current position as goal

        # --- Step 4: Calculate & Apply State Updates --- 
        try:
            # This method calculates updates AND applies them internally to self.state
            state_updates_dict = self._calculate_state_updates(
                purpose_vector=purpose_vector,
                stigmergic_trails=stigmergic_trails,
                global_best_node=global_best_node,
                task_specific_goal=primary_goal_for_cycle
            )
            self.logger.debug(f"Pilgrim '{self._name}': State updates calculated and applied internally.")
        except Exception as e:
            self.logger.error(f"Pilgrim '{self._name}': Error calculating state updates: {e}. Proceeding with potentially stale state.", exc_info=True)
            state_updates_dict = {} # Indicate no updates were successfully calculated/applied

        # --- Step 5: Perform Core Task Logic --- 
        try:
            # Pass the *updated* state reflecting changes from step 4
            # Ensure we pass a dict copy to the subclass
            task_result = await self.perform_task(task_data, self.current_state.copy())
            self.logger.debug(f"Pilgrim '{self._name}': Core task performed. Success: {not task_result.get('error')}")
        except NotImplementedError:
            self.logger.error(f"Pilgrim '{self._name}': Subclass has not implemented perform_task!")
            task_result = {"error": "perform_task not implemented"}
        except Exception as e:
            self.logger.error(f"Pilgrim '{self._name}': Error performing core task logic: {e}", exc_info=True)
            task_result = {"error": f"Core task failed: {str(e)}"}

        # --- Step 6: Generate Trail Signature --- 
        # Generate signature based on the task outcome and the state *after* updates
        trail_signature = self._generate_trail_signature(task_result, state_updates_dict)
        self.logger.debug(f"Pilgrim '{self._name}': Trail signature generated.")

        # --- Step 7: Package Results for Crown --- 
        # Ensure trail signature is a dictionary for JSON serialization if needed
        trail_signature_data_for_crown = None
        if trail_signature:
            if isinstance(trail_signature, TrailSignature):
                try:
                     if hasattr(trail_signature, 'model_dump'):
                          trail_signature_data_for_crown = trail_signature.model_dump(mode='json')
                     else:
                          trail_signature_data_for_crown = trail_signature.dict()
                except Exception as e:
                    self.logger.error(f"Pilgrim '{self._name}': Failed to serialize TrailSignature model: {e}", exc_info=True)
                    trail_signature_data_for_crown = {"error": "TrailSignature serialization failed"}
            elif isinstance(trail_signature, dict):
                trail_signature_data_for_crown = trail_signature

        result_package = {
            "task_result": task_result, # The actual outcome of the subclass's perform_task
            "new_state_data": state_updates_dict, # Dict of changes applied in this cycle
            "trail_signature_data": trail_signature_data_for_crown # Serializable dict for the Crown
        }

        self.logger.debug(f"Pilgrim '{self._name}': Execute cycle complete. Returning package.")
        return result_package

    def _update_internal_state(self, new_state_data: Dict[str, Any]):
        """Safely updates the internal state (self.state) with new data, using Pydantic validation if possible."""
        if not new_state_data or not isinstance(new_state_data, dict):
             self.logger.warning(f"Pilgrim '{self._name}': Attempted to update state with invalid data type: {type(new_state_data)} or empty data.")
             return

        try:
             if isinstance(self.state, dict):
                 self.state.update(new_state_data)
                 self.logger.debug(f"Pilgrim '{self._name}': Internal state updated as dictionary.")
             else:
                 # Simple dictionary update if Pydantic types are not available/used
                 # This performs a shallow update, potentially overwriting nested dicts
                 self.state.update(new_state_data)
                 self.logger.debug(f"Pilgrim '{self._name}': Internal state updated as dictionary.")

        except Exception as e:
            self.logger.error(f"Pilgrim '{self._name}': Unexpected error updating internal state: {e}", exc_info=True)
            # Fallback: Try a simple dict update if Pydantic failed unexpectedly
            if isinstance(self.state, dict):
                 self.state.update(new_state_data)
                 self.logger.warning(f"Pilgrim '{self._name}': State update failed unexpectedly, performed shallow dict update as fallback.")
            # else: If state was Pydantic, it might be safer *not* to fall back to dict here
            #      pass

    def _get_swarm_param(self, param_name: str, default: Any) -> Any:
        """Safely retrieves a swarm parameter from the state's swarm_params."""
        swarm_params = None
        # Access state safely using the property
        current_state_dict = self.current_state

        if isinstance(current_state_dict.get('swarm_params'), dict):
             swarm_params = current_state_dict['swarm_params']
        # Handle case where state is Pydantic model directly (less common now with property)
        elif isinstance(self.state, NodeStateModel) and hasattr(self.state, 'swarm_params'):
             # Check if swarm_params is a Pydantic model or dict within the model
             if isinstance(self.state.swarm_params, SwarmParams):
                 # If it's the Pydantic model, check attribute existence
                 return getattr(self.state.swarm_params, param_name, default)
             elif isinstance(self.state.swarm_params, dict):
                 swarm_params = self.state.swarm_params

        if swarm_params:
            return swarm_params.get(param_name, default)

        self.logger.debug(f"Pilgrim '{self._name}': Swarm parameter '{param_name}' not found or state structure incorrect, using default: {default}")
        return default

    def _calculate_state_updates(self,
                                 purpose_vector: Optional[PurposeVectorModel | Dict],
                                 stigmergic_trails: List[TrailSignature | Dict],
                                 global_best_node: Optional[GlobalBestNodeInfo | Dict],
                                 task_specific_goal: Optional[Any]) -> Dict[str, Any]:
        """
        Calculates updates to the Pilgrim's state (position, velocity, role, energy, pBest)
        and applies these updates internally to self.state.

        Returns:
            A dictionary containing the changes made in this step.
        """
        self.logger.debug(f"Pilgrim '{self._name}': Calculating state updates...")
        current_state_dict = self.current_state # Get state at start of calculation

        # --- 1. Calculate Movement (Velocity & Position) --- 
        new_velocity, new_position = self._calculate_new_velocity_and_position(
            purpose_vector=purpose_vector,
            stigmergic_trails=stigmergic_trails,
            global_best_node=global_best_node
        )
        self.logger.debug(f"Pilgrim '{self._name}': Movement calculation completed.")

        # --- 2. Determine Role --- 
        # Pass the *new* position calculated in step 1
        next_role = self._determine_next_role(new_position, stigmergic_trails, purpose_vector)
        self.logger.debug(f"Pilgrim '{self._name}': Role determination completed. Next Role: {next_role}")

        # --- 3. Update Other State Variables (Energy, etc.) --- 
        current_pos = current_state_dict.get('position', [0.0]*3)
        distance_moved = sum([(p_new - p_old)**2 for p_new, p_old in zip(new_position, current_pos)])**0.5
        energy_cost = distance_moved * self._get_swarm_param('energy_cost_per_unit', 0.1)
        current_energy = current_state_dict.get('energy_level', 1.0)
        new_energy_level = max(0.0, current_energy - energy_cost)
        self.logger.debug(f"Pilgrim '{self._name}': Energy update calculated. Cost: {energy_cost:.3f}, New Level: {new_energy_level:.3f}")

        # --- 4. Assemble State Updates Dictionary --- 
        state_updates = {
            "position": new_position,
            "velocity": new_velocity,
            "current_role": next_role,
            "energy_level": new_energy_level,
            "last_updated_timestamp": time.time()
            # pBest update added below
        }

        # --- 5. Update Personal Best (if applicable) --- 
        # This comparison needs a proper objective function based on the task/purpose.
        # Placeholder: Use energy level as a simple fitness proxy.
        # A real implementation would use a fitness function relevant to the swarm's goal.
        current_pbest_value = current_state_dict.get('personal_best_value', float('-inf'))
        # Evaluate fitness at the *new* position (using energy for now)
        new_fitness_value = new_energy_level # Replace with evaluate_fitness(new_position, purpose_vector, ...)

        if new_fitness_value > current_pbest_value:
             state_updates["personal_best_position"] = new_position[:]
             state_updates["personal_best_value"] = new_fitness_value
             self.logger.info(f"Pilgrim '{self._name}': New personal best found at {[f'{p:.2f}' for p in new_position]}. Value: {new_fitness_value:.3f}")
        else:
             self.logger.debug(f"Pilgrim '{self._name}': Personal best not updated. Current: {current_pbest_value:.3f}, New Potential: {new_fitness_value:.3f}")

        # --- 6. Apply the updates internally NOW --- 
        if state_updates: 
             self.logger.debug(f"Pilgrim '{self._name}': Applying calculated state updates internally: {list(state_updates.keys())}")
             self._update_internal_state(state_updates)
        else:
             self.logger.debug(f"Pilgrim '{self._name}': No state updates to apply this cycle.")

        # Return the dictionary of changes that were calculated/applied
        return state_updates

    # --- Placeholder definitions for methods to be implemented next --- 
    def _calculate_new_velocity_and_position(self,
                                             purpose_vector: Optional[PurposeVectorModel | Dict],
                                             stigmergic_trails: List[TrailSignature | Dict],
                                             global_best_node: Optional[GlobalBestNodeInfo | Dict]) -> Tuple[Position, Position]:
        """Calculates the new velocity and position based on StigmergicPSO principles."""

        # Get current state safely using property
        current_state_dict = self.current_state
        current_pos = current_state_dict.get('position', [0.0]*3)
        current_vel = current_state_dict.get('velocity', [0.0]*3)
        personal_best_pos = current_state_dict.get('personal_best_position', current_pos[:]) # Default to current if missing

        # --- Safely get swarm parameters --- 
        w = self._get_swarm_param('inertia_weight', DEFAULT_INERTIA_WEIGHT)
        c1 = self._get_swarm_param('cognitive_weight', DEFAULT_COGNITIVE_WEIGHT)
        c2 = self._get_swarm_param('social_weight', DEFAULT_SOCIAL_WEIGHT)
        c3 = self._get_swarm_param('stigmergic_weight', DEFAULT_STIGMERGIC_WEIGHT)
        max_speed = self._get_swarm_param('max_speed', DEFAULT_MAX_SPEED)

        # --- Validate Position and Dimensions --- 
        if not current_pos or not isinstance(current_pos, list) or len(current_pos) == 0:
             self.logger.error(f"Pilgrim '{self._name}': Invalid current_pos: {current_pos}. Cannot calculate movement.")
             # Return current velocity (or zero) and current position (or origin)
             return current_vel or [0.0]*3, current_pos or [0.0]*3

        num_dimensions = len(current_pos)
        # Ensure velocity and pBest match dimensions
        if not current_vel or len(current_vel) != num_dimensions: current_vel = [0.0] * num_dimensions
        if not personal_best_pos or len(personal_best_pos) != num_dimensions: personal_best_pos = current_pos[:]

        new_velocity = [0.0] * num_dimensions

        # --- StigmergicPSO Components --- 
        # 1. Inertia Term: Tendency to continue in the current direction
        inertia_term = [w * v for v in current_vel]

        # 2. Cognitive Term: Attraction towards the agent's personal best position found so far
        r1 = random.random()
        cognitive_term = [c1 * r1 * (p_best - p_curr) for p_best, p_curr in zip(personal_best_pos, current_pos)]

        # 3. Social Term: Attraction towards the global best position found by any agent in the swarm
        global_best_pos = personal_best_pos # Default to pBest if gBest is missing/invalid
        if global_best_node:
            # Safely extract position from Pydantic or dict
            gbest_pos_candidate = None
            if isinstance(global_best_node, GlobalBestNodeInfo):
                 gbest_pos_candidate = global_best_node.position
            elif isinstance(global_best_node, dict):
                 gbest_pos_candidate = global_best_node.get('position')
            
            if gbest_pos_candidate and isinstance(gbest_pos_candidate, list) and len(gbest_pos_candidate) == num_dimensions:
                 global_best_pos = gbest_pos_candidate
            else:
                 self.logger.debug(f"Pilgrim '{self._name}': Global best node position invalid or missing. Using personal best for social term.")

        r2 = random.random()
        social_term = [c2 * r2 * (g_best - p_curr) for g_best, p_curr in zip(global_best_pos, current_pos)]

        # --- 4. Stigmergic Term: Influence from nearby trails (pheromones/symbols) --- 
        stigmergic_vector = [0.0] * num_dimensions
        if stigmergic_trails:
            weighted_sum_vec = [0.0] * num_dimensions
            total_weight = 0.0
            epsilon = 1e-6 # Avoid division by zero

            for trail_info in stigmergic_trails:
                # Ensure trail_info is a dict (handles Pydantic model case)
                trail = trail_info.model_dump(mode='json') if isinstance(trail_info, TrailSignature) else (trail_info if isinstance(trail_info, dict) else {})

                trail_pos = trail.get('position_at_emission')
                # Example weighting: Use relevance score * value proposition, decay with distance
                relevance = trail.get('relevance_score', 0.0)
                value_prop = trail.get('value_proposition', 0.0)
                trail_weight = relevance * value_prop # Combine factors

                if trail_pos and isinstance(trail_pos, list) and len(trail_pos) == num_dimensions and trail_weight > epsilon:
                    direction_to_trail = [(tp - cp) for tp, cp in zip(trail_pos, current_pos)]
                    distance_sq = sum(d*d for d in direction_to_trail)
                    # Simple inverse square distance weighting
                    weight = trail_weight / (distance_sq + epsilon)

                    weighted_sum_vec = [wsv + d * weight for wsv, d in zip(weighted_sum_vec, direction_to_trail)]
                    total_weight += weight

            if total_weight > epsilon:
                # Average weighted direction vector towards influential trails
                stigmergic_vector = [wsv / total_weight for wsv in weighted_sum_vec]
                self.logger.debug(f"Pilgrim '{self._name}': Calculated stigmergic influence vector: {[f'{v:.3f}' for v in stigmergic_vector]}")
            else:
                 self.logger.debug(f"Pilgrim '{self._name}': No significant stigmergic influence detected.")

        r3 = random.random()
        stigmergic_term = [c3 * r3 * s_vec for s_vec in stigmergic_vector]

        # --- Calculate New Velocity: Sum of components --- 
        for i in range(num_dimensions):
            new_velocity[i] = inertia_term[i] + cognitive_term[i] + social_term[i] + stigmergic_term[i]

            # --- Clamp Velocity to Max Speed --- 
            if abs(new_velocity[i]) > max_speed:
                new_velocity[i] = max_speed * (1 if new_velocity[i] > 0 else -1)
                self.logger.debug(f"Pilgrim '{self._name}': Velocity clamped in dimension {i} to {new_velocity[i]:.3f}")

        # --- Calculate New Position --- 
        new_position = [p + v for p, v in zip(current_pos, new_velocity)]

        # TODO: Add boundary handling if the environment has limits
        # Example: Clamp position within [-100, 100] in each dimension
        # new_position = [max(-100, min(100, p)) for p in new_position]

        self.logger.debug(f"Pilgrim '{self._name}': Vel Calc: I{[f'{v:.2f}' for v in inertia_term]} C{[f'{v:.2f}' for v in cognitive_term]} S{[f'{v:.2f}' for v in social_term]} St{[f'{v:.2f}' for v in stigmergic_term]} -> NewVel{[f'{v:.2f}' for v in new_velocity]}")
        self.logger.debug(f"Pilgrim '{self._name}': Calculated New Position: {[f'{p:.2f}' for p in new_position]}")
        return new_velocity, new_position

    def _determine_next_role(self,
                             current_position: Position,
                             stigmergic_trails: List[TrailSignature | Dict],
                             purpose_vector: Optional[PurposeVectorModel | Dict]) -> str:
        """Determines the agent's next role based on context and internal state. Returns role as a string."""
        # Get current state safely
        current_state_dict = self.current_state
        # Use string value as default
        current_role_str = current_state_dict.get('current_role', "PILGRIM") # Get/default as string

        # --- Role Switching Logic --- 

        # 1. Energy-Based SHADE Role:
        energy_level = current_state_dict.get('energy_level', 1.0)
        low_energy_threshold = self._get_swarm_param('shade_energy_threshold', 0.1) 
        recovery_energy_threshold = self._get_swarm_param('shade_recovery_threshold', 0.3)

        if energy_level < low_energy_threshold:
             if current_role_str != "SHADE":
                 self.logger.info(f"Pilgrim '{self._name}': Switching role to SHADE due to critical energy ({energy_level:.2f}).")
                 return "SHADE"
             else:
                 return "SHADE"

        if current_role_str == "SHADE" and energy_level > recovery_energy_threshold:
             self.logger.info(f"Pilgrim '{self._name}': Recovered energy ({energy_level:.2f}). Switching role from SHADE back to PILGRIM.")
             return "PILGRIM"

        # --- Placeholder for Sophisticated Role Logic --- 
        # TODO: Implement logic based on:
        #   - Proximity to strong/relevant trails (-> SCRIBE?)
        #   - Alignment with purpose vector vs. local exploration (-> HERALD vs PILGRIM?)
        #   - Density of other agents
        #   - Task requirements
        # -----------------------------------------------

        # Example Placeholder: Random chance to switch (low probability)
        switch_probability = self._get_swarm_param('random_role_switch_prob', 0.05)
        if random.random() < switch_probability:
            available_roles_str = ["PILGRIM", "SCRIBE", "HERALD"]
            new_role_str = random.choice(available_roles_str)
            if new_role_str != current_role_str:
                self.logger.info(f"Pilgrim '{self._name}': Randomly switching role from {current_role_str} to {new_role_str}. REPLACE THIS WITH ACTUAL LOGIC.")
                return new_role_str

        # Default: Maintain current role if no other condition met
        self.logger.debug(f"Pilgrim '{self._name}': Maintaining current role: {current_role_str}")
        return current_role_str

    def _generate_trail_signature(self, task_result: Dict[str, Any], state_updates: Dict[str, Any]) -> Optional[Union[TrailSignature, Dict]]:
        """Generates data for a TrailSignature based on the task outcome and the state *after* updates."""
        # Get the state reflecting the updates applied in _calculate_state_updates
        current_state_dict = self.current_state
        self.logger.debug(f"Pilgrim '{self._name}': Generating trail signature based on state after updates.")

        # Extract common info
        node_id = current_state_dict.get('id', self.node_id)
        position = current_state_dict.get('position', [0.0]*3)
        # Use string value as default
        role_str = current_state_dict.get('current_role', "PILGRIM")
        energy = current_state_dict.get('energy_level', 0.0)
        task_success = not task_result.get("error")

        # --- Placeholder values for advanced fields --- 
        # TODO: Calculate these based on actual context, task, purpose alignment
        purpose_alignment = random.random() # Needs actual calculation
        value_proposition = random.uniform(0.1, 0.9) if task_success else random.uniform(0.0, 0.2) # Higher value if task succeeded
        relevance_score = random.uniform(0.1, 0.9) # Needs calculation based on purpose vector
        # Optional: Infer direction from velocity
        direction_vector = current_state_dict.get('velocity')

        # Construct the data dictionary
        signature_data = {
            "emitting_node_id": node_id,
            "position_at_emission": position[:], # Ensure it's a copy
            "timestamp": time.time(),
            "role_at_emission": role_str,
            "data": { # Example data payload
                 "task_success": task_success,
                 "energy_level": energy,
                 "task_result_summary": str(task_result.get('summary', str(task_result)[:100])) # Short summary
                 # Add any other relevant outcome data
                 },
            "purpose_alignment_score": purpose_alignment,
            "value_proposition": value_proposition,
            "relevance_score": relevance_score,
             # Add optional fields if they exist
             # "direction_vector": direction_vector if direction_vector else None,
        }

        # Attempt to validate/create Pydantic model if possible
        try:
            from pydantic import BaseModel
            is_pydantic_state = isinstance(self.state, BaseModel)
        except ImportError:
            is_pydantic_state = False
            
        if is_pydantic_state:
        # if isinstance(self.state, NodeStateModel): # Original check might be too specific
            try:
                # Clean data: remove keys not in the model if necessary, or ensure defaults
                # Example: If TrailSignature doesn't have 'direction_vector', remove it
                # model_fields = TrailSignature.model_fields.keys()
                # cleaned_signature_data = {k: v for k, v in signature_data.items() if k in model_fields}
                # Or rely on Pydantic's default handling
                return TrailSignature(**signature_data)
            except Exception as e:
                self.logger.error(f"Pilgrim '{self._name}': Unexpected error generating Pydantic TrailSignature: {e}", exc_info=True)
                return signature_data # Fallback to raw dict
        else:
            # Return the raw dictionary if Pydantic types are not used
            return signature_data

    @abstractmethod
    async def perform_task(self, task_data: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core task logic specific to the Pilgrim subclass.

        Receives original task data and the *current state dictionary* after updates
        (position, role, energy, etc.) have been applied internally for this cycle.
        Implement the agent's primary function here.

        Args:
            task_data: Original data dict from the Crown/task source.
            current_state: A dict copy of the agent's state *after* internal updates for this cycle.

        Returns:
            Dict with task results (e.g., {"status": "success", "output": ..., "summary": ...}).
        """
        pass # Subclasses must implement

    # --- Helper Methods (Concrete implementations can live here) ---

    def _update_internal_state_from_context(self, state_data: Optional[Dict[str, Any]]):
        """Safely updates the internal state reference from context data."""
        if state_data:
            try:
                # Use NodeStateModel if available and imported
                # Check if NodeStateModel is the actual Pydantic class, not the fallback Dict
                if 'NodeStateModel' in locals() and issubclass(NodeStateModel, Dict) is False:
                     self.state = NodeStateModel(**state_data)
                else:
                     # Fallback if NodeStateModel is not properly defined/imported
                     self.state = state_data # Store as dict
                self.logger.debug("Internal state updated from context.")
            except Exception as e:
                self.logger.error(f"Failed to parse incoming pilgrim state data: {e}. State remains unchanged.", exc_info=True)
        else:
             self.logger.warning("No pilgrim state provided in context.")

    def emit_trail_signature(self) -> Optional[Dict[str, Any]]:
        """
        Generates the symbolic footprint based on the current internal state.
        (Refined based on user's version and our Pydantic models).
        """
        if not self.state:
            self.logger.warning("Cannot emit trail signature, internal state not available.")
            return None

        is_model_instance = 'NodeStateModel' in locals() and not issubclass(NodeStateModel, Dict) and isinstance(self.state, NodeStateModel)

        # Extract relevant info from the state model or dict
        current_pos = self.state.position if is_model_instance else self.state.get('position', [0.0, 0.0, 0.0])
        emotional_tone = None
        if is_model_instance and self.state.last_trail_signature:
             emotional_tone = self.state.last_trail_signature.emotional_tone_imprint
        elif not is_model_instance and self.state.get('last_trail_signature'):
             emotional_tone = self.state['last_trail_signature'].get('emotional_tone_imprint')

        # Memory relics concept needs integration into NodeStateModel.trinity_core.memory first.
        # For now, using placeholder markers based on mode.
        current_mode = "unknown"
        if is_model_instance:
             current_mode = self.state.meta_balancer.current_mode
        elif isinstance(self.state.get('meta_balancer'), dict):
             current_mode = self.state['meta_balancer'].get('current_mode', 'unknown')

        symbolic_markers = [f"mode_{current_mode}"]

        try:
            # Construct data matching TrailSignature model if possible
            signature_data = {
                "emitting_node_id": self.node_id,
                "position_at_emission": list(current_pos), # Ensure it's a list
                "symbolic_markers": symbolic_markers,
                "symbolic_resonance_score": 0.5, # Placeholder
                "emotional_tone_imprint": emotional_tone,
                "fitness_signal": None # Needs calculation based on environment/evaluation
            }
            # Add resonance score from state if available
            if is_model_instance:
                 signature_data["symbolic_resonance_score"] = self.state.meta_balancer.self_assessment_score
            elif isinstance(self.state.get('meta_balancer'), dict):
                 signature_data["symbolic_resonance_score"] = self.state['meta_balancer'].get('self_assessment_score', 0.5)

            # Validate with TrailSignature model if available and imported correctly
            if 'TrailSignature' in locals() and not issubclass(TrailSignature, Dict):
                 validated_signature = TrailSignature(**signature_data)
                 return validated_signature.dict()
            else:
                 return signature_data # Return raw dict if model not available

        except Exception as e:
             self.logger.error(f"Error generating trail signature: {e}", exc_info=True)
             return None

    # --- Optional Lifecycle Methods ---
    async def startup(self):
        """Optional startup logic for the Pilgrim."""
        self.logger.info("Pilgrim is awakening...")

    async def shutdown(self):
        """Optional shutdown logic for the Pilgrim."""
        self.logger.info("Pilgrim is entering rest...")

    # --- NEW: A2A Messaging Methods --- 
    async def send_message(self, message: 'AgentMessage') -> Optional[str]:
        """Sends a pre-constructed message object to another agent via the message bus.
        
        Args:
            message: The AgentMessage object to send.
            
        Returns:
            The message_id of the sent message, or None if sending failed.
        """
        if not self.orchestrator or not hasattr(self.orchestrator, 'get_message_bus'):
            self.logger.error(f"Cannot send message: Orchestrator or Message Bus not available.")
            return None
            
        message_bus = self.orchestrator.get_message_bus()
        if not message_bus:
             self.logger.error(f"Cannot send message: Message Bus instance is None.")
             return None
             
        # --- Validation (Optional but good practice) ---
        # Import locally or ensure AgentMessage is available
        from vanta_seed.core.data_models import AgentMessage 
        if not isinstance(message, AgentMessage):
             self.logger.error(f"Invalid object passed to send_message. Expected AgentMessage, got {type(message)}")
             return None
        # Ensure sender is correctly set (could be done here or assumed correct)
        if message.sender_id != self.node_id:
            self.logger.warning(f"Message sender_id '{message.sender_id}' doesn't match agent's node_id '{self.node_id}'. Overwriting sender_id.")
            message.sender_id = self.node_id
        # ---------------------------------------------
        
        try:
            # --- Log correlation ID just before publishing --- 
            # Use attributes directly from the message object
            self.logger.debug(f"SENDING message {message.message_id} to {message.receiver_id}. Intent: {message.intent}. CorrID: {message.correlation_id}")
            # ---------------------------------------------------------
            # The bus will use message.receiver_id for lookup
            await message_bus.publish_message(message)
            self.logger.info(f"Message {message.message_id} sent to {message.receiver_id} with intent '{message.intent}'.")
            return message.message_id
        except Exception as e:
            self.logger.error(f"Failed to publish message {message.message_id} to bus: {e}", exc_info=True)
            return None

    @abstractmethod
    async def receive_message(self, message: 'AgentMessage'):
        """
        Handles an incoming message received from the message bus.
        This method MUST be implemented by concrete agent classes that
        wish to participate in A2A communication.
        
        Args:
            message: The AgentMessage object received.
        """
        # Example basic logging - implementation is up to the subclass
        self.logger.info(f"Received message {message.message_id} from {message.sender_id} with intent '{message.intent}'. Implement custom handling.")
        pass
    # --------------------------------

    # Optional: Add common helper methods here if needed
    # e.g., accessing memory, adding tasks back to the orchestrator
    def _get_memory_weave(self):
        if self.orchestrator and hasattr(self.orchestrator, 'get_memory_weave'):
            return self.orchestrator.get_memory_weave()
        self.logger.warning("Orchestrator reference not available to access MemoryWeave.")
        return None

    async def _add_task_to_orchestrator(self, task_data: dict):
        if self.orchestrator and hasattr(self.orchestrator, 'add_task'):
            await self.orchestrator.add_task(task_data)
        else:
            self.logger.warning("Orchestrator reference not available to add task.")

    def _generate_memory_event(self, decision: str, reason: str, payload: Optional[dict] = None, parent_token: Optional[str] = None) -> dict:
        """Helper to create a standard memory event dictionary."""
        import uuid # Local import okay for helper
        token = f"EVNT::{decision.upper()}::{self.node_id}::{uuid.uuid4().hex[:4]}"
        event = {
            "archetype_token": token,
            "drift_vector": self.settings.get('drift_factor', 0.01), # Example drift
            "decision": decision,
            "reason": reason,
            "payload": payload or {},
            "source_agent": self.node_id
        }
        if parent_token:
            event["parent_archetype_token"] = parent_token
            
        # Register the archetype immediately (optional, could be done by orchestrator)
        # weave = self._get_memory_weave()
        # if weave:
        #     weave.register_archetype(token, event)
            
        return event 

    # ADDED _initialize_default_state method
    def _initialize_default_state(self):
         """Sets up a basic default state if none is provided."""
         default_state_data = {
             'id': self.node_id, # Use generated ID
             'name': self._name,
             'position': [random.uniform(-10, 10) for _ in range(3)], # Random 3D position
             'velocity': [0.0, 0.0, 0.0],
             'current_role': "PILGRIM",
             'personal_best_position': None, # Will be set to initial position
             'personal_best_value': float('-inf'),
             'energy_level': 1.0,
             'swarm_params': { # Default swarm parameters
                 'inertia_weight': DEFAULT_INERTIA_WEIGHT,
                 'cognitive_weight': DEFAULT_COGNITIVE_WEIGHT,
                 'social_weight': DEFAULT_SOCIAL_WEIGHT,
                 'stigmergic_weight': DEFAULT_STIGMERGIC_WEIGHT,
                 'max_speed': DEFAULT_MAX_SPEED
             },
             'last_updated_timestamp': time.time()
             # Add other NodeStateModel fields with defaults if needed
         }
         # Set pBest to initial position
         default_state_data['personal_best_position'] = default_state_data['position'][:]

         if isinstance(self.state, NodeStateModel):
             try:
                 # Ensure all required fields for NodeStateModel are present or have defaults
                 # Add any missing fields with default values if necessary
                 # Example: Add trinity_core if required and not present
                 if 'trinity_core' not in default_state_data:
                      default_state_data['trinity_core'] = { # Add default TrinityCoreState structure
                          "memory_state": {"last_relic_id": None, "compression_ratio": 0.0},
                          "will_state": {"current_focus": None, "goal_alignment": 0.0},
                          "imagination_state": {"novelty_level": 0.0}
                      }
                 if 'meta_balancer' not in default_state_data:
                      default_state_data['meta_balancer'] = { # Add default NodeMetaBalancer structure
                           "current_mode": "EXPLORE",
                           "mode_stability": 0.5,
                           "self_assessment_score": 0.5
                      }

                 self.state = NodeStateModel(**default_state_data)
             except Exception as e:
                  self.logger.error(f"Pilgrim '{self._name}': Unexpected error initializing default Pydantic state: {e}. Falling back to dict.", exc_info=True)
                  self.state = default_state_data # Fallback to dict
         else:
             self.state = default_state_data
         self.logger.info(f"Pilgrim '{self._name}': Initialized with default state at position {self.state.get('position') if isinstance(self.state, dict) else getattr(self.state, 'position', 'Unknown')}")

    # ADDED current_state property
    @property
    def current_state(self) -> Dict[str, Any]:
         """Returns the current state as a dictionary, handling both Pydantic models and dicts."""
         if isinstance(self.state, dict):
             # If it's already a dict, return a copy directly
             return self.state.copy()
         # Check if it's a Pydantic BaseModel (safer check)
         # Import locally to avoid circular dependencies if needed, or ensure available
         try:
             from pydantic import BaseModel
             is_pydantic = isinstance(self.state, BaseModel)
         except ImportError:
             is_pydantic = False # Assume not Pydantic if import fails

         if is_pydantic:
         # elif isinstance(self.state, NodeStateModel): # Original check might be too specific
             try:
                 # Use Pydantic's method to convert to dict, handling potential serialization issues
                 # Use model_dump for Pydantic v2+
                 if hasattr(self.state, 'model_dump'):
                     return self.state.model_dump(mode='json')
                 elif hasattr(self.state, 'dict'): # Check for Pydantic v1 explicitly
                      return self.state.dict() # for older pydantic v1
                 else:
                     # Fallback if neither method exists (shouldn't happen for valid Pydantic)
                     self.logger.warning(f"Agent {self._name}: Pydantic state object lacks .dict() or .model_dump(). Returning raw object attributes.")
                     # Attempt to manually create a dict as a last resort
                     return {k: getattr(self.state, k) for k in dir(self.state) if not k.startswith('_') and not callable(getattr(self.state, k))}
             except Exception as e:
                 self.logger.error(f"Error converting Pydantic state to dict for agent {self._name}: {e}", exc_info=True)
                 # Fallback or simplified representation
                 return {"id": getattr(self.state, 'id', self.node_id), "name": self._name, "error": "State serialization failed"}
         else:
             # This case should ideally not happen if __init__ is correct
             self.logger.error(f"Agent {self._name} has unexpected state type: {type(self.state)}. Attempting to initialize default state.")
             self._initialize_default_state() # Attempt recovery
             # Check again after recovery attempt
             if isinstance(self.state, dict):
                 return self.state.copy()
             else:
                  # If recovery failed or resulted in non-dict state, log error
                  self.logger.error(f"Agent {self._name}: State is still not a dictionary after recovery attempt. Type: {type(self.state)}")
                  return {"error": f"Invalid state type after recovery attempt: {type(self.state)}"}

    # --- Property Getter for name --- 
    @property
    def name(self) -> str:
        """Returns the agent's name."""
        # Ensure _name exists before returning
        if hasattr(self, '_name'):
            return self._name
        else:
            # Fallback or raise error if _name wasn't set (shouldn't happen with __init__ change)
            self.logger.error("Agent name (_name) accessed before initialization!")
            return "UnnamedAgent" 
    # -------------------------------- 