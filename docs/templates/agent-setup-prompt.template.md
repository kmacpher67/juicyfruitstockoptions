# Agent Setup Prompt Template

Use or adapt this prompt when asking an agent to initialize a new repo with this framework.

```text
Set up a docs-first project framework for a finance operations application.

The application may include banking workflows, credit-card bookkeeping, transaction imports, reconciliation, tax-prep support, reporting, and third-party integrations.

Create this structure:
- docs/PROJECT_FRAMEWORK.md
- docs/features-requirements.md
- docs/features/
- docs/learning/
- docs/plans/
- docs/templates/
- .agent/workflows/create-a-plan.md
- .agent/workflows/test-coverage.md

Requirements:
- keep the framework abstract and reusable
- include status legend and hierarchical feature IDs
- include templates for feature docs, learning docs, and implementation plans
- include guidance for third-party entities, source-of-truth rules, reconciliation, exception handling, and auditability
- include a definition of done covering code, tests, docs, config, and operational behavior
- do not assume a specific language, framework, database, or vendor
```
