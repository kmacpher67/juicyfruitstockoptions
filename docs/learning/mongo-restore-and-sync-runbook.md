# Mongo Restore and Sync Runbook (Desktop, Dev Laptop, Optional Cloud DR)

## Why this exists
This runbook documents the intended default behavior and the repeatable restore/sync workflow so we do not lose account/user/trade/portfolio data during environment changes.

## Decision summary
- MongoDB runtime storage uses a Docker named volume (`mongo_data`) for reliability across Docker-on-WSL/Windows/Linux host filesystem edge cases.
- Default restore behavior prefers **full database restore** (`mongodump` + `mongorestore`).
- Legacy JSON (`mongo_backup.json`) is treated as a **single-collection fallback** path only.

## Storage answer (runtime vs backup)
- Runtime data location: Docker named volume (`juicyfruitstockoptions_mongo_data`) mounted at `/data/db` in the Mongo container.
- Formal backup location: dated artifacts under `./backups/mongo/...` (portable dump files + metadata/checksum), not raw WiredTiger files.
- Offsite backup location: encrypted copy of backup artifacts to designated Google Drive folder.

## Intent and constraints
- Preserve complete operational data: `users`, `system_config`, `ibkr_holdings`, `ibkr_nav_history`, `ibkr_trades`, `ibkr_orders`, `stock_data`, and related collections.
- Avoid misleading “successful restore” states that only repopulate one collection.
- Keep remote access safe: never expose MongoDB directly to WAN; expose app endpoints via Cloudflare Tunnel if needed.

## Current defaults in repo
- Startup helper: `./docker-run-stock-app.sh`
- Auto-restore default: enabled (`AUTO_RESTORE_ON_START=true`)
- Restore priority:
1. `./mongo_dump` full DB restore via `./scripts/restore_mongo.sh`
2. `mongo_backup.json` legacy JSON import via `./scripts/reload_docker_mongo.sh`
- Legacy JSON default collection: `stock_data`

## Repeatable restore workflows

### 0) Portable artifact workflow (recommended default)
Create a full backup artifact (dump + manifest + checksums):
```bash
./scripts/mongo_backup_artifact.sh
```

Package the latest artifact for transfer (preserves `backups/...` path layout):
```bash
./scripts/mongo_backup_package.sh --latest
```

Validate a specific artifact:
```bash
./scripts/mongo_backup_validate.sh ./backups/mongo/YYYY/MM/DD/<timestamp>
```

Restore from latest valid artifact:
```bash
./scripts/mongo_restore_artifact.sh --latest
```

Restore from a specific artifact:
```bash
./scripts/mongo_restore_artifact.sh --artifact ./backups/mongo/YYYY/MM/DD/<timestamp>
```

Run explicit post-restore smoke gate:
```bash
./scripts/mongo_restore_smoke_check.sh
```

### 0.1) Manual transfer to Desktop (tar.gz path)
1. Create package on source machine:
```bash
./scripts/mongo_backup_package.sh --latest
```
2. Upload resulting file `./backups/mongo_backup_<backup_id>.tar.gz` to transfer target.
3. On Desktop machine, download file into repo `./backups/`.
4. Unpack and restore:
```bash
./scripts/mongo_backup_unpack.sh ./backups/mongo_backup_<backup_id>.tar.gz
./scripts/mongo_restore_artifact.sh --latest
```

Google Drive backup folder:
- `https://drive.google.com/drive/folders/143kk-X98X-JBuA-73ZI9GfpOrX3fvKok`

## Automation setup (Linux)
Preferred scheduler is `systemd --user` timer; cron remains fallback.

### Install daily timer (preferred)
```bash
./scripts/install_mongo_backup_systemd_timer.sh
```

Optional schedule override (UTC):
```bash
SCHEDULE_UTC=03:30:00 ./scripts/install_mongo_backup_systemd_timer.sh
```

### Install cron fallback
```bash
./scripts/install_mongo_backup_cron.sh
```

Optional cron schedule override:
```bash
CRON_SCHEDULE="30 3 * * *" ./scripts/install_mongo_backup_cron.sh
```

### Windows equivalent
- Use Windows Task Scheduler to run:
  - `bash -lc "cd <repo> && ./scripts/mongo_backup_pipeline.sh >> logs/mongo_backup_pipeline.log 2>&1"`
- Match the same environment values used in `scripts/mongo_backup_pipeline.env`.

