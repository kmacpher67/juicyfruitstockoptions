import yfinance as yf
from datetime import datetime, timedelta
import logging

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

    def find_rolls(self, symbol, current_strike, current_exp_date, position_type="call"):
        """
        Find roll opportunities.
        current_exp_date: YYYY-MM-DD
        """
        ticker = yf.Ticker(symbol)
        try:
             current_price = ticker.fast_info['last_price']
             available_dates = ticker.options
        except:
             return {"error": "Failed to fetch ticker data"}
             
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
        
        for d in future_dates:
            try:
                chain = ticker.option_chain(d)
                df = chain.calls if position_type == "call" else chain.puts
                
                # Filter Strikes: 
                # For Covered Calls: Generally want Strike >= Current Strike (Up & Out) or Strike >= Current Price
                # Let's simple filter: Strike >= Current Strike
                
                candidates = df[df['strike'] >= current_strike]
                
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
                         
                         rolls.append({
                             "expiration": d,
                             "strike": new_strike,
                             "bid": premium,
                             "cost_to_close": cost_to_close,
                             "net_credit": round(net_credit, 2),
                             "roll_type": roll_type,
                             "days_extended": days_diff
                         })
            except:
                continue
                
        # Sort by Net Credit descending
        rolls.sort(key=lambda x: x['net_credit'], reverse=True)
        return {
            "symbol": symbol,
            "current_price": current_price,
            "cost_to_close": cost_to_close,
            "rolls": rolls
        }
