---
description: Rules for CI/CD Playwright testing and GitHub Actions
---

# Agent Workflow: CI/CD & Testing Guidelines

When instructed to modify CI/CD pipelines or write new tests for Juicy Fruit, adhere to the following rules:

1. **Frontend Isolation**: The GitHub Action builds ONLY the frontend context (`npm run dev`) and relies completely on the Playwright network mock intercepts (`page.route`). Do NOT start `docker-compose` or the backend services in the CI pipeline unless explicitly instructed to expand to full "True E2E" tests.
2. **Deterministic UI**: Always intercept dynamic API calls in `*.spec.js` using static JSON mocks so that test failures are purely related to UI/UX component regressions and not upstream IBKR rate limits.
3. **Artifact Debugging**: When debugging a CI failure, rely on downloading the `playwright-report/` artifact from GitHub Actions to visualize exactly where the test failed via traces/screenshots.
4. **POM Strictness**: Do not introduce raw selectors (e.g. `page.locator('.css-header')`) in test files to circumvent flaky queries. Follow the guidance in `playwright-manifesto.md` by wrapping all new queries inside a `frontend/tests/pages/*.js` model.
