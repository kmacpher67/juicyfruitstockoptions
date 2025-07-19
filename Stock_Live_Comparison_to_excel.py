import requests
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment
import glob
import os

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

def get_latest_spreadsheet(base_name="AI_Stock_Live_Comparison_"):
    files = glob.glob(f"{base_name}*.xlsx")
    if not files:
        return None, None
    files.sort(key=os.path.getmtime, reverse=True)
    latest_file = files[0]
    file_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
    return latest_file, file_time

tickers = [
    "AMD","MSFT","NVDA","META","AMZN","GOOG","AAPL","TSLA","IBM","ORCL",
    "TEM", "V", "GEV", "CPRX",
    "CRWD", "CVS", "FMNB", "GD", "JPM", "KMB", "MRVL", "NEE", "OKE", "SLB", "STLD", "TMUS"
]

# Remove duplicates while preserving order
tickers = list(dict.fromkeys(tickers))

date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"AI_Stock_Live_Comparison_{date_str}.xlsx"

latest_file, file_time = get_latest_spreadsheet()
records = []
now = datetime.now()
max_age_hours = 4

def is_recent(row):
    try:
        last_update = pd.to_datetime(row.get("Last Update"))
        if pd.isnull(last_update):
            return False
        age = (now - last_update).total_seconds() / 3600
        return age < max_age_hours
    except Exception:
        return False

if latest_file:
    df_existing = pd.read_excel(latest_file)
    # Ensure "Last Update" column exists
    if "Last Update" not in df_existing.columns:
        df_existing["Last Update"] = None
    # Find missing or outdated tickers
    ticker_status = {row["Ticker"]: is_recent(row) for _, row in df_existing.iterrows() if row["Ticker"] in tickers}
    missing_or_old = [t for t in tickers if t not in ticker_status or not ticker_status[t]]
    if not missing_or_old:
        print(f"All tickers are up-to-date in {latest_file}. No update needed.")
        df = df_existing
    else:
        print(f"Updating spreadsheet for missing or outdated tickers: {missing_or_old}")
        records = df_existing.to_dict(orient='records')
        tickers_to_fetch = missing_or_old
else:
    print("No recent spreadsheet found. Fetching all tickers.")
    tickers_to_fetch = tickers

if tickers_to_fetch:
    hist = yf.download(tickers_to_fetch, period="1y", group_by='ticker', threads=True)
    time.sleep(2)  # Sleep to avoid hitting API limits
    tickers_obj = yf.Tickers(" ".join(tickers_to_fetch))
    for t in tickers_to_fetch:
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
                call12, call12_strike = get_otm_call_yield(chain, current_price, 365)
                put_price = get_otm_put_price(chain, current_price, 365)
                analyst_target = info.get("targetMeanPrice")

                ex_div_raw = info.get("exDividendDate")
                if ex_div_raw:
                    try:
                        ex_div_date = datetime.fromtimestamp(ex_div_raw).strftime("%Y-%m-%d")
                    except Exception:
                        ex_div_date = str(ex_div_raw)
                else:
                    ex_div_date = None

                # Calculate annual yield for 1yr 6% OTM put (premium/current price)
                annual_yield_put = None
                if put_price and current_price:
                    annual_yield_put = round((put_price / current_price) * 100, 2)

                # Calculate annual yield for 1yr call (premium/current price)
                annual_yield_call = None
                if call12 and current_price:
                    annual_yield_call = round((call12 / current_price) * 100, 2)

                records.append({
                    "Ticker": t,
                    "Current Price": current_price,
                    "1D % Change": f"{day_change:.2f}%" if day_change is not None else None,
                    "Market Cap (T$)": info.get("marketCap") / 1e12 if info.get("marketCap") else None,
                    "P/E": info.get("trailingPE"),
                    "YoY Price %": f"{yoy:.1f}%" if yoy is not None else None,
                    "Ex-Div Date": ex_div_date,
                    "Div Yield": info.get("dividendYield"),
                    "Analyst 1-yr Target": analyst_target,
                    "1-yr 6% OTM PUT Price": put_price,
                    "Annual Yield Put Prem": annual_yield_put,  # <-- new column
                    "3-mo Call Yield": call3,
                    "6-mo Call Yield": call6,
                    "1-yr Call Yield": call12,
                    "Annual Yield Call Prem": annual_yield_call,  # <-- new column
                    "Example 6-mo Strike": strike6,
                    "Error": None,
                    "Last Update": now.strftime("%Y-%m-%d %H:%M:%S")
                })
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
                    "Annual Yield Put Prem": None,
                    "3-mo Call Yield": None,
                    "6-mo Call Yield": None,
                    "1-yr Call Yield": None,
                    "Annual Yield Call Prem": None,
                    "Example 6-mo Strike": None,
                    "Error": str(e),
                    "Last Update": now.strftime("%Y-%m-%d %H:%M:%S")
                })
                success = True
        if not success:
            print(f"Skipping {t} after 3 retries.")
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
                "Annual Yield Put Prem": None,
                "3-mo Call Yield": None,
                "6-mo Call Yield": None,
                "1-yr Call Yield": None,
                "Annual Yield Call Prem": None,
                "Example 6-mo Strike": None,
                "Error": "Max retries exceeded",
                "Last Update": now.strftime("%Y-%m-%d %H:%M:%S")
            })

    # Merge new records with existing, updating only outdated/missing tickers
    if latest_file:
        df_new = pd.DataFrame(records)
        # Remove outdated/missing tickers from existing
        df_existing = df_existing[~df_existing['Ticker'].isin(tickers_to_fetch)]
        df = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df = pd.DataFrame(records)
    df.to_excel(filename, index=False)
else:
    # If no update needed, just save/load the existing df
    df = df_existing
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
