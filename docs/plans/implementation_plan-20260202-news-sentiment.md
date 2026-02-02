# Implementation Plan - News & Sentiment Analysis

**Feature**: News Aggregation, Sentiment Analysis, and Macro Trends
**Epic**: [Features & Requirements](../features-requirements.md) #156-163
**Date**: 2026-02-02
**Status**: Revised (incorporating Learning Doc notes)

# Goal Description
Integrate external news sources and macro economic indicators to provide a holistic "Targeting System". Move beyond simple sentiment to a structured "Impact" model that records logic, reasoning, and time horizons.

## User Review Required
> [!IMPORTANT]
> **API Keys & Sources**:
> 1.  **NewsAPI**: Required for general headlines.
> 2.  **FRED**: Required for Macro data.
> 3.  **X (Twitter) API**: *New Requirement*. Be aware that the X API v2 "Basic" tier (needed for search/stream) is a paid service (~$100/mo). Free tier is write-only or extremely limited. **Decision needed**: Proceed with paid tier, or shelf X integration?
> 4.  **Yahoo Scout**: No official API. Will require researching unofficial wrappers/scraping or manual "Copy/Paste" flow initially.

## Proposed Changes

### Configuration
#### [MODIFY] [config.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/config.py)
- Add `NEWS_API_KEY` and `FRED_API_KEY`.
- Add `X_API_KEY` / `X_API_SECRET` (if proceeding).

### Data Model (MongoDB)
#### [NEW] [models_news.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/models_news.py)
- `NewsArticle` schema updated to match specific User requirements:
    ```python
    class NewsArticle(BaseModel):
        ticker: str
        title: str
        url: str
        published_at: datetime
        source: str
        source_weight: float  # e.g., Bloomberg=1.0, Twitter=0.5
        
        # AI/Logic Fields
        sentiment_score: float  # -1.0 to 1.0
        logic: str             # "Conflict between high growth..."
        impact_window: str     # "Short-term", "Medium-term", "Long-term"
        reasoning: str         # "Investors are punishing..."
        opportunity_score: float # 0-100 derived score
    ```
- `MacroIndicator`: Standard FRED series model.

### Services
#### [NEW] [news_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/news_service.py)
- `NewsService`:
    - **Sources**: NewsAPI (Primary).
    - **Future/Research**: X (Twitter) Lists, Yahoo Scout scraping.
    - `fetch_news_for_ticker(symbol)`: Aggregates from configured sources.
    - `calculate_source_weight(source_name)`: Helper to assign credibility scores.

#### [NEW] [sentiment_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/sentiment_service.py)
- `SentimentService`:
    - `analyze_impact(text, context_data)` -> Returns `dict` (logic, reasoning, scores).
    - **Stage 1 (Heuristic)**: Simple keyword rules (e.g., "Revenue Up" + "Price Down" = "Opportunity").
    - **Stage 2 (LLM)**: Hook for future Gemini/LLM integration to generate the `reasoning` text naturalistically.
    - `categorize_impact_window(text)`: Heuristic based on keywords (e.g., "Earnings" = Short-term, "Regulation" = Long-term).

#### [NEW] [macro_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/macro_service.py)
- `MacroService`:
    - `fetch_indicator(series_id)`: Calls FRED.
    - `get_market_condition()`: Returns "Regime" (e.g., "High Inflation").

### API Routes
#### [MODIFY] [routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- `GET /api/news/{symbol}`: Returns formatted `NewsArticle` objects.
- `GET /api/macro`: Returns macro summary.

## Verification Plan

### Automated Tests
- `tests/test_model_news.py`: Verify JSON serialization matches the required output format.
- `tests/test_logic_heuristics.py`: Test that simple "Rule based" logic correctly assigns "Short-term" vs "Long-term" tags.

### Manual Verification
1.  **Mock Data Injection**: Manually insert the "Sea Limited" JSON example into MongoDB.
2.  **UI Verification**: Ensure the frontend (future task) can display the `reasoning` and `logic` fields correctly.
3.  **Source Check**: Verify simple NewsAPI fetch works with a free key.

## Definition of Done
- [ ] Models defined with `logic`, `reasoning`, `impact_window`.
- [ ] NewsService fetching from at least one live source (NewsAPI).
- [ ] SentimentService populating fields with basic heuristics (or placeholders for LLM).
- [ ] "Sea Limited" example data structure is reproducible in the system.
