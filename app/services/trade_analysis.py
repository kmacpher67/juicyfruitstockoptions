from typing import List, Dict
from app.models import TradeRecord, AnalyzedTrade, TradeMetrics
from collections import defaultdict
import logging


# Create logger for this module
logger = logging.getLogger(__name__)

from typing import Tuple

def calculate_pnl(trades: List[Dict]) -> Tuple[List[AnalyzedTrade], Dict[str, dict]]:
    """
    Calculates Realized P&L for a list of trade dictionaries using FIFO matching.
    Returns a tuple of:
      - List of AnalyzedTrade objects.
      - Dict of open positions: { symbol: {"qty": float, "avg_cost": float} }
    """
    # Group by symbol to process independently
    logger.info("Starting P&L Calculation...")
    trades_by_symbol = defaultdict(list)
    for t in trades:
        # Some legacy trades might still be TradeRecords or have different keys
        sym = t.get("symbol") if hasattr(t, "get") else t.symbol
        trades_by_symbol[sym].append(t)
        
    logger.info(f"Grouped {len(trades)} trades into {len(trades_by_symbol)} symbols.")
    analyzed_results = []
    open_positions = {}
    
    count = 0
    for symbol, symbol_trades in trades_by_symbol.items():
        count += 1
        if count % 100 == 0:
            logger.debug(f"Processed {count}/{len(trades_by_symbol)} symbols...")
            
        def get_dt(t):
            return t.get("date_time", "") if hasattr(t, "get") else getattr(t, "date_time", "")
            
        # Sort by date
        sorted_trades = sorted(symbol_trades, key=get_dt)
        
        # FIFO Queue for open positions: List of (quantity, price_per_share)
        long_queue = [] 
        short_queue = []
        
        for t in sorted_trades:
            try:
                # Handle both dict and object for backward compatibility
                is_dict = isinstance(t, dict)
                data = dict(t) if is_dict else t.model_dump()
                
                # Normalize keys for the loop
                qty_raw = data.get("quantity", data.get("Quantity", 0.0))
                
                # Safe float conversion helper
                def safe_float(val, default=0.0):
                    if val is None: return default
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return default

                qty = safe_float(qty_raw)
                
                # Prioritize 'price' (snake) then 'TradePrice' (legacy)
                price_raw = data.get("price") if data.get("price") is not None else data.get("TradePrice")
                if price_raw is None:
                    price_raw = data.get("trade_price")
                price = safe_float(price_raw)
                
                # Simple Commission handling
                comm_raw = data.get("commission") if data.get("commission") is not None else data.get("IBCommission")
                if comm_raw is None:
                    comm_raw = data.get("ib_commission")
                comm = safe_float(comm_raw)
            except Exception as e:
                logger.error(f"Error preparing trade logic for {symbol}: {e}")
                continue
            
            # Passthrough for Dividends
            if data.get("buy_sell") == "DIVIDEND":
                data["realized_pl"] = data.get("realized_pnl", 0.0)
                analyzed_results.append(AnalyzedTrade(**data))
                continue
            
            realized_pl = 0.0
            
            if qty > 0: # BUY
                # If we are short, cover match
                remaining_buy = qty
                while remaining_buy > 0 and short_queue:
                    short_qty, short_price = short_queue[0]
                    
                    match_qty = min(remaining_buy, abs(short_qty))
                    
                    # PL = (Short Price - Buy Price) * Match Qty
                    realized_pl += (short_price - price) * match_qty
                    
                    matched_remainder =  abs(short_qty) - match_qty
                    
                    if matched_remainder == 0:
                        short_queue.pop(0)
                    else:
                        short_queue[0] = (-matched_remainder, short_price)
                        
                    remaining_buy -= match_qty
                    
                # Add remainder to Long Queue
                if remaining_buy > 0:
                    long_queue.append((remaining_buy, price))

            elif qty < 0: # SELL
                abs_sell_qty = abs(qty)
                remaining_sell = abs_sell_qty
                
                # If we are long, close match
                while remaining_sell > 0 and long_queue:
                    long_qty, long_price = long_queue[0]
                    match_qty = min(remaining_sell, long_qty)
                    
                    # PL = (Sell Price - Buy Price) * Match Qty
                    realized_pl += (price - long_price) * match_qty
                    
                    matched_remainder = long_qty - match_qty
                    
                    if matched_remainder == 0:
                        long_queue.pop(0)
                    else:
                        long_queue[0] = (matched_remainder, long_price)
                        
                    remaining_sell -= match_qty
                    
                # Add remainder to Short Queue
                if remaining_sell > 0:
                    short_queue.append((-remaining_sell, price))
            
            data["realized_pl"] = realized_pl - abs(comm) # Subtract commission from PL
            analyzed_results.append(AnalyzedTrade(**data))
            
        # Compute remainder for open positions
        total_open_qty = 0.0
        total_cost = 0.0
        
        if long_queue:
            for q, p in long_queue:
                total_open_qty += q
                total_cost += (q * p)
        elif short_queue:
            for q, p in short_queue:
                total_open_qty += q  # q is already negative
                total_cost += (abs(q) * p)
                
        if total_open_qty != 0:
            avg_cost = total_cost / abs(total_open_qty)
            open_positions[symbol] = {
                "qty": total_open_qty,
                "avg_cost": avg_cost
            }
            
    logger.info(f"P&L Analysis complete. Created {len(analyzed_results)} analyzed records, {len(open_positions)} open positions.")
    return analyzed_results, open_positions

