from typing import List, Dict
from app.models import TradeRecord, AnalyzedTrade, TradeMetrics
from collections import defaultdict
import logging


# Create logger for this module
logger = logging.getLogger(__name__)

def calculate_pnl(trades: List[TradeRecord]) -> List[AnalyzedTrade]:
    """
    Calculates Realized P&L for a list of trades using FIFO matching.
    Returns a list of AnalyzedTrade objects.
    """
    # Group by symbol to process independently
    logger.info("Starting P&L Calculation...")
    trades_by_symbol = defaultdict(list)
    for t in trades:
        trades_by_symbol[t.symbol].append(t)
        
    logger.info(f"Grouped {len(trades)} trades into {len(trades_by_symbol)} symbols.")
    analyzed_results = []
    
    count = 0
    for symbol, symbol_trades in trades_by_symbol.items():
        count += 1
        if count % 100 == 0:
            logger.debug(f"Processed {count}/{len(trades_by_symbol)} symbols...")
            
        # Sort by date
        sorted_trades = sorted(symbol_trades, key=lambda x: x.date_time or "")
        
        # FIFO Queue for open positions: List of (quantity, price_per_share)
        long_queue = [] 
        short_queue = []
        
        for t in sorted_trades:
            try:
                analyzed = AnalyzedTrade(**t.model_dump())
                qty = t.quantity
                # Safe float conversion helper
                def safe_float(val, default=0.0):
                    if val is None: return default
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return default

                data = t.model_dump()
                # Prioritize 'trade_price' (snake) then 'TradePrice' (legacy)
                price_raw = data.get("trade_price") if data.get("trade_price") is not None else data.get("TradePrice")
                price = safe_float(price_raw)
                
                # Simple Commission handling
                comm_raw = data.get("ib_commission") if data.get("ib_commission") is not None else data.get("IBCommission")
                comm = safe_float(comm_raw)
            except Exception as e:
                logger.error(f"Error preparing trade logic for {symbol}: {e}")
                continue
            
            # TODO: Robust Buy/Sell detection. 
            # In IBKR: Positive Qty = Buy, Negative Qty = Sell
            
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
            
            analyzed.realized_pl = realized_pl - abs(comm) # Subtract commission from PL
            analyzed_results.append(analyzed)
            
    logger.info(f"P&L Analysis complete. Created {len(analyzed_results)} analyzed records.")
    return analyzed_results

def calculate_metrics(trades: List[AnalyzedTrade]) -> TradeMetrics:
    """
    Aggregates AnalyzedTrades into high-level metrics.
    """
    total_pl = 0.0
    winning = 0
    losing = 0
    total = 0
    gross_win = 0.0
    gross_loss = 0.0
    logger.info("Starting Metrics Calculation...")
    total_pl = 0.0
    
    for t in trades:
        # Only count "Closing" trades towards metrics? 
        # Or just sum all PL (Opening trades have 0 PL usually)
        if t.realized_pl != 0:
            total_pl += t.realized_pl
            total += 1
            if t.realized_pl > 0:
                winning += 1
                gross_win += t.realized_pl
            else:
                losing += 1
                gross_loss += abs(t.realized_pl)
                
    win_rate = (winning / total * 100) if total > 0 else 0.0
    
    if gross_loss > 0:
        profit_factor = gross_win / gross_loss
    else:
        # Avoid Infinity for JSON serialization
        profit_factor = gross_win if gross_win > 0 else 0.0
    
    m = TradeMetrics(
        total_pl=round(total_pl, 2),
        win_rate=round(win_rate, 2),
        profit_factor=round(profit_factor, 2),
        total_trades=total,
        winning_trades=winning,
        losing_trades=losing
    )
    logger.info(f"Metrics calculated: {m}")
    return m
