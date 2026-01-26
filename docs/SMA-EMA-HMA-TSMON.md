# Moving Average & Momentum Strategy Guide

## 1. Overview
This document outlines a hybrid trading strategy that combines **Trend Following (TSMOM)** with **Value/Reversion (Moving Averages)**. The goal is to filter out market noise, avoid "falling knife" scenarios, and identify high-probability entry points.

---

## 2. Core Metrics & Definitions

### A. The "Trend" Metric: TSMOM (Time Series Momentum)
**Definition:** Calculates the absolute return over a specific lookback period to determine the dominant market direction.
* **Formula:** `Momentum = (Price_Today / Price_N_Days_Ago) - 1`
* **Lookbacks:**
    * **30-Day:** Fast, aggressive, captures breakouts early but prone to "whipsaws."
    * **60-Day (Recommended):** Aligns with quarterly earnings cycles; statistically more robust for filtering noise.

### B. The "Value" Metrics: Moving Averages
**Important:** Use trading days (252/year), not calendar days.
* **200-Day SMA:** The institutional baseline for long-term trend.
* **20-Day EMA (Exponential):** Short-term trend filter that reacts faster than SMA.
* **Hull Moving Average (HMA):** A low-lag average used for precise entry/exit triggers.

---

## 3. Strategy Logic

### Step 1: Filter (Direction)
Use **TSMOM (60-Day)** to decide if you are allowed to be in the market.
* **If Momentum > +1%:** The trend is UP. Look for Buy signals.
* **If Momentum < -1%:** The trend is DOWN. Cash or Short only.
* **If -1% to +1%:** Market is flat/dead. **Do Nothing.**

### Step 2: Trigger (Entry)
Once the trend is confirmed UP, wait for a "Value" entry to improve risk/reward.
* **Conservative:** Buy when price touches the **EMA 20** and bounces.
* **Aggressive:** Buy when price crosses *above* the **HMA**.

### Step 3: Thresholds & Color Coding
Use these break points to color-code your Python/Excel dashboard:

| Indicator | **Green (Buy/Bullish)** | **Red (Sell/Bearish)** | **Blank (Neutral/Hold)** |
| :--- | :--- | :--- | :--- |
| **TSMOM** | Return > **+1%** | Return < **-1%** | Return is **-1% to +1%** |
| **EMA Cross** | Price > EMA by **0.5%** | Price < EMA by **0.5%** | Price within **0.5%** of EMA |
| **HMA Cross** | Price > HMA | Price < HMA | *(N/A - HMA is the trigger)* |

---

## 4. Python Implementation

### Dependencies
Requires `yfinance`, `pandas`, and `numpy`.

### A. HMA & EMA Code Snippet
```python
import yfinance as yf
import pandas as pd
import numpy as np

def weighted_moving_average(series, window):
    weights = np.arange(1, window + 1)
    return series.rolling(window).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def hull_moving_average(series, window):
    wma_half = weighted_moving_average(series, window // 2)
    wma_full = weighted_moving_average(series, window)
    raw_hma = (2 * wma_half) - wma_full
    lag = int(np.sqrt(window))
    return weighted_moving_average(raw_hma, lag)

# Fetch Data
symbol = "NVDA"
df = yf.download(symbol, start="2023-01-01", end="2024-06-01")

# Calculate Indicators
df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
df['HMA_20'] = hull_moving_average(df['Close'], 20)

# Calculate TSMOM (60-Day)
lookback = 60
df['TSMOM_60'] = df['Close'] / df['Close'].shift(lookback) - 1


## 5. Risk Management Limits
The "Falling Knife" Rule: Never buy purely because price is 2% below an average. Only buy if TSMOM is positive OR price has crossed back above the HMA.

The "Whipsaw" Protection: The "Blank/Neutral" zones (e.g., +/- 1% on TSMOM) prevent over-trading in sideways markets.