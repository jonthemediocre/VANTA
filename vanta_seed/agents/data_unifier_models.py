from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class RawRecordInput(BaseModel):
    """Schema for inputting raw data records."""
    data: Dict[str, Any] = Field(..., description="The raw data record as a dictionary.")
    source: Optional[str] = Field(None, description="Identifier for the source system or dataset.")
    record_id: Optional[str] = Field(None, description="Original ID of the record in the source system.")

class UnifiedEntityOutput(BaseModel):
    """Schema for returning a unified entity."""
    entity_id: str = Field(..., description="The unique identifier assigned to the unified entity.")
    unified_data: Dict[str, Any] = Field(..., description="The merged and cleaned data for the entity.")
    sources: List[str] = Field(default_factory=list, description="List of source identifiers contributing to this entity.")
    confidence: Optional[float] = Field(None, description="Confidence score of the unification/match.")
    last_updated: Optional[str] = Field(None, description="Timestamp of the last update.") 