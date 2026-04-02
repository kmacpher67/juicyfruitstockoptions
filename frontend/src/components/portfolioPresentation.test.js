import test from 'node:test';
import assert from 'node:assert/strict';

import {
    getDisplaySymbol,
    getVisibleRowCounterLabel,
    normalizeSecurityType,
    resolveSecurityTypeLabel,
} from './portfolioPresentation.js';

test('normalizeSecurityType resolves canonical security type across mixed shapes', () => {
    assert.equal(normalizeSecurityType({ secType: 'opt' }), 'OPT');
    assert.equal(normalizeSecurityType({ asset_class: 'stk' }), 'STK');
    assert.equal(normalizeSecurityType({ local_symbol: 'AMD   260402C00202500' }), 'OPT');
});

test('resolveSecurityTypeLabel maps canonical types to user-friendly labels', () => {
    assert.equal(resolveSecurityTypeLabel({ secType: 'OPT' }), 'Option');
    assert.equal(resolveSecurityTypeLabel({ asset_class: 'STK' }), 'Stock');
    assert.equal(resolveSecurityTypeLabel({ secType: 'bag' }), 'BAG');
});

test('getDisplaySymbol prefers normalized display symbol then sensible fallbacks', () => {
    assert.equal(getDisplaySymbol({ display_symbol: 'AMD 2026-04-02 202.5 Call', symbol: 'AMD' }), 'AMD 2026-04-02 202.5 Call');
    assert.equal(getDisplaySymbol({ description: 'AMD Call', symbol: 'AMD' }), 'AMD Call');
    assert.equal(getDisplaySymbol({ local_symbol: 'AMD   260402C00202500' }), 'AMD   260402C00202500');
});

test('getVisibleRowCounterLabel reports post-filter visible row count', () => {
    assert.equal(getVisibleRowCounterLabel(0), 'Rows: 0');
    assert.equal(getVisibleRowCounterLabel(17), 'Rows: 17');
});
