# Implementation Plan: Portfolio Detail Link

## Target Issue
`docs/features-requirements.md:L320`
- [ ] **LINK to Stock Analysis Detail**: Portfolio Page quick link next to ticker and existing Google / Yahoo links should use the external-link arrow-out-of-box glyph for Stock Analysis detail, not a `D` text label. Improve the glyph color/contrast so it reads clearly against the background, and keep using the same shared modal detail window logic used from the ticker analysis list.

## Proposed Changes

### 1. `frontend/src/components/PortfolioGrid.jsx`
- Keep the existing external-link arrow-out-of-box glyph (`lucide-external-link`) as the stock-analysis quick link on the portfolio row.
- Restyle the glyph so it is easier to see against the portfolio grid background and remains visually distinct from the Google / Yahoo quick links.
- Add or confirm tooltip/accessible labeling that explicitly communicates Stock Analysis detail while preserving the compact icon treatment.
- Keep the existing click behavior wired to `params.context.onTickerClick(sym)` so it continues to open the shared `TickerModal.jsx` logic already used elsewhere.
- Preserve row-click behavior by keeping the control isolated and using `e.stopPropagation()` if needed.

### 2. `docs/features-requirements.md`
- Leave the item unchecked until the portfolio external-link glyph contrast and labeling are corrected and validated.

### 3. Related Docs Review
- Treat this doc as the primary starting point for the portfolio-view quick-link fix.
- Use `docs/plans/implementation_plan-20260328-stock_analysis_profile_tab.md` only as secondary context for Yahoo / website link styling patterns inside `TickerModal`, not as the primary implementation plan for the portfolio glyph issue.

## Verification Plan

### Automated Tests
- Run `npm test` or `pytest` to ensure no build/test breakages, though this is primarily a frontend UI styling change.

### Manual Verification
1. Open the UI to the "My Portfolio" view.
2. Locate the "Ticker" column.
3. Hover over a ticker to see the quick links appear.
4. Verify that Google, Yahoo, and the external-link arrow-out-of-box stock-analysis quick link are visible.
5. Verify the stock-analysis glyph has stronger contrast than before and remains distinguishable from the background in normal and hover states.
6. Verify tooltip text or accessible labeling clearly identifies the glyph as the Stock Analysis detail action.
7. Click the stock-analysis quick link and ensure it opens the 6-tab Ticker Analysis modal successfully, utilizing the shared logic.
8. Verify the existing ticker text click also still opens the modal correctly.

## Review Process
Requesting user review before executing.
