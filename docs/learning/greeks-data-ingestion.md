# Greeks Data Ingestion & Calculation

## Problem Statement
The "Smart Roll" strategy requires advanced Option Greeks—specifically **Delta**, **Gamma**, and **Theta**—to assess risk (Gamma risk) and neutrality (Delta neutral). However, our current data provider, `yfinance`, does not provide these metrics directly in its option chain data. It only provides **Implied Volatility (IV)**.

## Etymology & First Principles
- **Delta ($\Delta$)**: Rate of change of option price with respect to the underlying assets price. Speed.
- **Gamma ($\Gamma$)**: Rate of change of Delta. Acceleration. High Gamma means Delta changes rapidly, increasing risk.
- **Theta ($\Theta$)**: Time decay. How much value the option loses per day.

To "get" this data without paying for expensive feeds (like IBKR real-time streams which require a complex TWS Gateway setup), we can derive it from the **Black-Scholes-Merton** model using the data we *do* have.

## Proposed Solution: Calculation via `py_vollib`

Since `yfinance` gives us the **Market Price** (or Bid/Ask) and **Implied Volatility**, we have all the variables needed to solve the Black-Scholes equation for the Greeks.

### Required Inputs
We need the following 5 variables for each option contract:
1.  **S (Underlying Price)**: Available via `yf.Ticker(symbol).fast_info['last_price']`.
2.  **K (Strike Price)**: Available in option chain (`strike`).
3.  **t (Time to Expiration)**: Calculated as `(ExpirationDate - CurrentDate) / 365.0`.
4.  **r (Risk-Free Interest Rate)**: Can be fetched via `^TNX` (10-Year Treasury Yield) or hardcoded to a conservative estimate (e.g., 4.5% or 0.045).
5.  **$\sigma$ (Sigma / Volatility)**: Available in option chain (`impliedVolatility`).

### Library Recommendation
We should use **`py_vollib`** (or its faster cousin **`py_vollib_vectorized`**) to perform these calculations robustly. It is a pure Python implementation of existing standard libraries.

#### Implementation Example
```python
# pip install py_vollib_vectorized

import numpy as np
from py_vollib_vectorized import vectorized_implied_volatility, get_all_greeks

def calculate_greeks(dataframe, underlying_price, risk_free_rate=0.045):
    """
    Enriches a yfinance option chain DataFrame with Greeks.
    """
    # Calculate Time to Expiration (t) in Years
    # Assuming 'expirationDate' is available or calculated from contract metadata
    
    # Example using py_vollib_vectorized for batch processing
    # flags: 'c' for call, 'p' for put
    
    greeks = get_all_greeks(
        flag=dataframe['type'], # 'c' or 'p'
        S=underlying_price,
        K=dataframe['strike'],
        t=dataframe['time_to_expiry_years'],
        r=risk_free_rate,
        sigma=dataframe['impliedVolatility'],
        q=0 # Dividend yield (can ignore for short term or fetch from yf.info['dividendYield'])
    )
    
    dataframe['delta'] = greeks['delta']
    dataframe['gamma'] = greeks['gamma']
    dataframe['theta'] = greeks['theta'] # Note: Returns annualized theta. Divide by 365 for daily.
    
    return dataframe
```

## Integration Plan

### 1. New Dependencies
Add `py_vollib_vectorized` (or `py_vollib` + `numpy`) to `requirements.txt`.

### 2. Service Layer Modification (`RollService`)
Update `RollService.get_option_chain_data` or `find_rolls` to:
1.  Retrieve the raw chain from `yfinance`.
2.  Calculate `time_to_expiry` for each row.
3.  Pass the dataframe to a new `GreekCalculator` utility.
4.  Return the enriched structure.

### 3. Data Model Updates
If we intend to store these "Juicy Opportunities," we should update our Mongo models (or `TradeRecord` if looking at history) to include fields for `delta`, `gamma`, and `theta`.

#### Example Model (Pydantic)
```python
class OptionGreeks(BaseModel):
    delta: float
    gamma: float
    theta: float
    iv: float

class OptionContract(BaseModel):
    symbol: str
    strike: float
    expiration: datetime
    greeks: OptionGreeks
```

## Citations
- **py_vollib**: [http://vollib.org/](http://vollib.org/)
- **Black-Scholes Model**: [Investopedia](https://www.investopedia.com/terms/b/blackscholes.asp)
- **yfinance**: [Ran Aroussi](https://github.com/ranaroussi/yfinance)
