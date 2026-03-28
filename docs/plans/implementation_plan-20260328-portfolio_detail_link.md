# Implementation Plan: Portfolio Detail Link

## Target Issue
`docs/features-requirements.md:L200`
- [ ] **LINK to Stock Analysis Detail**: Portfolio Page Add small link next to ticker and existing Google, Yahoo finance, D to modal detail window shared logic same pop up window used from the ticker analysis list.

## Proposed Changes

### 1. `frontend/src/components/PortfolioGrid.jsx`
- Add a small text button `D` next to the existing `G` (Google Finance) and `Y` (Yahoo Finance) quick links in the ticker column renderer.
- On click, this `D` link will trigger `params.context.onTickerClick(sym)` seamlessly leveraging the already-existing modal logic (`TickerModal.jsx`) that the Dashboard view provides.
- Wrap it in a span with appropriate styling (e.g., `text-emerald-400 cursor-pointer hover:text-emerald-300 ml-1`) and a `title="Ticker Detail Analysis"` tooltip to match the aesthetic. (Using an `onClick` with `e.stopPropagation()` if necessary to prevent bubbling, though typical span-in-cell logic is safe here).

### 2. `docs/features-requirements.md`
- Mark line 200 as done once implemented and validated.

## Verification Plan

### Automated Tests
- Run `npm test` or `pytest` to ensure no build/test breakages, though this is primarily a frontend UI styling change.

### Manual Verification
1. Open the UI to the "My Portfolio" view.
2. Locate the "Ticker" column.
3. Hover over a ticker to see the quick links appear.
4. Verify that `G`, `Y`, and a new `D` link are visible.
5. Click the `D` link and ensure it opens the 6-tab Ticker Analysis modal successfully, utilizing the shared logic.
6. Verify the existing ticker text click also still opens the modal correctly.

## Review Process
Requesting user review before executing.
