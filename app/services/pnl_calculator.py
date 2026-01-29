from pymongo import MongoClient
from app.config import settings

def get_ticker_pnl(ticker: str):
    """
    Calculate Net Profit for a Base Ticker.
    Aggregates:
    1. Realized PnL from TRADES (Stock + Options matching underlying).
    2. Unrealized PnL from HOLDINGS (Current snapshot).
    3. Dividends (from TRADES? Or Cash Transactions? - Pending implementation).
    """
    client = MongoClient(settings.MONGO_URI)
    db = client.get_default_database("stock_analysis")
    
    # 1. Identify all related symbols (The stock itself + options)
    # Strategy: Match `underlying_symbol` == ticker
    
    # --- Realized PnL (from Trades) ---
    # Need to verify if 'realized_pnl' field exists in docs
    pipeline_trades = [
        {
            "$match": {
                "underlying_symbol": ticker
            }
        },
        {
            "$group": {
                "_id": "$underlying_symbol",
                "total_realized_pnl": {"$sum": "$realized_pnl"},
                "total_commission": {"$sum": "$commission"},
                "trade_count": {"$sum": 1}
            }
        }
    ]
    
    trades_result = list(db.ibkr_trades.aggregate(pipeline_trades))
    realized_pnl = trades_result[0]["total_realized_pnl"] if trades_result else 0.0
    commissions = trades_result[0]["total_commission"] if trades_result else 0.0
    
    # --- Unrealized PnL (from Latest Holdings) ---
    # Fetch latest snapshot date first
    latest_date_doc = db.ibkr_holdings.find_one(sort=[("date", -1)])
    unrealized_pnl = 0.0
    market_value = 0.0
    
    if latest_date_doc:
        report_date = latest_date_doc.get("report_date")
        pipeline_holdings = [
            {
                "$match": {
                    "report_date": report_date,
                    "underlying_symbol": ticker
                }
            },
            {
                "$group": {
                    "_id": "$underlying_symbol",
                    "total_unrealized_pnl": {"$sum": "$unrealized_pnl"},
                    "total_market_value": {"$sum": "$market_value"}
                }
            }
        ]
        holdings_result = list(db.ibkr_holdings.aggregate(pipeline_holdings))
        if holdings_result:
            unrealized_pnl = holdings_result[0]["total_unrealized_pnl"]
            market_value = holdings_result[0]["total_market_value"]
            
    # --- Net Profit ---
    # Net = Realized + Unrealized - Commissions (if Realized doesn't already capture it? Usually it does)
    # IBKR "FifoPnlRealized" usually is Net of commission, but we should verify. 
    # For now, simplistic sum.
    
    return {
        "ticker": ticker,
        "realized_pnl": realized_pnl,
        "unrealized_pnl": unrealized_pnl,
        "commissions_paid": commissions,
        "total_net_profit": realized_pnl + unrealized_pnl,
        "current_market_value": market_value
    }
