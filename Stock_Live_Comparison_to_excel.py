import yfinance as yf
import pandas as pd
import time
from datetime import datetime


def closest_expiration(option_dates, target_days):
    """Return the expiration date closest to the desired days out."""
    target = datetime.now() + pd.Timedelta(days=target_days)
    dates = [datetime.strptime(d, "%Y-%m-%d") for d in option_dates]
    if not dates:
        return None
    return min(dates, key=lambda d: abs((d - target).days)).strftime("%Y-%m-%d")


def get_otm_call_yield(sym, current_price, target_days, otm_pct=6):
    """Return the yield and strike for an OTM call near target_days."""
    exp_date = closest_expiration(sym.options, target_days)
    if not exp_date:
        return None, None
    chain = sym.option_chain(exp_date)
    target_strike = current_price * (1 + otm_pct / 100)
    calls = chain.calls
    calls = calls[calls['strike'] >= target_strike]
    if calls.empty:
        return None, None
    call = calls.iloc[0]
    yield_pct = (call['lastPrice'] / current_price) * 100
    return round(yield_pct, 2), call['strike']


def get_otm_put_price(sym, current_price, target_days, otm_pct=6):
    """Return the put price for an OTM put near target_days."""
    exp_date = closest_expiration(sym.options, target_days)
    if not exp_date:
        return None
    chain = sym.option_chain(exp_date)
    target_strike = current_price * (1 - otm_pct / 100)
    puts = chain.puts
    puts = puts[puts['strike'] <= target_strike]
    if puts.empty:
        return None
    put = puts.iloc[-1]
    return put['lastPrice']

#
# retrieves live market cap, price, P/E, and YoY return via yfinance, and builds the spreadsheet automatically:
#

tickers = ["AMD","MSFT","NVDA","META","AMZN","GOOG","AAPL","TSLA","IBM","ORCL", "TEM"]
records = []

for t in tickers:
    sym = yf.Ticker(t)
    print (f"Fetching data for {t}...", sym)
    time.sleep(1)  # Avoid hitting API limits
    info = sym.info
    hist = sym.history(period="1y")
    yoy = (hist['Close'][-1] - hist['Close'][0]) / hist['Close'][0] * 100

    current_price = info.get("regularMarketPrice") or info.get("currentPrice")
    prev_close = (info.get("regularMarketPreviousClose") or
                  info.get("previousClose") or
                  hist['Close'][-2])
    day_change = None
    if current_price and prev_close:
        day_change = (current_price - prev_close) / prev_close * 100

    call3, _ = get_otm_call_yield(sym, current_price, 90)
    call6, strike6 = get_otm_call_yield(sym, current_price, 180)
    call12, _ = get_otm_call_yield(sym, current_price, 365)
    put_price = get_otm_put_price(sym, current_price, 365)
    analyst_target = info.get("targetMeanPrice")

    records.append({
        "Ticker": t,
        "Current Price": current_price,
        "1D % Change": f"{day_change:.2f}%" if day_change is not None else None,
        "Market Cap (T$)": info.get("marketCap") / 1e12 if info.get("marketCap") else None,
        "P/E": info.get("trailingPE"),
        "YoY Price %": f"{yoy:.1f}%",
        "Ex-Div Date": info.get("exDividendDate"),
        "Div Yield": info.get("dividendYield"),
        "Analyst 1-yr Target": analyst_target,
        "1-yr 6% OTM PUT Price": put_price,
        "3-mo Call Yield": call3,
        "6-mo Call Yield": call6,
        "1-yr Call Yield": call12,
        "Example 6-mo Strike": strike6,
    })

df = pd.DataFrame(records)
df.to_excel("AI_Stock_Live_Comparison.xlsx", index=False)
print("Spreadsheet generated: AI_Stock_Live_Comparison.xlsx")
