import pandas as pd
import numpy as np

class PriceActionService:
    @staticmethod
    def analyze_ticker(df):
        """
        Main entry point to analyze a ticker dataframe.
        Returns a dict with structure, bos, fvg, obs.
        """
        service = PriceActionService()
        pivots = service.find_pivots(df)
        structure = service.identify_structure(pivots)
        bos_events = service.detect_bos(df, structure)
        fvgs = service.detect_fvg(df)
        obs = service.find_order_blocks(df, bos_events)
        
        # Determine Current Trend based on last structure
        trend = "Neutral"
        if structure:
            last = structure[-1]["label"]
            if last in ["HH", "HL"]:
                trend = "Bullish"
            elif last in ["LH", "LL"]:
                trend = "Bearish"
                
        return {
            "trend": trend,
            "structure": structure,
            "bos_events": bos_events,
            "fvgs": fvgs,
            "order_blocks": obs
        }

    def find_pivots(self, df, n=5):
        """
        Identify Swing Highs and Lows using a rolling window of n candles left/right.
        A candle i is a High if High[i] > High[i-n...i-1] and High[i] > High[i+1...i+n].
        """
        pivots = []
        if df is None or df.empty or len(df) < 2 * n + 1:
            return pivots

        # Convert to numpy for speed
        highs = df['High'].values
        lows = df['Low'].values
        dates = df['Date'].values
        
        for i in range(n, len(df) - n):
            # Check Swing High
            if all(highs[i] > highs[i - k] for k in range(1, n + 1)) and \
               all(highs[i] > highs[i + k] for k in range(1, n + 1)):
                pivots.append({
                    "index": i,
                    "type": "High",
                    "value": highs[i],
                    "date": dates[i]
                })
            
            # Check Swing Low
            if all(lows[i] < lows[i - k] for k in range(1, n + 1)) and \
               all(lows[i] < lows[i + k] for k in range(1, n + 1)):
                pivots.append({
                    "index": i,
                    "type": "Low",
                    "value": lows[i],
                    "date": dates[i]
                })

        return pivots

    def identify_structure(self, pivots):
        """
        Label pivots as HH, HL, LH, LL.
        We iterate through pivots of the SAME TYPE (Highs vs Highs, Lows vs Lows).
        """
        if not pivots:
            return []
            
        structure = []
        last_high = None
        last_low = None
        
        for p in pivots:
            label = None
            if p["type"] == "High":
                if last_high:
                    if p["value"] > last_high["value"]:
                        label = "HH"
                    else:
                        label = "LH"
                else:
                    label = "H" # Initial
                last_high = p
            elif p["type"] == "Low":
                if last_low:
                    if p["value"] > last_low["value"]:
                        label = "HL"
                    else:
                        label = "LL"
                else:
                    label = "L" # Initial
                last_low = p
            
            # Create a copy with label
            s_point = p.copy()
            s_point["label"] = label
            structure.append(s_point)
            
        return structure

    def detect_bos(self, df, structure):
        """
        Identify Break of Structure events (Body Close).
        A Bullish BOS occurs when a candle CLOSES above the most recent HH or LH?
        Usually BOS breaks the most recent Swing High in an uptrend or Swing Low in a downtrend.
        For simplicity: A close above the last Swing High = Bullish BOS.
        """
        events = []
        if df is None or df.empty or not structure:
            return events

        # Sort structure by index
        structure_sorted = sorted(structure, key=lambda x: x["index"])
        
        # We need to scan from the last structural point forward
        closes = df['Close'].values
        dates = df['Date'].values
        
        last_high = None
        last_low = None
        
        # Replay the sequence to find breaks
        # We'll just look for breaks OF the structure points AFTER they occurred.
        
        # Optimization: We only care about active breaks. 
        # But for the graph, we might want historical.
        # Let's just iterate through candles and track "active" swing points.
        
        # Map structure by index for easy lookup
        struct_map = {s["index"]: s for s in structure}
        
        for i in range(len(df)):
            # Update active swings if we passed one
            if i in struct_map:
                s = struct_map[i]
                if s["type"] == "High":
                    last_high = s
                elif s["type"] == "Low":
                    last_low = s
            
            # Check for Break of Last High (Bullish BOS)
            if last_high and i > last_high["index"]:
                if closes[i] > last_high["value"]:
                    # Check if we already recorded a break for this specific high
                    # We only want the FIRST break
                    already_broken = any(e["level_index"] == last_high["index"] for e in events)
                    if not already_broken:
                        events.append({
                            "index": i,
                            "type": "BOS_BULL",
                            "level": last_high["value"],
                            "level_index": last_high["index"],
                            "date": dates[i]
                        })
                        # Ideally we 'invalidate' this high as a resistance level now, 
                        # but trend continues.
            
            # Check for Break of Last Low (Bearish BOS)
            if last_low and i > last_low["index"]:
                if closes[i] < last_low["value"]:
                    already_broken = any(e["level_index"] == last_low["index"] for e in events)
                    if not already_broken:
                        events.append({
                            "index": i,
                            "type": "BOS_BEAR",
                            "level": last_low["value"],
                            "level_index": last_low["index"],
                            "date": dates[i]
                        })

        return events

    def detect_fvg(self, df):
        """
        Identify Fair Value Gaps.
        Bullish FVG: Low[i+2] > High[i]. Gap is (High[i], Low[i+2]).
        Bearish FVG: High[i+2] < Low[i]. Gap is (High[i+2], Low[i]).
        """
        fvgs = []
        if df is None or len(df) < 3:
            return fvgs

        highs = df['High'].values
        lows = df['Low'].values
        dates = df['Date'].values

        for i in range(len(df) - 2):
            # Bullish FVG
            # Candle 0 High vs Candle 2 Low
            if lows[i+2] > highs[i]:
                fvgs.append({
                    "index": i+1, # The FVG is in the middle candle
                    "type": "Bullish",
                    "top": lows[i+2],
                    "bottom": highs[i],
                    "date": dates[i+1]
                })
            
            # Bearish FVG
            # Candle 0 Low vs Candle 2 High
            if highs[i+2] < lows[i]:
                fvgs.append({
                    "index": i+1,
                    "type": "Bearish",
                    "top": lows[i],
                    "bottom": highs[i+2], # Fixed: Bottom of gap is the high of candle 2
                    # Wait. Gap is between Low[i] and High[i+2].
                    # Low[i] is higher (100). High[i+2] is lower (90).
                    # Gap is 90 to 100. Top=100, Bottom=90. Correct.
                    "date": dates[i+1]
                })
                
        return fvgs

    def find_order_blocks(self, df, bos_events):
        """
        Find Order Blocks associated with BOS events.
        Bullish BOS -> Look for last Bearish candle (Close < Open) before the move started?
        Or simply the candle at the Swing Low that started the move?
        Usually: The last down candle BEFORE the impulsive move that broke structure.
        
        Algorithm:
        For each BOS event:
          1. Look backwards from the BOS index to the 'level_index' (the Swing High/Low).
          2. Or look backwards from BOS index until we find the lowest point (for Bullish) 
             between BOS and the previous structure break?
             Actually, OB is usually near the Swing extremum. 
          3. Let's look for the Swing Point (level_index) and find the OB *around* there.
          But strictly, OB is the candle *before* the expansion.
          
        Simplified V1:
        Take the Swing Low/High responsible for the break.
        The OB is the candle at (or adjacent to) that Swing Low/High.
        """
        obs = []
        if not bos_events:
            return obs
            
        opens = df['Open'].values
        closes = df['Close'].values
        highs = df['High'].values
        lows = df['Low'].values
        dates = df['Date'].values
        
        for bos in bos_events:
            if bos["type"] == "BOS_BULL":
                # Look back from BOS index to find the origin of the move.
                # The 'level_index' is the High that was broken. 
                # The move started AFTER a Swing Low.
                # Use a heuristic: Find the lowest low between [level_index] and [bos_index].
                # Actually, the move that broke the high started from a Low.
                
                # Let's search backwards from BOS index for the lowest point.
                # Limit search to 50 candles?
                search_limit = bos["index"] - 50 if bos["index"] > 50 else 0
                
                # Wait, we need the range between "Previous High" and "BOS".
                # The "Origin" is the lowest point in that range.
                # BUT, technically the OB is the down candle before that low, or the down candle AT that low.
                
                # Heuristic: Scan backwards from BOS index to find the Lowest Low.
                # Stop if we hit the 'level_index' (the previous high).
                start_search = max(0, bos["level_index"])
                end_search = bos["index"]
                
                if end_search <= start_search:
                     continue

                # Find index of min low in this range
                segment_lows = lows[start_search:end_search]
                if len(segment_lows) == 0: continue
                
                min_low_idx_rel = np.argmin(segment_lows)
                min_low_idx = start_search + min_low_idx_rel
                
                # OB is this candle (if bearish) or the one before it?
                # Standard ICT: Last down candle before the up move.
                # If the bottom candle is Green, maybe the one before it was Red?
                # Let's check min_low_idx and 1-2 candles before.
                
                candidate_idx = min_low_idx
                # Check up to 3 candles backwards for a Red candle
                found = False
                for k in range(3):
                    idx = min_low_idx - k
                    if idx < 0: break
                    if closes[idx] < opens[idx]: # Red Candle
                        candidate_idx = idx
                        found = True
                        break
                
                # Even if green, use the pivot low candle as the OB base for now.
                obs.append({
                    "index": candidate_idx,
                    "type": "Bullish",
                    "top": highs[candidate_idx],
                    "bottom": lows[candidate_idx],
                    "date": dates[candidate_idx],
                    "associated_bos_index": bos["index"]
                })

            elif bos["type"] == "BOS_BEAR":
                # Look back for Highest High between level_index and BOS index
                start_search = max(0, bos["level_index"])
                end_search = bos["index"]
                
                if end_search <= start_search: continue
                
                segment_highs = highs[start_search:end_search]
                if len(segment_highs) == 0: continue
                
                max_high_idx_rel = np.argmax(segment_highs)
                max_high_idx = start_search + max_high_idx_rel
                
                # Look for last Up candle (Green)
                candidate_idx = max_high_idx
                for k in range(3):
                    idx = max_high_idx - k
                    if idx < 0: break
                    if closes[idx] > opens[idx]: # Green Candle
                        candidate_idx = idx
                        break
                
                obs.append({
                    "index": candidate_idx,
                    "type": "Bearish",
                    "top": highs[candidate_idx],
                    "bottom": lows[candidate_idx],
                    "date": dates[candidate_idx],
                    "associated_bos_index": bos["index"]
                })
        
        return obs
