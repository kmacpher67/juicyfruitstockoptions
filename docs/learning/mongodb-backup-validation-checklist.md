# MongoDB Backup Validation Checklist

Use this checklist after any full restore and during scheduled restore drills.

## 1) Pre-Restore Checks
1. Confirm target environment and host.
2. Confirm artifact path.
3. Confirm required files exist:
   - `mongo_dump/`
   - `manifest.json`
   - `sha256sums.txt`
4. Run checksum verification and record result.

## 2) Restore Execution
1. Ensure MongoDB container is running and healthy.
2. Execute full restore using `mongorestore` workflow.
3. Capture stdout/stderr into `restore-log.txt`.

## 3) Required Collections Check
Verify existence of:
1. `users`
2. `user_settings`
3. `system_config`
4. `ibkr_holdings`
5. `ibkr_nav_history`
6. `ibkr_trades`
7. `stock_data`

## 4) Baseline Count Check
Verify counts are non-zero (or document reason for exception):
1. `users`
2. `stock_data`
3. `ibkr_holdings`
4. `ibkr_nav_history`
5. `ibkr_trades`

## 5) Auth/Access Smoke Test
1. Run token login request.
2. Confirm successful auth response.
3. If auth fails, restore is considered failed.

## 6) Metadata Sanity Check
1. Confirm `manifest.json` environment fields match expected source.
2. Confirm backup timestamp recency is within accepted RPO window.

## 7) Completion Gate
A restore is marked successful only if all are true:
1. checksum verification passed
2. restore command succeeded
3. required collections exist
4. baseline counts passed (or approved exception documented)
5. auth smoke test passed

## 8) Drill Recording
For monthly drills, record:
1. date/time
2. operator
3. artifact id
4. elapsed restore duration (RTO observed)
5. pass/fail and follow-up actions
