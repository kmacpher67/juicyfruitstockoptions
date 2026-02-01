from typing import List, Optional, Any
from enum import Enum
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

class TradeRecord(BaseModel):
    """
    Represents a single trade row.
    """
    trade_id: str = Field(..., alias="TradeID") # Required, used as PK
    symbol: str = Field(..., alias="Symbol")
    date_time: Optional[str] = Field(None, alias="DateTime")
    quantity: Optional[float] = Field(0.0, alias="Quantity")
    
    # Allow extra fields for ODS pattern (Store Everything)
    model_config = {"extra": "allow"}

class StockResponse(BaseModel):
    count: int
    data: List[StockRecord]

class User(BaseModel):
    username: str
    disabled: Optional[bool] = None
    role: str = "basic"  # valid: basic, analyst, portfolio, admin

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

class IBKRConfig(BaseModel):
    flex_token: Optional[str] = None
    query_id_holdings: Optional[str] = None
    query_id_trades: Optional[str] = None
    query_id_nav: Optional[str] = None # For Generic/History if needed
    query_id_nav_1d: Optional[str] = None
    query_id_nav_7d: Optional[str] = None
    query_id_nav_30d: Optional[str] = None
    query_id_nav_mtd: Optional[str] = None
    query_id_nav_ytd: Optional[str] = None
    query_id_nav_1y: Optional[str] = None


class NavReportType(str, Enum):
    NAV_1D = "NAV1D"
    NAV_7D = "Nav7D" # Case sensitive matching user request? Or internal enum? Let's use internal enum keys.
    NAV_30D = "Nav30D"
    NAV_MTD = "NAVMTD"
    NAV_YTD = "NAVYTD"
    NAV_1Y = "NAV1Y"
class IBKRStatus(BaseModel):
    configured: bool
    flex_token_masked: Optional[str] = None
    query_id_holdings: Optional[str] = None
    query_id_trades: Optional[str] = None
    query_id_nav: Optional[str] = None 
    query_id_nav_1d: Optional[str] = None
    query_id_nav_7d: Optional[str] = None
    query_id_nav_30d: Optional[str] = None
    query_id_nav_mtd: Optional[str] = None
    query_id_nav_ytd: Optional[str] = None
    query_id_nav_1y: Optional[str] = None
    last_sync: Optional[dict] = None
