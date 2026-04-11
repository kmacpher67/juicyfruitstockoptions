import test from 'node:test';
import assert from 'node:assert/strict';

import {
    calculateTradeHistoryDateRange,
    getLastCompletedTradingDay,
    getTradeActionLabel,
} from './tradeHistoryUtils.js';

test('1D trade history range uses prior completed trading day on Monday', () => {
    const now = new Date('2026-04-13T15:00:00Z');
    const range = calculateTradeHistoryDateRange('1D', now);

    assert.equal(range.start, '2026-04-10');
    assert.equal(range.end, '2026-04-10');
});

test('1D trade history range uses Friday on Sunday', () => {
    const now = new Date('2026-04-12T15:00:00Z');
    const range = calculateTradeHistoryDateRange('1D', now);

    assert.equal(range.start, '2026-04-10');
    assert.equal(range.end, '2026-04-10');
});

test('getLastCompletedTradingDay skips weekends', () => {
    const now = new Date('2026-04-11T12:00:00Z');
    const result = getLastCompletedTradingDay(now);

    assert.equal(result.toISOString().slice(0, 10), '2026-04-10');
});

test('trade action label preserves expired and assigned actions', () => {
    assert.equal(getTradeActionLabel({ action: 'EXPIRED', quantity: 1 }), 'EXPIRED');
    assert.equal(getTradeActionLabel({ raw_action: 'ASSIGNED', quantity: -1 }), 'ASSIGNED');
});

test('trade action label still normalizes classic buy and sell sides', () => {
    assert.equal(getTradeActionLabel({ buy_sell: 'BOT', quantity: 1 }), 'BUY');
    assert.equal(getTradeActionLabel({ buy_sell: 'SLD', quantity: -1 }), 'SELL');
});
