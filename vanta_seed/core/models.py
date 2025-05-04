from pydantic import BaseModel, Field, Extra
from typing import List, Dict, Any, Optional

class TrinityState(BaseModel):
    cognitive_load: float = Field(default=0.5, ge=0.0, le=1.0)
    emotional_state: float = Field(default=0.5, ge=0.0, le=1.0)
    operational_focus: float = Field(default=0.5, ge=0.0, le=1.0)
    memory_state: Dict[str, Any] = Field(default_factory=dict)
    will_state: Dict[str, Any] = Field(default_factory=dict)
    imagination_state: Dict[str, Any] = Field(default_factory=dict)

class SymbolicIdentity(BaseModel):
    archetype: str = "default_archetype"
    mythos_role: str = "default_role"
    narrative_version: str = "1.0"
    # Add other symbolic fields as needed

class AgentSettings(BaseModel):
    """Flexible settings model."""
    # Allow any field, useful for agent-specific settings
    # Replaced extra='allow' with dynamic fields via __root__ or leave as is if validation isn't strict
    # For simplicity, let's assume settings are accessed via .dict() later and allow arbitrary keys initially
    # If stricter validation is needed, define known fields or use Extra.allow
    class Config:
        extra = Extra.allow # Allows arbitrary fields
    max_retries: int = 3
    base_retry_delay_seconds: float = 1.0
    misfire_grace_time_seconds: Optional[int] = 60 # For scheduler
    compatible_model_names: Optional[List[str]] = None

class AgentConfig(BaseModel):
    """Configuration for a single agent loaded from the blueprint."""
    name: str
    class_path: str
    enabled: bool = True
    settings: AgentSettings = Field(default_factory=AgentSettings)
    symbolic_identity: SymbolicIdentity = Field(default_factory=SymbolicIdentity)
    initial_trinity_state: TrinityState = Field(default_factory=TrinityState)
    compatible_model_names: Optional[List[str]] = None
    # Add other common agent config fields if needed

class TaskData(BaseModel):
    task_id: str
    intent: str
    origin_agent: str = "unknown"
    target_agent: Optional[str] = None # If directly targeting an agent
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # For OpenAI compatibility
    requested_model: Optional[str] = None # e.g., "echo-model"
    messages: Optional[List[Dict[str, str]]] = None # e.g., [{"role": "user", "content": "Hello"}]

class PilgrimState(BaseModel):
    name: str
    config: AgentConfig
    instance: Any # Holds the actual agent instance
    trinity_state: TrinityState
    purpose_pulse: Any # Placeholder for PurposePulse object/state
    mythic_role: Any # Placeholder for MythicRole object/state
    status: str = "idle" # e.g., idle, processing, error
    last_heartbeat: Optional[float] = None

# Example of extending for a specific agent
class SchedulerAgentSettings(AgentSettings):
    job_interval_seconds: int = 60

class SchedulerAgentConfig(AgentConfig):
    settings: SchedulerAgentSettings = Field(default_factory=SchedulerAgentSettings)

# Model for the overall blueprint structure
class BlueprintConfig(BaseModel):
    agents: List[AgentConfig]
    version: Optional[str] = None
    description: Optional[str] = None
    # --- Add optional top-level config sections --- 
    swarm_config: Optional[Dict[str, Any]] = None
    vanta_crown_interface: Optional[Dict[str, Any]] = None
    storage: Optional[Dict[str, Any]] = None
    governance: Optional[Dict[str, Any]] = None
    procedural: Optional[Dict[str, Any]] = None
    rituals: Optional[List[Dict[str, Any]]] = None # CHANGED: Expect List of Dicts
    automutator: Optional[Dict[str, Any]] = None
    autonomous_tasker: Optional[Dict[str, Any]] = None
    behavior_protocols: Optional[List[str]] = None # Added based on YAML
    dev_flags: Optional[Dict[str, bool]] = None # Added based on YAML
    moral_stance: Optional[str] = None # Added based on YAML
    router_strategy: Optional[Dict[str, str]] = None # Added based on YAML
    # ----------------------------------------------

# Model for Mutation Proposals used in KernelManager
class MutationProposal(BaseModel):
    id: str
    source_agent: str
    mutation_type: str  # e.g., "config_update", "myth_addition", "myth_update"
    proposed_changes: Dict[str, Any] | List[Any] | str # Flexible type for changes
    target_element_id: Optional[str] = None # e.g., myth ID for myth_update
    rationale: str
    status: str = "staged" # e.g., staged, active, rejected
    timestamp: float 