### Pipeline command (what scheduler runs)
```bash
./scripts/mongo_backup_pipeline.sh
```

### Google Drive automation configuration
By default, pipeline upload is skipped unless `DRIVE_FOLDER_ID` is configured.

Native Drive automation uses:
- `scripts/mongo_backup_drive.py upload-and-verify` (upload + checksum verify)
- `scripts/mongo_backup_drive.py retention` (remote retention cleanup)

Create env file from template:
```bash
cp scripts/mongo_backup_pipeline.env.example scripts/mongo_backup_pipeline.env
```

Set token source in env file (one of):
1. `DRIVE_ACCESS_TOKEN` (short-lived direct token)
2. `DRIVE_ACCESS_TOKEN_CMD` (command that prints token, preferred for automation)

Systemd installer auto-loads:
- `scripts/mongo_backup_pipeline.env` (if present)

### Optional custom upload hook configuration
If you do not use native Drive path, you can still use custom upload command.
```bash
BACKUP_UPLOAD_CMD='<your-upload-command>' ./scripts/mongo_backup_pipeline.sh
```

Example with `rclone` (if installed/configured):
```bash
BACKUP_UPLOAD_CMD='rclone copyto' BACKUP_UPLOAD_TARGET='gdrive:JuicyFruit/mongo_backups' ./scripts/mongo_backup_pipeline.sh
```

### A) Full database restore (recommended)
1. Ensure stack is up and Mongo is healthy.
2. Restore:
```bash
./scripts/restore_mongo.sh ./mongo_dump
```
3. Validate key collections:
```bash
docker exec stock_portal_mongo mongosh --quiet -u admin -p admin123 --authenticationDatabase admin --eval "db.getSiblingDB('stock_analysis').users.countDocuments({})"
docker exec stock_portal_mongo mongosh --quiet -u admin -p admin123 --authenticationDatabase admin --eval "db.getSiblingDB('stock_analysis').ibkr_holdings.countDocuments({})"
docker exec stock_portal_mongo mongosh --quiet -u admin -p admin123 --authenticationDatabase admin --eval "db.getSiblingDB('stock_analysis').stock_data.countDocuments({})"
```

### B) Legacy JSON fallback (single collection only)
Use only when full dump is unavailable.
```bash
MONGO_COLLECTION_NAME=stock_data ./scripts/reload_docker_mongo.sh mongo_backup.json
```
Note: this does not restore users/settings/other collections.

## Desktop -> Dev Laptop sync pattern
Recommended topology:
- Desktop: primary runtime/source of truth.
- Dev Laptop: replica for development/testing.

Suggested pipeline:
1. On Desktop, generate full dump:
```bash
docker exec stock_portal_mongo mongodump \
  --username admin --password admin123 --authenticationDatabase admin \
  --out /tmp/mongo_dump
docker cp stock_portal_mongo:/tmp/mongo_dump ./mongo_dump
```
2. Transfer `mongo_dump` securely (encrypted channel/storage).
3. On Laptop, restore with `./scripts/restore_mongo.sh ./mongo_dump`.
4. Run validation counts for baseline collections.

## Cloud/remote note
- If app is remotely accessed from outside home network, use Cloudflare Tunnel for web/API endpoints.
- Do not publish MongoDB port (`27017`) to the public internet.
- If adding cloud, start as DR/backup replica, not multi-writer primary, until conflict-resolution policy is designed.

## Related files
- `docker-run-stock-app.sh`
- `scripts/restore_mongo.sh`
- `scripts/reload_docker_mongo.sh`
- `scripts/mongo_backup_artifact.sh`
- `scripts/mongo_backup_validate.sh`
- `scripts/mongo_backup_package.sh`
- `scripts/mongo_backup_unpack.sh`
- `scripts/mongo_backup_pipeline.sh`
- `scripts/mongo_backup_drive.py`
- `scripts/mongo_backup_pipeline.env.example`
- `scripts/mongo_backup_retention.sh`
- `scripts/mongo_restore_smoke_check.sh`
- `scripts/install_mongo_backup_systemd_timer.sh`
- `scripts/install_mongo_backup_cron.sh`
- `scripts/mongo_restore_artifact.sh`
- `restore_mongo.py`
- `docs/features/automated_mongo_backup.md`
- `docs/learning/mongodb-portable-backup-contract.md`
- `docs/learning/mongodb-backup-validation-checklist.md`
