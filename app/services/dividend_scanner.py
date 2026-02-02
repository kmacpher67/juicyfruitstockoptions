import yfinance as yf
from datetime import datetime, timedelta
import logging

class DividendScanner:
    def __init__(self):
        pass

    def scan_dividend_capture_opportunities(self, tickers: list[str]) -> list[dict]:
        """
        Scan a list of tickers for Dividend Capture opportunities.
        Criteria:
        - Ex-Dividend Date is within 3-10 days.
        - Dividend Yield (Annualized) > 2%.
        """
        opportunities = []
        now = datetime.utcnow()
        
        for symbol in tickers:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Check Dividend
                ex_ts = info.get("exDividendDate")
                if not ex_ts: continue
                
                ex_date = datetime.fromtimestamp(ex_ts)
                days_to_ex = (ex_date - now).days
                
                if 2 <= days_to_ex <= 14: # Window: 2 days to 2 weeks
                     div_rate = info.get("dividendRate")
                     current_price = info.get("currentPrice") or info.get("previousClose")
                     
                     if not div_rate or not current_price: continue
                     
                     yield_pct = (div_rate / current_price) * 100
                     
                     if yield_pct > 2.0: # Filter for decent yield
                         # Suggest Opportunity
                         opp = {
                             "symbol": symbol,
                             "ex_date": ex_date.strftime("%Y-%m-%d"),
                             "dividend_amount": div_rate / 4, # Est Quarterly
                             "yield_annual": round(yield_pct, 2),
                             "current_price": current_price,
                             "days_to_ex": days_to_ex,
                             "strategy": "Buy-Write (Dividend Capture)",
                             "score": 80 # Base score for now
                         }
                         opportunities.append(opp)
                         
            except Exception as e:
                logging.warning(f"Error scanning div for {symbol}: {e}")
                continue
                
        return opportunities
