import requests
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import os
import openpyxl
from openpyxl.styles import Font, Alignment
import boto3
from io import StringIO

POLYGON_API_KEY = os.environ.get('POLYGON_API_KEY')
POLYGON_S3_KEY = os.environ.get('POLYGON_S3_KEY')
POLYGON_S3_SECRET = os.environ.get('POLYGON_S3_SECRET')


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


def get_polygon_s3_daily_prices(ticker, date_from="2023-01-01", date_to=None):
    """
    Download daily prices for a ticker from Polygon S3 flat file API using boto3.
    Returns a DataFrame or None if not available.
    """
    bucket = "flatfiles"
    object_key = f"stocks/daily/{ticker.upper()}.csv"
    print (POLYGON_S3_KEY, POLYGON_S3_SECRET)
    try:

        session = boto3.Session(
            aws_access_key_id='cd042cd4-b524-4c42-b31d-23d7f5f9d0ba',
          aws_secret_access_key='enuk99JbTkgm6jzhNmwJ9gnzdBWAI0Pq',
        )
        s3 = boto3.client(
            "s3",
            endpoint_url='https://files.polygon.io',
            aws_access_key_id=POLYGON_S3_KEY,
            aws_secret_access_key=POLYGON_S3_SECRET,
            config=Config(signature_version='s3v4'),
            region_name="us-east-1"
        )
        obj = s3.get_object(Bucket=bucket, Key=object_key)
        df = pd.read_csv(StringIO(obj['Body'].read().decode()))
        df['date'] = pd.to_datetime(df['date'])
        if date_to:
            df = df[(df['date'] >= date_from) & (df['date'] <= date_to)]
        else:
            df = df[df['date'] >= date_from]
        return df
    except Exception as e:
        print(f"Error fetching S3 daily prices for {ticker}: {e}")
        return None


def get_polygon_data(ticker):
    # Get fundamentals
    url = f"https://api.polygon.io/v3/reference/tickers/{ticker}?apiKey={POLYGON_API_KEY}"
    resp = requests.get(url)
    info = resp.json().get('results', {})
    # Get last trade price
    price_url = f"https://api.polygon.io/v2/last/trade/{ticker}?apiKey={POLYGON_API_KEY}"
    price_resp = requests.get(price_url)
    price_data = price_resp.json().get('results', {})
    current_price = price_data.get('price')
    # Format Ex-Div Date
    ex_div_raw = info.get("ex_dividend_date")
    if ex_div_raw:
        try:
            ex_div_date = datetime.strptime(ex_div_raw, "%Y-%m-%d").strftime("%Y-%m-%d")
        except Exception:
            ex_div_date = str(ex_div_raw)
    else:
        ex_div_date = None
    return {
        "Ticker": ticker,
        "Current Price": current_price,
        "Market Cap (T$)": info.get("market_cap") / 1e12 if info.get("market_cap") else None,
        "P/E": info.get("pe_ratio"),
        "YoY Price %": None,  # Will be filled from S3
        "Ex-Div Date": ex_div_date,
        "Div Yield": info.get("dividend_yield"),
        "Analyst 1-yr Target": None,
        "1-yr 6% OTM PUT Price": None,
        "3-mo Call Yield": None,
        "6-mo Call Yield": None,
        "1-yr Call Yield": None,
        "Example 6-mo Strike": None,
        "Error": None
    }


def get_yfinance_data(ticker):
    try:
        sym = yf.Ticker(ticker)
        info = sym.info
        hist = sym.history(period="1y")
        yoy = (hist['Close'][-1] - hist['Close'][0]) / hist['Close'][0] * 100 if not hist.empty else None
        prev_close = hist['Close'][-2] if not hist.empty else None
        current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        day_change = None
        if current_price and prev_close:
            day_change = (current_price - prev_close) / prev_close * 100
        ex_div_raw = info.get("exDividendDate")
        if ex_div_raw:
            try:
                ex_div_date = datetime.fromtimestamp(ex_div_raw).strftime("%Y-%m-%d")
            except Exception:
                ex_div_date = str(ex_div_raw)
        else:
            ex_div_date = None
        return {
            "Ticker": ticker,
            "Current Price": current_price,
            "Market Cap (T$)": info.get("marketCap") / 1e12 if info.get("marketCap") else None,
            "P/E": info.get("trailingPE"),
            "YoY Price %": f"{yoy:.1f}%" if yoy is not None else None,
            "Ex-Div Date": ex_div_date,
            "Div Yield": info.get("dividendYield"),
            "Analyst 1-yr Target": info.get("targetMeanPrice"),
            "1-yr 6% OTM PUT Price": None,
            "3-mo Call Yield": None,
            "6-mo Call Yield": None,
            "1-yr Call Yield": None,
            "Example 6-mo Strike": None,
            "Error": None
        }
    except Exception as e:
        return {
            "Ticker": ticker,
            "Current Price": None,
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
        }


tickers = ["AMD","MSFT","NVDA","META","AMZN","GOOG","AAPL","TSLA","IBM","ORCL", "TEM"]
records = []

for t in tickers:
    # Try Polygon S3 for historical prices first
    s3_hist = get_polygon_s3_daily_prices(t)
    yoy = None
    if s3_hist is not None and not s3_hist.empty:
        try:
            yoy = (s3_hist['close'].iloc[-1] - s3_hist['close'].iloc[0]) / s3_hist['close'].iloc[0] * 100
        except Exception:
            yoy = None
    try:
        data = get_polygon_data(t)
        # Fill YoY Price % from S3 if available
        if yoy is not None:
            data["YoY Price %"] = f"{yoy:.1f}%"
        # If Polygon returns no price, fallback to yfinance
        if data["Current Price"] is None:
            print(f"Polygon data missing for {t}, using yfinance fallback.")
            data = get_yfinance_data(t)
    except Exception as e:
        print(f"Polygon error for {t}: {e}, using yfinance fallback.")
        data = get_yfinance_data(t)
    records.append(data)

df = pd.DataFrame(records)
date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"AI_Stock_Live_Comparison_{date_str}.xlsx"
df.to_excel(filename, index=False)

# Format header row: bold and wrap text, and set row height to auto
wb = openpyxl.load_workbook(filename)
ws = wb.active
for cell in ws[1]:
    cell.font = Font(bold=True)
    cell.alignment = Alignment(wrap_text=True)
ws.row_dimensions[1].height = None  # Let Excel auto-adjust row height
wb.save(filename)
print(f"Spreadsheet generated: {filename}")
# filepath: /home/kenmac/personal/juicyfruitstockoptions/Stock_Live_Comparison_to_excel.py
