# data-freshness-instrument-abstraction

This document defines DB-first freshness behavior for Juicy Fruit across stocks and options.

## 1. Terminology
- **Instrument** is the correct umbrella term for STK/OPT/FUT/BOND.
- Use stable naming across docs/code. Prefer one naming scheme:
  - `stock_data` (existing heavy analysis snapshot for stock analytics),
  - `instrument_snapshot` (generalized latest snapshot for fast reads),
  - `instrument_price_history` (append-only high-churn price/history stream).

## 2. Core Read Contract (DB-First)
All frontend-facing market-data APIs should follow this flow:
1. Query MongoDB first for the canonical instrument key.
2. Return best-available persisted data immediately.
3. Evaluate staleness by field tier and market session.
4. If stale, queue asynchronous refresh (do not block API response on external calls).
5. Return freshness metadata in response:
   - `data_source`
   - `last_updated`
   - `is_stale`
   - `stale_reason`
   - `refresh_queued`

This contract applies beyond ticker detail APIs to all data-related queries.

## 3. Source Precedence
- **Intraday live state (price-sensitive):** prefer TWS when connected and fresh.
- **Historical and EOD truth:** Flex remains authoritative.
- **Fallback/backfill:** yfinance and Flex are used when TWS is unavailable/stale or for non-realtime fields.

Implemented precedence rules (2026-04-07):
- Portfolio stats use `data_source: "tws_live"` only when the latest TWS snapshot is recent.
- If the latest TWS snapshot is stale, source falls back to `data_source: "flex_eod"` for canonical portfolio values.
- DB-first stock endpoints keep persisted Mongo data as primary; yfinance is fallback for missing records (`db_record_missing` path).

Source precedence should be explicit and testable, not inferred in the UI.

## 4. Freshness Tiers (Field-Based)
- **Tier A: price-derived fields** (`Current Price`, `% change`, price-based `P/E`, market value)
  - short intraday freshness window during market session.
- **Tier B: periodic fundamentals** (quarterly earnings, analyst targets, derived valuation snapshots)
  - daily or report-cadence refresh.
- **Tier C: slow/static profile** (long name, sector, industry, profile text)
  - weekly or on-demand refresh.

Current API thresholds (from `data_freshness_config`, with defaults):
- Tier A (`price`): `price_open_min=15`, `price_closed_min=720`
- Tier B (`mixed`): `mixed_open_min=30`, `mixed_closed_min=1440`
- Tier C (`profile`): `profile_open_min=1440`, `profile_closed_min=10080`

Avoid one fixed stale threshold for all fields.

## 5. Market Session Logic
- Do not hardcode close times (for example, a fixed `6:00 PM EST` rule).
- Staleness should use exchange-session aware logic:
  - market open/closed,
  - holidays,
  - early closes,
  - timezone-safe handling.

Implemented baseline session logic (2026-04-07):
- Timezone: `America/New_York`
- Standard session: `09:30` to `16:00` ET
- Early close session: `09:30` to `13:00` ET on common NYSE early-close dates
- NYSE holiday closure checks include New Year, MLK, Presidents, Good Friday, Memorial Day, Juneteenth, Independence Day, Labor Day, Thanksgiving, Christmas

## 6. Data Model Guidance
- Keep heavy analytics/profile payloads out of high-frequency write paths.
- Use append-only history for price time series and auditability.
- Add retention/index strategy for growth control:
  - timestamp indexes,
  - instrument key indexes,
  - optional rollups for long-range history.

At ~100 tracked stocks, daily snapshots are manageable, but intraday streams still need indexing and retention planning.

## 7. Data Hygiene Rules
- Normalize instrument keys (case/whitespace, option symbol canonicalization).
- Remove duplicate logical fields from ingestion mappings.
- Convert NaN-like artifacts to `null` or omit where appropriate.
- Keep schema names explicit (avoid CSV artifact keys such as `Unnamed: ...`).

Canonical key format in code (2026-04-07):
- Stock: `STK:<TICKER>` (example `STK:AAPL`)
- Option/FOP: `OPT:<TICKER>:<YYYYMMDD>:<C|P>:<STRIKE>`

## 8. Operational Pattern
- Ingest is asynchronous background work.
- API reads are low-latency DB-first.
- UI is freshness-aware via metadata and should not trigger blocking live scans.
