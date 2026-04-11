# Project Framework

This document defines a reusable docs-first framework for projects that automate or assist with operational work such as banking workflows, credit-card bookkeeping, reconciliation, tax-prep support, vendor integrations, and other systems that depend on third-party entities.

The goal is to make the project understandable, restartable, and delegatable to humans or agents without losing business context.

## Core Idea

Use documentation as the control plane for development.

The project should have:
- one master requirements and roadmap document
- one detail document per meaningful feature or workflow
- one learning document per research topic, external dependency, or business rule
- one implementation plan per coding initiative
- one consistent definition of done

This framework is especially useful when:
- multiple third-party systems are involved
- terminology is domain-specific
- auditability matters
- data freshness, reconciliation, and exception handling matter
- work may be handed to agents repeatedly over time

## Principles

1. Source of truth lives in the repo.
Avoid depending on memory, chat history, or external notes for critical rules.

2. Requirements and implementation history are related but not identical.
The roadmap says what the system should do. Feature docs and plan docs explain how and why.

3. Research should be preserved.
Anything learned about institutions, APIs, statement formats, file contracts, reconciliation rules, compliance constraints, or accounting treatment should be written down.

4. Small increments beat giant rewrites.
Features should be decomposed into slices that can be planned, implemented, tested, and reviewed independently.

5. Every integration must define a trust model.
For each external system, define what it is authoritative for, what can be stale, and what is only advisory.

6. Exceptions are first-class.
Operational systems fail at edges: duplicates, late files, broken exports, missing fields, locked accounts, changed CSV layouts, API rate limits, partial syncs, and ambiguous matches. Those cases should be documented before they become incidents.

## Recommended Repository Structure

```text
.agent/
  workflows/
    create-a-plan.md
    test-coverage.md

docs/
  PROJECT_FRAMEWORK.md
  features-requirements.md
  features/
  learning/
  plans/
  templates/
```

Optional supporting folders:

```text
docs/runbooks/      **Are these for support docs or troubleshooting?**
docs/glossary/      **Good for defining terms and etymology, could be used in tooltips etc**
docs/decisions/     **Memorialize why a design or path was chosen, like not using IBKR web clientportal**
```

## Document Roles

### 1. Master Requirements Document

Path:
- `docs/features-requirements.md`

Purpose:
- hold the master roadmap
- track status
- capture feature IDs and decomposition
- provide a simple source-of-truth queue for future work

This document should contain:
- project purpose
- status legend
- major capability areas
- feature IDs
- dependency notes
- explicit open questions and blockers
- changelog or references to completed work

This document should not become the only place where details live. Once an item becomes substantial, it should link to a dedicated feature doc.

### 2. Feature Documents

Path:
- `docs/features/<feature_name>.md`

Purpose:
- define a feature contract clearly enough that someone else can implement or review it later

A feature doc should capture:
- business purpose
- user/operator workflow
- inputs and outputs
- data sources
- source-of-truth rules
- validation rules
- edge cases and failure modes
- acceptance criteria
- links back to the master requirements doc

Examples in a bookkeeping or banking project:
- bank statement import
- credit-card transaction categorization
- reconciliation workspace
- duplicate detection
- monthly close checklist
- third-party file ingestion contract
- vendor API fallback behavior

### 3. Learning Documents

Path:
- `docs/learning/<topic>.md`

Purpose:
- preserve research and definitions that will matter again later

A learning doc is appropriate for:
- how a bank export format behaves
- how a lender or card provider identifies pending vs posted transactions
- what a payment processor includes in settlement files
- what an institution means by “available balance” vs “ledger balance”
- what fields are stable identifiers and which are not
- how a third-party API handles pagination, retries, or corrections

These docs reduce repeated research and help agents make fewer bad assumptions.

### 4. Implementation Plans

Path:
- `docs/plans/implementation_plan-YYYYMMDD-short_name.md`

Purpose:
- define the next implementation slice before coding starts

