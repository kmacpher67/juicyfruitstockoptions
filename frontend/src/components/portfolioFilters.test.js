import test from 'node:test';
import assert from 'node:assert/strict';

import { applyPortfolioFilters, DEFAULT_PORTFOLIO_FILTERS } from './portfolioFilters.js';

const sampleRows = [
    {
        symbol: 'AMD',
        underlying_symbol: 'AMD',
        account_id: 'U110638',
        coverage_status: 'Covered',
        dte: 0,
        dist_to_strike_pct: 0.04,
    },
    {
        symbol: 'AMZN',
        underlying_symbol: 'AMZN',
        account_id: 'U110638',
        coverage_status: 'Covered',
        dte: 12,
        dist_to_strike_pct: 0.09,
    },
    {
        symbol: 'TSLA',
        underlying_symbol: 'TSLA',
        account_id: 'U280132',
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

    assert.equal(filtered.length, 1);
    assert.equal(filtered[0].symbol, 'AMD');
});

test('applyPortfolioFilters keeps coverage mutually exclusive while leaving other toggles optional', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        coverage: 'Covered',
        account: 'U110638',
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['AMD', 'AMZN'],
    );
});

test('applyPortfolioFilters respects ticker matching against symbol and underlying symbol', () => {
    const filtered = applyPortfolioFilters(sampleRows, DEFAULT_PORTFOLIO_FILTERS, 'tsla');

    assert.equal(filtered.length, 1);
    assert.equal(filtered[0].symbol, 'TSLA');
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
        ['AMD'],
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
        ['AMD', 'AMZN'],
    );
});
