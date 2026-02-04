from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional

class NewsArticle(BaseModel):
    ticker: str
    title: str
    url: str
    published_at: datetime
    source: str
    source_weight: float = Field(default=0.5, description="Credibility weight 0.0-1.0")
    
    # Analysis fields
    sentiment_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    logic: str = Field(default="", description="The logic rule applied")
    impact_window: str = Field(default="Medium-term", description="Short-term, Medium-term, Long-term")
    reasoning: str = Field(default="", description="Natural language reasoning")
    opportunity_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Derived opportunity score")

class MacroIndicator(BaseModel):
    series_id: str
    title: str
    value: float
    date: datetime
    unit: str

class CorporateEvent(BaseModel):
    ticker: str
    event_type: str  # Earnings, Ex-Dividend, Split
    date: datetime
    details: str = Field(default="", description="Details like Estimated Earnings, Rate, etc.")
    created_at: datetime = Field(default_factory=datetime.utcnow)
