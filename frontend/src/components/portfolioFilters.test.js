import test from 'node:test';
import assert from 'node:assert/strict';

import { applyPortfolioFilters, DEFAULT_PORTFOLIO_FILTERS } from './portfolioFilters.js';

const sampleRows = [
    {
        symbol: 'AMD',
        underlying_symbol: 'AMD',
        account_id: 'U110638',
        asset_class: 'STK',
        coverage_status: 'Covered',
    },
    {
        symbol: 'AMD 2026-04-02 202.5 Call',
        underlying_symbol: 'AMD',
        account_id: 'U110638',
        asset_class: 'OPT',
        coverage_status: 'Covered',
        dte: 0,
        dist_to_strike_pct: 0.04,
    },
    {
        symbol: 'AMZN',
        underlying_symbol: 'AMZN',
        account_id: 'U110638',
        asset_class: 'STK',
        coverage_status: 'Covered',
    },
    {
        symbol: 'AMZN 2026-04-10 210 Call',
        underlying_symbol: 'AMZN',
        account_id: 'U110638',
        asset_class: 'OPT',
        coverage_status: 'Covered',
        dte: 12,
        dist_to_strike_pct: 0.09,
    },
    {
        symbol: 'TSLA',
        underlying_symbol: 'TSLA',
        account_id: 'U280132',
        asset_class: 'STK',
        coverage_status: 'Uncovered',
    },
    {
        symbol: 'TSLA 2026-04-04 250 Call',
        underlying_symbol: 'TSLA',
        account_id: 'U280132',
        asset_class: 'OPT',
        coverage_status: 'Uncovered',
        dte: 3,
        dist_to_strike_pct: 0.03,
    },
];

test('applyPortfolioFilters combines coverage, expiring, near-money, and account filters with AND logic', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        coverage: 'Covered',
        account: 'U110638',
        expiringOnly: true,
        nearMoneyOnly: true,
        dteLimit: 6,
        nearMoneyPercent: 8,
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['AMD', 'AMD 2026-04-02 202.5 Call'],
    );
});

test('applyPortfolioFilters keeps coverage mutually exclusive while leaving other toggles optional', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        coverage: 'Covered',
        account: 'U110638',
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['AMD', 'AMD 2026-04-02 202.5 Call', 'AMZN', 'AMZN 2026-04-10 210 Call'],
    );
});

test('applyPortfolioFilters respects ticker matching against symbol and underlying symbol', () => {
    const filtered = applyPortfolioFilters(sampleRows, DEFAULT_PORTFOLIO_FILTERS, 'tsla');

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['TSLA', 'TSLA 2026-04-04 250 Call'],
    );
});

test('applyPortfolioFilters uses configurable near-money percent threshold', () => {
    const filteredAtEightPercent = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        coverage: 'Covered',
        account: 'U110638',
        nearMoneyOnly: true,
        nearMoneyPercent: 8,
    });

    assert.deepEqual(
        filteredAtEightPercent.map((row) => row.symbol),
        ['AMD', 'AMD 2026-04-02 202.5 Call'],
    );

    const filteredAtTenPercent = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        coverage: 'Covered',
        account: 'U110638',
        nearMoneyOnly: true,
        nearMoneyPercent: 10,
    });

    assert.deepEqual(
        filteredAtTenPercent.map((row) => row.symbol),
        ['AMD', 'AMD 2026-04-02 202.5 Call', 'AMZN', 'AMZN 2026-04-10 210 Call'],
    );
});

test('applyPortfolioFilters includes underlying stock rows only for the matched option groups', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        nearMoneyOnly: true,
        nearMoneyPercent: 5,
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['AMD', 'AMD 2026-04-02 202.5 Call', 'TSLA', 'TSLA 2026-04-04 250 Call'],
    );
});

test('applyPortfolioFilters does not include unrelated stock rows when option-focused filters are active', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        expiringOnly: true,
        dteLimit: 1,
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['AMD', 'AMD 2026-04-02 202.5 Call'],
    );
});
