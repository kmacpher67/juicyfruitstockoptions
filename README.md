# Juicy Fruit Stock Options

Utilities for analysing equity call options and covered call positions.

## Setup

Install dependencies with:

```bash
pip install -r requirements.txt
```

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

Run the unit tests with:

```bash
pytest -q
```

