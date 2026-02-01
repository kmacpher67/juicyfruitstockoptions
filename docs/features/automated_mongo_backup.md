# Automated MongoDB Backup

## Feature Overview
The system performs an automated backup of the entire MongoDB `stock_analysis` collection to a JSON file (`mongo_backup.json`) daily.

## First Principles & Motivation
- **Data Portability**: JSON (JavaScript Object Notation) is a universal, human-readable text format. Exporting the binary MongoDB data to JSON ensures the data can be inspected, moved, or imported into other systems without requiring a running MongoDB instance.
- **Data Durability**: While MongoDB has its own storage engine (WiredTiger), having a flat-file backup allows for version control (git) and easy restoration in case of container corruption.
- **Automation**: Backups should occur without user intervention to ensure they are never forgotten.

## Implementation Details

### 1. Generation Logic
- **Script**: `export_mongo.py`
- **Function**: `export_data()`
- **Mechanism**:
  - Connects to the local MongoDB instance.
  - Fetches all documents from the collection.
  - Serializes them to JSON using `bson.json_util` (preserves types like ObjectId and DateTime).
  - Overwrites `mongo_backup.json` in the application root.

### 2. Automation Trigger
The backup is NOT a standalone cron job but is integrated into the daily Analysis pipeline.

- **Trigger Chain**:
  1. **Scheduler**: `app/scheduler/jobs.py` triggers `run_stock_live_comparison` daily (default 10:00 AM).
  2. **Service**: `run_stock_live_comparison` calls `StockLiveComparison.run()`.
  3. **Execution**: `StockLiveComparison.run()` performs data fetching and analysis.
  4. **Backup**: At the very end of `run()`, it calls `export_data()`.

### 3. File Location
- **Container Path**: `/app/mongo_backup.json`
- **Host Path**: The file is created in the root directory where the docker container is running (mapped volume).

## Current Constraints
- **Single Slot**: The file is named `mongo_backup.json`. Every run overwrites the previous backup. There is no historical rotation (e.g., `backup_2023-10-27.json`) unless `git` is used to commit the changes.
- **Dependency**: Backup only happens if the `StockLiveComparison` job completes successfully.

## Code References
- [`export_mongo.py`](file:///home/kenmac/personal/juicyfruitstockoptions/export_mongo.py)
- [`stock_live_comparison.py`](file:///home/kenmac/personal/juicyfruitstockoptions/stock_live_comparison.py) (Lines ~829)
- [`app/scheduler/jobs.py`](file:///home/kenmac/personal/juicyfruitstockoptions/app/scheduler/jobs.py)
