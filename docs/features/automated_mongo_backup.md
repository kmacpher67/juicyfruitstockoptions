# Automated MongoDB Backup

## Feature Overview
The system performs an automated backup of the entire MongoDB `stock_analysis` collection to a JSON file (`mongo_backup.json`) daily.

> [!IMPORTANT]
> Operational default restore policy has moved to full database restore via `mongodump`/`mongorestore`.
> `mongo_backup.json` should be treated as a legacy single-collection fallback.
> See: `docs/learning/mongo-restore-and-sync-runbook.md`

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
- **Scope**: JSON backup/restore path does not guarantee full-database coverage; prefer full dump artifacts for complete environment migration.

## Code References
- [`export_mongo.py`](file:///home/kenmac/personal/juicyfruitstockoptions/export_mongo.py)
- [`stock_live_comparison.py`](file:///home/kenmac/personal/juicyfruitstockoptions/stock_live_comparison.py) (Lines ~829)
- [`app/scheduler/jobs.py`](file:///home/kenmac/personal/juicyfruitstockoptions/app/scheduler/jobs.py)

----- 
From gemini discussion on Split brain multiple site operating code (Desktop vs Laptop)

The reason your portfolio data didn't "come over" is that **Named Volumes** are internal to Docker's virtual storage. Unlike the host bind mount you had before, they don't look at your local folder; they start empty and persist within Docker's own managed space.

To make this the "default restore behavior," we need to shift from a file-sync mindset to a **database-native sync** or a **centralized host** mindset.

Here are some thoughts on how to handle the "Master/Child" architecture and the syncing challenges you mentioned.

### 1. The Architecture: Centralized vs. Decentralized
Since your portfolio and trade data are pulled from Interactive Brokers (IB), the database is essentially a cache of the IB source of truth plus your unique "Analyst Ticker List."

* **The "Home Server" Approach (Recommended):**
    You host the primary MongoDB instance on your desktop in Warren. Use Cloudflare Tunnel (`cloudflared`) to securely expose the DB or the App UI. Your laptop becomes a "thin client"—it doesn't have its own DB; it just connects to the desktop's DB. This is the most "elegant" because there is zero syncing to manage.
* **The Syncing Approach (The "Crazy" Way):**
    You run a DB on both. When the laptop goes offline and comes back, it has to figure out which ticker list is newer. This leads to "Split Brain" scenarios where you have to decide which version of a note or a ticker list wins.

### 2. How would syncing occur? (The Elegant Approach)
If you want to keep two distinct databases in sync, don't try to sync the files. Instead, use a **Replica Set**.

MongoDB has built-in replication. You would define a "Primary" (Desktop) and a "Secondary" (Laptop). 
* **How it works:** Every write to the Desktop is recorded in an `oplog`. When the laptop connects, it "replays" that log to catch up.
* **Offline Handling:** MongoDB handles this natively. If the laptop is offline for a day, it stores a pointer to where it left off in the `oplog`. Once it reconnects via your Cloudflare proxy, it pulls the missing entries.
* **Note:** This is usually done for high availability, but it works for your dev-parity needs.



### 3. Implementation Ideas
Given your setup, here is how to handle the "restore" and "sync" requirements:

* **For the "Restore" problem:** To move your old data into the new named volume, you can use a temporary "sidecar" container to copy the files, or simply run a `mongodump` from the old folder and a `mongorestore` into the new volume.
* **For the "Sync" problem:** Instead of a complex Replica Set, consider a **State-Sync Script**. Since the IB data can be re-fetched, you only need to sync the `analyst_tickers` collection. A simple Python script using `pymongo` could "upsert" missing tickers from a central source whenever the app starts.

---

### Update to `features-requirements.md`

I have drafted the following entries for your ledger:

```markdown
### Database & Synchronization Requirements
- **FR-DB-01: Persistent Named Volumes:** Transition from host bind mounts to Docker Named Volumes to resolve filesystem permission issues (WiredTiger `Operation not permitted`).
- **FR-DB-02: Multi-Environment Data Parity:** Implement a mechanism to sync the "Analyst Ticker List" between Desktop (Master) and Laptop (Client).
- **FR-DB-03: Remote Access:** Utilize Cloudflare Tunnel to proxy the home-hosted instance for secure remote access without VPN overhead.
- **FR-DB-04: Offline Resiliency:** If a sync-based approach is used, the system must resolve conflicts for the `analyst_tickers` collection based on the latest timestamp.
- **FR-DB-05: IB Source of Truth:** Portfolio, trades, and orders should be treated as ephemeral/cacheable, with IB serving as the ultimate source of truth, reducing the need for heavy DB syncing of these specific items.
```

### Thoughts on the "Crazy" vs "Elegant"
The "Simple Elegant" approach is **Centralization**. If you are already planning to use Cloudflare to proxy into your home network, just let the laptop app point to the Desktop DB IP. 

If the laptop is truly offline (no internet), you just work with a local "mock" DB, and when you get back to a hotel or cafe, it reconnects to Warren. This avoids the headache of merging two different databases that have diverged. 

Would you like me to show you how to configure the MongoDB connection string to handle a "Remote Master" setup?