---
description: verify test coverage
---

## Docuentation and Tests 
- Read a function or method and evaluate the actions and code write tests for postive and negative outcomes conforming to the README-out and other implementation tasks documents 
- Create a /doc and memorialize all implementation and task documents with implementation-{summary} and task-{summary} make sure the requirements are sufficiently memorialized so as to be useful for test case validation and or completely rebuilding the project from scratch 
- **Backend Tests**: Every method should cause a complete `pytest` case.
- **Frontend E2E Tests**: All frontend UI changes, DOM interactions, and feature workflows MUST be tested using Playwright. No raw selectors are allowed in `.spec.js` files; use the Page Object Model (POM) pattern inside `frontend/tests/pages/`. Tests should intercept API calls (e.g. `page.route`) instead of touching live data environments.