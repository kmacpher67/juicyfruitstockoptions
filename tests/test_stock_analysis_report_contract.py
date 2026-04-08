import asyncio
import math

import pandas as pd

from app.api.routes import User, get_report_data
from stock_live_comparison import StockLiveComparison


def test_save_to_excel_enforces_canonical_report_column_order(tmp_path):
    comp = StockLiveComparison(['AAA'])
    comp.filename = str(tmp_path / 'ordered.xlsx')

    df = pd.DataFrame(
        [
            {
                'Ticker': 'AAA',
                'Current Price': 101.25,
                'Annual Yield Put Prem': 5.1,
                'Annual Yield Call Prem': 8.2,
                'MA_200': 98.3,
                'RSI_14': 54.2,
                'Last Update': '2026-04-08 10:00:00',
            }
        ]
    )

    df, put_col, call_col = comp.add_ratio_column(df)
    comp.save_to_excel(df, put_col, call_col)

    exported = pd.read_excel(comp.filename, engine='openpyxl')
    headers = list(exported.columns)

    canonical = StockLiveComparison.CANONICAL_REPORT_COLUMNS
    assert headers[: len(canonical)] == canonical


def test_fetch_ticker_record_normalizes_dividend_yield_to_percent(monkeypatch):
    comp = StockLiveComparison(['AAA'])

    monkeypatch.setattr(comp, 'get_otm_call_yield', lambda *args, **kwargs: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_price', lambda *args, **kwargs: (None, None))
    monkeypatch.setattr(comp, 'get_otm_call_contract', lambda *args, **kwargs: (None, None, None))
    monkeypatch.setattr(comp, 'get_otm_put_contract', lambda *args, **kwargs: (None, None, None))

    hist = pd.DataFrame(
        {
            'Close': [99, 100],
            'High': [100, 101],
            'Low': [98, 99],
            'Open': [99, 100],
            'Volume': [1000, 1000],
        }
    )
    info = {'regularMarketPrice': 100, 'dividendYield': 0.0437, 'shortName': 'AAA'}

    record = comp.fetch_ticker_record('AAA', info, hist, chain=None)
    assert record['Div Yield'] == 4.37


async def _run_get_report_data_with_frame(frame, monkeypatch):
    monkeypatch.setattr('os.path.exists', lambda *_args, **_kwargs: True)
    monkeypatch.setattr('pandas.read_excel', lambda *_args, **_kwargs: frame)

    return await get_report_data(
        filename='AI_Stock_Live_Comparison_20260408_000000.xlsx',
        current_user=User(username='test', role='admin'),
    )


def test_get_report_data_replaces_nan_and_inf_with_null(monkeypatch):
    frame = pd.DataFrame(
        [
            {
                'Ticker': 'AAA',
                'MA_200': math.nan,
                'EMA_20': math.inf,
                'HMA_20': -math.inf,
                'RSI_14': 52.3,
            }
        ]
    )

    payload = asyncio.run(_run_get_report_data_with_frame(frame, monkeypatch))
    row = payload[0]

    assert row['Ticker'] == 'AAA'
    assert row['MA_200'] is None
    assert row['EMA_20'] is None
    assert row['HMA_20'] is None
    assert row['RSI_14'] == 52.3
