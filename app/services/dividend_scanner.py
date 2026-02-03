import yfinance as yf
from datetime import datetime, timedelta
import logging
from app.services.opportunity_service import OpportunityService
from app.models.opportunity import JuicyOpportunity, OpportunityStatus
from app.services.signal_service import SignalService
from pymongo import MongoClient
from app.config import settings

from app.services.roll_service import RollService

class DividendScanner:
    def __init__(self):
        self.opp_service = OpportunityService()
        self.signal_service = SignalService()
        self.roll_service = RollService()

    def analyze_capture_strategy(self, ticker_symbol: str) -> list[dict]:
        """
        Analyze and propose Buy-Write strategies (Protective, Balanced, Aggressive).
        """
        strategies = []
        try:
            # 1. Fetch Basic Info & Holdings
            # Fetch Holdings Context
            client = MongoClient(settings.MONGO_URI)
            db = client.get_default_database("stock_analysis")
            latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
            holdings_context = []
            
            if latest:
                 snap_id = latest.get("snapshot_id")
                 query = {"snapshot_id": snap_id, "symbol": ticker_symbol} if snap_id else {"report_date": latest.get("report_date"), "symbol": ticker_symbol}
                 for h in db.ibkr_holdings.find(query):
                     holdings_context.append({
                         "account": h.get("account_id"),
                         "quantity": h.get("quantity"),
                         "asset_class": h.get("asset_class", "STK") # Could be OPT?
                     })
                     
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            current_price = info.get("currentPrice") or info.get("previousClose")
            ex_ts = info.get("exDividendDate")
            div_rate = info.get("dividendRate", 0) / 4 # Est Quarterly
            
            if not current_price or not ex_ts:
                return []
                
            ex_date = datetime.fromtimestamp(ex_ts)
            
            # 2. Find Expiration > Ex-Date
            # Need at least 1 day holding? Actually need to hold through ex-date.
            # So expires AFTER ex-date.
            valid_expiry = None
            for exp_str in ticker.options:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
                if exp_date > ex_date:
                    valid_expiry = exp_str
                    break
            
            if not valid_expiry:
                return []
            
            # 3. Get Option Chain
            chain = self.roll_service.get_option_chain_data(ticker_symbol, valid_expiry)
            if chain is None or chain.calls.empty:
                return []
            
            calls = chain.calls
            
            # 4. Select Strikes
            # Filter for liquidity?
            calls = calls[calls['bid'] > 0.05]
            
            if calls.empty: return []

            # Find ATM
            # Sort by distance to current price
            calls['abs_diff'] = abs(calls['strike'] - current_price)
            calls = calls.sort_values('abs_diff')
            
            atm_call = calls.iloc[0]
            
            # Find ITM (Protective) - Lower strike
            itm_calls = calls[calls['strike'] < current_price].sort_values('strike', ascending=False)
            itm_call = itm_calls.iloc[0] if not itm_calls.empty else atm_call
            
            # Find OTM (Aggressive) - Higher strike
            otm_calls = calls[calls['strike'] > current_price].sort_values('strike', ascending=True)
            otm_call = otm_calls.iloc[0] if not otm_calls.empty else atm_call
            
            selected = [
                ("Protective", itm_call),
                ("Balanced", atm_call),
                ("Aggressive", otm_call)
            ]
            
            # Dedup if strikes are same (e.g. if close to strike)
            seen_strikes = set()
            
            for name, opt in selected:
                strike = float(opt['strike'])
                if strike in seen_strikes and len(selected) > 1: continue 
                seen_strikes.add(strike)
                
                bid = float(opt['bid'])
                net_cost = current_price - bid
                
                # Scenarios
                # 1. Called Away (Price > Strike): Profit = (Strike - NetCost) + Div
                # 2. Not Called (Price < Strike): Profit = (Price_End - NetCost) + Div
                
                # Assume Called Away for Max Return
                # If Strike < Net Cost (Deep ITM), profit is locked + div?
                # Profit = (Strike - NetCost) + Div
                
                max_profit_amt = (strike - net_cost) + div_rate
                max_return = (max_profit_amt / net_cost) * 100
                
                # Breakeven
                breakeven = net_cost - div_rate
                
                # Downside Protection
                downside = ((current_price - breakeven) / current_price) * 100
                
                strategies.append({
                    "type": name,
                    "strike": strike,
                    "expiry": valid_expiry,
                    "premium": bid,
                    "net_cost": round(net_cost, 2),
                    "max_profit": round(max_profit_amt, 2),
                    "max_return": round(max_return, 2),
                    "breakeven": round(breakeven, 2),
                    "downside_protection": round(downside, 1),
                    "otm_prob": 100 # TODO: use delta
                })
                
            # Fetch Rolls (SmartRoll)
            rolls = self.opp_service.get_opportunities(source="SmartRoll", symbol=ticker_symbol, limit=5)
            roll_proposals = [r.get("proposal", {}) for r in rolls]
            
            return {
                "strategies": strategies,
                "holdings_context": holdings_context,
                "rolls": roll_proposals
            }
            
        except Exception as e:
            logging.error(f"Error analyzing capture for {ticker_symbol}: {e}")
            return {"strategies": [], "holdings_context": []}

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
        
        # 1. Fetch Holdings for Account Mapping
        client = MongoClient(settings.MONGO_URI)
        db = client.get_default_database("stock_analysis")
        latest = db.ibkr_holdings.find_one(sort=[("date", -1)])
        
        holdings_map = {} # symbol -> "Acct1: 100, Acct2: 50"
        if latest:
             snapshot_id = latest.get("snapshot_id")
             query = {"snapshot_id": snapshot_id} if snapshot_id else {"report_date": latest.get("report_date")}
             for h in db.ibkr_holdings.find(query):
                 sym = h.get("symbol")
                 acct = h.get("account_id", "Unknown")
                 qty = h.get("quantity", 0)
                 if qty != 0:
                     if sym not in holdings_map: holdings_map[sym] = []
                     holdings_map[sym].append(f"{acct}: {qty}")
        
        # Flatten map
        for k, v in holdings_map.items():
            holdings_map[k] = ", ".join(v)

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
                         # 2. Advanced Metrics
                         analyst_target = info.get("targetMeanPrice") or 0.0
                         
                         # Markov Prediction
                         try:
                             pred_res = self.signal_service.predict_future_price(
                                 symbol, 
                                 days_ahead=days_to_ex, 
                                 current_price=current_price
                             )
                             markov_price = pred_res.get("predicted_price", current_price)
                         except Exception:
                             markov_price = current_price
                         
                         # Accounts
                         accounts_held = holdings_map.get(symbol, "")

                         # Suggest Opportunity
                         opp_data = {
                             "symbol": symbol,
                             "ex_date": ex_date.strftime("%Y-%m-%d"),
                             "dividend_amount": div_rate / 4, # Est Quarterly
                             "yield_annual": round(yield_pct, 2),
                             "return_pct": round(((div_rate / 4) / current_price) * 100, 2),
                             "current_price": current_price,
                             "predicted_price": markov_price,
                             "analyst_target": analyst_target,
                             "accounts_held": accounts_held,
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
