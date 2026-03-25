# Remove Opportunities from Portfolio View

## Goal Description
The user wants to remove the "opportunities" grid from the Portfolio View of the dashboard. This corresponds to the `AlertsDashboard` component which displays portfolio alerts, expiration alerts, and the dividend scanner at the top of the "My Portfolio" view.

## Proposed Changes

### Frontend Components
#### [MODIFY] [Dashboard.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/Dashboard.jsx)
- Remove the `<AlertsDashboard ... />` component rendering block from the `viewMode === 'PORTFOLIO'` section (lines 507-516).
- This will remove the entire row of opportunities and alerts from above the main portfolio grid.

### Documentation
#### [MODIFY] [features-requirements.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/features-requirements.md)
- Update line 160 to mark the task as explicitly completed: `- [x] **Portfolio View**: ...`.

## Verification Plan

### Automated Tests
- Run `pytest` to ensure no backend regressions (though this is purely a frontend change).
- Run `npm run build` in the `frontend/` directory to ensure there are no compilation errors in the React application after removing the component.

### Manual Verification
- The user can start the app and navigate to "My Portfolio" to verify that the opportunities grid is removed.