A plan should answer:
- what is changing
- why now
- what data/config/env changes are required
- what risks exist
- how the work will be tested
- what docs must be updated
- what remains out of scope

### 5. Agent Workflow Files

Path:
- `.agent/workflows/`

Purpose:
- tell an agent how to work in this repo

At minimum include:
- `create-a-plan.md`
- `test-coverage.md`

These files should be generic, repo-local, and not depend on hidden global instructions.

## Standard Development Flow

1. Capture or refine the requirement in `docs/features-requirements.md`.
2. If the item is meaningful, create or update a feature doc in `docs/features/`.
3. If research or external dependency knowledge is needed, create or update a learning doc in `docs/learning/`.
4. Create an implementation plan in `docs/plans/`.
5. Mark the master item as in progress.
6. Implement in a small slice.
7. Add or update tests.
8. Update docs to reflect the final behavior.
9. Mark the item complete, or split follow-up work into a new requirement.

## How To Model Third-Party Entities

For each external entity, maintain a lightweight contract in docs.

That contract should answer:
- what system is this
- what business process depends on it
- what data can it provide
- what data is authoritative
- what data is delayed or approximate
- what credentials or setup are required
- what failure modes are known
- what fallback exists if it is unavailable
- what identifiers are safe to use for matching or dedupe

Useful entity categories:
- banks
- credit-card issuers
- payment processors
- brokerages
- payroll systems
- accounting platforms
- tax software
- cloud file stores
- email inboxes used as document sources

## Data and Reconciliation Guidance

For operational finance projects, document these concepts explicitly.

### Source Hierarchy
Define which source wins when records disagree.

Example categories:
- authoritative ledger source
- operational convenience source
- enrichment source
- manual override source

### Record Identity
Document how a record is matched across systems.

Examples:
- institution transaction ID
- statement date + amount + payee hash
- card last four + posted date + amount
- external reference number

### Freshness
Define what can be stale and for how long.

Examples:
- balances may be intraday snapshots
- posted transactions may lag by one business day
- pending transactions may disappear or settle differently
- statement PDFs may be final, while APIs are provisional

### Exception Queue
Assume some records will need manual review.

Examples:
- unmatched transactions
- suspected duplicates
- category conflicts
- reversed charges
- account ownership ambiguity
- transfers where both sides are not clearly linked

## What To Ask An Agent To Set Up

Use a prompt like this:

```text
Set up a reusable docs-first project framework for a finance operations app.

The app may automate banking, bookkeeping, reconciliation, tax-prep support, and third-party institution integrations.

Create:
- docs/PROJECT_FRAMEWORK.md
- docs/features-requirements.md
- docs/features/
- docs/learning/
- docs/plans/
- docs/templates/
- .agent/workflows/create-a-plan.md
- .agent/workflows/test-coverage.md

Requirements:
- master requirements doc with status legend and hierarchical IDs
- feature doc template
- learning doc template
- implementation plan template
- agent setup prompt template
- guidance for third-party entities, source-of-truth rules, reconciliation, and exception handling
- definition of done covering code, tests, docs, config, and operational impact
```

## Definition Of Done

A feature is not done just because code exists.

A useful definition of done for this kind of project is:
- requirements updated
- feature doc updated if behavior is non-trivial
- learning doc updated if new external knowledge was discovered
- implementation plan saved
- config/env changes documented
- tests added or updated
- operator-visible behavior verified
- failure modes considered
- any leftover scope split into explicit follow-up items

## Recommended Improvements Over Time

As the project grows, add:
- a glossary for domain terms
- a runbook folder for operational tasks
- architecture decision records for major design choices
- an integrations registry for third-party entities
- a data contracts doc for imports and exports
- a month-end or close-process checklist if accounting workflows matter

## Framework Boundaries

This framework is intentionally abstract. It does not prescribe:
- a specific language
- a specific framework
- a specific database
- a specific accounting method
- a specific institution or vendor

It is meant to preserve clarity, reduce rework, and make agent collaboration safer in domains where mistakes can be expensive.
