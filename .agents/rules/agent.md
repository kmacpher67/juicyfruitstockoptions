---
trigger: always_on
---

# Code Design & Architecture
- **Pragmatic SOLID Principles:**
  - **SRP (Single Responsibility):** A class or function must have only one reason to change.
  - **Explicit DIP (Dependency Injection):**
    - **No "Magic" Autowiring:** Avoid framework-heavy DI that obscures flow.
    - **Constructor Injection:** Pass dependencies explicitly via `__init__`.
    - **Factory Pattern:** Use simple Factory classes/functions to wire objects.
- **Composition over Inheritance:** Favor composing objects with small, focused classes.
- **Pure Functions:** Prefer deterministic functions (same input = same output) that do not alter state.
- **Complexity Limits (The "Anti-Spaghetti" Rules):**
  - **Max Nesting Level:** Limit indentation to 2 levels. Extract deep logic into separate methods.
  - **Single Level of Abstraction (SLAP):** Do not mix high-level logic with low-level details.
- **DRY (Don't Repeat Yourself):** Abstract repeated logic into utility helpers.

# Database and Persistance 
- Store more data even the code model doesn't need it
- Use 

# Observability & Logging
- **Structured Logging:** Use the standard `logging` library.
- **Levels:** `DEBUG` (internal state), `INFO` (milestones), `ERROR` (exceptions with `exc_info=True`).
- **Style:** preface all logs with "{datetime stamp} - {filename-class-method/function_name} - {LEVEL} - {message text}"
- **Traceability:** Errors must provide context (e.g., "Failed to process file X due to Y").

# Python Specific Standards
- **Strong Typing:** Use `typing` module for ALL function signatures.
- **PEP 8 Compliance:** Follow standard Python styling.
- **Docstrings:** Google-style docstrings (Args, Returns, Raises).
- **Configuration:** Use environment variables or injected config objects.
- **Error Handling:**
  - Use custom exception classes.
  - **Fail Fast:** Validate inputs immediately at the public method boundary.

# Testing Strategy (The Test Pyramid)
- **Test-First Mindset:** Plan the test case before writing implementation.
- **Pytest:** Use `pytest` as the runner.
- **Unit Tests (Fast):**
  - Mock ALL external I/O (APIs, DBs, Files).
  - Test logic in isolation.
- **Integration Tests (Real):**
  - **Separate Suite:** Mark these tests (e.g., `@pytest.mark.integration`) so they can be run separately.
  - **Real Dependencies:** interact with real files, ephemeral databases, or local servers. Do not use mocks here.
  - **Lifecycle Management:** Tests must strictly clean up their own data/files (setup/teardown).
- **Regression / Golden Master Tests:**
  - **Snapshot Testing:** Maintain a directory of "Golden Data" (known correct inputs and expected outputs).
  - **Deterministic Checks:** Compare current output against the "Golden" output. Any deviation causes failure.
  - **Version Control:** Commit Golden Data to the repo to track changes in output format over time.
- **Refactoring Safety:** Do not delete tests during refactoring.
# Strict Verification Protocol
- **MANDATORY VERIFICATION:** You MUST run `pytest` after EVERY code change to verify the fix or feature.
- **NO SKIP:** Do not proceed to the next step until the relevant tests pass.
- **Coverage Requirement:** New code must be covered by tests. If unsure, run pytest with coverage (e.g., `pytest --cov=.`) and check that new lines are hit.

# Operational & Version Control
- **Atomic Commits:** `git add` and `git commit` after every logical unit of work.
- **Commit Messages:** Imperative mood ("Add feature X", "Fix bug Y").
- **Documentation:** Update `README.md` and `README_updates.md` with changelogs.
- **NEVER DELETE FILES** Never delete files without first moving copies to trash bin or some /tmp location 

# Workflow & Planning
- **Implementation Plans:** When generating an `implementation_plan.md` or embarking on a new feature/fix, you **MUST** strictly follow the workflow defined in `.agent/workflows/create-a-plan.md`.
- **Checklist Compliance:** Ensure all 11 points in the create-a-plan workflow are addressed before requesting user review.