import test from 'node:test';
import assert from 'node:assert/strict';

import {
    formatAccountsHeldLines,
    formatDividendCurrency,
    formatDividendPercent,
    resolveAnalystTarget,
    resolvePredictedPrice,
    resolveQuarterlyReturnPct,
} from './dividendPresentation.js';

test('formatters return dash for missing values', () => {
    assert.equal(formatDividendCurrency(undefined), '-');
    assert.equal(formatDividendPercent(null), '-');
});

test('resolvePredictedPrice falls back to current price when prediction is missing', () => {
    assert.equal(resolvePredictedPrice({ current_price: 123.45 }), 123.45);
    assert.equal(resolvePredictedPrice({ predicted_price: 150.1, current_price: 123.45 }), 150.1);
});

test('resolveAnalystTarget suppresses empty/non-positive targets', () => {
    assert.equal(resolveAnalystTarget({ analyst_target: null }), null);
    assert.equal(resolveAnalystTarget({ analyst_target: 0 }), null);
    assert.equal(resolveAnalystTarget({ analyst_target: -10 }), null);
    assert.equal(resolveAnalystTarget({ analyst_target: 200.55 }), 200.55);
});

test('resolveQuarterlyReturnPct uses explicit value first, then computes fallback', () => {
    assert.equal(resolveQuarterlyReturnPct({ return_pct: 2.5, dividend_amount: 1, current_price: 100 }), 2.5);
    assert.equal(resolveQuarterlyReturnPct({ return_pct: null, dividend_amount: 1, current_price: 100 }), 1);
    assert.equal(resolveQuarterlyReturnPct({ return_pct: null, dividend_amount: null, current_price: 100 }), null);
});

test('formatAccountsHeldLines splits and trims account holdings', () => {
    assert.deepEqual(formatAccountsHeldLines('U1: 100, U2: 50'), ['U1: 100', 'U2: 50']);
    assert.deepEqual(formatAccountsHeldLines(' - '), []);
    assert.deepEqual(formatAccountsHeldLines(''), []);
});
