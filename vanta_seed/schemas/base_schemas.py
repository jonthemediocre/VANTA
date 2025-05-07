from pydantic import BaseModel, Field
from datetime import datetime, timezone
import uuid

class BaseMemoryRecord(BaseModel):
    """
    Base model for all memory records, including required agentic session metadata.
    """
    session_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="Unique identifier for the session in which this record was created.")
    source: str = Field(description="Identifier for the source of the data (e.g., 'user_id:123', 'app:InnerCircle', 'event_id:xyz').")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of when the record was created, in UTC.")
    agentic_opt_in: bool = Field(default=True, description="Indicates if the user/session has opted into agentic processing for this data.")
    do_not_narrativize: bool = Field(default=False, description="Flag to indicate if this specific record should NOT be used for narrative generation/compression.")

    model_config = {
        "extra": "allow",
        "validate_assignment": True, # Useful for ensuring type correctness on attribute assignment
        "populate_by_name": True, # Allows using alias names for population
    } 