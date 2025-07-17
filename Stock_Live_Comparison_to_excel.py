import yfinance as yf
import pandas as pd
import time
from datetime import datetime
from yfinance.exceptions import YFRateLimitError
import requests
import os

POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY')


def closest_expiration(option_dates, target_days):
    """Return the expiration date closest to the desired days out."""
    target = datetime.now() + pd.Timedelta(days=target_days)
    dates = [datetime.strptime(d, "%Y-%m-%d") for d in option_dates]
    if not dates:
        return None
    return min(dates, key=lambda d: abs((d - target).days)).strftime("%Y-%m-%d")


def get_otm_call_yield(chain, current_price, target_days, otm_pct=6):
    """Return the yield and strike for an OTM call near target_days."""
    exp_date = closest_expiration(chain.options, target_days)
    if not exp_date:
        return None, None
    calls = chain.option_chain(exp_date).calls
    target_strike = current_price * (1 + otm_pct / 100)
    calls = calls[calls['strike'] >= target_strike]
    if calls.empty:
        return None, None
    call = calls.iloc[0]
    yield_pct = (call['lastPrice'] / current_price) * 100
    return round(yield_pct, 2), call['strike']


def get_otm_put_price(chain, current_price, target_days, otm_pct=6):
    """Return the put price for an OTM put near target_days."""
    exp_date = closest_expiration(chain.options, target_days)
    if not exp_date:
        return None
    puts = chain.option_chain(exp_date).puts
    target_strike = current_price * (1 - otm_pct / 100)
    puts = puts[puts['strike'] <= target_strike]
    if puts.empty:
        return None
    put = puts.iloc[-1]
    return put['lastPrice']


def get_polygon_data(ticker):
    url = f"https://api.polygon.io/v3/reference/tickers/{ticker}?apiKey={POLYGON_API_KEY}"
    resp = requests.get(url)
    info = resp.json().get('results', {})

    price_url = f"https://api.polygon.io/v2/last/trade/{ticker}?apiKey={POLYGON_API_KEY}"
    price_resp = requests.get(price_url)
    price_data = price_resp.json().get('results', {})
    current_price = price_data.get('price')

    return {
        "Ticker": ticker,
        "Current Price": current_price,
        "Market Cap (T$)": info.get("market_cap") / 1e12 if info.get("market_cap") else None,
        "P/E": info.get("pe_ratio"),
        "YoY Price %": None,
        "Ex-Div Date": info.get("ex_dividend_date"),
        "Div Yield": info.get("dividend_yield"),
        "Analyst 1-yr Target": None,
        "1-yr 6% OTM PUT Price": None,
        "3-mo Call Yield": None,
        "6-mo Call Yield": None,
        "1-yr Call Yield": None,
        "Example 6-mo Strike": None,
        "Error": "Polygon fallback"
    }

#
# retrieves live market cap, price, P/E, and YoY return via yfinance, and builds the spreadsheet automatically:
#

tickers = ["AMD","MSFT","NVDA","META","AMZN","GOOG","AAPL","TSLA","IBM","ORCL", "TEM"]
records = []

# Batch download historical prices for all tickers
hist = yf.download(tickers, period="1y", group_by='ticker', threads=True)
# Batch fetch info for all tickers
tickers_obj = yf.Tickers(" ".join(tickers))

for t in tickers:
    tries = 0
    success = False
    while tries < 3 and not success:
        try:
            time.sleep(1 + tries * 2)
            info = tickers_obj.tickers[t].info
            ticker_hist = hist[t] if t in hist else None
            if ticker_hist is not None and not ticker_hist.empty:
                yoy = (ticker_hist['Close'][-1] - ticker_hist['Close'][0]) / ticker_hist['Close'][0] * 100
                prev_close = ticker_hist['Close'][-2]
            else:
                yoy = None
                prev_close = None

            current_price = info.get("regularMarketPrice") or info.get("currentPrice")
            day_change = None
            if current_price and prev_close:
                day_change = (current_price - prev_close) / prev_close * 100

            chain = tickers_obj.tickers[t]
            call3, _ = get_otm_call_yield(chain, current_price, 90)
            call6, strike6 = get_otm_call_yield(chain, current_price, 180)
            call12, _ = get_otm_call_yield(chain, current_price, 365)
            put_price = get_otm_put_price(chain, current_price, 365)
            analyst_target = info.get("targetMeanPrice")

            records.append({
                "Ticker": t,
                "Current Price": current_price,
                "1D % Change": f"{day_change:.2f}%" if day_change is not None else None,
                "Market Cap (T$)": info.get("marketCap") / 1e12 if info.get("marketCap") else None,
                "P/E": info.get("trailingPE"),
                "YoY Price %": f"{yoy:.1f}%" if yoy is not None else None,
                "Ex-Div Date": info.get("exDividendDate"),
                "Div Yield": info.get("dividendYield"),
                "Analyst 1-yr Target": analyst_target,
                "1-yr 6% OTM PUT Price": put_price,
                "3-mo Call Yield": call3,
                "6-mo Call Yield": call6,
                "1-yr Call Yield": call12,
                "Example 6-mo Strike": strike6,
                "Error": None
            })
            success = True
        except YFRateLimitError as e:
            print(f"Rate limit hit for {t}, retrying...")
            tries += 1
            if hasattr(e, 'response') and getattr(e.response, 'status_code', None) == 409:
                print(f"YFinance 409 error for {t}, using Polygon API fallback.")
                polygon_data = get_polygon_data(t)
                records.append(polygon_data)
                success = True
        except Exception as e:
            print(f"Error fetching data for {t}: {e}")
            records.append({
                "Ticker": t,
                "Current Price": None,
                "1D % Change": None,
                "Market Cap (T$)": None,
                "P/E": None,
                "YoY Price %": None,
                "Ex-Div Date": None,
                "Div Yield": None,
                "Analyst 1-yr Target": None,
                "1-yr 6% OTM PUT Price": None,
                "3-mo Call Yield": None,
                "6-mo Call Yield": None,
                "1-yr Call Yield": None,
                "Example 6-mo Strike": None,
                "Error": str(e)
            })
            success = True

    if not success:
        print(f"Skipping {t} after 3 rate limit retries.")
        records.append({
            "Ticker": t,
            "Current Price": None,
            "1D % Change": None,
            "Market Cap (T$)": None,
            "P/E": None,
            "YoY Price %": None,
            "Ex-Div Date": None,
            "Div Yield": None,
            "Analyst 1-yr Target": None,
            "1-yr 6% OTM PUT Price": None,
            "3-mo Call Yield": None,
            "6-mo Call Yield": None,
            "1-yr Call Yield": None,
            "Example 6-mo Strike": None,
            "Error": "Rate limit exceeded"
        })

df = pd.DataFrame(records)
date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"AI_Stock_Live_Comparison_{date_str}.xlsx"
df.to_excel(filename, index=False)
print(f"Spreadsheet generated: {filename}")
