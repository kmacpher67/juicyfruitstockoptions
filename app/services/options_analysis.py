from collections import defaultdict

class OptionsAnalyzer:
    def __init__(self, holdings):
        """
        Initialize with a list of holding dicts.
        Expected keys: symbol, sec_type, quantity, underlying, multiplier
        """
        self.holdings = holdings
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
                
                # Check if it's a Call (Simple check: 'C' in symbol typically, or explicit field)
                # IBKR Symbol format often: "AAPL 250117C00200000"
                # If quantity < 0, it's a Short position.
                if qty < 0 and "C" in sym.split(" ")[-1]: 
                    # Assuming standard OCC symbol or similar. 
                    # If strictly adhering to IBKR report, we might need robust parsing.
                    # For now, let's assume standard format or explicit field if available.
                    # The test mock uses "AAPL 250117C..."
                    multiplier = float(h.get("multiplier", 100))
                    contracts = abs(qty)
                    
                    # Logic: total shares covered = contracts * multiplier
                    grouped[und]["short_calls"] += (contracts * multiplier)
                    
        return grouped

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
                    alerts.append({
                        "type": "UNCOVERED_SHARES",
                        "symbol": und,
                        "shares_owned": shares,
                        "shares_covered": covered,
                        "shares_free": free,
                        "message": f"{und}: {free} shares uncovered. Consider selling calls."
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
                    "short_contracts": covered / 100, # Assuming 100 mult
                    "shares_owned": shares,
                    "exposed_shares": exposed,
                    "message": f"CRITICAL: {und} has naked calls covering {exposed} shares!"
                })
        return alerts

    def analyze_profit(self, threshold_pct=0.50):
        """Identify SHORT options with high unrealized profit (decay)."""
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
                        "message": f"Take Profit: {h.get('symbol')} is up {profit_pct*100:.1f}% ({pnl:+.0f})."
                    })
        return alerts
