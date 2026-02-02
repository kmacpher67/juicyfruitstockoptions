# Walkthrough - News & Sentiment Analysis (Backend)

**Date**: 2026-02-02
**Feature**: News Aggregation, Sentiment Logic, Macro Data
**Status**: Backend Complete / Tests Passed

## Changes Implemented

### 1. Data Models (`app/models_news.py`)
- Created `NewsArticle` Pydantic model with strict fields for AI/Logic:
    - `logic`: The rule applied (e.g. "Conflict: Growth vs Price").
    - `reasoning`: Natural language explanation.
    - `impact_window`: Time horizon (Short/Medium/Long-term).
    - `opportunity_score`: 0-100 derived score.
    - `source_weight`: Credibility score.

### 2. Services (`app/services/`)
- **SentimentService** (`sentiment_service.py`):
    - Implemented `analyze_impact()` using VADER (`nltk`) + Heuristics.
    - Added `categorize_impact_window()` to detect "Earnings" (Short) vs "Regulation" (Long).
    - Added `generate_heuristic_logic()` to create the "Reasoning" text (Stage 1).
- **NewsService** (`news_service.py`):
    - Fetches from **NewsAPI** (requires key).
    - Aggregates and enriches articles with SentimentService.
    - Implemented `calculate_source_weight()` (Bloomberg=1.0, Twitter=0.5).
- **MacroService** (`macro_service.py`):
    - Fetches from **FRED API** (requires key).
    - Placeholder for Market Regime logic.

### 3. API Routes (`app/api/routes.py`)
- `GET /api/news/{symbol}`: Returns the enriched JSON list.
- `GET /api/macro`: Returns key indicators (FedOpen, CPI, Unemployment).

### 4. Configuration
- Added `NEWS_API_KEY`, `FRED_API_KEY`, `X_API_KEY` to `config.py`.

## Verification Results

### Automated Tests (`tests/test_news_sentiment.py`)
- **Passed**: Strict JSON structure compliance (verified "Sea Limited" fields exist).
- **Passed**: Short-term/Long-term heuristic categorization.
- **Passed**: Logic generation based on sentiment score.

### Manual Step Required
- User must populate `.env` with real API keys:
    ```bash
    NEWS_API_KEY=...
    FRED_API_KEY=...
    ```

## Next Steps
- **UI Implementation**: Update Ticker Modal to display the "Reasoning" and "Logic" pills.
- **X Integration**: Decide on paid tier for X API vs alternative scraping.
