# Feature: Thorp Audit Tab — Ticker Detail Modal

**Feature ID:** `stock-analysis-thorpe`  
**Status:** Proposed  
**Owner:** Ken  
**Implementation Plan:** [implementation_plan-20260419-thorp-protocol.md](../plans/implementation_plan-20260419-thorp-protocol.md)

---

## Overview

Adds a **"Thorp Audit"** tab (7th tab) to `TickerModal.jsx`. Each ticker click surfaces a 10-point mathematical risk/edge audit derived from Edward Thorp's 60-year investment framework. Data is computed by a new `thorp_service.py` backend service from existing MongoDB collections — no external API calls required for Phase 1.

**Reference Material:**
- [Thorp Protocol Framework](../learning/thorp-protocol-investing.md)
- [Kelly Criterion for Options](../learning/kelly-criterion-options.md)

---

## UI/UX Specification

### Tab Header
- Label: `Thorp Audit`
- Position: 7th tab (after Smart Rolls)
- Loading state: spinner per existing `TabErrorBadge` pattern

### Main Layout — 10-Point Audit Table

Dense, scrollable table (dark theme, consistent with Analytics tab):

| Column | Width | Content |
|---|---|---|
| `#` | 40px | Point number (1-10) |
| `Framework Point` | 180px | Thorp point name |
| `Status` | 80px | Colored badge: `EDGE` (green) / `CAUTION` (yellow) / `RISK` (red) / `NO DATA` (gray) |
| `Key Metric` | 120px | Primary computed value (e.g., Kelly `f* = 12.4%`) |
| `Detail` | auto | One-line plain-English explanation |

### Thorp Decision Panel (pinned bottom)

Separate card below table. Three ranked action rows:

```
TOP MOVE 1: [action label]
  Edge: [edge description]
  Risk: [risk description]
  First Step: [concrete next action]
```

Color-coded borders: green/yellow/red per action risk level.

---

## Data Binding

**API Endpoint:** `GET /api/thorp/{symbol}`

**Response shape** (see `app/models/thorp.py`):

```json
{
  "symbol": "AMD",
  "as_of": "2026-04-19T14:30:00Z",
  "points": [
    {
      "id": "edge_audit",
      "label": "Edge Audit",
      "status": "EDGE",
      "key_metric": "Win Rate 68% vs 5.9% baseline",
      "detail": "Proven edge: historical wheel yield 23.4% annualized"
    },
    {
      "id": "position_sizing",
      "label": "Kelly Position Sizing",
      "status": "CAUTION",
      "key_metric": "Half-Kelly = 8.2% NLV",
      "detail": "Current exposure 14.1% NLV — over-committed vs Half-Kelly"
    }
    // ... 8 more points
  ],
  "thorp_decision": [
    {
      "rank": 1,
      "action": "Scale back to Half-Kelly (reduce 1 contract)",
      "edge": "Current Kelly over-bet risks 12% drawdown on -25% move",
      "risk": "Leaves open premium on table if stock holds",
      "first_step": "Place GTC limit order to close 1 contract at mid"
    }
  ],
  "data_completeness": 0.85
}
```

**`data_completeness`**: 0.0–1.0 ratio of points with sufficient data. If `< 0.5`, show banner: *"Insufficient trade history for full Thorp audit. Run Live Analysis to populate data."*

---

## Service Architecture

```
TickerModal.jsx (tab 7)
    → GET /api/thorp/{symbol}          (routes.py — appended, not modified)
        → thorp_service.ThorpService.compute(symbol)
            → stock_data collection
            → juicy_opportunities collection
            → ibkr_holdings collection
            → trades collection
            → system_config (inflation_baseline)
        → ThorpAuditResponse (app/models/thorp.py)
```

---

## Feature Requirements Traceability

| F-R ID | Description | Done? |
|---|---|---|
| thorpe-001 | Thorp Audit tab in TickerModal | [ ] |
| thorpe-002 | `thorp_service.py` — 10-point computation | [ ] |
| thorpe-003 | Edge Audit — win rate vs inflation baseline | [ ] |
| thorpe-004 | Kelly Criterion position sizing calculator | [ ] |
| thorpe-005 | Inefficiency Map — IV/RV gap + skew anomalies | [ ] |
| thorpe-006 | Ruin Check — -25% Black Monday simulation | [ ] |
| thorpe-007 | Fraud Scan — volume vs avg + premium vs BS | [ ] |
| thorpe-008 | Compounding Review — annualized yield vs linear | [ ] |
| thorpe-009 | Adaptability Check — yield trend slope last 3-4 | [ ] |
| thorpe-010 | Independence Test — sentiment vs Markov consensus | [ ] |
| thorpe-011 | Circle of Competence — win rate by asset/strategy | [ ] |
| thorpe-012 | Thorp Decision — top 3 ranked actions | [ ] |

---

## Test Coverage Requirements

- `tests/test_thorp_service.py`: unit tests for each of the 10 point calculations
- `tests/test_thorp_routes.py`: route-level tests for symbol validation, auth guard, `INSUFFICIENT_DATA` path
- `frontend/tests/specs/modal.spec.js`: extend with Thorp tab render + `NO DATA` badge state
- All tests must pass before F-R items are marked `[x]`
