# Data Freshness SLA Policy

## Purpose
Define explicit freshness tiers and TTL windows so DB-first endpoints evaluate staleness consistently and operators can tune policy without code changes.

## Config Source
- Mongo document: `system_config._id = "data_freshness_config"`
- API:
  - `GET /api/settings/data-freshness`
  - `POST /api/settings/data-freshness` (admin)
- Admin UI:
  - `Dashboard Settings` -> `Data Freshness TTLs`

## Tier Definitions
- Tier A (`price`): intraday price-derived fields (`Current Price`, `% Change`, price-driven metrics)
- Tier B (`mixed`): blended analytic payloads (ticker detail, signals/opportunity context)
- Tier C (`profile`): slower profile/news/static payloads

## Default TTL/SLA Windows (minutes)
| Tier | Market Open | Market Closed | Config Keys |
|---|---:|---:|---|
| A (`price`) | 15 | 720 | `price_open_min`, `price_closed_min` |
| B (`mixed`) | 30 | 1440 | `mixed_open_min`, `mixed_closed_min` |
| C (`profile`) | 1440 | 10080 | `profile_open_min`, `profile_closed_min` |

## Endpoint Tier Mapping
- `GET /api/ticker/{symbol}` -> Tier B (`mixed`)
- `GET /api/opportunity/{symbol}` -> Tier A (`price`)
- `GET /api/portfolio/optimizer/{symbol}` -> Tier A (`price`)
- `GET /api/ticker/{symbol}/price-history` -> Tier A (`price`)
- `GET /api/news/{symbol}` -> Tier C (`profile`)
- `GET /api/analysis/signals/{ticker}` -> Tier B (`mixed`)

## Metadata Contract
Responses include:
- `data_source`
- `last_updated`
- `is_stale`
- `stale_reason`
- `refresh_queued`

## Validation Rules
- All TTL values must be positive integers (`>= 1`).
- Invalid values are rejected at API model validation.
