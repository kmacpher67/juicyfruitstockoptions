# MongoDB Portable Backup Contract

## Purpose
Define a formal and repeatable MongoDB backup contract for Juicy Fruit so backups are portable, verifiable, and recoverable across Desktop/Laptop environments.

## Scope
- Primary database: `stock_analysis`
- Backup method: `mongodump` artifact (full database)
- Legacy fallback: `mongo_backup.json` is single-collection only and not a full-environment backup

## Contract: Artifact Layout
Each backup run writes to a dated folder:

`./backups/mongo/YYYY/MM/DD/<timestamp>/`

Required contents:
1. `mongo_dump/`
2. `manifest.json`
3. `sha256sums.txt`

Optional contents:
1. `restore-log.txt`
2. `verify-log.txt`

## Contract: `manifest.json` Fields
Minimum required fields:
1. `backup_id`
2. `created_at_utc`
3. `source_host`
4. `source_os`
5. `mongo_image`
6. `mongo_version`
7. `database_names`
8. `collections`
9. `collection_counts`
10. `tool_versions` (`mongodump`, `mongorestore`)
11. `notes`

## Contract: Integrity
- `sha256sums.txt` must include checksums for all files in the artifact.
- A backup is considered valid only if checksum verification passes before restore.
- Retrieval logic must select the latest artifact with:
  1. complete required files
  2. parseable manifest
  3. passing checksum verification

## Contract: Restore Validation Gate
After restore, validate all required baseline collections exist:
1. `users`
2. `user_settings`
3. `system_config`
4. `ibkr_holdings`
5. `ibkr_nav_history`
6. `ibkr_trades`
7. `stock_data`

Validation must also assert:
1. baseline count checks are non-zero (or explicitly waived for clean-room envs)
2. login-path smoke test succeeds
3. validation output is logged in `verify-log.txt`

## Contract: Storage Strategy
Primary local artifact location:
- `./backups/mongo/...`

Offsite copy:
- Encrypted artifact copy uploaded to designated Google Drive folder.
- Offsite copy is not valid until download + checksum verification is successful.

## Contract: Retention
Target policy (proposed):
1. Daily backups: keep 14 days
2. Weekly backups: keep 8 weeks
3. Monthly backups: keep 12 months

## Recovery SLOs
Define and document:
1. RPO target (maximum acceptable data loss window)
2. RTO target (maximum acceptable restore duration)

## Related Docs
- `docs/learning/mongo-restore-and-sync-runbook.md`
- `docs/learning/mongodb-backup-validation-checklist.md`
- `docs/plans/implementation_plan-20260409-mongodb-portable-backup-validation.md`
