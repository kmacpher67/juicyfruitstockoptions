import yfinance as yf
from datetime import datetime, timedelta
import logging
import pandas as pd
from app.utils.greeks_calculator import GreeksCalculator

class RollService:
    def __init__(self):
        pass

    def get_realtime_price(self, symbol):
        try:
            ticker = yf.Ticker(symbol, session=None) # session=None uses default
            # fast_info is faster
            return ticker.fast_info['last_price']
        except Exception as e:
            logging.error(f"Failed to get price for {symbol}: {e}")
            return 0.0

    def get_option_chain_data(self, symbol, exp_date_str):
        """Fetch option chain for a specific date (YYYY-MM-DD)."""
        try:
            ticker = yf.Ticker(symbol)
            chain = ticker.option_chain(exp_date_str)
            return chain
        except Exception as e:
            logging.error(f"Failed to get chain for {symbol} on {exp_date_str}: {e}")
            return None

    def score_roll(self, roll_data, current_pos, market_data, dividend_info=None):
        """
        Calculate 0-100 score for a roll opportunity.
        roll_data: {net_credit, strike, days_extended, delta, gamma, bid, expiration...}
        current_pos: {strike, average_cost, ...}
        market_data: {current_price, one_day_change, ...}
        dividend_info: {ex_date: 'YYYY-MM-DD', amount: float} (Optional)
        """
        score = 50.0  # Base Score

        # 1. Net Credit (Weight: 40%)
        credit = roll_data.get("net_credit", 0)
        if credit > 0:
            score += 20
            # Bonus for Yield
            # Assume 1 contract = 100 shares. Yield = Credit / Strike Price roughly
            strike = roll_data.get("strike", 100)
            if strike > 0 and (credit / strike) > 0.005:  # > 0.5% return on notional
                score += 10
        elif credit < 0:
            score -= 20  # Paying debit is discouraged unless defensive

        # 2. Strike Improvement (Weight: 30%)
        # Up and Out is preferred for Calls
        new_strike = roll_data.get("strike", 0)
        old_strike = current_pos.get("strike", 0)
        curr_price = market_data.get("current_price", 0)
        if new_strike > old_strike:
            score += 20
            # Bonus if we move from ITM to OTM
            if old_strike < curr_price < new_strike:
                score += 10  # Rescued the position!

        # 3. Duration Strategy (Weight: 20%)
        # Preference: Short Duration (< 10 days)
        days = roll_data.get("days_extended", 0) # Days between old exp and new exp
        if days < 10:
            score += 10
        elif days > 30:
            score -= 10

        # 4. Momentum & Urgency (Weight: Variable)
        # 1D Change
        one_day = market_data.get("one_day_change", 0)
        # If Bullish (> 1%) and we are rolling up, that's good.
        if one_day > 1.0 and new_strike > old_strike:
            score += 10

        # 5. Greeks Optimization
        # Delta: Prefer ~0.30 (Standard OTM target)
        delta = abs(roll_data.get("delta", 0))
        if 0.20 <= delta <= 0.40:
            score += 10
        elif delta > 0.60: # Deep ITM
            score -= 10

        # 6. Dividend Assignment Risk (X-DIV Strategy)
        if dividend_info and dividend_info.get('amount', 0) > 0:
            div_date_str = dividend_info.get('ex_date')
            div_amount = dividend_info.get('amount')
            roll_exp_str = roll_data.get('expiration', '')

            if div_date_str and roll_exp_str:
                try:
                    div_dt = datetime.strptime(div_date_str, "%Y-%m-%d")
                    # If roll expiry is AFTER or ON ex-date, we hold through it (Risk!)
                    # Wait, if we roll TO a date, we are liable if that date is >= ExDate. 
                    # If we roll to Exp < ExDate, we are safe? No, short options expire. 
                    # If Short Call Expiry >= ExDate, we are at risk on ExDate - 1.
                    
                    roll_exp_dt = datetime.strptime(roll_exp_str, "%Y-%m-%d")
                    
                    if roll_exp_dt >= div_dt:
                        # We are holding through the dividend.
                        # Check ITM status
                        if new_strike < curr_price:
                            # We are ITM. Risk Analysis.
                            intrinsic = max(0.0, curr_price - new_strike)
                            option_price = roll_data.get('bid', 0) # Using Bid as proxy for market price
                            extrinsic = max(0.0, option_price - intrinsic)
                            
                            if extrinsic < div_amount:
                                # DANGER ZONE
                                score -= 50
                                logging.info(f"Dividend Risk Detected: Extrinsic {extrinsic} < Div {div_amount}")
                            elif extrinsic > div_amount * 1.5:
                                # Safe Buffer
                                score += 10
                except ValueError:
                    pass

        return max(0.0, min(100.0, score))


    def analyze_portfolio_rolls(self, portfolio_items, max_days_to_expiration=10):
        """
        Analyze portfolio for roll opportunities.
        """
        suggestions = []
        now = datetime.utcnow()
        
        for item in portfolio_items:
            # Check for Options (OPT/FOP) or explicit secType
            sec_type = item.get("secType") or item.get("asset_class")
            
            # Simple check: If we have an 'expiry' field, it's likely an option we parsed
            if not item.get("expiry"): 
                 if sec_type not in ["OPT", "FOP"]: continue
            
            # Must be Short
            if item.get("quantity", 0) >= 0: continue 

            # Must be Call (for now)
            # Check parse 'right' (C/P) or 'putCall' (Put/Call)
            right = item.get("right") or item.get("putCall")
            if str(right).upper() not in ["C", "CALL"]: continue
            
            # Parse Expiry
            exp_str = item.get("expiry") # YYYY-MM-DD from parser
            if not exp_str: continue
            
            try:
                # Normalize
                if len(exp_str) == 8 and "-" not in exp_str:
                     exp_dt = datetime.strptime(exp_str, "%Y%m%d")
                     exp_fmt = exp_dt.strftime("%Y-%m-%d")
                else:
                     try:
                        exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
                        exp_fmt = exp_str
                     except:
                        # Fallback for other formats? 
                        continue
                
                # Check Duration Window
                days_to_exp = (exp_dt - now).days
                if days_to_exp > max_days_to_expiration:
                    continue # Skip far out options
                
                # Find Rolls
                # Use underlying symbol if parsed
                symbol = item.get("underlying_symbol") or item.get("symbol")
                # If symbol is still the long string, we might have issues fetching data. 
                # But 'underlying_symbol' should have been populated by parser.
                
                if len(symbol) > 6 and not item.get("underlying_symbol"):
                     # Try to strip if parser failed?
                     symbol = symbol[:6].strip()
                
                strike = float(item.get("strike", 0))
                
                current_pos = {
                    "strike": strike,
                    "average_cost": float(item.get("averageCost") or item.get("cost_basis") or 0) 
                }
                
                res = self.find_rolls(symbol, strike, exp_fmt, position_type="call", current_pos_context=current_pos)
                
                if "rolls" in res and res["rolls"]:
                    # Attach context
                    res["days_to_expiry"] = days_to_exp
                    res["position_qty"] = item.get("quantity")
                    suggestions.append(res)
                    
            except Exception as e:
                logging.error(f"Error analyzing roll for {item.get('symbol')}: {e}")
                continue
                
        return suggestions

    def find_rolls(self, symbol, current_strike, current_exp_date, position_type="call", current_pos_context=None):
        """
        Find roll opportunities.
        current_exp_date: YYYY-MM-DD
        """
        ticker = yf.Ticker(symbol)
        try:
             # Use fast_info if possible, or history
             # We need 1D Change for momentum
             fast = ticker.fast_info
             current_price = fast['last_price']
             prev_close = fast['previous_close']
             
             one_day_change = 0.0
             if prev_close and prev_close > 0:
                 one_day_change = ((current_price - prev_close) / prev_close) * 100.0
             
             # Fetch Dividend Info
             # yfinance uses 'dividends' series or 'info["exDividendDate"]'
             dividend_info = {"amount": 0, "ex_date": None}
             try:
                 info = ticker.info
                 ex_ts = info.get("exDividendDate") # Timestamp
                 div_rate = info.get("dividendRate") or info.get("trailingAnnualDividendRate") or 0.0
                 # If rate is annual, we need the quarterly amount? 
                 # Usually dividendRate is annual sum. 
                 # Let's try to get the *next* specific dividend if possible.
                 # ticker.dividends is history.
                 
                 if ex_ts:
                      # Check if future?
                      ex_date = datetime.fromtimestamp(ex_ts)
                      now = datetime.utcnow()
                      if ex_date > now - timedelta(days=1): # If it's today or future
                           # Estimate amount: Rate / 4 ? 
                           # Or check last dividend?
                           amount = 0.0
                           if div_rate:
                               amount = div_rate / 4.0 # Crude estimate
                               
                           dividend_info = {
                               "ex_date": ex_date.strftime("%Y-%m-%d"),
                               "amount": amount
                           }
             except Exception as dev:
                 logging.warning(f"Failed to fetch div info for {symbol}: {dev}")
                 
             available_dates = ticker.options
        except:
             return {"error": "Failed to fetch ticker data"}
             
        market_data = {
            "current_price": current_price,
            "one_day_change": one_day_change
        }
             
        # Filter Dates: Must be AFTER current_exp_date
        # Convert inputs
        try:
            curr_exp_dt = datetime.strptime(current_exp_date, "%Y-%m-%d")
        except ValueError:
             return {"error": "Invalid date format"}
             
        future_dates = [d for d in available_dates if datetime.strptime(d, "%Y-%m-%d") > curr_exp_dt]
        
        # Limit to next 4 expirations to save time/bandwidth
        future_dates = future_dates[:4]
        
        # 1. Estimate Cost to Close (Old Option)
        # We need to find the specific option in the chain for 'current_exp_date'.
        cost_to_close = 0.0
        try:
            old_chain = ticker.option_chain(current_exp_date)
            # calls or puts
            old_df = old_chain.calls if position_type == "call" else old_chain.puts
            # Find closest strike
            # Exact match?
            row = old_df[old_df['strike'] == current_strike]
            if not row.empty:
                # Use Ask price (Buy to Close)
                cost_to_close = row.iloc[0]['ask'] or row.iloc[0]['lastPrice']
            else:
                 # Fallback?
                 return {"error": f"Could not find existing option {current_strike} for {current_exp_date}"}
        except Exception as e:
             logging.error(f"Error fetching old chain: {e}")
             return {"error": f"Failed to fetch old chain: {str(e)}"}
             
        rolls = []
        
        # Helper Context
        if not current_pos_context:
            current_pos_context = {"strike": current_strike, "average_cost": 0}

        for d in future_dates:
            try:
                chain = ticker.option_chain(d)
                df = chain.calls if position_type == "call" else chain.puts
                
                # Filter Strikes: 
                # For Covered Calls: Generally want Strike >= Current Strike (Up & Out) or Strike >= Current Price
                # Let's simple filter: Strike >= Current Strike
                
                candidates = df[df['strike'] >= current_strike].copy()
                
                if not candidates.empty:
                    # Calculate Greeks for the batch
                    # 1. Add Type
                    candidates['type'] = 'c' if position_type == "call" else 'p'
                    
                    # 2. Add Time to Expiry (years)
                    # d is String YYYY-MM-DD
                    exp_dt = datetime.strptime(d, "%Y-%m-%d")
                    # Use current time vs expiry time (approx 16:00)
                    now = datetime.utcnow()
                    diff = exp_dt - now
                    # Ensure positive
                    days = max(diff.days, 0)
                    years = days / 365.0
                    if years == 0: years = 1/365.0 # At least 1 day for math stability
                    
                    candidates['time_to_expiry_years'] = years
                    
                    # 3. Calculate
                    candidates = GreeksCalculator.calculate_dataframe(candidates, current_price)
                
                for index, row in candidates.iterrows():
                    new_strike = row['strike']
                    # Sell to Open: Use Bid
                    premium = row['bid'] or row['lastPrice']
                    if premium == 0: continue
                    
                    net_credit = premium - cost_to_close
                    
                    # Logic: Only show if Net Credit > 0 OR if we are improving strike significantly for small debit
                    if net_credit > -0.10: # Allow small debit if necessary
                         roll_type = "Up & Out" if new_strike > current_strike else "Roll Out"
                         
                         days_diff = (datetime.strptime(d, "%Y-%m-%d") - curr_exp_dt).days
                         
                         roll_item = {
                             "expiration": d,
                             "strike": new_strike,
                             "bid": premium,
                             "cost_to_close": cost_to_close,
                             "net_credit": round(net_credit, 2),
                             "roll_type": roll_type,
                             "days_extended": days_diff,
                             "delta": float(row.get('delta', 0)),
                             "gamma": float(row.get('gamma', 0)),
                             "theta": float(row.get('theta', 0))
                         }
                         
                         # CALCULATE SCORE
                         score = self.score_roll(roll_item, current_pos_context, market_data, dividend_info)
                         roll_item["score"] = score
                         
                         rolls.append(roll_item)
            except Exception as e:
                logging.error(f"Error processing chain for {d}: {e}")
                continue
                
        # Sort by Score descending (Priority)
        rolls.sort(key=lambda x: x['score'], reverse=True)
        
        # Return Top 5
        rolls = rolls[:10]
        
        return {
            "symbol": symbol,
            "current_price": current_price,
            "one_day_change": round(one_day_change, 2),
            "cost_to_close": cost_to_close,
            "rolls": rolls
        }
