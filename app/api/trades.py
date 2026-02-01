from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.models import TradeRecord, AnalyzedTrade, TradeMetrics, User
from app.auth.dependencies import get_current_active_user
from app.config import settings
from pymongo import MongoClient
from app.services.trade_analysis import calculate_pnl, calculate_metrics

router = APIRouter()

# TODO: Refactor DB connection to a dependency injection pattern
def get_db():
    client = MongoClient(settings.MONGO_URI)
    return client.get_default_database("stock_analysis")

@router.get("/", response_model=List[TradeRecord])
async def get_trades(
    skip: int = 0,
    limit: int = 100,
    symbol: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get raw trade history with pagination and optional symbol filtering.
    """
    db = get_db()
    query = {}
    if symbol:
        query["symbol"] = symbol
        
    cursor = db.ibkr_trades.find(query).sort("date_time", -1).skip(skip).limit(limit)
    return [TradeRecord(**doc) for doc in cursor]

@router.get("/analysis", response_model=dict)
async def get_trade_analysis(
    symbol: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get analyzed trades (P&L) and summary metrics.
    Returns: { "trades": List[AnalyzedTrade], "metrics": TradeMetrics }
    """
    db = get_db()
    query = {}
    if symbol:
        query["symbol"] = symbol
        
    # Fetch ALL trades for analysis (metrics need full history ideally, or at least full history for the symbol)
    # TODO: Date range filtering
    cursor = db.ibkr_trades.find(query).sort("date_time", 1) # Metrics need FIFO, so sort Ascending
    
    raw_trades = [TradeRecord(**doc) for doc in cursor]
    
    analyzed_trades = calculate_pnl(raw_trades)
    metrics = calculate_metrics(analyzed_trades)
    
    return {
        "trades": analyzed_trades,
        "metrics": metrics
    }
