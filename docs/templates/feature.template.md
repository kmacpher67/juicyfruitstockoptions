# Feature: <Feature Name>

## Summary

Describe the feature in plain language.

## Parent Requirement

- `docs/features-requirements.md` -> `<feature-id>`

## Business Purpose

Why this matters.

## Workflow

1. Describe the operator or user flow.
2. Describe what the system does.
3. Describe what success looks like.

## Inputs

List the inputs.

## Outputs

List the outputs.

## Data Sources

- Primary source:
  - Massive Financial API (https://massive.com/landing/financial-api)
- Secondary source:
  - yfinance (https://github.com/ranaroussi/yfinance)
- Manual source:

## Source-of-Truth Rules

Document precedence when sources disagree.

## Validation Rules

List what must be validated.

## Edge Cases and Failure Modes

- duplicate records
- missing identifiers
- partial files
- changed column names
- institution outage
- late-arriving corrections

Add feature-specific items here.

## Security and Privacy Considerations

Document access, masking, sensitive fields, retention, and logging constraints.

## Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Tests

List the tests that should exist.

## Documentation Updates

List any docs that should be updated when this feature changes.
