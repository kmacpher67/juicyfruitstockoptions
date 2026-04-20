from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ThorpStatus(str, Enum):
    EDGE = "EDGE"
    CAUTION = "CAUTION"
    RISK = "RISK"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    PENDING_DATA = "PENDING_DATA"


class ThorpPoint(BaseModel):
    id: str
    label: str
    status: ThorpStatus
    key_metric: str
    detail: str


class ThorpDecision(BaseModel):
    rank: int
    action: str
    edge: str
    risk: str
    first_step: str


class ThorpAuditResponse(BaseModel):
    symbol: str
    as_of: datetime = Field(default_factory=datetime.utcnow)
    points: List[ThorpPoint]
    thorp_decision: List[ThorpDecision]
    data_completeness: float = Field(ge=0.0, le=1.0)
