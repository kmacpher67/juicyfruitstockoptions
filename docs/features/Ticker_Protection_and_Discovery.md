# Ticker Protection and Discovery

## Overview
This feature enhances the robustness of the Analysis and Portfolio views by preventing accidental data loss and automating the tracking of relevant financial instruments.

## Features

### 1. Portfolio Item Protection
- **Goal**: Prevent users from accidentally "stopping tracking" (deleting) tickers that are currently held in the portfolio.
- **Implementation**:
  - Modified `StockGrid.jsx` to check if a ticker exists in the `portfolioTickers` set.
  - If a ticker is in the portfolio, the "Delete" (Trash) button is replaced with a disabled "Checkmark" icon.
  - Adds a visual cue (opacity and tooltip) indicating the item is protected.

### 2. Intelligent Ticker Discovery
- **Goal**: Ensure that underlying stocks for option positions are automatically tracked, even if the user hasn't explicitly added the stock ticker. This is critical for keeping price data current for options.
- **Implementation**:
  - Created `app/services/ticker_discovery.py`.
  - Scans `ibkr_holdings` for:
    - `symbol` (for Stocks)
    - `underlying_symbol` (for Options)
  - Automatically adds any newly found unique symbols to the `tracked_tickers` collection in MongoDB.
  - **Automation**: This discovery runs:
    - **Lazily**: When the `get_tracked_tickers` API is called (e.g., loading the Analysis page).
    - **Daily**: As part of the `run_daily_job` in `jobs.py`, ensuring data is fresh every morning.

## Technical Components
- **Frontend**: `frontend/src/components/StockGrid.jsx`
- **Backend Service**: `app/services/ticker_discovery.py`
- **Scheduled Job**: `app/scheduler/jobs.py`
- **API Route**: `app/api/routes.py` (`get_tracked_tickers`)

## Usage
- No manual action required.
- **Protection**: visual indicator appears automatically for portfolio items.
- **Discovery**: New option positions' underlying stocks will appear in the Analysis grid automatically within 24 hours (or upon manual refresh).
