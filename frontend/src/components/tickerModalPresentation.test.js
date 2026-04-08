import test from 'node:test';
import assert from 'node:assert/strict';

import {
    buildSectionLines,
    buildTickerNotFoundLogPayload,
    formatDisplayValue,
    getAnalyticsSummaryCards,
} from './tickerModalPresentation.js';

test('formatDisplayValue normalizes percent, date, currency, and fallback values', () => {
    assert.equal(formatDisplayValue('1D % Change', 1.234), '1.23%');
    assert.equal(formatDisplayValue('Current Price', 12.3), '12.30');
    assert.equal(formatDisplayValue('Last Update', '2026-04-08T10:30:00Z'), '2026-04-08T10:30:00.000Z');
    assert.equal(formatDisplayValue('Any Field', null), '-');
});

test('getAnalyticsSummaryCards provides stable summary card set', () => {
    const cards = getAnalyticsSummaryCards({
        'Current Price': 123.45,
        '1D % Change': -2.1,
        'Call/Put Skew': 0.9,
        'TSMOM_60': 0.12,
        'Div Yield': 3.4,
        'RSI_14': 72,
    });
    assert.equal(cards.length, 6);
    assert.equal(cards[0].label, 'Price');
    assert.equal(cards[1].value, '-2.10%');
    assert.equal(cards[2].tone, 'text-amber-300');
    assert.equal(cards[5].tone, 'text-rose-300');
});

test('buildSectionLines produces predictable copy section blocks', () => {
    const lines = buildSectionLines('[Core Pricing]', [
        ['Current Price', 12.5],
        ['Last Update', '2026-04-08T10:30:00Z'],
    ]);
    assert.deepEqual(lines, [
        '[Core Pricing]',
        'Current Price: 12.50',
        'Last Update: 2026-04-08T10:30:00.000Z',
        '',
    ]);
});

test('buildTickerNotFoundLogPayload emits warning telemetry shape', () => {
    const payload = buildTickerNotFoundLogPayload({ ticker: 'AAPL', activeTab: 'analytics' });
    assert.equal(payload.level, 'warning');
    assert.equal(payload.boundary, 'ticker_modal_detail_lookup');
    assert.equal(payload.ticker, 'AAPL');
    assert.equal(payload.active_tab, 'analytics');
    assert.ok(payload.timestamp);
});
