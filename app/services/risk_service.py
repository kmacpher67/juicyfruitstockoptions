class RiskService:
    """
    Evaluates tickers against 'Bad Trade Heuristics' to warn the user.
    """
    
    @staticmethod
    def analyze_risk(data: dict):
        warnings = []
        
        # 1. Impatience Check (RSI)
        rsi = data.get("RSI_14")
        if rsi is not None and rsi > 75:
            warnings.append({
                "type": "Impatience",
                "message": f"RSI is {rsi} (Overbought). Avoid Long Calls. Wait for pullback.",
                "level": "warning"
            })
            
        # 2. Trend Extension Check (Price vs EMA + 3*ATR)
        price = data.get("Current Price")
        ema = data.get("EMA_20")
        atr = data.get("ATR_14")
        
        if price and ema and atr:
            upper_band = ema + (3 * atr)
            if price > upper_band:
                dist = round(((price - upper_band) / upper_band) * 100, 1)
                warnings.append({
                    "type": "Trend Extension",
                    "message": f"Price is extended {dist}% above 3xATR band. Reversion risk high.",
                    "level": "danger"
                })
                
        # 3. Liquidity Check (Spread)
        # Using "Option Spread Pct" if available (calculated upstream)
        spread_pct = data.get("Option Spread Pct")
        if spread_pct is not None and spread_pct > 0.10:
             warnings.append({
                "type": "Liquidity",
                "message": f"Option spreads are wide ({spread_pct*100:.1f}%). Execution risk.",
                "level": "warning"
            })
            
        return warnings
