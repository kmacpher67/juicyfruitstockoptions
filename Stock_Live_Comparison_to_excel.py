import yfinance as yf
import pandas as pd
import time
import datetime

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
    
    records.append({
        "Ticker": t,
        "Current Price": info.get("currentPrice"),
        "Market Cap (T$)": info.get("marketCap") / 1e12 if info.get("marketCap") else None,
        "P/E": info.get("trailingPE"),
        "YoY Price %": f"{yoy:.1f}%",
        "Ex-Div Date": info.get("exDividendDate"),
        "Div Yield": info.get("dividendYield"),
        # Placeholder for analyst targets, option prices:
        "Analyst 1-yr Target": None,
        "1-yr 6% OTM PUT Price": None,
        "6-mo Call Yield": None,
        "3-mo Call Yield": None,
        "1-yr Call Yield": None,
    })

df = pd.DataFrame(records)
date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"AI_Stock_Live_Comparison_{date_str}.xlsx"
df.to_excel(filename, index=False)
print(f"Spreadsheet generated: {filename}")
