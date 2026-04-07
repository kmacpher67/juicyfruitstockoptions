# Stock Analysis HTTP + Scheduler Sharding Configuration

## Purpose
This runbook documents how to configure stock-analysis HTTP pacing and scheduler sharding so daily yfinance-heavy runs avoid burst traffic and reduce `HTTP 429` risk.

## Scope
These settings apply to stock-analysis execution paths that use `stock_analysis_http_config`:
- Daily scheduled stock-analysis run (`stock_comparison_job`)
- Stock-analysis service HTTP pacing defaults

Sharding settings affect daily scheduled runs only. Manual "Run Live Comparison" remains a single run.

Data-freshness thresholds use a separate `system_config` document (`_id: data_freshness_config`) and are configurable from the same Dashboard Settings modal.

## Config Keys (`system_config._id = stock_analysis_http_config`)
- `download_batch_size` (int, min 1): number of symbols per history download batch.
- `batch_pause_sec` (float, min 0): pause between history batches.
- `request_throttle_interval_sec` (float, min 0): minimum gap between outbound yfinance requests.
- `scheduler_sharding_enabled` (bool): enable splitting daily ticker list into shards.
- `scheduler_shard_size` (int, min 1): symbols per scheduler shard.
- `scheduler_shard_pause_sec` (float, min 0): pause between shard executions.

## Admin UI Path
1. Open Dashboard.
2. Open `Dashboard Settings`.
3. Use the `Stock Analysis HTTP` section (admin only).
4. Click `Save All`.

Related UI component:
- `frontend/src/components/SettingsModal.jsx`

## API Configuration (Manual)
Use authenticated admin API calls.

Read current values:
```bash
curl -s -H "Authorization: Bearer <TOKEN>" \
  http://localhost:8000/api/settings/stock-analysis-http
```

Update values:
```bash
curl -s -X POST -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  http://localhost:8000/api/settings/stock-analysis-http \
  -d '{
    "download_batch_size": 4,
    "batch_pause_sec": 1.5,
    "request_throttle_interval_sec": 0.8,
    "scheduler_sharding_enabled": true,
    "scheduler_shard_size": 20,
    "scheduler_shard_pause_sec": 15.0
  }'
```

## Mongo Configuration (Manual)
If API access is unavailable, update directly:

```javascript
db.system_config.updateOne(
  { _id: "stock_analysis_http_config" },
  {
    $set: {
      download_batch_size: 4,
      batch_pause_sec: 1.5,
      request_throttle_interval_sec: 0.8,
      scheduler_sharding_enabled: true,
      scheduler_shard_size: 20,
      scheduler_shard_pause_sec: 15.0
    }
  },
  { upsert: true }
)
```

## Verification Checklist
1. Confirm config readback from `GET /api/settings/stock-analysis-http`.
2. Confirm scheduler run logs include shard execution lines:
   - `Scheduler: running stock comparison shard ...`
3. Confirm no large burst pattern in logs during daily run.
4. Confirm `stock_ingest_runs` telemetry continues to record per-run diagnostics:
   - `source_used`
   - `rows_updated`
   - `stale_hit_ratio`
   - `failure_count`
   - `failures`
5. Confirm data-freshness settings read and write through `GET/POST /api/settings/data-freshness`:
   - `price_open_min`, `price_closed_min`
   - `mixed_open_min`, `mixed_closed_min`
   - `profile_open_min`, `profile_closed_min`

## Suggested Starting Values
- `download_batch_size`: `4` to `8`
- `batch_pause_sec`: `1.0` to `3.0`
- `request_throttle_interval_sec`: `0.8` to `2.0`
- `scheduler_sharding_enabled`: `true` for larger ticker universes
- `scheduler_shard_size`: `15` to `30`
- `scheduler_shard_pause_sec`: `10` to `30`

Tune gradually and observe 429/error rate before tightening.
