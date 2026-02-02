# Implementation Plan - Price Action Analysis

This plan addresses the "Price Action" requirements (Market Structure, BOS, Order Blocks) by creating a new analysis service and integrating it into the Ticker Modal.

## Goal Description
Implement a `PriceActionService` to detect Market Structure (HH, HL, LH, LL), Break of Structure (BOS), Fair Value Gaps (FVG), and Order Blocks (OB) using daily OHLCV data. Visualize these structural elements in the Frontend.

## User Review Required
> [!IMPORTANT]
> **Algorithm Confirmations**:
> *   **BOS**: Confirmed use of **Body Close** (not Wick) to validate breakouts.
> *   **Market Structure**: Will use `n=5` (Weekly window) for Daily charts to reduce noise, as `n=3` is too sensitive.
> *   **FVG**: Will implement **Fair Value Gap** detection to validate high-probability Order Blocks.

## Proposed Changes

### Backend Components

#### [NEW] [app/services/price_action_service.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/services/price_action_service.py)
- **Functions**:
    - `find_pivots(df, n=5)`: Identify Swing Highs/Lows (Updated default to 5).
    - `identify_structure(pivots)`: Label HH, HL, LH, LL.
    - `detect_bos(df, structure)`: Identify Break of Structure (Body Close).
    - `detect_fvg(df)`: Identify Fair Value Gaps (3-candle pattern).
    - `find_order_blocks(df, bos_events)`: Identify Order Blocks + FVG validation.
    - `analyze_ticker(df)` -> `PriceActionReport`: Wrapper to run all above.

#### [MODIFY] [stock_live_comparison.py](file:///home/kenmac/personal/juicyfruitstockoptions/stock_live_comparison.py)
- **Update**: Call `PriceActionService.analyze_ticker(hist)` during the `fetch_ticker_record` process.
- **Store**: Add `Market Structure`, `Last BOS Level`, and `Nearest OB` to the stock record.

#### [MODIFY] [app/api/routes.py](file:///home/kenmac/personal/juicyfruitstockoptions/app/api/routes.py)
- **Update `/ticker/{symbol}`**: Include the `price_action` data in the response.

### Frontend Components

#### [MODIFY] [frontend/src/components/TickerModal.jsx](file:///home/kenmac/personal/juicyfruitstockoptions/frontend/src/components/TickerModal.jsx)
- **New Tab**: `Price Action` (Analysis).
- **Display**:
    - Current Trend (Bullish/Bearish).
    - List of recent structure points.
    - Active Order Blocks and FVGs.

## Verification Plan

### Automated Tests
- **Backend Unit Tests**:
    - `tests/test_price_action.py`:
        - Create synthetic OHLC data with specific patterns.
        - Verify `detect_bos` only triggers on Body Closures.
        - Verify `detect_fvg` identifies correct gaps.
        - Verify `find_order_blocks` correctly identifies the candle *before* the move.

### Manual Verification
- **Visual Check**:
    - Open `TickerModal` for a trending stock.
    - Compare findings with a manual chart review.
