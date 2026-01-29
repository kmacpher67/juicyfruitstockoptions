from collections import defaultdict

class OptionsAnalyzer:
    def __init__(self, holdings, market_data=None):
        """
        Initialize with a list of holding dicts and optional market data.
        market_data: dict {symbol: StockRecord_dict}
        """
        self.holdings = holdings
        self.market_data = market_data or {}
        self.grouped = self._group_by_underlying()

    def _group_by_underlying(self):
        grouped = defaultdict(lambda: {"shares": 0, "short_calls": 0, "options": []})
        
        for h in self.holdings:
            # Fallback for underlying if not present
            und = h.get("underlying_symbol") or h.get("underlying") or h.get("symbol")
            sec_type = h.get("asset_class") or h.get("sec_type")
            qty = float(h.get("quantity", 0))
            
            # Aggregate Shares
            if sec_type == "STK":
                grouped[und]["shares"] += qty
                
            # Aggregate Options
            elif sec_type == "OPT":
                grouped[und]["options"].append(h)
                sym = h.get("symbol", "")
                
                # Check if it's a Call (Simple check: 'C' in symbol)
                if qty < 0 and "C" in sym.split(" ")[-1]: 
                    multiplier = float(h.get("multiplier", 100))
                    contracts = abs(qty)
                    grouped[und]["short_calls"] += (contracts * multiplier)
                    
        return grouped

    def get_market_metrics(self, symbol):
        """Extract relevant metrics from market data."""
        data = self.market_data.get(symbol, {})
        
        # Parse 1D Change "1.25%" -> 1.25
        chg_str = data.get("1D % Change", "0").replace("%", "").replace("+", "")
        try:
            one_day = float(chg_str)
        except:
            one_day = 0.0
            
        return {
            "price": float(data.get("Current Price", 0) or 0),
            "one_day": one_day,
            "tsmom": float(data.get("TSMOM_60", 0) or 0),
            "skew": float(data.get("Call/Put Skew", 0) or 0)
        }

    def calculate_strength(self, metrics):
        """
        Calculate Opportunity Strength (0-100).
        User Rule: Longer time (Trend) is stronger than short term.
        """
        score = 0
        
        # 1. Long Term Trend (TSMOM) - Weight 40
        if metrics["tsmom"] > 0:
            score += 40
            
        # 2. Short Term Momentum (1D) - Weight 30
        if metrics["one_day"] > 0:
            score += 30
        elif metrics["one_day"] > 2.0: # Strong pop
            score += 10
            
        # 3. Volatility Premium (Skew) - Weight 30
        # Skew > 1.0 implies Calls are expensive (good to sell)
        if metrics["skew"] > 1.0:
            score += 30
        elif metrics["skew"] > 0.5:
            score += 15
            
        return min(score, 100)

    def analyze_coverage(self):
        """Identify stocks that are owned but not fully covered by short calls."""
        alerts = []
        for und, data in self.grouped.items():
            shares = data["shares"]
            covered = data["short_calls"]
            
            if shares > 0 and covered < shares:
                # Potential Covered Call Opportunity
                free = shares - covered
                if free >= 100: # Only alert if at least one contract can be sold
                    metrics = self.get_market_metrics(und)
                    
                    # USER RULE: Only if Daily Trend is UP
                    if metrics["one_day"] <= 0:
                        continue
                        
                    score = self.calculate_strength(metrics)
                    
                    alerts.append({
                        "type": "UNCOVERED_SHARES",
                        "symbol": und,
                        "shares_owned": shares,
                        "shares_free": free,
                        "score": score,
                        "message": f"{und}: Gap of {free} shares. Trend is UP (+{metrics['one_day']}%) - Strong Sell Opp (Score: {score})."
                    })
        return alerts

    def analyze_naked(self):
        """Identify SHORT CALLS that exceed share ownership (Naked)."""
        alerts = []
        for und, data in self.grouped.items():
            shares = data["shares"]
            covered = data["short_calls"]
            
            if covered > shares:
                # Naked Call Warning
                exposed = covered - shares
                alerts.append({
                    "type": "NAKED_OPTION",
                    "symbol": und,
                    "exposed_shares": exposed,
                    "score": 100, # Critical
                    "message": f"CRITICAL: {und} has naked calls covering {exposed} shares!"
                })
        return alerts

    def analyze_profit(self, threshold_pct=0.50):
        """Identify SHORT options with high unrealized profit."""
        alerts = []
        for h in self.holdings:
            sec_type = h.get("asset_class") or h.get("sec_type")
            qty = float(h.get("quantity", 0))
            
            if sec_type == "OPT" and qty < 0:
                # Short Option
                cost = float(h.get("cost_basis", 0)) # Usually negative for credit
                mkt_val = float(h.get("market_value", 0)) # Negative liability
                
                # Check to avoid division by zero
                if abs(cost) < 0.01: continue
                
                # PnL logic: 
                # Sold for $500 (Cost -500). Current Value -$50. PnL +450.
                pnl = mkt_val - cost # -50 - (-500) = 450
                profit_pct = pnl / abs(cost) # 450 / 500 = 0.90
                
                if profit_pct >= threshold_pct:
                    alerts.append({
                        "type": "PROFIT_TAKE",
                        "symbol": h.get("symbol"),
                        "profit_pct": profit_pct,
                        "pnl": pnl,
                        "score": int(profit_pct * 100), # Score scales with profit
                        "message": f"Take Profit: {h.get('symbol')} is up {profit_pct*100:.1f}% ({pnl:+.0f})."
                    })
        return alerts
