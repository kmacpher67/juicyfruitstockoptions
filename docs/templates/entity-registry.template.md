# Entity Registry

Use this document as the index of all third-party entities the system depends on.

Each entity should either have a section here or its own linked document in `docs/features/` or `docs/learning/`.

## Purpose

The entity registry helps answer:
- what outside systems we depend on
- what each one is authoritative for
- how records are identified and matched
- what setup or credentials are required
- what known risks and failure modes exist
- what fallback exists if the entity is unavailable

## Entity Categories

- Banks
- Credit-card issuers
- Payment processors
- Payroll systems
- Accounting platforms
- Tax software
- Cloud storage providers
- Email/document intake providers
- OCR or extraction vendors

## Entity Index

| Entity ID | Name | Category | Integration Type | Authority Level | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `bank-example-001` | Example Bank | Bank | CSV Import | Statement-authoritative | Proposed | Replace with real entity |
| `card-example-001` | Example Card | Credit Card | API + CSV | Posted-authoritative | Proposed | Replace with real entity |

## Standard Entity Contract Template

Copy this section for each real entity.

### `<entity-id>`: `<Entity Name>`

#### Summary

Describe what this entity is and why the project depends on it.

#### Category

Bank / Credit Card / Payroll / Accounting Platform / Tax Software / Other

#### Business Process Supported

Examples:
- transaction intake
- statement retrieval
- balance sync
- reconciliation support
- tax-prep export

#### Integration Type

Examples:
- API
- CSV import
- XLSX import
- PDF statement upload
- email attachment intake
- manual export/import

#### Authority Rules

Document what this entity is authoritative for.

Examples:
- statement PDF is authoritative for finalized monthly statement values
- posted transaction export is authoritative for settled card activity
- API balance is operational only and may be stale or provisional

#### Data Provided

List key data types this entity provides.

#### Stable Identifiers

List identifiers safe to use for matching, dedupe, or reconciliation.

#### Unstable Fields / Known Caveats

List fields that often change or cannot be trusted blindly.

Examples:
- pending transaction IDs
- merchant descriptions
- memo text
- available balance during settlement windows

#### Freshness Expectations

Document how fresh the data normally is and what lag is acceptable.

#### Failure Modes

Examples:
- API outages
- changed CSV headers
- delayed posting
- duplicate export rows
- corrections after settlement
- MFA/login issues

#### Fallback Strategy

What should the system do if this entity is unavailable?

#### Setup and Credentials

Describe secrets, accounts, permissions, and operational prerequisites.

#### Security and Privacy Notes

Describe masking, logging, retention, and least-privilege constraints.

#### Testing Notes

Describe how to test integrations safely without depending on live data.

#### Documentation Links

- Feature docs:
- Learning docs:
- Runbooks:
