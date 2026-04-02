from collections import defaultdict
import re


def _looks_like_short_call(holding):
    sec_type = holding.get("asset_class") or holding.get("secType") or holding.get("sec_type")
    if str(sec_type or "").upper() != "OPT":
        return False

    qty = float(holding.get("quantity", 0) or 0)
    if qty >= 0:
        return False

    right = str(holding.get("right") or "").strip().upper()
    if right == "C":
        return True

    local_symbol = str(holding.get("local_symbol") or holding.get("localSymbol") or "")
    symbol = str(holding.get("symbol") or "")
    return bool(re.search(r"\d{6}C\d+", local_symbol) or re.search(r"\d{6}C\d+", symbol))

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
        grouped = defaultdict(lambda: {"shares": 0, "short_calls": 0, "options": [], "total_cost": 0.0})
        
        for h in self.holdings:
            # Fallback for underlying if not present
            und = h.get("underlying_symbol") or h.get("underlying") or h.get("symbol")
            sec_type = h.get("asset_class") or h.get("secType") or h.get("sec_type")
            qty = float(h.get("quantity", 0))
            
            # Aggregate Shares
            if sec_type == "STK":
                grouped[und]["shares"] += qty
                grouped[und]["total_cost"] += (qty * float(h.get("cost_basis", 0)))
                
            # Aggregate Options
            elif sec_type == "OPT":
                grouped[und]["options"].append(h)
                if _looks_like_short_call(h):
                    multiplier = float(h.get("multiplier", 100))
                    contracts = abs(qty)
                    grouped[und]["short_calls"] += (contracts * multiplier)
                    
        return grouped

    def get_market_metrics(self, symbol):
        """Extract relevant metrics from market data."""
        data = self.market_data.get(symbol, {})
        
        # Parse 1D Change "1.25%" -> 1.25
        val = data.get("1D % Change")
        if val is None:
            val = "0"
        chg_str = str(val).replace("%", "").replace("+", "")
        
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

    def calculate_strength(self, metrics, cost_basis=0):
        """
        Calculate Opportunity Strength (0-100).
        User Rule: Longer time (Trend) is stronger than short term.
        New Rule: Price vs Cost Basis influences score.
        """
        score = 0
        
        # 1. Long Term Trend (TSMOM) - Weight 30
        if metrics["tsmom"] > 0:
            score += 30
            
        # 2. Short Term Momentum (1D) - Weight 20 (plus 10 bonus for strong pop)
        if metrics["one_day"] > 0:
            score += 20
            
        if metrics["one_day"] > 2.0: # Strong pop bonus
            score += 10
            
        # 3. Volatility Premium (Skew) - Weight 20
        # Skew > 1.0 implies Calls are expensive (good to sell)
        if metrics["skew"] > 1.0:
            score += 20
        elif metrics["skew"] > 0.5:
            score += 10

        # 4. Cost Basis Factor - Weight 30
        # Ideally, we want to sell calls ABOVE our basis.
        price = metrics["price"]
        if price > 0 and cost_basis > 0:
            if price >= cost_basis:
                # Winning position: Great for selling calls (Capital Gains buffer)
                score += 30
            else:
                # Underwater: Harder to find good premiums without locking in loss
                # Calculate depth
                diff = (cost_basis - price) / cost_basis
                if diff < 0.05: # <5% down, okay
                    score += 20
                elif diff < 0.10: # <10% down, risky
                    score += 10
                else:
                    # >10% down "Bagholder": Penalty or Zero bonus
                    # User says: "If no juicy options... influence score".
                    # We penalize here.
                    score -= 10 
            
        return max(0, min(score, 100))

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
                        
                    avg_basis = 0
                    if shares > 0:
                         avg_basis = data["total_cost"] / shares
                    
                    score = self.calculate_strength(metrics, cost_basis=avg_basis)
                    
                    alerts.append({
                        "type": "UNCOVERED_SHARES",
                        "symbol": und,
                        "shares_owned": shares,
                        "shares_free": free,
                        "score": score,
                        "message": f"Gap {int(free)} Shares, Trend UP (+{metrics['one_day']}%)"
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
