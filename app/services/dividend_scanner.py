import yfinance as yf
from datetime import datetime, timedelta
import logging
from app.services.opportunity_service import OpportunityService
from app.models.opportunity import JuicyOpportunity, OpportunityStatus

class DividendScanner:
    def __init__(self):
        self.opp_service = OpportunityService()

    def scan_dividend_capture_opportunities(self, tickers: list[str]) -> list[dict]:
        """
        Scan a list of tickers for Dividend Capture opportunities.
        Criteria:
        - Ex-Dividend Date is within 3-10 days.
        - Dividend Yield (Annualized) > 2%.
        """
        logging.info(f"[DividendScanner] Starting scan for {len(tickers)} tickers.")
        opportunities = []
        now = datetime.utcnow()
        
        for symbol in tickers:
            try:
                # logging.debug(f"Checking {symbol}...")
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Check Dividend
                ex_ts = info.get("exDividendDate")
                if not ex_ts: 
                    # logging.debug(f"No ex-div date for {symbol}")
                    continue
                
                ex_date = datetime.fromtimestamp(ex_ts)
                days_to_ex = (ex_date - now).days
                
                if 2 <= days_to_ex <= 14: # Window: 2 days to 2 weeks
                     div_rate = info.get("dividendRate")
                     current_price = info.get("currentPrice") or info.get("previousClose")
                     
                     if not div_rate or not current_price: continue
                     
                     yield_pct = (div_rate / current_price) * 100
                     
                     if yield_pct > 2.0: # Filter for decent yield
                         # Suggest Opportunity
                         opp_data = {
                             "symbol": symbol,
                             "ex_date": ex_date.strftime("%Y-%m-%d"),
                             "dividend_amount": div_rate / 4, # Est Quarterly
                             "yield_annual": round(yield_pct, 2),
                             "current_price": current_price,
                             "days_to_ex": days_to_ex,
                             "strategy": "Buy-Write (Dividend Capture)",
                             "score": 80 # Base score for now
                         }
                         
                         # Persist Opportunity
                         try:
                             juicy_opp = JuicyOpportunity(
                                 symbol=symbol,
                                 trigger_source="DividendScanner",
                                 status=OpportunityStatus.DETECTED,
                                 context={
                                     "price": current_price,
                                     "yield_annual": yield_pct,
                                     "ex_date": ex_date.strftime("%Y-%m-%d"),
                                     "days_to_ex": days_to_ex
                                 },
                                 proposal=opp_data
                             )
                             self.opp_service.create_opportunity(juicy_opp)
                             logging.info(f"[DividendScanner] Persisted opportunity for {symbol}")
                         except Exception as db_err:
                             logging.error(f"[DividendScanner] Failed to persist {symbol}: {db_err}")
                             
                         opportunities.append(opp_data)
                         
                         
            except Exception as e:
                logging.warning(f"Error scanning div for {symbol}: {e}")
                continue
                
        logging.info(f"[DividendScanner] Completed scan. Found {len(opportunities)} opportunities.")
        return opportunities

    def generate_dividend_calendar(self) -> str:
        """
        Generates an ICS calendar file for all tracked holdings with upcoming dividends.
        Persists to 'xdivs/' directory.
        Returns the path to the generated file.
        """
        import os
        from ics import Calendar, Event
        from pymongo import MongoClient
        from app.config import settings
        
        logging.info("[DividendScanner] Starting ICS Calendar Generation...")
        
        # 0. Setup Directory
        cache_dir = "xdivs"
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
            
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        filename = f"dividends_{today_str}.ics"
        file_path = os.path.join(cache_dir, filename)
        
        # 1. Fetch Symbols (From IBKR Holdings)
        # TODO: Abstract this symbol fetching logic shared with jobs.py
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        
        latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
        symbols = []
        if latest:
            query = {"snapshot_id": latest.get("snapshot_id")} if latest.get("snapshot_id") else {"report_date": latest.get("report_date")}
            holdings = list(db.ibkr_holdings.find(query, {"symbol": 1}))
            symbols = list(set([h["symbol"] for h in holdings]))
        
        now = datetime.utcnow()
        events_count = 0
        c = Calendar()
        c.creator = "JuicyFruitOptions"

        # 2. Fetch Data & Build Calendar
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                ts = ticker.info.get("exDividendDate")
                if ts:
                     dt = datetime.fromtimestamp(ts)
                     # Look back 30 days to capture recent, look forward plenty
                     if dt > now - timedelta(days=30): 
                         rate = ticker.info.get("dividendRate", 0)
                         
                         e = Event()
                         e.name = f"Ex-Div: {symbol}"
                         e.begin = dt.strftime("%Y-%m-%d")
                         e.make_all_day()
                         e.description = f"Annual Rate: ${rate}\nEst Qtr: ${rate/4}"
                         c.events.add(e)
                         events_count += 1
            except Exception as e:
                 # logging.warning(f"Failed to fetch div info for {symbol}: {e}")
                 pass

        # 3. Save to file
        with open(file_path, 'w') as f:
            f.write(str(c))
            
        logging.info(f"[DividendScanner] ICS Generation Complete. Saved {events_count} events to {file_path}")
        return file_path
