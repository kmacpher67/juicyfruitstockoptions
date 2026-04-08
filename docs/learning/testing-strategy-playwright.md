# Strategic Blueprint: Frontend Integration & E2E
**Topic Key:** `testing-strategy-playwright` Integration Specs

## 1. The "Why" (The North Star)
We prioritize **Confidence over Coverage**. We don't test every button hover; we test that the user can successfully execute a trade and view their "Juicy Fruit" dashboard.
* **Goal:** Zero "Flaky" tests. If a test fails, it must be a real bug, not a timing issue. Refer to them as Integration Specs. Not "Scripts" as it sounds throwaway; "Specs" implies a source of truth for behavior.
* **Speed:** Keep the feedback loop under 3 minutes for the core integration suite.

## 2. Framework Architecture: Playwright
We use Playwright (Microsoft) because it communicates directly with the browser via CDP, eliminating the "wait-and-hope" flakiness of legacy tools.

### Structural Requirements
* **Page Object Model (POM):** All selectors live in `tests/pages/`. Spec files (tests) must never contain raw CSS/XPath selectors. They call methods like `DashboardPage.getPortfolioValue()`.
* **Locators:** Priority order for selecting elements:
    1.  `role` (e.g., `button`, `heading`) — *Ensures accessibility.*
    2.  `label` / `text` — *Mirrors user experience.*
    3.  `data-testid` — *The "Escape Hatch" for complex UI components.*
* **Atomic State:** Use `global-setup.ts` to handle authentication. Tests should start "logged in" by injecting a storage state, not by clicking through a login form every time.

## 3. Agent Instructions (The "Ditch Digger" Rules)
*When an agent is tasked with creating or updating tests, they must adhere to these constraints:*

* **No Hardcoded Delays:** `page.waitForTimeout()` is a firing offense. Use web-first assertions like `expect(locator).toBeVisible()`.
* **Auto-Healing:** If a selector breaks due to a UI refinement, run `npx playwright test --heal` first to propose a POM update before rewriting the test logic.
* **Boundary Strategy:**
    * **Unit (Vitest):** Math, data parsing, and logic (e.g., Option Greeks calculations).
    * **Integration (Playwright):** Data flow from API to UI (e.g., "Does the AMZN ticker update on the dashboard?").
    * **E2E (Playwright):** Critical user paths (e.g., "Full trade execution flow").

## 4. Maintenance & Regressions
* **Feature Updates:** When a feature is "refined" (e.g., changing "Sell" to "Close Position"), the agent is responsible for updating the **Label** in the Page Object, not the logic in the Spec.
* **Failure Protocol:** A failing test is either a **Regression** (the code broke) or an **Evolution** (the UI changed). Agents must identify which it is before applying a fix.

## 5. Local CI-Parity Docker Run (Node-Version Safe)
When host Node versions drift (for example Node 21 while Vite requires Node 20/22), run Integration Specs in Docker so local and CI behavior stay aligned.

* **One command (recommended):**
  * `./scripts/run-playwright-docker.sh`
* **What it does:**
  * Uses `docker-compose.yml` + `docker-compose.e2e.yml`.
  * Starts frontend/backend dependencies in containers.
  * Runs Playwright inside pinned image `mcr.microsoft.com/playwright:v1.59.1-jammy`.
  * Exits with Playwright's status code for CI-friendly pass/fail behavior.
* **Via test umbrella script:**
  * `PLAYWRIGHT_IN_DOCKER=1 ./test-all.sh`
* **Config contract used by Docker run:**
  * `PLAYWRIGHT_BASE_URL=http://frontend:5173`
  * `PLAYWRIGHT_SKIP_WEBSERVER=true`
  * `CI=true`

---

### Why this works for you:
By putting this in `docs/learning/`, you can point your coding agent to it and say: *"Read the strategy in `/docs/learning/testing-strategy-playwright.md` and then refactor the 'Juicy Fruit' watchlist tests to follow the POM pattern."* It stops them (various Agent Code monkeys) from hallucinating their own way of doing things.
