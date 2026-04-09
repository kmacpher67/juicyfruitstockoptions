# Implementation Plan: MongoDB Portable Backup + Restore Validation

## Goal
Move from ad-hoc/raw-volume recovery to a formal backup workflow that is portable, integrity-checked, and reliably restorable with objective validation gates.

## Non-Goals
- No immediate production architecture change (single-host runtime remains valid).
- No direct MongoDB internet exposure.
- No replacement of current app-level JSON export for analytics use cases; this plan focuses on full-DB recoverability.

## Deliverables
1. Full backup artifact contract (`mongo_dump` + `manifest.json` + `sha256sums.txt`).
2. Repeatable backup command path writing to dated `./backups/mongo/...` folders.
3. Repeatable restore command path that selects the latest valid artifact.
4. Post-restore validation script/checklist with fail-fast behavior.
5. Offsite encrypted copy policy (Google Drive target + verification).
6. Restore drill process with RPO/RTO tracking.

## Phase 1: Artifact Contract + Local Storage
1. Define canonical artifact directory structure.
2. Define required manifest fields.
3. Generate SHA256 checksums for all backup files.
4. Add docs and examples in runbook.

Exit criteria:
1. A single command can create an artifact with all required files.
2. Artifact validation can detect missing/invalid files.

## Phase 2: Restore Selection + Validation Gate
1. Implement retrieval logic: latest valid artifact by manifest+checksum.
2. Restore using `mongorestore` from selected artifact.
3. Run required collection and baseline count checks.
4. Run auth smoke test (`/api/token`) and capture result.

Exit criteria:
1. Restore is blocked/fails if validation gate fails.
2. Success output includes collection counts and smoke-test pass.

## Phase 3: Offsite Copy + Drill Process
1. Define encrypted offsite upload path (Google Drive folder).
2. Define periodic download verification with checksum re-check.
3. Define monthly restore drill template and storage location for drill logs.
4. Track observed RTO and artifact recency against RPO target.

Exit criteria:
1. Offsite backup can be retrieved and validated from scratch.
2. At least one recorded restore drill exists with pass/fail evidence.

## Operational Policy (Proposed)
1. Backup cadence: daily.
2. Retention: 14 daily / 8 weekly / 12 monthly snapshots.
3. Required baseline collections: `users`, `user_settings`, `system_config`, `ibkr_holdings`, `ibkr_nav_history`, `ibkr_trades`, `stock_data`.
4. Legacy `mongo_backup.json` remains fallback and is explicitly marked non-authoritative for full-environment restore.

## Risks and Mitigations
1. Risk: false confidence from partial backups.
   Mitigation: mandatory validation gate and smoke tests.
2. Risk: corrupted artifact accepted as latest.
   Mitigation: checksum and manifest validation before restore.
3. Risk: offsite copy drift/staleness.
   Mitigation: scheduled pull-and-verify job and recency checks.

## Verification Plan
1. Run backup command twice and verify artifact structure both times.
2. Perform clean restore into test instance and run checklist.
3. Confirm auth works after restore.
4. Confirm required collections and baseline counts are present.

## Related Documents
- `docs/features-requirements.md`
- `docs/learning/mongo-restore-and-sync-runbook.md`
- `docs/learning/mongodb-portable-backup-contract.md`
- `docs/learning/mongodb-backup-validation-checklist.md`
