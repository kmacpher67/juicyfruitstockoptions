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
├── main.py                 # FastAPI Application entry point
├── config.py               # Pydantic Settings
├── models.py               # Data Models
├── api/
├── auth/
├── scheduler/
└── services/
frontend/                   # React Frontend (Phase 2)
docker-compose.yml          # Container configuration
```

## Web Portal Architecture (New)

The project has been upgraded to a Dockerized Web Application.

- **Backend**: FastAPI (Python) serving REST endpoints and managing the Scheduler.
- **Frontend**: React (Vite) for the Dashboard (In Progress).
- **Database**: MongoDB (Persists to `./mongo_data`).
- **Scheduler**: Runs daily jobs automatically (configurable in `app/config.py`).

### Quick Start (Web Portal)

1.  **Run with Docker**:
    ```bash
    docker-compose up --build
    ```
2.  **Access API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
3.  **Admin Login**: `admin` / `admin123` (Default)

---

## Legacy Script Usage



## Stock Live Comparison Script

This script collects stock metrics, calculates moving averages (30, 60, 120, 200 days), and exports to Excel and MongoDB.

### Usage

```bash
python stock_live_comparison.py [--highlight-threshold 0.1]
```

- `--highlight-threshold`: Set the percentage (as a decimal) for highlighting moving average cells. Default is 0.05 (5%).
- **Output**: Files are saved to the `report-results/` directory by default.

### Features
- Calculates 30, 60, 120, and 200-day Simple Moving Averages (SMA) for each stock.
- **EMA (20-day)**: Exponential Moving Average, weighted to recent prices.
- **HMA (20-day)**: Hull Moving Average, reduces lag.
- **TSMOM (60-day)**: Time Series Momentum, volatility-scaled.
- **Call/Put Skew**: Ratio of Annual Call Yield to Annual Put Yield.
- Displays the percentage delta in highlight columns:
    - **Green**: Bullish signal (Price > EMA/HMA, TSMOM > 2%, or Skew > 1.1).
    - **Red**: Bearish signal (Price < EMA/HMA, TSMOM < -2%, or Skew < 0.8).
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
