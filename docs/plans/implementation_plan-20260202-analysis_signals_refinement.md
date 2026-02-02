# Implementation Plan - Refine Analysis & Signals Features

## Goal Description
Refine the "Analysis & Signals" section of `docs/features-requirements.md` (specifically around line 136) to provide a comprehensive roadmap for "Juicy Opportunity" collection, storage, and analysis. This supports the long-term goal of automated strategy validation and AI-driven signal calibration.

## User Review Required
> [!NOTE]
> This plan focuses on *documentation updates* to `features-requirements.md` and creating a roadmap. No code changes are scheduled in this immediate step, but the plan defines future backend work.

## Proposed Changes

### Documentation
#### [MODIFY] [features-requirements.md](file:///home/kenmac/personal/juicyfruitstockoptions/docs/features-requirements.md)
- **Refine Item**: "Juicy Opportunity Finder" (Line 135-136).
- **Decompose**: Break down "Juicy Opportunity Collection" into specific actionable sub-tasks:
    - **Data Schema Definition**: Define fields for `JuicyOpportunity` (Symbol, Timestamp, Underlying Price, Greeks, IV Rank, Signal Source, etc.).
    - **Persistence Layer**: Requirements to store these snapshots (MongoDB `opportunities` collection?).
    - **Grading Engine**: A scheduled job to revisit past opportunities and grade them (Profit/Loss, Max Drawdown, etc.) based on subsequent market data.
    - **Signal Correlation Analysis**: A dashboard/report to analyze which signals (e.g., "High IV", "Gap Up") yield the best Hit Rate.
- **Cross-Referencing**: Link to existing learning docs (`learning/opportunity-scoring.md`, `learning/bad-trade-heuristics.md`, `learning/price-action-concepts.md`).
- **New Features**:
    - **"Paper Trading" Simulator**: Virtual execution of found opportunities.
    - **Calibration Loop**: Feedback mechanism to adjust weights in `OpportunityScorer`.
    - **Options Due in X Days Signal**: Alert system for positions nearing expiration (e.g., <7 DTE), prompting roll or management decisions.

### Learning / Research
- [ ] Create `docs/learning/opportunity-persistence-and-grading.md`:
    - Define the "Lifecycle of a Signal" (Detection -> Storage -> Tracking -> Grading).
    - Discuss "Path Dependency" (what happened *during* the trade, not just start/end).

## Plan Breakdown (to be added to features-requirements.md)
1.  **Opportunity Persistence**:
    -   Requirement: "Snapshot" the exact market state when an opportunity is flagsed.
    -   Reasoning: You cannot grade a decision if you don't know the inputs available at that time.
2.  **Outcome Tracking (The "Truth" Engine)**:
    -   Requirement: Automated tracker that monitors the specific option/stock for the duration of the proposed trade.
    -   Metrics: Max Profit, Max Loss, Days to Profit, Expiration Value.
3.  **Signal Attribution**:
    -   Requirement: Tag each opportunity with *why* it was chosen (e.g., `iv_rank > 50`, `rsi < 30`, `delta_neutral`).

## Verification Plan
### Automated Tests
- None for this documentation task. Future code implementation will require tests for the Grading Engine.

### Manual Verification
- Review the updated `features-requirements.md` to ensure:
    -   Hierarchy is preserved.
    -   Links are valid.
    -   New items are actionable and clear.
    -   "Why" and "Next Steps" are included.
