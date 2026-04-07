# Playwright E2E Integration Testing Plan & NFR

## Goal
Implement a robust, modern frontend testing framework using **Playwright (by Microsoft)**. This document outlines how we will organize the frontend tests so that autonomous AI coding agents can implement full test coverage in single, focused chat sessions.

## Strategy for Agentic Completion
An agent operates best within isolated, well-defined contexts. E2E tests are perfectly suited for this if organized correctly. To allow an agent to comfortably complete tests for a feature in a single chat session:

1.  **Page Object Model (POM) Strategy**: Create a specific class for each major page/modal (e.g., `PortfolioPage`, `TradeHistoryPage`, `TickerModal`). The agent's first session task is to just build the POM file. 
2.  **Modular Test Suites**: Break tests down by logical feature sets rather than having monolith test files. 
    *   *Session 1:* Set up Playwright config, Dockerize runner, and test simple `App.js` loading.
    *   *Session 2:* Write `PortfolioFilters.spec.js` (Tests the near-money, expiring buttons).
    *   *Session 3:* Write `TickerModal.spec.js` (Tests clicking a ticker and waiting for the API intercept).
3.  **Mocked Network State vs Live E2E**: Agents will rely heavily on Playwright's `page.route()` to mock backend API responses. This guarantees the frontend works decoupled from IBKR live state, making tests flakeless and quick for an agent to run and verify locally.

---

## Proposed F-R Addition
*(This section will be merged into `docs/features-requirements.md` under the Technical / Testing section once the initial setup is complete.)*

```markdown
### Automated Frontend E2E Testing (Playwright NFR)
**Non-Functional Requirement (NFR):** The Modern Standard for all frontend interaction and end-to-end integration testing in the Juicy Fruit project is **Playwright**. All cross-browser, DOM interaction, and UX verification must be automated through this framework.

- [ ] **Infrastructure Setup**:
    - [ ] `npm install -D @playwright/test` and initialize `playwright.config.js` in the frontend directory.
    - [ ] Setup Playwright to run Headless by default (Chromium, Firefox, WebKit) and integrate into Github Actions or local Docker CI.
- [ ] **Page Object Model (POM) Pattern**:
    - [ ] Ensure agents create/use classes in `frontend/tests/pages/` to abstract UI selectors (e.g., `PortfolioGridPage.js`, `StockAnalysisPage.js`).
    - [ ] Limit hardcoded selectors in `*.spec.js` files; mandate POM usage.
- [ ] **Mocked Network Reliability**:
    - [ ] Tests must use `page.route('**/api/portfolio/**', ...)` to intercept and provide static JSON responses for UI validation, ensuring tests do not fail due to IBKR rate limits or offline states.
- [ ] **Session-Focused Test Suites** (Ready for Agent Action):
    - [ ] **Auth & Navigation (`tests/specs/nav.spec.js`)**: Test login view, token expiration handling, and sidebar routing.
    - [ ] **Stock Analysis Flow (`tests/specs/analysis.spec.js`)**: Test the "Run Live Analysis" button states, row sorting, and spreadsheet download hook.
    - [ ] **Portfolio Filters (`tests/specs/portfolio.spec.js`)**: Test Coverage Status (Covered/Uncovered/Naked), Expiring, and Near-Money filter toggles.
    - [ ] **Ticker Modal Validation (`tests/specs/modal.spec.js`)**: Verify that clicking a ticker opens the modal, fires the parallel intercept requests, and handles the "Offline" degraded state badge.
```

## How to Proceed
When you are ready to begin, we will sequentially tackle each unchecked box in the above list. A single session should focus strictly on **"Infrastructure Setup"** or **"One specific `.spec.js` file"** to ensure complete context digestion and verification.
