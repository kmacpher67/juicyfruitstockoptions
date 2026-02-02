import pytest
import pandas as pd
import numpy as np
from app.services.price_action_service import PriceActionService

# Initial Mock Data
@pytest.fixture
def uptrend_df():
    # Create a synthetic uptrend: HH, HL series
    # Pivots at indexes: 2 (Low), 5 (High), 8 (Higher Low), 11 (Higher High)
    # n=2 requires index 11 to checks 12, 13.
    prices = [100, 95, 90, 100, 110, 120, 110, 105, 100, 110, 120, 130, 120, 115, 110]
    dates = pd.date_range(start="2023-01-01", periods=len(prices))
    df = pd.DataFrame({
        "Date": dates,
        "Open": prices,
        "High": [p + 2 for p in prices],
        "Low": [p - 2 for p in prices],
        "Close": prices,
        "Volume": 1000
    })
    return df

def test_find_pivots(uptrend_df):
    service = PriceActionService()
    # Use n=2 for this small dataset to ensure we catch the turns
    pivots = service.find_pivots(uptrend_df, n=2)
    print(f"DEBUG: Found Pivots: {pivots}")
    
    # We expect a Low at index 2 (Price 90)
    # We expect a High at index 5 (Price 120)
    # We expect a Low at index 8 (Price 100)
    # We expect a High at index 11 (Price 130)
    
    # Check identifying indices
    assert any(p["index"] == 2 and p["type"] == "Low" for p in pivots)
    assert any(p["index"] == 5 and p["type"] == "High" for p in pivots)
    assert any(p["index"] == 8 and p["type"] == "Low" for p in pivots)
    assert any(p["index"] == 11 and p["type"] == "High" for p in pivots)

def test_identify_structure(uptrend_df):
    service = PriceActionService()
    pivots = service.find_pivots(uptrend_df, n=2)
    structure = service.identify_structure(pivots)
    
    # Index 8 should be a Higher Low (HL) compared to Index 2
    # Index 11 should be a Higher High (HH) compared to Index 5
    
    hl = next((s for s in structure if s["index"] == 8), None)
    hh = next((s for s in structure if s["index"] == 11), None)
    
    assert hl is not None
    assert hl["label"] == "HL"
    assert hh is not None
    assert hh["label"] == "HH"

def test_detect_bos_body_close():
    # Setup a scenario where price wicks above HH but closes below (No BOS)
    # then closes above (BOS)
    dates = pd.date_range(start="2023-01-01", periods=5)
    df = pd.DataFrame({
        "Date": dates,
        "High":  [100, 105, 110, 112, 115],
        "Close": [ 90,  95, 100, 108, 112], # HH is at 100 initially? No wait.
        "Low":   [ 80,  85,  90,  95, 100],
        "Open":  [ 85,  90,  95, 100, 110]
    })
    
    # Manually define structure for testing
    structure = [{"index": 0, "type": "High", "label": "HH", "value": 100, "date": dates[0]}]
    
    service = PriceActionService()
    events = service.detect_bos(df, structure)
    
    # Depending on logic. If HH is 100 (High or Close? usually High/Low for pivot, Close for break)
    # If Pivot High was 100.
    # Candle 2 High 110, Close 100. (Equal? No break)
    # Candle 3 High 112, Close 108. (Break of 100)
    
    # Let's verify we get a bullish BOS
    assert len(events) > 0
    assert events[0]["type"] == "BOS_BULL"

def test_detect_fvg():
    # Bearish FVG Pattern:
    # 1. Big Down Candle
    # Candle 0: Low 100
    # Candle 1: High 98 (Gap of 2) -> FVG
    # Candle 2: High 90
    dates = pd.date_range(start="2023-01-01", periods=3)
    df = pd.DataFrame({
        "Date": dates,
        "High": [110, 98, 90],
        "Low":  [100, 90, 80],
        "Close":[102, 92, 82],
        "Open": [108, 98, 88]
    })
    
    service = PriceActionService()
    fvgs = service.detect_fvg(df)
    
    # Gap exists between Candle 0 Low (100) and Candle 2 High (90) - Wait, standard FVG definition:
    # Bearish FVG: Candle 1 (middle) gap is between Candle 0 Low and Candle 2 High.
    # Gap: 100 - 90 = 10pts. 
    
    assert len(fvgs) == 1
    assert fvgs[0]["top"] == 100
    assert fvgs[0]["bottom"] == 90
    assert fvgs[0]["type"] == "Bearish"

def test_find_order_blocks():
    # Construct a Bullish OB scenario:
    # 1. Bearish Candle (The OB)
    # 2. Impulsive Move Up causing BOS
    dates = pd.date_range(start="2023-01-01", periods=5)
    df = pd.DataFrame({
        "Date": dates,
        "Open": [100, 98, 100, 110, 120],
        "Close":[ 98, 96, 105, 115, 125], # Candle 1 is Red (98->96). Candle 2 breaks structure?
        "High": [100, 98, 105, 115, 125],
        "Low":  [ 98, 95, 96, 105, 115]
    })
    # Assume prev high was 100. Candle 2 closes at 105 (BOS).
    # Last down candle before move was Candle 1 (Open 98, Close 96, Low 95, High 98).
    
    # Manually pass BOS event
    bos_events = [{"index": 2, "type": "BOS_BULL", "level": 100, "level_index": 0}]
    
    service = PriceActionService()
    obs = service.find_order_blocks(df, bos_events)
    
    assert len(obs) > 0
    assert obs[0]["index"] == 1
    assert obs[0]["type"] == "Bullish"
    assert obs[0]["top"] == 98 # High of OB candle
    assert obs[0]["bottom"] == 95 # Low of OB candle
