from typing import List, Optional, Any
from pydantic import BaseModel, Field

class StockRecord(BaseModel):
    """
    Represents a single stock row. 
    Uses alias to map from the existing Dictionary keys (with spaces) to Python attributes.
    """
    Ticker: str
    Current_Price: Optional[float] = Field(None, alias="Current Price")
    One_Day_Change: Optional[str] = Field(None, alias="1D % Change")
    YoY_Price: Optional[str] = Field(None, alias="YoY Price %")
    
    # Indicators
    MA_200: Optional[float] = None
    RSI: Optional[float] = None
    EMA_20: Optional[float] = None
    HMA_20: Optional[float] = None
    TSMOM_60: Optional[float] = None
    
    # Option Data
    Implied_Volatility: Optional[float] = None
    Call_Put_Skew: Optional[float] = Field(None, alias="Call/Put Skew")
    
    Last_Update: Optional[str] = Field(None, alias="Last Update")
    
    # Allow extra fields since the logic produces many dynamic keys
    model_config = {"extra": "allow"}

class StockResponse(BaseModel):
    count: int
    data: List[StockRecord]

class User(BaseModel):
    username: str
    disabled: Optional[bool] = None

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class RefreshStatus(BaseModel):
    status: str
    message: Optional[str] = None
