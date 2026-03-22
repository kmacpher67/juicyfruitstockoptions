# Learning: Legacy Trade Reprocessing

## Overview
The `app/scripts/reprocess_legacy_trades.py` script is designed to handle historical trade data from Interactive Brokers (IBKR). This is particularly useful when you have legacy CSV files that need to be ingested into the current MongoDB database for historical analysis and metrics.

## First Principles
- **Data Integrity**: Reprocessing ensures that all historical trades are accounted for in the FIFO (First-In, First-Out) matching logic used for P&L and metrics.
- **Environment Isolation**: The script identifies that while the application usually runs in Docker, administrative tasks like reprocessing are often performed from the host machine (localhost) to avoid container overhead or for easier data access.

## Technical Details
### Data Source
The script looks for files matching `Recent_Trades*.csv` in the `/home/kenmac/personal/juicyfruitstockoptions/ibkr-legacy-data` directory.

### Execution Context
To run this script successfully, the environment must be configured to point to the **local** MongoDB instance (not the one internal to the Docker network).

### Environment Variables
The following environment variables are required:
- `MONGO_URI`: The connection string for the local MongoDB (e.g., `mongodb://admin:admin123@localhost:27017/?authSource=admin`).
- `ADMIN_USER`: The MongoDB admin username.
- `ADMIN_PASS`: The MongoDB admin password.

## Security & Best Practices
- **Credential Management**: Always export credentials in your shell session rather than hardcoding them in scripts.
- **Database Backup**: Before running bulk reprocessing, it is recommended to have a backup of the `ibkr_trades` collection.

## References
- [IBKR Trade Import Logic](file:///home/kenmac/personal/juicyfruitstockoptions/app/scripts/import_manual_csv.py)
- [Trade Metrics Learning](file:///home/kenmac/personal/juicyfruitstockoptions/docs/learning/trade-metrics.md)
