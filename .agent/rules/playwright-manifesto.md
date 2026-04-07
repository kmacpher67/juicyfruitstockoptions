---
trigger: always_on
---

# Playwright Implementation Manifesto (Juicy Fruit)

## 1. Architectural Mandates
* **Page Object Model (POM) Only**: No raw selectors are allowed in `*.spec.js` files. All UI interactions must be abstracted into classes within `frontend/tests/pages/`.
* **Decoupled Testing (Mocking)**: Do not rely on live IBKR or Yahoo Finance data for UI/UX verification. Use `page.route()` to intercept API calls and provide static JSON snapshots.
* **Atomic Tests**: Every test must be independent. Use `global-setup.js` to manage authentication states so tests do not have to perform the login flow repeatedly.

## 2. Selector Priority (User-Centric)
When creating Page Objects, use locators in this strict order of preference:
1.  **Role/Label**: `page.getByRole('button', { name: 'Run Live Analysis' })`.
2.  **Text Content**: `page.getByText('Annualized Yield %')`.
3.  **Data-TestID**: `page.getByTestId('juicy-fruit-submit')` (Use as an escape hatch for complex grids).
4.  **Avoid**: Never use brittle CSS classes (e.g., `.css-1v8z8`) or absolute XPaths.

## 3. Stability & Performance
* **No Manual Waits**: Use of `page.waitForTimeout()` is strictly prohibited. Use web-first assertions like `expect(locator).toBeVisible()` that include automatic retries.
* **Healer Mode**: If a test fails due to a UI refinement, run `npx playwright test --heal` to evaluate and propose Page Object updates before rewriting test logic.

## 4. Definition of Done for Testing Tasks
An agent has not completed a testing task unless:
* The test passes in a **Headless** environment.
* The code follows the hierarchical naming conventions defined in `docs/features-requirements.md`.
* Any new feature detail or learning discovered during implementation is memorialized in `docs/features/` or `docs/learning/`.