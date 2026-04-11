from typing import List, Optional, Any, Dict, Literal
from enum import Enum
from pydantic import BaseModel, Field, AliasChoices

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
    account_id: Optional[str] = Field(None, alias="AccountId", validation_alias=AliasChoices("AccountId", "ClientAccountID"))
    date_time: Optional[str] = Field(None, alias="DateTime")
    quantity: Optional[float] = Field(0.0, alias="Quantity")
    
    # Option Greeks
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    
    # New Extended Fields
    asset_class: Optional[str] = Field(None, alias="AssetClass")
    put_call: Optional[str] = Field(None, alias="Put/Call")
    net_cash: Optional[float] = Field(None, alias="NetCash")
    close_price: Optional[float] = Field(None, alias="ClosePrice")
    exchange: Optional[str] = None
    underlying_symbol: Optional[str] = None
    source: Optional[str] = None
    buy_sell: Optional[str] = None
    normalized_buy_sell: Optional[str] = None
    action: Optional[str] = None
    raw_action: Optional[str] = None
    outcome_action: Optional[str] = None
    source_stage: Optional[str] = None
    record_status: Optional[str] = None

    # Allow extra fields for ODS pattern (Store Everything)
    # Allow population by internal name (snake_case) or alias (CamelCase)
    model_config = {"extra": "allow", "populate_by_name": True}

class AnalyzedTrade(TradeRecord):
    """
    Extends TradeRecord with calculated P&L data.
    """
    realized_pl: Optional[float] = 0.0
    cost_basis: Optional[float] = 0.0
    # For grouping/display
    asset_class: Optional[str] = "STK" 

class TradeMetrics(BaseModel):
    """
    Summary statistics for a set of trades.
    """
    total_pl: float = 0.0
    unrealized_profit: float = 0.0
    unrealized_loss: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    open_trades: int = 0
    closed_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    account_metrics: Dict[str, Any] = {}

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
    query_id_orders: Optional[str] = None
    query_id_nav: Optional[str] = None # For Generic/History if needed
    query_id_nav_1d: Optional[str] = None
    query_id_nav_7d: Optional[str] = None
    query_id_nav_30d: Optional[str] = None
    query_id_nav_mtd: Optional[str] = None
    query_id_nav_ytd: Optional[str] = None
    query_id_nav_1y: Optional[str] = None
    query_id_dividends: Optional[str] = None


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
    query_id_orders: Optional[str] = None
    query_id_nav: Optional[str] = None 
    query_id_nav_1d: Optional[str] = None
    query_id_nav_7d: Optional[str] = None
    query_id_nav_30d: Optional[str] = None
    query_id_nav_mtd: Optional[str] = None
    query_id_nav_ytd: Optional[str] = None
    query_id_nav_1y: Optional[str] = None
    query_id_dividends: Optional[str] = None
    last_sync: Optional[dict] = None


class FrontendLogPayload(BaseModel):
    level: Literal["debug", "info", "warning", "error"] = "error"
    source: str = "frontend"
    boundary: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=2000)
    stack: Optional[str] = Field(None, max_length=12000)
    componentStack: Optional[str] = Field(None, max_length=12000)
    timestamp: Optional[str] = None
    path: Optional[str] = Field(None, max_length=1024)
    userAgent: Optional[str] = Field(None, max_length=1024)
