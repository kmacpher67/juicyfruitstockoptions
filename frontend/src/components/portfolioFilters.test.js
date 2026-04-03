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
        market_price: 175.25,
    },
    {
        symbol: 'AMD 2026-04-02 202.5 Call',
        underlying_symbol: 'AMD',
        account_id: 'U110638',
        asset_class: 'OPT',
        coverage_status: 'Covered',
        dte: 0,
        dist_to_strike_pct: 0.04,
        market_price: 12.5,
    },
    {
        symbol: 'AMZN',
        underlying_symbol: 'AMZN',
        account_id: 'U110638',
        asset_class: 'STK',
        coverage_status: 'Covered',
        market_price: 192.4,
    },
    {
        symbol: 'AMZN 2026-04-10 210 Call',
        underlying_symbol: 'AMZN',
        account_id: 'U110638',
        asset_class: 'OPT',
        coverage_status: 'Covered',
        dte: 12,
        dist_to_strike_pct: 0.09,
        market_price: 8.3,
    },
    {
        symbol: 'TSLA',
        underlying_symbol: 'TSLA',
        account_id: 'U280132',
        asset_class: 'STK',
        coverage_status: 'Uncovered',
        pending_order_effect: 'covering_uncovered',
        market_price: 240.12,
    },
    {
        symbol: 'TSLA 2026-04-04 250 Call',
        underlying_symbol: 'TSLA',
        account_id: 'U280132',
        asset_class: 'OPT',
        coverage_status: 'Uncovered',
        pending_order_effect: 'covering_uncovered',
        dte: 3,
        dist_to_strike_pct: 0.03,
        market_price: 6.45,
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

test('applyPortfolioFilters matches coverage focus regardless of coverage_status casing', () => {
    const rows = [
        ...sampleRows,
        {
            symbol: 'NVDA',
            underlying_symbol: 'NVDA',
            account_id: 'U110638',
            asset_class: 'STK',
            coverage_status: 'uncovered',
        },
    ];

    const filtered = applyPortfolioFilters(rows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        coverage: 'Uncovered',
        account: 'U110638',
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['NVDA'],
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

test('applyPortfolioFilters hides stock rows when Show "STK ?" is unchecked', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        showStocks: false,
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['AMD 2026-04-02 202.5 Call', 'AMZN 2026-04-10 210 Call', 'TSLA 2026-04-04 250 Call'],
    );
});

test('applyPortfolioFilters keeps underlying stock row for matched options when Show "STK ?" is checked', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        expiringOnly: true,
        dteLimit: 4,
        showStocks: true,
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['AMD', 'AMD 2026-04-02 202.5 Call', 'TSLA', 'TSLA 2026-04-04 250 Call'],
    );
});

test('applyPortfolioFilters pending cover focus returns actionable pending-cover rows', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        pendingEffect: 'pending_cover',
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['TSLA', 'TSLA 2026-04-04 250 Call'],
    );
});

test('applyPortfolioFilters applies pending-effect focus with other filters using AND semantics', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        pendingEffect: 'pending_cover',
        coverage: 'Uncovered',
        account: 'U280132',
        nearMoneyOnly: true,
        nearMoneyPercent: 5,
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['TSLA', 'TSLA 2026-04-04 250 Call'],
    );
});

test('applyPortfolioFilters keeps export-visible rows aligned for Expiring + Near Money + Account + Coverage + Show STK on', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        coverage: 'Covered',
        account: 'U110638',
        expiringOnly: true,
        nearMoneyOnly: true,
        dteLimit: 6,
        nearMoneyPercent: 8,
        showStocks: true,
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['AMD', 'AMD 2026-04-02 202.5 Call'],
    );
});

test('applyPortfolioFilters keeps export-visible rows aligned for same filter combo when Show STK is off', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        coverage: 'Covered',
        account: 'U110638',
        expiringOnly: true,
        nearMoneyOnly: true,
        dteLimit: 6,
        nearMoneyPercent: 8,
        showStocks: false,
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['AMD 2026-04-02 202.5 Call'],
    );
});

test('applyPortfolioFilters supports last price min/max range filtering', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        lastPriceMin: 170,
        lastPriceMax: 200,
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['AMD', 'AMZN'],
    );
});

test('applyPortfolioFilters combines last price range with existing filters using AND semantics', () => {
    const filtered = applyPortfolioFilters(sampleRows, {
        ...DEFAULT_PORTFOLIO_FILTERS,
        coverage: 'Uncovered',
        account: 'U280132',
        lastPriceMin: 200,
        lastPriceMax: 260,
    });

    assert.deepEqual(
        filtered.map((row) => row.symbol),
        ['TSLA'],
    );
});
