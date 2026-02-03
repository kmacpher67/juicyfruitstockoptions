from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class OpportunityStatus(str, Enum):
    DETECTED = "DETECTED"
    TRACKING = "TRACKING"
    CLOSED = "CLOSED"
    DISCARDED = "DISCARDED"

class JuicyOpportunity(BaseModel):
    symbol: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    trigger_source: str
    status: OpportunityStatus = OpportunityStatus.DETECTED
    context: Dict[str, Any]
    proposal: Dict[str, Any]
    outcome: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True
