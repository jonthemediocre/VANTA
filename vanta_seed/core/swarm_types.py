from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo
from typing import List, Dict, Tuple, Optional, Literal, Union, Any
import time
import uuid

# --- Base Types ---
NodeID = str
RelicID = str
VectorID = str
GoalID = str
SymbolicTarget = str
EmotionalTone = str
Timestamp = float
Position = List[float] # Assuming 3D for now based on YAML
Velocity = List[float] # Assuming 3D for now based on YAML

# --- Node Internal Trinity Core ---

class TrinityMemory(BaseModel):
    trail_history_buffer_size: int = Field(50, description="Max size of recent trail history")
    stimuli_log_size: int = Field(20, description="Max size of recent stimuli log")
    compression_score: float = Field(0.5, description="Current density/meaningfulness of memory")
    memory_relic_refs: List[RelicID] = Field(default_factory=list, description="Links to immutable core Memory Relics")
    # Future: Add actual trail history and stimuli log lists here

class TrinityWill(BaseModel):
    desire_vectors: List[Dict[GoalID, Any]] = Field(default_factory=list, description="List of goals the node seeks")
    # Example desire_vector structure: {'goal_id': 'reach_light', 'target_value': 1.0, 'current_progress': 0.2}
    risk_tolerance: float = Field(0.5, ge=0.0, le=1.0, description="Node's tolerance for uncertainty (0=cautious, 1=reckless)")
    destiny_pull_weight: float = Field(0.5, ge=0.0, le=1.0, description="Alignment strength to VANTA Purpose Vector")

class TrinityImagination(BaseModel):
    hypothesis_buffer_size: int = Field(10, description="Max concurrent explorations/hypotheses")
    divergence_pressure: float = Field(0.5, ge=0.0, le=1.0, description="Tendency towards radical exploration (0=conformist, 1=radical)")
    symbolic_expansion_potential: float = Field(0.5, ge=0.0, description="Ability to create new symbolic meanings")
    # Future: Add actual hypothesis buffer list

class TrinityCoreState(BaseModel):
    memory: TrinityMemory = Field(default_factory=TrinityMemory)
    will: TrinityWill = Field(default_factory=TrinityWill)
    imagination: TrinityImagination = Field(default_factory=TrinityImagination)

# --- Node Meta-Balancer ---

NodeMode = Literal["Explore", "Exploit", "Recall"]

class NodeMetaBalancer(BaseModel):
    current_mode: NodeMode = Field("Exploit", description="Current dominant mode based on internal Trinity balance")
    mode_stability: float = Field(0.8, ge=0.0, le=1.0, description="How entrenched the current mode is")
    self_assessment_score: float = Field(0.75, description="Node's own sense of internal balance/coherence") # Example value

# --- Node Swarm Interaction Parameters ---

NodeRole = Literal["Scout", "Employed", "Onlooker"]

class NodeSwarmParams(BaseModel):
    # PSO Related
    inertia_weight: float = Field(0.7, alias="w")
    personal_best_coeff: float = Field(1.5, alias="c1")
    global_best_coeff: float = Field(1.5, alias="c2")
    personal_trinity_best_pos: Optional[Position] = Field(None, description="Position where node achieved its own best internal balance")

    # ACO Related
    stigmergic_coeff: float = Field(1.0, alias="c3")
    pheromone_deposition_rate: float = Field(0.1, ge=0.0) # Example value
    symbolic_resonance_sensitivity: float = Field(0.5, alias="gamma") # Weighting for symbolic trails

    # ABC Related
    current_role: NodeRole = Field("Employed", description="Dynamically assigned role")
    role_switch_threshold: float = Field(0.6, description="Sensitivity/threshold for changing roles") # Example value
    exploration_coeff: float = Field(0.1, alias="gamma_E", description="Exploration factor, potentially linked to Imagination Divergence") # Example value

# --- Node Trail Signature ---

class TrailSignature(BaseModel):
    timestamp: Timestamp = Field(default_factory=time.time)
    emitting_node_id: NodeID
    position_at_emission: Position
    symbolic_markers: List[SymbolicTarget] = Field(default_factory=list, description="Compressed meaning payload")
    symbolic_resonance_score: float = Field(0.0, description="Strength of alignment/meaning of this trail")
    emotional_tone_imprint: Optional[EmotionalTone] = Field(None, description="e.g., 'ReverentAche'")
    fitness_signal: Optional[float] = Field(None, description="Local environmental quality assessment at time of emission")

# --- Full Micro-Trinity Node State ---

class NodeStateModel(BaseModel):
    id: NodeID = Field(default_factory=lambda: f"node_{uuid.uuid4()}")
    type: Literal["TrinityPilgrim"] = "TrinityPilgrim"
    created_at: Timestamp = Field(default_factory=time.time)
    last_updated: Timestamp = Field(default_factory=time.time)
    position: Position = Field(default=[0.0, 0.0, 0.0])
    velocity: Velocity = Field(default=[0.0, 0.0, 0.0])

    trinity_core: TrinityCoreState = Field(default_factory=TrinityCoreState)
    meta_balancer: NodeMetaBalancer = Field(default_factory=NodeMetaBalancer)
    swarm_params: NodeSwarmParams = Field(default_factory=NodeSwarmParams)
    last_trail_signature: Optional[TrailSignature] = None # Stores the last signature emitted

    # Updated validator for Pydantic V2 using @field_validator
    @field_validator('position', 'velocity', mode='before') # mode='before' is similar to pre=True
    def check_vector_length(cls, v, info: ValidationInfo):
        # Example validator: Ensure position/velocity are 3D vectors
        # Adjust dimensionality based on swarm_config if needed
        if not isinstance(v, list) or len(v) != 3:
            # Use info.field_name to get the field name in V2
            raise ValueError(f"{info.field_name} must be a list of 3 floats")
        return v

# --- Stigmergic Field Point ---

class StigmergicFieldPoint(BaseModel):
    coordinates: Position # Key identifying the point in space
    pheromone_level: float = 0.0
    recent_trail_signatures: List[TrailSignature] = Field(default_factory=list, max_items=50) # Keep recent trails

# --- VANTA Crown Interface Related ---

class PurposeVectorModel(BaseModel):
    vector_id: VectorID = Field(default_factory=lambda: f"pulse_{uuid.uuid4()}")
    timestamp: Timestamp = Field(default_factory=time.time)
    symbolic_target: List[SymbolicTarget] = Field(default_factory=list)
    intensity: float = Field(0.7, ge=0.0, le=1.0) # Example default intensity

class GlobalBestNodeInfo(BaseModel):
    node_id: NodeID
    position: Position
    resonance_score: float
    timestamp: Timestamp

class SwarmHealthMetricsModel(BaseModel):
    status: str = "initializing"
    timestamp: Timestamp = Field(default_factory=time.time)
    active_pilgrims: int = 0
    avg_trinity_deviation: Optional[float] = None # How far nodes are from ideal balance
    role_distribution: Dict[NodeRole, float] = Field(default_factory=dict) # e.g., {"Scout": 0.1, ...}
    overall_symbolic_vitality: Optional[float] = None # Aggregate resonance/meaningfulness

# --- Placeholder for Crown configuration/state ---
# class VantaCrownState(BaseModel):
#     current_purpose_vector: PurposeVectorModel
#     swarm_health_metrics: SwarmHealthMetricsModel
#     global_trinity_best_node: Optional[GlobalBestNodeInfo] = None
#     blessing_threshold: float = 0.85 # Example threshold 