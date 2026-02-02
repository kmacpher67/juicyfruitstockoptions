# Ex-Dividend Rolling Strategy (X-DIV)

**Purpose**: To define the mechanics, risks, and strategies for rolling options around Ex-Dividend dates. This document serves as the "First Principles" guide for implementing the `X-DIV Strategy` feature.

## Core Concepts

### 1. Dividend Risk (Short Calls)
When you are short a call option, you are at risk of "Early Assignment" specifically just before the ex-dividend date.
- **Why?** The option holder wants to exercise the call to own the stock *before* the ex-dividend date to collect the dividend payout.
- **The Rule**: If **Dividend Amount > Remaining Time Value (Extrinsic Value)** of the Put/Call, prompt assignment is mathematically optimal for the holder.
- **The Danger Zone**: Being Short ITM (In-The-Money) Calls on the day before Ex-Div.

### 2. Dividend Capture
Strategy where an investor buys a stock just before the ex-dividend date to receive the dividend, often selling a call against it (Covered Call) to offset potential price drops (stock usually drops by dividend amount on ex-date).

### 3. "X-DIV" Rolling Heuristics

When considering a roll, the **Ex-Dividend Date** acts as a critical "Event Horizon".

#### Rule 1: The Safety Buffer (Avoid Assignment)
If you hold a Short Call that is ITM or near ITM, and the Ex-Div date is within the current options window:
- **Check**: Is `Extrinsic Value < Dividend Amount`?
- **Action**: You MUST roll **before** the ex-date.
- **Roll Target**: Roll to a strike/expiry where the new Extrinsic Value is significantly higher than the dividend, making early exercise irrational for the holder.

#### Rule 2: Pricing the Drop
The underlying stock price is expected to drop by approximately the dividend amount on the ex-date.
- **Impact on Puts**: Long Puts increase in value (Deep ITM Puts might be exercised early? No, usually Calls). Short Puts might become ITM?
- **Impact on Rolls**: Rolling *through* an ex-date requires factoring in this price drop. The "Strike Improvement" logic must account for the phantom drop.

## Implementation Guide

### Data Requirements
1.  **Ex-Dividend Date**: `yfinance` Ticker info `exDividendDate`.
2.  **Dividend Rate**: `yfinance` Ticker info `dividendRate` or `trailingAnnualDividendRate`.

### Scoring Integration (`score_roll`)
The Smart Roll scoring algorithm should be updated:

1.  **"Danger Zone" Penalty**:
    - `IF (Short Call is ITM) AND (Ex-Div Date <= Expiry) AND (Extrinsic < Dividend)`:
    - **Score**: -50 (Critical Warning).
    - **Tag**: "ASSIGNMENT RISK".

2.  **"Safety Roll" Bonus**:
    - `IF (Target Roll Extrinsic > Dividend * 1.5)`:
    - **Score**: +20 (Safe Harbor).

### UI Indicators
- Display a "Dividend Alert" icon next to tickers with upcoming Ex-Div dates (< 10 days).
- Show "Est. Dividend" vs "Extrinsic" comparison in the Roll Analysis view.
