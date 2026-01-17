from pathlib import Path
import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment
from Ai_Stock_Database import AiStockDatabase

class StockLiveComparison:
    """Collect stock metrics and export them to an Excel sheet."""

    def __init__(self, tickers, max_age_hours=4, highlight_threshold=0.05):
        self.tickers = list(dict.fromkeys(tickers))
        self.max_age_hours = max_age_hours
        self.highlight_threshold = highlight_threshold  # e.g. 0.05 for 5%
        self.records = []
        self.output_dir = Path(".")
        self.now = datetime.now()
        self.filename = None
        self.latest_file = None
    @staticmethod
    def calculate_moving_averages(hist, windows=(30, 60, 120, 200)):
        """Return a dict of moving averages for the given windows from a price series."""
        result = {f"MA_{w}": None for w in windows}
        if hist is None or hist.empty:
            return result
        closes = hist['Close']
        for w in windows:
            if len(closes) >= w:
                # Use pandas rolling window for standard SMA calculation
                result[f"MA_{w}"] = round(closes.rolling(window=w).mean().iloc[-1], 2)
        return result

    def calculate_ma_delta(self, current_price, avg):
        """Return the percentage delta: (current_price - avg) / avg."""
        if avg is None or current_price is None or avg == 0:
            return None
        delta = (current_price - avg) / avg
        return round(delta, 4)  # Return as float, e.g. 0.0521 for 5.21%

    # ------------------------------------------------------------------
    @staticmethod
    def get_latest_spreadsheet(directory: Path, base_name="AI_Stock_Live_Comparison_"):
        files = list(directory.glob(f"{base_name}*.xlsx"))
        if not files:
            return None, None
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        latest_file = files[0]
        file_time = datetime.fromtimestamp(latest_file.stat().st_mtime)
        return latest_file, file_time

    # ------------------------------------------------------------------
    @staticmethod
    def closest_expiration(option_dates, target_days):
        target = datetime.now() + pd.Timedelta(days=target_days)
        dates = [datetime.strptime(d, "%Y-%m-%d") for d in option_dates]
        if not dates:
            return None
        return min(dates, key=lambda d: abs((d - target).days)).strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    def get_otm_call_yield(self, chain, current_price, target_days, otm_pct=6):
        exp_date = self.closest_expiration(chain.options, target_days)
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

    # ------------------------------------------------------------------
    def get_otm_put_price(self, chain, current_price, target_days, otm_pct=6):
        exp_date = self.closest_expiration(chain.options, target_days)
        if not exp_date:
            return None
        puts = chain.option_chain(exp_date).puts
        target_strike = current_price * (1 - otm_pct / 100)
        puts = puts[puts['strike'] <= target_strike]
        if puts.empty:
            return None
        put = puts.iloc[-1]
        return put['lastPrice']

    # ------------------------------------------------------------------
    def is_recent(self, row):
        try:
            last_update = pd.to_datetime(row.get("Last Update"))
            if pd.isnull(last_update):
                return False
            age = (self.now - last_update).total_seconds() / 3600
            return age < self.max_age_hours
        except Exception:
            return False

    # ------------------------------------------------------------------
    def fetch_ticker_record(self, ticker, info, hist, chain):
        ticker_hist = hist if hist is not None else None
        yoy = None
        prev_close = None
        if ticker_hist is not None and not ticker_hist.empty:
            yoy = (ticker_hist['Close'].iloc[-1] - ticker_hist['Close'].iloc[0]) / ticker_hist['Close'].iloc[0] * 100
            prev_close = ticker_hist['Close'].iloc[-2]

        current_price = info.get("regularMarketPrice") or info.get("currentPrice")
        day_change = None
        if current_price and prev_close:
            day_change = (current_price - prev_close) / prev_close * 100

        call3, _ = self.get_otm_call_yield(chain, current_price, 90)
        call6, strike6 = self.get_otm_call_yield(chain, current_price, 180)
        call12, _ = self.get_otm_call_yield(chain, current_price, 365)
        put_price = self.get_otm_put_price(chain, current_price, 365)
        analyst_target = info.get("targetMeanPrice")

        ex_div_raw = info.get("exDividendDate")
        if ex_div_raw:
            try:
                ex_div_date = datetime.fromtimestamp(ex_div_raw).strftime("%Y-%m-%d")
            except Exception:
                ex_div_date = str(ex_div_raw)
        else:
            ex_div_date = None

        annual_yield_put = None
        if put_price and current_price:
            annual_yield_put = round((put_price / current_price) * 100, 2)

        annual_yield_call = None
        if call12 and current_price:
            annual_yield_call = round((call12 / current_price) * 100, 2)

        # Moving averages and highlight status
        ma_windows = (30, 60, 120, 200)
        ma_dict = self.calculate_moving_averages(ticker_hist, windows=ma_windows)
        highlight_dict = {f"MA_{w}_highlight": self.calculate_ma_delta(current_price, ma_dict[f"MA_{w}"])
                  for w in ma_windows}

        record = {
            "Ticker": ticker,
            "Current Price": current_price,
            "1D % Change": f"{day_change:.2f}%" if day_change is not None else None,
            "Market Cap (T$)": info.get("marketCap") / 1e12 if info.get("marketCap") else None,
            "P/E": info.get("trailingPE"),
            "YoY Price %": f"{yoy:.1f}%" if yoy is not None else None,
            "Ex-Div Date": ex_div_date,
            "Div Yield": info.get("dividendYield"),
            "Analyst 1-yr Target": analyst_target,
            "1-yr 6% OTM PUT Price": put_price,
            "Annual Yield Put Prem": annual_yield_put,
            "3-mo Call Yield": call3,
            "6-mo Call Yield": call6,
            "1-yr Call Yield": call12,
            "Annual Yield Call Prem": annual_yield_call,
            "6-mo Call Strike": strike6,
            "Error": None,
            "Last Update": self.now.strftime("%Y-%m-%d %H:%M:%S"),
        }
        # Add moving averages and highlight info
        record.update(ma_dict)
        record.update(highlight_dict)
        return record

    # ------------------------------------------------------------------
    def fetch_data(self, tickers_to_fetch):
        tickers_to_fetch = StockLiveComparison.unique_tickers(tickers_to_fetch)
        if not tickers_to_fetch:
            return []
        try:
            hist = yf.download(
                tickers_to_fetch,
                period="1y",
                group_by="ticker",
                threads=True,
                auto_adjust=False,  # explicit to avoid FutureWarning (set True if you want adjusted prices)
            )
        except Exception:
            hist = {}
        time.sleep(1)
        try:
            tickers_obj = yf.Tickers(" ".join(tickers_to_fetch))
        except Exception as e:
            return [
                {
                    "Ticker": t,
                    "Error": str(e),
                    "Last Update": self.now.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for t in tickers_to_fetch
            ]
        records = []
        for t in tickers_to_fetch:
            tries = 0
            success = False
            while tries < 3 and not success:
                try:
                    time.sleep(1 + tries * 2)
                    info = tickers_obj.tickers[t].info
                    ticker_hist = hist[t] if t in hist else None
                    chain = tickers_obj.tickers[t]
                    record = self.fetch_ticker_record(t, info, ticker_hist, chain)
                    records.append(record)
                    success = True
                except Exception as e:
                    record = {
                        "Ticker": t,
                        "Error": str(e),
                        "Last Update": self.now.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                    records.append(record)
                    success = True
        return records

    # ------------------------------------------------------------------
    def merge_with_existing(self, df_existing, tickers_to_fetch):
        df_new = pd.DataFrame(self.records)
        df_existing = df_existing[~df_existing['Ticker'].isin(tickers_to_fetch)]
        return pd.concat([df_existing, df_new], ignore_index=True)

    # ------------------------------------------------------------------
    def get_missing_or_outdated_tickers(self, df_existing):
        """Return tickers missing form the DataFrame, older than max_age_hours, or having missing MA data."""
        missing = []
        ma_cols = ["MA_30", "MA_60", "MA_120", "MA_200"]
        
        for t in self.tickers:
            row = df_existing[df_existing["Ticker"] == t]
            if row.empty:
                missing.append(t)
                continue
            try:
                # Check age
                last = pd.to_datetime(row.iloc[0]["Last Update"])
                if pd.isna(last) or (
                    (self.now - last).total_seconds() / 3600 >= self.max_age_hours
                ):
                    missing.append(t)
                    continue
                
                # Check for missing Moving Averages (NaN)
                # If any MA column is missing or NaN, consider it outdated to force re-fetch
                for ma in ma_cols:
                    if ma not in row.columns or pd.isna(row.iloc[0][ma]):
                        missing.append(t)
                        break
                else:
                    # Check for legacy "green"/"red" strings in highlight columns
                    # Only check if the previous check didn't already mark it as missing
                    for ma in ma_cols:
                        hl_col = f"{ma}_highlight"
                        if hl_col in row.columns:
                            val = row.iloc[0][hl_col]
                            if isinstance(val, str) and val in ["green", "red"]:
                                missing.append(t)
                                break
                        
            except Exception:
                missing.append(t)
        return missing

    # ------------------------------------------------------------------
    def add_ratio_column(self, df):
        """Add Put/Call Yield Ratio column to DataFrame, catching errors and printing them."""
        ratio_col_name = "Put/Call Yield Ratio"
        try:
            if "Annual Yield Put Prem" not in df.columns:
                df["Annual Yield Put Prem"] = None
            if "Annual Yield Call Prem" not in df.columns:
                df["Annual Yield Call Prem"] = None
            put_col = df.columns.get_loc("Annual Yield Put Prem") + 1
            call_col = df.columns.get_loc("Annual Yield Call Prem") + 1
            if ratio_col_name not in df.columns:
                df.insert(call_col, ratio_col_name, None)
            df[ratio_col_name] = df.apply(
                lambda row: (
                    row["Annual Yield Put Prem"] / row["Annual Yield Call Prem"]
                    if row["Annual Yield Call Prem"] not in [0, None, ""]
                    and row["Annual Yield Put Prem"] not in [None, ""]
                    else None
                ),
                axis=1,
            )
            return df, put_col, call_col
        except Exception as e:
            print(f"Error in add_ratio_column: {e}")
            return df, None, None

    # ------------------------------------------------------------------
    def upsert_ratio_column(self, df, put_col_name="Annual Yield Put Prem", call_col_name="Annual Yield Call Prem", ratio_col_name="Put/Call Yield Ratio"):
        """Upsert the Put/Call Yield Ratio column, print errors, and continue."""
        try:
            if ratio_col_name in df.columns:
                print(f'Column "{ratio_col_name}" already exists. Updating values.')
            else:
                # Insert after call_col_name
                if call_col_name in df.columns:
                    call_col = df.columns.get_loc(call_col_name) + 1
                    df.insert(call_col, ratio_col_name, None)
                    print(f'Column "{ratio_col_name}" inserted.')
                else:
                    df[ratio_col_name] = None
                    print(f'Column "{ratio_col_name}" added at end (call column not found).')

            # Update values
            df[ratio_col_name] = df.apply(
                lambda row: (
                    row[put_col_name] / row[call_col_name]
                    if row[call_col_name] not in [0, None, ""] and row[put_col_name] not in [None, ""] else None
                ),
                axis=1
            )
            return df
        except Exception as e:
            print(f"Error in upsert_ratio_column: {e}")
            return df

    # ------------------------------------------------------------------
    def save_to_excel(self, df, put_col, call_col):
        # Ensure all MA columns exist in DataFrame before saving
        ma_windows = [30, 60, 120, 200]
        for w in ma_windows:
            col_name = f"MA_{w}"
            if col_name not in df.columns:
                df[col_name] = None

        df = self.sort_dataframe_for_excel(df)
        df.to_excel(self.filename, index=False)
        wb = openpyxl.load_workbook(self.filename)
        ws = wb.active
        ws.row_dimensions[1].height = None

        if "Ticker" in df.columns:
            ticker_col_idx = df.columns.get_loc("Ticker") + 1
        else:
            ticker_col_idx = None

        # Ratio formula and Hyperlinks
        for i in range(2, ws.max_row + 1):
            put_letter = openpyxl.utils.get_column_letter(put_col)
            call_letter = openpyxl.utils.get_column_letter(call_col)
            ratio_cell = ws.cell(row=i, column=call_col + 1)
            ratio_cell.value = f"=IFERROR({put_letter}{i}/{call_letter}{i},\"\")"

            # Add Google Finance Hyperlink to Ticker Column
            if ticker_col_idx:
                ticker_cell = ws.cell(row=i, column=ticker_col_idx)
                ticker_val = ticker_cell.value
                if ticker_val:
                    url = f"https://www.google.com/finance?q={str(ticker_val)}"
                    # print(f"DEBUG: Ticker found '{ticker_val}', adding hyperlink: {url}")
                    ticker_cell.hyperlink = url
                    ticker_cell.style = "Hyperlink"

        for w in ma_windows:
            col_name = f"MA_{w}"
            if col_name in df.columns:
                col_idx = df.columns.get_loc(col_name) + 1
                for i in range(2, ws.max_row + 1):
                    avg_cell = ws.cell(row=i, column=col_idx)
                    price_cell = ws.cell(row=i, column=df.columns.get_loc("Current Price") + 1)
                    try:
                        avg = avg_cell.value
                        price = price_cell.value
                        if avg is not None and price is not None:
                            if price <= avg * (1 - self.highlight_threshold):
                                avg_cell.fill = openpyxl.styles.PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")  # green
                            elif price >= avg * (1 + self.highlight_threshold):
                                avg_cell.fill = openpyxl.styles.PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")  # red
                    except Exception:
                        pass
            
            # Format highlight column as percentage
            hl_col_name = f"MA_{w}_highlight"
            if hl_col_name in df.columns:
                hl_col_idx = df.columns.get_loc(hl_col_name) + 1
                for i in range(2, ws.max_row + 1):
                    cell = ws.cell(row=i, column=hl_col_idx)
                    cell.number_format = '0.0%'

        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(wrap_text=True)

        ws.freeze_panes = "A2"  # Freeze the first row

        wb.save(self.filename)

    # ------------------------------------------------------------------
    def sort_dataframe_for_excel(self, df):
        """Sort the DataFrame by Last Update (descending) and Ticker (ascending)."""
        try:
            if "Last Update" in df.columns and "Ticker" in df.columns:
                df = df.sort_values(by=["Last Update", "Ticker"], ascending=[False, True])
            else:
                print("Warning: 'Last Update' or 'Ticker' column missing. Skipping sort.")
            return df
        except Exception as e:
            print(f"Error in sort_dataframe_for_excel: {e}")
            return df

    # ------------------------------------------------------------------
    def upsert_to_mongo(self, df):
        """
        Upsert each row of the DataFrame to MongoDB using Ticker and Last Update as unique keys.
        Includes moving averages and highlight status.
        Prints errors but does not crash the program.
        """
        try:
            db = AiStockDatabase()
            records = df.to_dict(orient="records")
            for record in records:
                try:
                    # Use Ticker and Last Update as unique key for idempotency
                    db.upsert_stock_record(record, key_fields=("Ticker", "Last Update"))
                except Exception as e:
                    print(f"Error upserting record for {record.get('Ticker')}: {e}")
            print(f"Upserted {len(records)} records to MongoDB.")
        except Exception as e:
            print(f"Error connecting to MongoDB: {e}")

    # ------------------------------------------------------------------
    @staticmethod
    def unique_tickers(tickers):
        """Return a list of unique tickers, preserving order."""
        # variable tickers_to_fetch in your code is a native Python list, not a pandas Series.
        seen = set()
        unique = []
        for t in tickers:
            if t not in seen:
                unique.append(t)
                seen.add(t)
        return unique

    @staticmethod
    def get_default_tickers():
        """Return the default list of tickers to track."""
        return sorted(list({
            "^IXIC", "^SPX", "SPXS", "^DJI",
            "AA", "AAPL", "AMAT", "AMD", "AMZN", "AVGO", "BHP", "BMY", "CCJ", "CEG", "COPP",
            "CPRX", "CRWD", "CRWV", "CVS", "CVX", "D", "DUK", "ENB", "ETN",
            "F", "FDX", "FMNB", "GD", "GE", "GEV", "GOOG", "GOOGL", "FCX", 
            "IBM", "IONQ", "JNJ", "JPM", "KMB", "KO", "LAC", "LRCX", "MCD", "META",
            "MO", "MRVL", "MSFT", "MU", "NEE", "NNE", "NUE", "NVDA",
            "OKE", "OLN", "ORCL", "PAAS", "PFE", "PLTR", "RIO", "SLB", "SMG", "SMR", "STLD",
            "SCCO", "TEM", "TMUS", "TSLA", "TSM", "UPS", 
            "V", "VLO", "VSAT", "VST", "WM", "WMT", "XOM"
        }))

    def run(self):
        self.now = datetime.now()
        self.filename = self.output_dir / f"AI_Stock_Live_Comparison_{self.now.strftime('%Y%m%d_%H%M%S')}.xlsx"
        self.latest_file, _ = self.get_latest_spreadsheet(self.output_dir)
        print(f"Latest spreadsheet: {self.latest_file}")
        
        final_records = []
        put_col = None
        call_col = None
        
        if self.latest_file:
            df_existing = pd.read_excel(self.latest_file)
            if "Last Update" not in df_existing.columns:
                df_existing["Last Update"] = None
            
            missing_or_old = self.get_missing_or_outdated_tickers(df_existing)
            
            # Start with existing records converted to list of dicts
            existing_records = df_existing.to_dict(orient='records')
            
            if not missing_or_old:
                print("All tickers are up to date.")
                final_records = existing_records
                put_col = df_existing.columns.get_loc("Annual Yield Put Prem") + 1
                call_col = df_existing.columns.get_loc("Annual Yield Call Prem") + 1
            else:
                tickers_to_fetch = missing_or_old
                print(f"Fetching data for {len(tickers_to_fetch)} tickers: {tickers_to_fetch}")
                
                # Filter out records that are about to be updated
                # We keep only records for tickers NOT in tickers_to_fetch
                preserved_records = [
                    r for r in existing_records 
                    if r.get("Ticker") not in tickers_to_fetch
                ]
                
                fetched_records = self.fetch_data(tickers_to_fetch)
                print(f"fetched: {len(fetched_records)} records")
                
                # Combine preserved existing records with new fetched records
                final_records = preserved_records + fetched_records
                
        else:
            print("No existing spreadsheet found. Fetching all data.")
            tickers_to_fetch = self.tickers
            final_records = self.fetch_data(tickers_to_fetch)

        # Create DataFrame from final combined list
        df = pd.DataFrame(final_records)
        if df.empty:
             df = pd.DataFrame(
                columns=["Ticker", "Annual Yield Put Prem", "Annual Yield Call Prem", "Last Update"]
            )
            
        # Deduplicate: Keep only the latest record for each Ticker
        if "Last Update" in df.columns and "Ticker" in df.columns:
            # Ensure Last Update is datetime for sorting
            df["Last Update"] = pd.to_datetime(df["Last Update"], errors='coerce')
            df = df.sort_values(by=["Last Update", "Ticker"], ascending=[False, True])
            initial_count = len(df)
            df = df.drop_duplicates(subset=["Ticker"], keep="first")
            final_count = len(df)
            if initial_count != final_count:
                print(f"Removed {initial_count - final_count} duplicate records. Keeping {final_count} unique tickers.")
            # Convert Last Update back to string for consistency/Excel if needed, though datetime is fine.
            # But the current format is string "%Y-%m-%d %H:%M:%S".
            df["Last Update"] = df["Last Update"].dt.strftime("%Y-%m-%d %H:%M:%S")

        # Ensure we have column indices for formatting
        # If we didn't get them from existing DF, calculate them now
        # Note: add_ratio_column handles adding columns if missing
        df, put_col, call_col = self.add_ratio_column(df)
            
        self.save_to_excel(df, put_col, call_col)
        self.upsert_to_mongo(df)
        
        print(f"Spreadsheet generated: {self.filename}")

import argparse

def main():
    parser = argparse.ArgumentParser(description="Stock Live Comparison")
    parser.add_argument('--highlight-threshold', type=float, default=0.05, help='Highlight threshold as a decimal (default 0.05 for 5%)')
    args = parser.parse_args()

    tickers = StockLiveComparison.get_default_tickers()
    print(f"Processing {tickers} tickers...")

    comp = StockLiveComparison(tickers, highlight_threshold=args.highlight_threshold)
    comp.run()

if __name__ == "__main__":
    main()
