# Features & Requirements

This document is the master roadmap and status board for a finance operations application focused on banking, credit-card bookkeeping, reconciliation, close workflows, and tax-prep support.

## Purpose

This system should help intake records from financial institutions and other third parties, normalize them into consistent internal records, support reconciliation and exception review, and produce reliable outputs for bookkeeping and tax-prep work.

The design should assume:
- multiple institutions with different data quality and file formats
- both API and file-import workflows
- corrections, reversals, and duplicate records
- a need for traceability and human review

## Status Legend

- [ ] Proposed / Todo
- [/] In Progress
- [x] Done
- [!] Blocked / Needs Research
- [D] Deprecated / Reference Only

## Working Rules

- Use this file as the master source of truth for planned work.
- Create or update `docs/features/<feature_name>.md` for meaningful features.
- Create or update `docs/learning/<topic>.md` when research or external behavior needs to be preserved.
- Create an implementation plan in `docs/plans/` before non-trivial coding work.
- Break work into small slices with stable IDs.
- When a third-party entity is involved, update the entity registry and document source-of-truth rules.

## Capability Areas

### 0. Operations, Bugs, and Maintenance
- [ ] `ops-env-bootstrap-001`: Define environment bootstrap, secrets contract, and local/dev/test setup.
- [ ] `ops-backup-001`: Define backup, restore, and retention policy for operational and financial records.
- [ ] `ops-audit-log-001`: Add operator and system audit logging for important mutations and sync runs.

### 1. Entity Registry and External Contracts
- [ ] `entity-registry-001`: Create a registry of all third-party entities and their contracts.
- [ ] `entity-registry-bank-001`: Document each bank connection or import contract.
- [ ] `entity-registry-card-001`: Document each credit-card issuer connection or import contract.
- [ ] `entity-registry-accounting-001`: Document accounting-system export/import contract.
- [ ] `entity-registry-tax-001`: Document tax-prep export package contract.

### 2. Data Intake and Imports
- [ ] `imports-bank-csv-001`: Import bank CSV or XLSX exports into normalized transaction records.
- [ ] `imports-card-csv-001`: Import credit-card transaction exports into normalized transaction records.
- [ ] `imports-statement-pdf-001`: Support statement PDF upload and extraction workflow.
- [ ] `imports-manual-adjustment-001`: Allow documented manual entry or correction workflows with audit trail.
- [ ] `imports-email-dropbox-001`: Support intake of files from inbox or watched folder workflows.

### 3. Normalization and Canonical Data Model
- [ ] `normalize-records-001`: Define canonical transaction schema across all institutions.
- [ ] `normalize-accounts-001`: Define canonical account schema and institution/account mapping.
- [ ] `normalize-merchants-001`: Normalize merchant/payee naming for categorization and reporting.
- [ ] `normalize-currency-001`: Define handling for currencies, signs, credits, debits, and reversals.

### 4. Matching, Reconciliation, and Dedupe
- [ ] `reconcile-ledger-001`: Match imported transactions to internal ledger entries.
- [ ] `reconcile-transfer-001`: Detect likely internal transfers between owned accounts.
- [ ] `reconcile-duplicate-001`: Detect and quarantine likely duplicate records.
- [ ] `reconcile-correction-001`: Handle reversals, chargebacks, and corrected records.
- [ ] `reconcile-close-001`: Support monthly reconciliation completion status by account.

### 5. Categorization and Review
- [ ] `categorize-rules-001`: Add rules-based categorization with confidence scoring.
- [ ] `categorize-review-001`: Add operator review flow for uncategorized or low-confidence items.
- [ ] `categorize-split-001`: Support split transactions and multi-category assignments.
- [ ] `exception-queue-001`: Create an exception queue for unmatched, conflicting, or malformed records.

### 6. Balances, Statements, and Period Close
- [ ] `balances-ledger-vs-available-001`: Define balance semantics across institutions.
- [ ] `statements-monthly-001`: Track monthly statement availability and import status.
- [ ] `close-checklist-001`: Create monthly close checklist by entity/account/period.
- [ ] `close-lock-001`: Add optional period lock after reconciliation and review are complete.

### 7. Reporting and Tax-Prep Support
- [ ] `reports-cashflow-001`: Build cashflow and spend reporting views.
- [ ] `reports-account-activity-001`: Build account activity reports and downloadable extracts.
- [ ] `reports-cpa-package-001`: Create CPA/tax-prep export package with supporting detail.
- [ ] `reports-year-end-001`: Add year-end support workflow and open-items checklist.

### 8. Security, Privacy, and Compliance
- [ ] `security-roles-001`: Define role-based access and least-privilege model.
- [ ] `security-secrets-001`: Define secrets handling, credential storage, and rotation rules.
- [ ] `security-pii-001`: Define masking and logging rules for sensitive financial data.
- [ ] `security-retention-001`: Define retention and deletion rules.

### 9. Integrations and Sync Reliability
- [ ] `sync-api-001`: Add API-based sync where supported.
- [ ] `sync-fallback-import-001`: Add file-import fallback where APIs are unavailable or unstable.
- [ ] `sync-telemetry-001`: Record sync telemetry, failures, and last-success timestamps.
- [ ] `sync-idempotency-001`: Ensure imports and syncs are idempotent.

### 10. Open Questions and Research
- [ ] `research-identity-001`: What fields are stable enough to identify the same transaction across systems?
- [ ] `research-pending-vs-posted-001`: How should pending vs posted transactions be modeled?
- [ ] `research-statement-authority-001`: When statement files disagree with API data, which source wins?
- [ ] `research-tax-boundaries-001`: Which outputs are bookkeeping support vs formal tax-prep artifacts?

## Changelog / Completed Work

Record completed milestones here or link to release notes.
