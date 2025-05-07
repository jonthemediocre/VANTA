from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

from .base_schemas import BaseMemoryRecord

class MythicObject(BaseMemoryRecord):
    mythic_object_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the MythicObject.")
    source_ids: List[uuid.UUID] = Field(..., description="List of UUIDs from KnowledgeData or OperationalData that were collapsed into this object.")
    type: str = Field(..., description="Type of the MythicObject (e.g., 'event_pattern', 'causal_chain', 'symbolic_echo').")
    collapsed_content: Dict[str, Any] = Field(..., description="The compressed, symbolic representation of the collapsed data.")
    tags: Optional[List[str]] = Field(default_factory=list)
    revision: int = Field(default=1, description="Revision number of this mythic object.")

class MythicLink(BaseMemoryRecord):
    mythic_link_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the MythicLink.")
    source_object_id: uuid.UUID = Field(..., description="UUID of the source MythicObject.")
    target_object_id: uuid.UUID = Field(..., description="UUID of the target MythicObject.")
    link_type: str = Field(..., description="Type of link (e.g., 'precedes', 'causes', 'implies', 'associates_with', 'symbolizes').")
    strength: Optional[float] = Field(default=1.0, description="Strength or confidence of the link (0.0 to 1.0).")
    tags: Optional[List[str]] = Field(default_factory=list)

# Example Usage (Illustrative)
if __name__ == "__main__":
    obj1_id = uuid.uuid4()
    obj2_id = uuid.uuid4()

    obj1 = MythicObject(
        mythic_object_id=obj1_id,
        source="example_script",
        source_ids=[uuid.uuid4(), uuid.uuid4()],
        type="event_pattern",
        collapsed_content={"pattern_name": "UserLoginSpike", "details": "Repeated login spikes after feature deployment X"},
        tags=["login", "spike", "feature_X"]
    )
    print(f"MythicObject 1: {obj1.model_dump_json(indent=2)}")

    obj2 = MythicObject(
        mythic_object_id=obj2_id,
        source="example_script",
        source_ids=[uuid.uuid4()],
        type="causal_chain_node",
        collapsed_content={"event": "HighLatencyAlert", "cause_hypothesis": "Increased DB load from UserLoginSpike"},
        tags=["latency", "alert", "database"]
    )
    print(f"\nMythicObject 2: {obj2.model_dump_json(indent=2)}")

    link1 = MythicLink(
        source="example_script",
        source_object_id=obj1.mythic_object_id,
        target_object_id=obj2.mythic_object_id,
        link_type="potentially_causes",
        strength=0.75,
        tags=["performance_impact"]
    )
    print(f"\nMythicLink 1: {link1.model_dump_json(indent=2)}") 