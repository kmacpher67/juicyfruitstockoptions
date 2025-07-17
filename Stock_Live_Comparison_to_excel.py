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
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    latest_file = files[0]
    file_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
    return latest_file, file_time

tickers = ["AMD","MSFT","NVDA","META","AMZN","GOOG","AAPL","TSLA","IBM","ORCL", "TEM"]
records = []

# Batch download historical prices for all tickers
hist = yf.download(tickers, period="1y", group_by='ticker', threads=True)
tickers_obj = yf.Tickers(" ".join(tickers))

for t in tickers:
    tries = 0
    success = False
    while tries < 3 and not success:
        try:
            time.sleep(1 + tries * 2)  # Sleep: 1s, 3s, 5s
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

            ex_div_raw = info.get("exDividendDate")
            if ex_div_raw:
                try:
                    ex_div_date = datetime.fromtimestamp(ex_div_raw).strftime("%Y-%m-%d")
                except Exception:
                    ex_div_date = str(ex_div_raw)
            else:
                ex_div_date = None

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
                "3-mo Call Yield": call3,
                "6-mo Call Yield": call6,
                "1-yr Call Yield": call12,
                "Example 6-mo Strike": strike6,
                "Error": None
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
                "3-mo Call Yield": None,
                "6-mo Call Yield": None,
                "1-yr Call Yield": None,
                "Example 6-mo Strike": None,
                "Error": str(e)
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
            "3-mo Call Yield": None,
            "6-mo Call Yield": None,
            "1-yr Call Yield": None,
            "Example 6-mo Strike": None,
            "Error": "Max retries exceeded"
        })

df = pd.DataFrame(records)
date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"AI_Stock_Live_Comparison_{date_str}.xlsx"

latest_file, file_time = get_latest_spreadsheet()
need_update = True

if latest_file:
    age = (datetime.now() - file_time).total_seconds() / 7200
    if age < 1:
        # Load existing spreadsheet
        df_existing = pd.read_excel(latest_file)
        # Check for missing tickers
        existing_tickers = set(df_existing['Ticker'].dropna())
        missing_tickers = [t for t in tickers if t not in existing_tickers]
        if not missing_tickers:
            print(f"Recent spreadsheet found: {latest_file} (age: {age:.2f} hours). No update needed.")
            df = df_existing
            need_update = False
        else:
            print(f"Updating spreadsheet for missing tickers: {missing_tickers}")
            # Only fetch data for missing tickers, then append to df_existing
            new_records = []
            for t in missing_tickers:
                # ... (insert your data fetch logic here, e.g. yfinance block) ...
                # For brevity, you can copy the main loop logic for fetching each ticker
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

                        ex_div_raw = info.get("exDividendDate")
                        if ex_div_raw:
                            try:
                                ex_div_date = datetime.fromtimestamp(ex_div_raw).strftime("%Y-%m-%d")
                            except Exception:
                                ex_div_date = str(ex_div_raw)
                        else:
                            ex_div_date = None

                        new_records.append({
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
                            "3-mo Call Yield": call3,
                            "6-mo Call Yield": call6,
                            "1-yr Call Yield": call12,
                            "Example 6-mo Strike": strike6,
                            "Error": None
                        })
                        success = True
                    except Exception as e:
                        print(f"Error fetching data for {t}: {e}")
                        new_records.append({
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
                    print(f"Skipping {t} after 3 retries.")
                    new_records.append({
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
                        "Error": "Max retries exceeded"
                    })
            # Append new records and save
            df = pd.concat([df_existing, pd.DataFrame(new_records)], ignore_index=True)
            df.to_excel(filename, index=False)
    else:
        print(f"Recent spreadsheet found but older than 1 hour ({age:.2f} hours). Generating new data.")
        need_update = True

if need_update:
    # ...your main data fetch loop for all tickers (as already in your code)...
    # After fetching, save as usual
    df = pd.DataFrame(records)
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
