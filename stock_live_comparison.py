import yfinance as yf
import pandas as pd
import time
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment
import glob
import os

class StockLiveComparison:
    """Collect stock metrics and export them to an Excel sheet."""

    def __init__(self, tickers, max_age_hours=4):
        self.tickers = list(dict.fromkeys(tickers))
        self.max_age_hours = max_age_hours
        self.records = []
        self.now = datetime.now()
        date_str = self.now.strftime("%Y%m%d_%H%M%S")
        self.filename = f"AI_Stock_Live_Comparison_{date_str}.xlsx"
        self.latest_file, _ = self.get_latest_spreadsheet()

    # ------------------------------------------------------------------
    @staticmethod
    def get_latest_spreadsheet(base_name="AI_Stock_Live_Comparison_"):
        files = glob.glob(f"{base_name}*.xlsx")
        if not files:
            return None, None
        files.sort(key=os.path.getmtime, reverse=True)
        latest_file = files[0]
        file_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
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

        return {
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
            "Example 6-mo Strike": strike6,
            "Error": None,
            "Last Update": self.now.strftime("%Y-%m-%d %H:%M:%S"),
        }

    # ------------------------------------------------------------------
    def fetch_data(self, tickers_to_fetch):
        if not tickers_to_fetch:
            return []
        hist = yf.download(tickers_to_fetch, period="1y", group_by='ticker', threads=True)
        time.sleep(2)
        tickers_obj = yf.Tickers(" ".join(tickers_to_fetch))
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
    def add_ratio_column(self, df):
        """Add Put/Call Yield Ratio column to DataFrame, catching errors and printing them."""
        ratio_col_name = "Put/Call Yield Ratio"
        try:
            put_col = df.columns.get_loc("Annual Yield Put Prem") + 1
            call_col = df.columns.get_loc("Annual Yield Call Prem") + 1
            # Only insert if not already present
            if ratio_col_name not in df.columns:
                df.insert(call_col, ratio_col_name, "")
            # Add formulas or values as needed (example: fill with NaN for now)
            df[ratio_col_name] = df.apply(
                lambda row: row["Annual Yield Put Prem"] / row["Annual Yield Call Prem"]
                if row["Annual Yield Call Prem"] not in [0, None, ""] and row["Annual Yield Put Prem"] not in [None, ""] else None,
                axis=1
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
        df = self.sort_dataframe_for_excel(df)
        df.to_excel(self.filename, index=False)
        wb = openpyxl.load_workbook(self.filename)
        ws = wb.active
        for i in range(2, ws.max_row + 1):
            put_letter = openpyxl.utils.get_column_letter(put_col)
            call_letter = openpyxl.utils.get_column_letter(call_col)
            ratio_cell = ws.cell(row=i, column=call_col + 1)
            ratio_cell.value = f"=IFERROR({put_letter}{i}/{call_letter}{i},\"\")"
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(wrap_text=True)
        ws.row_dimensions[1].height = None

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
    def run(self):
        latest_file = self.latest_file
        if latest_file:
            df_existing = pd.read_excel(latest_file)
            if "Last Update" not in df_existing.columns:
                df_existing["Last Update"] = None
            ticker_status = {row["Ticker"]: self.is_recent(row) for _, row in df_existing.iterrows() if row["Ticker"] in self.tickers}
            missing_or_old = [t for t in self.tickers if t not in ticker_status or not ticker_status[t]]
            if not missing_or_old:
                df = df_existing
                put_col = df.columns.get_loc("Annual Yield Put Prem") + 1
                call_col = df.columns.get_loc("Annual Yield Call Prem") + 1
            else:
                self.records = df_existing.to_dict(orient='records')
                tickers_to_fetch = missing_or_old
                fetched = self.fetch_data(tickers_to_fetch)
                self.records.extend(fetched)
                df = self.merge_with_existing(df_existing, tickers_to_fetch)
                df, put_col, call_col = self.add_ratio_column(df)
        else:
            tickers_to_fetch = self.tickers
            self.records = self.fetch_data(tickers_to_fetch)
            df = pd.DataFrame(self.records)
            df, put_col, call_col = self.add_ratio_column(df)
        self.save_to_excel(df, put_col, call_col)
        print(f"Spreadsheet generated: {self.filename}")

if __name__ == "__main__":
    tickers = [
        "AMD", "MSFT", "NVDA", "META", "AMZN", "GOOG", "AAPL", "TSLA", "IBM", "ORCL",
        "TEM", "V", "GEV", "CPRX", "CRWD", "CVS", "FMNB", "GD", "JPM", "KMB", "MRVL", "NEE", "OKE", "SLB", "STLD", "TMUS",
    ]
    comp = StockLiveComparison(tickers)
    comp.run()
