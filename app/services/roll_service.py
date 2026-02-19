import yfinance as yf
from datetime import datetime, timedelta, timezone
import logging
import pandas as pd
from app.utils.greeks_calculator import GreeksCalculator
from app.services.signal_service import SignalService
from app.services.opportunity_service import OpportunityService
from app.models.opportunity import JuicyOpportunity, OpportunityStatus

class RollService:
    def __init__(self, signal_service=None):
        self.signal_service = signal_service or SignalService()
        self.opp_service = OpportunityService()

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

    def score_roll(self, roll_data, current_pos, market_data, dividend_info=None, signal_data=None):
        """
        Calculate 0-100 score for a roll opportunity.
        roll_data: {net_credit, strike, days_extended, delta, gamma, bid, expiration...}
        current_pos: {strike, average_cost, ...}
        market_data: {current_price, one_day_change, ...}
        dividend_info: {ex_date: 'YYYY-MM-DD', amount: float} (Optional)
        signal_data: {prob_up, prob_down, recommendation, ...} (Optional)
        """
        score = 50.0  # Base Score
        reasons = []

        # 1. Net Credit (Weight: 35%)
        credit = roll_data.get("net_credit", 0)
        target_yield = 0.005 # 0.5% yield target
        
        strike = roll_data.get("strike", 100)
        if strike <= 0: strike = 100 # Safety

        if credit > 0:
            score += 20
            # Bonus for Yield
            yield_pct = credit / strike
            if yield_pct > target_yield:
                score += 10
                reasons.append(f"High Yield ({yield_pct*100:.1f}%)")
        elif credit < 0:
            # Debit
            score -= 20
            reasons.append("Net Debit")
            # But if it's a "Rescue" roll (Deep ITM -> OTM), we might accept a debit
            if roll_data.get("roll_type") == "Up & Out" and signal_data and signal_data.get("prob_up", 0) > 0.6:
                 score += 15 # Mitigate the penalty
                 reasons.append("Strategic Debit (Rescue)")

        # 2. Strike Improvement (Weight: 25%)
        new_strike = roll_data.get("strike", 0)
        old_strike = current_pos.get("strike", 0)
        curr_price = market_data.get("current_price", 0)
        
        if new_strike > old_strike:
            score += 20
            reasons.append("Strike Improved")
            # Bonus if we move from ITM to OTM
            if old_strike < curr_price < new_strike:
                score += 15
                reasons.append("Rescued ITM -> OTM")
        elif new_strike < old_strike:
            score -= 10
            reasons.append("Strike Reduced")

        # 3. Duration Strategy (Weight: 15%)
        days = roll_data.get("days_extended", 0)
        if days <= 7:
            score += 10
            reasons.append("Short Duration (<7d)")
        elif 7 < days <= 21:
             score += 5
        elif days > 45:
            score -= 10
            reasons.append("Long Duration Penalty")

        # 4. Momentum & Urgency (Weight: 10%)
        one_day = market_data.get("one_day_change", 0)
        dte_current = market_data.get("days_to_expiry_current", 0)
        
        # Momentum Trigger: Strong UP move + Short DTE -> Urgency to Roll Up
        if one_day > 1.5 and dte_current < 7:
             if new_strike > old_strike:
                 score += 15
                 reasons.append("Momentum Trigger (Roll Up!)")
        
        # 5. Greeks Optimization (Weight: 15%)
        delta = abs(roll_data.get("delta", 0))
        if 0.20 <= delta <= 0.35:
            score += 10
            reasons.append("Optimal Delta (20-35)")
        elif delta > 0.60: 
            score -= 15
            reasons.append("Deep ITM Risk")
            
        # Gamma Penalty
        # High Gamma Risk: DTE < 2 days AND ATM (Moneyness 0.98 - 1.02)
        # We generally want to avoid holding these through expiration unless we close/roll.
        new_dte_days = float(roll_data.get('time_to_expiry_years', 0)) * 365
        moneyness = curr_price / new_strike if new_strike and new_strike > 0 else 0
        
        if new_dte_days < 2 and 0.97 <= moneyness <= 1.03:
             score -= 25
             reasons.append("Gamma/Pin Risk")

        # 6. Signal Integration (Markov/Kalman)
        if signal_data:
            prob_up = signal_data.get('prob_up', 0.5)
            prob_down = signal_data.get('prob_down', 0.5)
            trend = signal_data.get('recommendation', 'HOLD') # ROLL, HOLD, CAUTION
            
            # If AI predicts UP (Bullish) and we are Short Call
            if prob_up > 0.60:
                if new_strike > old_strike:
                    score += 15
                    reasons.append(f"AI: Bullish ({prob_up:.0%}) -> Roll Up")
                elif new_strike <= old_strike:
                    score -= 15
                    reasons.append("AI: Bullish Conflict")
            
            # If AI predicts DOWN (Bearish)
            elif prob_down > 0.60:
                # If Bearish, we prefer credit (income) or holding.
                if credit > 0.5: # Significant credit
                    score += 10
                    reasons.append("AI: Bearish -> Collecting Premium")
                
        # 7. Dividend Risk
        if dividend_info and dividend_info.get('amount', 0) > 0:
            div_date_str = dividend_info.get('ex_date')
            div_amount = dividend_info.get('amount', 0)
            roll_exp_str = roll_data.get('expiration', '')

            if div_date_str and roll_exp_str and div_amount > 0:
                try:
                    div_dt = datetime.strptime(div_date_str, "%Y-%m-%d")
                    roll_exp_dt = datetime.strptime(roll_exp_str, "%Y-%m-%d")
                    
                    if roll_exp_dt >= div_dt:
                        # Check assignment risk
                        # ITM calls are at risk if Extrinsic < Dividend
                        if new_strike < curr_price:
                            # Use Bid for intrinsic calculation conservative
                            intrinsic = max(0.0, curr_price - new_strike)
                            option_price = roll_data.get('bid', 0)
                            extrinsic = max(0.0, option_price - intrinsic)
                            
                            if extrinsic < div_amount:
                                score -= 50
                                reasons.append("Dividend Assignment Risk!")
                            elif extrinsic > div_amount * 1.5:
                                score += 5
                                reasons.append("Dividend Safe")
                except ValueError:
                    pass

        return max(0.0, min(100.0, score)), reasons



    def analyze_portfolio_rolls(self, portfolio_items, max_days_to_expiration=10, persist: bool = False):
        """
        Analyze portfolio for roll opportunities.
        """
        suggestions = []
        # use naive UTC timestamp for comparisons
        now = datetime.utcnow()
        
        for item in portfolio_items:
            try:
                # Check for Options (OPT/FOP) or explicit secType
                sec_type = item.get("secType") or item.get("asset_class")
                # Simple check: If we have an 'expiry' field, it's likely an option we parsed
                if not item.get("expiry") and sec_type not in ["OPT", "FOP"]: continue
                
                # Must be Short Position (quantity < 0)
                if float(item.get("quantity", 0)) >= 0: continue 

                # Must be Call (for now)
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
                         exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
                         exp_fmt = exp_str
                except:
                    continue
                
                # Check Duration Window
                days_to_exp = (exp_dt - now).days
                if days_to_exp > max_days_to_expiration:
                    continue
                
                symbol = item.get("underlying_symbol") or item.get("symbol")
                if len(symbol) > 6 and not item.get("underlying_symbol"):
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
                    # Friendly Description
                    res["position_description"] = f"{symbol} {exp_fmt} {strike}C"
                    suggestions.append(res)
                    
            except Exception as e:
                logging.error(f"Error analyzing roll for {item.get('symbol', 'Unknown')}: {e}")
                continue
                
        if persist and suggestions:
            self._persist_suggestions(suggestions)

        return suggestions

    def _persist_suggestions(self, suggestions):
        """Persist top roll suggestions to MongoDB."""
        for item in suggestions:
            symbol = item.get("symbol")
            rolls = item.get("rolls", [])
            if not rolls: continue
            
            # Persist Top 3 Rolls per position to avoid noise
            # Only persist if Score > 60 (Quality Check)
            top_rolls = [r for r in rolls if r.get("score", 0) > 60][:3]
            
            for roll in top_rolls:
                 try:
                      # Create Opportunity
                      opp = JuicyOpportunity(
                          symbol=symbol,
                          trigger_source="SmartRoll",
                          status=OpportunityStatus.DETECTED,
                          context={
                              "current_price": item.get("current_price"),
                              "position_description": item.get("position_description"),
                              "days_to_expiry": item.get("days_to_expiry"),
                              "score": roll.get("score"),
                              "signal_analysis": item.get("signal_analysis")
                          },
                          proposal=roll
                      )
                      self.opp_service.create_opportunity(opp)
                      logging.info(f"Persisted Smart Roll for {symbol} (Score: {roll.get('score')})")
                 except Exception as e:
                      logging.error(f"Failed to persist roll for {symbol}: {e}")
            
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
                 
                 if ex_ts:
                     # Check if future?
                     # convert timestamp to UTC datetime
                     ex_date = datetime.fromtimestamp(ex_ts, timezone.utc)
                     now = datetime.utcnow()  # naive UTC
                     if ex_date > now - timedelta(days=1): 
                         # Simple Estimation
                         amount = div_rate / 4.0 if div_rate else 0.0
                         dividend_info = {
                             "ex_date": ex_date.strftime("%Y-%m-%d"),
                               "amount": amount
                           }
             except Exception:
                 pass
                 
             available_dates = ticker.options
        except:
             return {"error": "Failed to fetch ticker data"}
             
        # Calculate DTE (Calendar Days)
        exp_dt = datetime.strptime(current_exp_date, "%Y-%m-%d")
        dte_days = (exp_dt.date() - datetime.now().date()).days
        
        market_data = {
            "current_price": current_price,
            "one_day_change": one_day_change,
            "days_to_expiry_current": dte_days
        }
        
        # Get AI Signals
        if self.signal_service:
            # We pass empty data so it fetches inside, or we could pass price data if we had it
            signal_data = self.signal_service.get_roll_vs_hold_advice(symbol, {}, None)
        else:
            signal_data = {}
             
        # Filter Dates: Must be AFTER current_exp_date
        try:
            curr_exp_dt = datetime.strptime(current_exp_date, "%Y-%m-%d")
        except ValueError:
             return {"error": "Invalid date format"}
             
        future_dates = [d for d in available_dates if datetime.strptime(d, "%Y-%m-%d") > curr_exp_dt]
        
        # Limit to next 4 expirations to save time/bandwidth
        future_dates = future_dates[:4]
        
        # 1. Estimate Cost to Close (Old Option)
        cost_to_close = 0.0
        try:
            old_chain = ticker.option_chain(current_exp_date)
            old_df = old_chain.calls if position_type == "call" else old_chain.puts
            row = old_df[old_df['strike'] == current_strike]
            if not row.empty:
                cost_to_close = row.iloc[0]['ask'] or row.iloc[0]['lastPrice']
            else:
                 cost_to_close = 0 # Assume 0 if can't find? Bad.
        except Exception as e:
             logging.error(f"Error fetching old chain: {e}")
             
        rolls = []
        
        if not current_pos_context:
            current_pos_context = {"strike": current_strike, "average_cost": 0}

        # RESET PROTOCOL Check
        # If Deep ITM and Bearish/Reversal -> Suggest Closing (BTC)
        # Deep ITM: Price > Strike * 1.05 (for Call)
        # Bearish: Prob Down > 60%
        if current_price > current_strike * 1.05 and signal_data.get('prob_down', 0) > 0.6:
            # Suggest BTC as a special "Roll" item
            rolls.append({
                "expiration": "IMMEDIATE",
                "strike": current_strike,
                "bid": 0,
                "cost_to_close": cost_to_close,
                "net_credit": -cost_to_close,
                "roll_type": "CLOSE POSITION",
                "days_extended": 0,
                "score": 95, # Very High Priority
                "reasons": ["Reset Protocol: Deep ITM + Bearish", "Protect Capital"],
                "total_yield_pct": 0,
                "static_yield_pct": 0,
                "up_return_pct": 0,
                "delta": 1.0, 
                "theta": 0,
                "time_to_expiry_years": 0
            })

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
                    # Use current UTC time vs expiry time (approx 16:00)
                    now = datetime.utcnow()
                    diff = exp_dt - now
                    # Ensure positive
                    days = max(diff.days, 0)
                    years = max(days, 1) / 365.0 # At least 1 day
                    
                    candidates['time_to_expiry_years'] = years
                    
                    # 3. Calculate
                    candidates = GreeksCalculator.calculate_dataframe(candidates, current_price)
                
                for index, row in candidates.iterrows():
                    new_strike = row['strike']
                    premium = row['bid'] or row['lastPrice']
                    if premium == 0: continue
                    
                    net_credit = premium - cost_to_close
                    
                    # Looser Filter: Allow debits if it's a "Rescue" (Roll Up)
                    if net_credit > -0.10: 
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
                             "theta": float(row.get('theta', 0)),
                             "time_to_expiry_years": float(row.get('time_to_expiry_years', 0))
                         }
                         
                         # Yield Calcs
                         up_return_pct = 0
                         static_yield_pct = 0
                         total_yield_pct = 0
                         
                         if current_price > 0:
                             # UP Return: (New Strike - Price) / Price
                             # Assuming we get assigned at Strike
                             assigned_val = new_strike - current_price if new_strike > current_price else 0
                             up_return_pct = (assigned_val / current_price) * 100
                              
                             # Static Yield (Credit / Price)
                             static_yield_pct = (net_credit / current_price) * 100
                              
                             # Total Yield (Assigned)
                             total_yield_pct = up_return_pct + static_yield_pct
                              
                             roll_item["up_return_pct"] = round(up_return_pct, 2)
                             roll_item["static_yield_pct"] = round(static_yield_pct, 2)
                             roll_item["total_yield_pct"] = round(total_yield_pct, 2)
 
                         # CALCULATE SCORE
                         score, reasons = self.score_roll(roll_item, current_pos_context, market_data, dividend_info, signal_data)
                         roll_item["score"] = score
                         roll_item["reasons"] = reasons
                         
                         rolls.append(roll_item)
            except Exception as e:
                logging.error(f"Error processing chain for {d}: {e}")
                continue
                
        # Sort by Score descending (Priority)
        rolls.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        # Return Top 10
        rolls = rolls[:10]
        
        return {
            "symbol": symbol,
            "current_price": current_price,
            "one_day_change": round(one_day_change, 2),
            "cost_to_close": cost_to_close,
            "rolls": rolls,
            "signal_analysis": signal_data
        }
