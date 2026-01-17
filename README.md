# Juicy Fruit Stock Options


Utilities for analysing equity call options, covered call positions, and stock price trends versus moving averages.

## Setup

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Directory Layout

```
app/
├── zen_garden.py           # FastAPI entrypoint with scheduler
├── api/
│   └── routes.py           # REST endpoints to trigger jobs
├── auth/
│   └── users.py            # fastapi-users configuration
├── scheduler/
│   └── jobs.py             # APScheduler jobs
├── services/
│   ├── portfolio_fixer.py
│   └── stock_live_comparison.py
└── utils/
    ├── excel_exporter.py
    └── mongo_client.py
```


## Stock Live Comparison Script

This script collects stock metrics, calculates moving averages (30, 60, 120, 200 days), and exports to Excel and MongoDB.

### Usage

```bash
python stock_live_comparison.py [--highlight-threshold 0.1]
```

- `--highlight-threshold`: Set the percentage (as a decimal) for highlighting moving average cells. Default is 0.05 (5%).

### Features
- Calculates 30, 60, 120, and 200-day moving averages for each stock using a simple rolling window.
- Displays the percentage delta ((Current - SMA) / SMA) in `MA_XX_highlight` columns.
    - **Green**: Current price is at least the threshold below the average.
    - **Red**: Current price is at least the threshold above the average.
- Moving averages and highlight status are also stored in MongoDB.

### Example

To use a 10% threshold for highlighting:

```bash
python stock_live_comparison.py --highlight-threshold 0.10
```


### Docker

Build and launch the API together with MongoDB using Docker:

```bash
./docker-run-stock-app.sh
```

The service will be available at http://localhost:8000.

## Modules

### `option_analyzer_v5.py`

`analyze_options(ticker_symbol, min_volume=50, max_expirations=2, min_annual_tv_pct=9.9, max_otm_pct=5.0) -> pandas.DataFrame`

```python
from option_analyzer_v5 import analyze_options
df = analyze_options("ORCL")
print(df.head())
```

### `option_time_value.py`

`analyze_options(tickers, min_time_value=0.10) -> pandas.DataFrame`

```python
from option_time_value import analyze_options
df = analyze_options(["ORCL", "MSFT"], min_time_value=0.25)
```

### `option_optimizer.py`

`optimize_options(ticker_symbol, min_volume=50, max_expirations=2, min_annual_tv_pct=9.9, max_otm_pct=5.0, min_days=5, max_results=20) -> pandas.DataFrame`

```python
from option_optimizer import optimize_options
df = optimize_options("ORCL")
```

### `covered_call_analysis.py`

`analyze_covered_calls(file_path) -> pandas.DataFrame`

```python
from covered_call_analysis import analyze_covered_calls
df = analyze_covered_calls("ibkr_positions.csv")
```

Each module also includes a small `main()` function so it can be executed
directly, e.g. `python option_optimizer.py`.

## Testing

A `pytest.ini` file is provided to configure the test runner, specifically to exclude the `mongo_data` directory.

Run all tests with:

```bash
pytest
```

Run a specific test file:

```bash
pytest test_stock_ticker_list.py
```
