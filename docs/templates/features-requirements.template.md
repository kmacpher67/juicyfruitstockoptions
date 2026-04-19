# Features & Requirements

This document is the master roadmap and status board for the project.

## Purpose

Describe the project in 2-4 sentences.

Example:
- automate transaction intake from banks and card issuers
- normalize records into a common ledger
- support reconciliation, categorization, exception review, and reporting
- keep institution-specific behavior documented and testable

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
- Break work into small slices.

## Capability Areas

### 0. Operations, Bugs, and Maintenance
- [ ] `ops-example-001`: Example maintenance item.

### 1. Data Intake and Imports
- [ ] `imports-bank-csv-001`: Import bank CSV exports into normalized transaction records.
- [ ] `imports-card-pdf-001`: Support statement-PDF extraction or manual upload workflow.
- [ ] `imports-email-ingest-001`: Capture documents arriving by email and route them for review.

### 2. Third-Party Integrations
- [ ] `entity-registry-001`: Document institution contracts and trust rules.
- [ ] `api-sync-001`: Add API sync for supported institutions where feasible.
- [ ] `fallback-import-001`: Support file-based fallback when API access is unavailable or unstable.

### 3. Reconciliation and Matching
- [ ] `reconcile-ledger-001`: Match imported records against ledger entries.
- [ ] `reconcile-transfer-001`: Detect likely internal transfers across accounts.
- [ ] `reconcile-duplicates-001`: Detect and quarantine likely duplicates.

### 4. Categorization and Review
- [ ] `categorize-rules-001`: Rules-based categorization with operator override.
- [ ] `exception-queue-001`: Manual review queue for unmatched or ambiguous records.
- [ ] `audit-trail-001`: Preserve who changed what and why.

### 5. Reporting and Close Workflows
- [ ] `reports-monthly-close-001`: Monthly close checklist and status.
- [ ] `reports-tax-support-001`: Tax-prep export package and supporting detail.
- [ ] `reports-cashflow-001`: Reporting views for balances, spending, and account activity.

### 6. Security, Access, and Compliance
- [ ] `security-roles-001`: Role-based access and least-privilege review.
- [ ] `security-secrets-001`: Secret management and environment setup contract.
- [ ] `security-retention-001`: Data retention and backup policy.

## Changelog / Completed Work

Record completed milestones here or link to release notes.