import yfinance as yf

import time

_PRICE_CACHE = {}
_CACHE_TTL = 300 # 5 minutes

def calculate_metrics(trades: List[AnalyzedTrade], open_positions: Dict[str, dict] = None) -> TradeMetrics:
    """
    Aggregates AnalyzedTrades into high-level metrics.
    Optionally fetches current prices for open_positions to calculate Unrealized P&L.
    """
    if open_positions is None:
        open_positions = {}
        
    total_pl = 0.0
    winning = 0
    losing = 0
    total = 0
    open_trades = 0
    closed_trades = 0
    gross_win = 0.0
    gross_loss = 0.0
    
    logger.info("Starting Metrics Calculation...")
    
    for t in trades:
        total += 1
        if t.realized_pl != 0:
            closed_trades += 1
            total_pl += t.realized_pl
            if t.realized_pl > 0:
                winning += 1
                gross_win += t.realized_pl
            else:
                losing += 1
                gross_loss += abs(t.realized_pl)
                
    # Open trades count should reflect active underlying positions, not just empty legs
    open_trades = len(open_positions.keys()) if open_positions else 0
                
    win_rate = (winning / closed_trades * 100) if closed_trades > 0 else 0.0
    
    if gross_loss > 0:
        profit_factor = gross_win / gross_loss
    else:
        # Avoid Infinity for JSON serialization
        profit_factor = gross_win if gross_win > 0 else 0.0
    
    unrealized_profit = 0.0
    unrealized_loss = 0.0
    
    if open_positions:
        now = time.time()
        # Batch fetch prices using yfinance for symbols not in cache
        symbols = list(open_positions.keys())
        yf_symbols = []
        for sym in symbols:
            query_sym = sym.split()[0] if " " in sym else sym
            if query_sym not in _PRICE_CACHE or (now - _PRICE_CACHE[query_sym]["ts"] > _CACHE_TTL):
                yf_symbols.append(query_sym)
        
        yf_query_string = " ".join(set(yf_symbols))
        
        if yf_query_string:
            try:
                tickers = yf.Tickers(yf_query_string)
                for query_sym in set(yf_symbols):
                    current_price = None
                    try:
                        ticker = tickers.tickers.get(query_sym)
                        if ticker:
                            # Use fast info instead of info
                            current_price = ticker.fast_info.get("lastPrice") or ticker.fast_info.get("previousClose")
                    except Exception as e:
                        logger.warning(f"Could not fetch current price for {query_sym}: {e}")
                    
                    if current_price is not None:
                        _PRICE_CACHE[query_sym] = {"price": current_price, "ts": now}
            except Exception as e:
                 logger.error(f"Failed to fetch prices for open positions: {e}")

        # Calculate unrealized P&L using cached prices
        for sym, pos in open_positions.items():
            query_sym = sym.split()[0] if " " in sym else sym
            if query_sym in _PRICE_CACHE:
                current_price = _PRICE_CACHE[query_sym]["price"]
                qty = pos["qty"]
                avg_cost = pos["avg_cost"]
                
                multiplier = 100 if " " in sym or (len(sym) > 5 and any(c.isdigit() for c in sym)) else 1
                
                upl = 0.0
                if qty > 0: # Long
                    upl = (current_price - avg_cost) * qty * multiplier
                else: # Short
                    upl = (avg_cost - current_price) * abs(qty) * multiplier
                    
                if upl > 0:
                    unrealized_profit += upl
                else:
                    unrealized_loss += abs(upl)

    m = TradeMetrics(
        total_pl=round(total_pl, 2),
        unrealized_profit=round(unrealized_profit, 2),
        unrealized_loss=round(unrealized_loss, 2),
        win_rate=round(win_rate, 2),
        profit_factor=round(profit_factor, 2),
        total_trades=total,
        open_trades=open_trades,
        closed_trades=closed_trades,
        winning_trades=winning,
        losing_trades=losing
    )
    logger.info(f"Metrics calculated: {m}")
    return m
