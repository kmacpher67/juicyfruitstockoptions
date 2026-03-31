from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.models import TradeRecord, AnalyzedTrade, TradeMetrics, User
from app.auth.dependencies import get_current_active_user
from app.config import settings
from pymongo import MongoClient
from app.services.trade_analysis import calculate_pnl, calculate_metrics
from app.services.ibkr_tws_service import get_ibkr_tws_service

router = APIRouter()

# TODO: Refactor DB connection to a dependency injection pattern
def get_db():
    client = MongoClient(settings.MONGO_URI)
    return client.get_default_database("stock_analysis")


def fix_oid(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("/live-status", response_model=dict)
async def get_trade_live_status(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get TWS live execution status for Trade History RT mode.
    """
    db = get_db()
    tws_service = get_ibkr_tws_service()
    live_status = tws_service.get_live_status()

    today_prefix = datetime.now().strftime("%Y%m%d")
    today_live_trade_count = db.ibkr_trades.count_documents({
        "source": "tws_live",
        "date_time": {"$regex": f"^{today_prefix}"},
    })
    latest_live_trade = db.ibkr_trades.find_one(
        {
            "source": "tws_live",
            "date_time": {"$regex": f"^{today_prefix}"},
        },
        sort=[("date_time", -1), ("last_tws_update", -1)],
    )

    return {
        **live_status,
        "today_live_trade_count": today_live_trade_count,
        "latest_live_trade_at": (
            latest_live_trade.get("last_tws_update")
            or latest_live_trade.get("date_time")
            if latest_live_trade
            else None
        ),
    }

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
        
    # Fetch Trades
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Querying ibkr_trades with query={query}, skip={skip}, limit={limit}")

    trade_cursor = db.ibkr_trades.find(query).sort("date_time", -1).skip(skip).limit(limit)
    raw_trades = [TradeRecord(**fix_oid(doc)) for doc in trade_cursor]
    
    logger.debug(f"Found {len(raw_trades)} trades in ibkr_trades")
    
    # Fetch Dividends (Realized only)
    # We use limit as a rough cap, sorting later might misalign pagination slightly if heavy mixing, 
    # but sufficient for combined view.
    div_query = {"code": "RE"}
    if symbol: div_query["symbol"] = symbol
    div_cursor = db.ibkr_dividends.find(div_query).limit(limit)
    
    for doc in div_cursor:
        # Convert YYYY-MM-DD to YYYYMMDD string for sorting/display compatibility if needed,
        # or just use the string directly if UI handles it.
        dt = (doc.get("pay_date") or "").replace("-", "")
        raw_trades.append(TradeRecord(
            trade_id=f"div_{doc.get('_id')}",
            symbol=doc.get("symbol"),
            account_id=doc.get("account_id"),
            date_time=dt,
            quantity=0,
            price=0,
            buy_sell="DIVIDEND",
            realized_pnl=doc.get("net_amount", 0) # Store straight as extra field or map depending on UI needs
        ))
        
    # Sort combined results descending
    raw_trades.sort(key=lambda x: str(x.date_time) if x.date_time else "", reverse=True)
    return raw_trades[:limit]

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
    import logging
    logger = logging.getLogger(__name__)
    logger.debug(f"Querying ibkr_trades for analysis with query={query}")

    cursor = db.ibkr_trades.find(query).sort("date_time", 1) # Metrics need FIFO, so sort Ascending
    
    import logging
    logger = logging.getLogger(__name__)
    
    import time
    start_total = time.time()
    try:
        logging.info(f"Starting trade analysis for symbol={symbol}...")
        
        # Step 1: Fetch Trades
        t0 = time.time()
        raw_trades = [fix_oid(doc) for doc in cursor]
        t_fetch_trades = time.time() - t0
        logger.info(f"Retrieved {len(raw_trades)} raw trades in {t_fetch_trades:.4f}s")
        
        # Step 2: Fetch Dividends
        t0 = time.time()
        div_query = {"code": "RE"}
        if symbol: div_query["symbol"] = symbol
        div_cursor = db.ibkr_dividends.find(div_query)
        
        # Add Dividends as AnalyzedTrades basically, so they factor into PL
        div_count = 0
        for doc in div_cursor:
            div_count += 1
            dt = (doc.get("pay_date") or "").replace("-", "")
            raw_trades.append({
                "trade_id": f"div_{doc.get('_id')}",
                "symbol": doc.get("symbol"),
                "account_id": doc.get("account_id"),
                "date_time": dt,
                "quantity": 0,
                "price": 0,
                "buy_sell": "DIVIDEND",
                "realized_pnl": doc.get("net_amount", 0)
            })
            
        t_fetch_divs = time.time() - t0
        logger.info(f"Retrieved {div_count} dividends in {t_fetch_divs:.4f}s")
            
        # Step 3: Sort combined list
        t0 = time.time()
        # Re-sort combined list ascending for FIFO
        raw_trades.sort(key=lambda x: str(x.get("date_time", "")) if x.get("date_time") else "")
        t_sort = time.time() - t0
        logger.info(f"Sorted {len(raw_trades)} total items in {t_sort:.4f}s")
        
        # Step 4: Calculate PNL
        t0 = time.time()
        analyzed_trades, open_positions = calculate_pnl(raw_trades)
        t_pnl = time.time() - t0
        logger.info(f"Calculated PNL in {t_pnl:.4f}s")

        # Apply date filters post-calculation so FIFO P&L is correct
        if start_date or end_date:
            s_val = start_date.replace("-", "") if start_date else None
            e_val = end_date.replace("-", "") if end_date else None
            
            filtered_trades = []
            for t in analyzed_trades:
                # Use date_time (or empty string) truncated to first 8 chars (YYYYMMDD)
                # t is AnalyzedTrade here, so use getattr
                t_dt = getattr(t, "date_time", getattr(t, "DateTime", ""))
                t_date = str(t_dt)[:8] if t_dt else ""
                
                # We include trades that are on or after start_date
                if s_val and t_date < s_val:
                    continue
                # We include trades that are on or before end_date
                if e_val and t_date > e_val:
                    continue
                    
                filtered_trades.append(t)
            analyzed_trades = filtered_trades
            
            filtered_open_positions = {}
            for key, pos in open_positions.items():
                filtered_lots = []
                for lot in pos.get("lots", []):
                    lot_dt = str(lot.get("date_time", ""))[:8]
                    if s_val and lot_dt < s_val:
                        continue
                    if e_val and lot_dt > e_val:
                        continue
                    filtered_lots.append(lot)
                
                if filtered_lots:
                    tot_q = sum(l["qty"] for l in filtered_lots)
                    tot_c = sum(abs(l["qty"]) * l["price"] for l in filtered_lots)
                    if tot_q != 0:
                        filtered_open_positions[key] = {
                            "qty": tot_q,
                            "avg_cost": tot_c / abs(tot_q),
                            "lots": filtered_lots
                        }
            open_positions = filtered_open_positions
        
        # Step 5: Fetch current prices from holdings for unrealized PL
        t0 = time.time()
        # Get latest snapshot per symbol
        holdings_cursor = db.ibkr_holdings.find({}, {"symbol": 1, "market_price": 1})
        current_prices = {}
        for h in holdings_cursor:
            sym = h.get("symbol")
            price = h.get("market_price")
            if sym and price is not None:
                current_prices[sym] = float(price)
        t_price_fetch = time.time() - t0
        logger.info(f"Fetched {len(current_prices)} prices from holdings in {t_price_fetch:.4f}s")

        # Step 6: Calculate Metrics
        t0 = time.time()
        metrics = calculate_metrics(analyzed_trades, open_positions, current_prices=current_prices)
        t_metrics = time.time() - t0
        logger.info(f"Calculated metrics in {t_metrics:.4f}s")
        
        total_time = time.time() - start_total
        logging.info(f"Analysis complete in {total_time:.4f}s. Trades={len(analyzed_trades)}, Metrics={metrics}")
        return {
            "trades": analyzed_trades,
            "metrics": metrics
        }
    except Exception as e:
        import traceback
        error_msg = f"Analysis Failed: {str(e)}"
        logger.error(f"Critical error in trade analysis: {error_msg}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)
