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


def fix_oid(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

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
    return [TradeRecord(**fix_oid(doc)) for doc in cursor]

@router.get("/analysis", response_model=dict)
async def get_trade_analysis(
    symbol: Optional[str] = None,
    start_date: Optional[str] = None, # YYYY-MM-DD
    end_date: Optional[str] = None,   # YYYY-MM-DD
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
        
    # Date Filtering
    # The field in DB is "date_time" (e.g., "20240101") or ISO? 
    # Let's check the model or assume standard string comparison works for YYYYMMDD if we covert input
    # IBKR dates are usually YYYYMMDD or YYYY-MM-DD? Standardize on YYYYMMDD for query if needed.
    # Looking at test_api_trades.py, DateTime is "20240101" (YYYYMMDD).
    
    # Fetch ALL trades for analysis (metrics need full history ideally to match open/close via FIFO)
    cursor = db.ibkr_trades.find(query).sort("date_time", 1) # Metrics need FIFO, so sort Ascending
    
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logging.info(f"Starting trade analysis for symbol={symbol}...")
        raw_trades = [TradeRecord(**fix_oid(doc)) for doc in cursor]
        
        analyzed_trades = calculate_pnl(raw_trades)

        # Apply date filters post-calculation so FIFO P&L is correct
        if start_date or end_date:
            s_val = start_date.replace("-", "") if start_date else None
            e_val = end_date.replace("-", "") if end_date else None
            
            filtered_trades = []
            for t in analyzed_trades:
                # Use date_time (or empty string) truncated to first 8 chars (YYYYMMDD)
                t_date = str(t.date_time)[:8] if t.date_time else ""
                
                # We include trades that are on or after start_date
                if s_val and t_date < s_val:
                    continue
                # We include trades that are on or before end_date
                if e_val and t_date > e_val:
                    continue
                    
                filtered_trades.append(t)
            analyzed_trades = filtered_trades

        metrics = calculate_metrics(analyzed_trades)
        
        logging.info(f"Analysis complete. Trades={len(analyzed_trades)}, Metrics={metrics}")
        return {
            "trades": analyzed_trades,
            "metrics": metrics
        }
    except Exception as e:
        import traceback
        error_msg = f"Analysis Failed: {str(e)}"
        logger.error(f"Critical error in trade analysis: {error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)
