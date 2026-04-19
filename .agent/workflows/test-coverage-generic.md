# Test Coverage

Testing is part of delivery, not a follow-up task.

## Expectations

- Add tests for the new behavior, not only the happy path.
- Cover negative cases, malformed inputs, and known failure modes.
- Where third-party entities are involved, prefer deterministic mocks or fixtures over live dependencies.
- Verify reconciliation and dedupe logic with realistic sample records.
- Verify exception-queue behavior for ambiguous or incomplete cases.
- Verify source-of-truth precedence when multiple systems can provide overlapping data.

## Minimum Review Questions

- What user or operator workflow is protected by this test?
- What regression would this test catch?
- Does the test cover both success and failure behavior?
- Does the test rely on unstable external systems unnecessarily?
- If data contracts changed, do tests assert the updated contract explicitly?
