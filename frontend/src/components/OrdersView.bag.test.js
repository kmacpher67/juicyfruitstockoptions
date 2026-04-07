/**
 * OrdersView.bag.test.js
 *
 * Tests for ibkr-orders-012 (BAG leg decomposition) and
 * ibkr-orders-013 (BAG-parent visibility toggles).
 *
 * Uses node:test + node:assert - no React renderer needed.
 * The BAG logic lives in ordersViewUtils.js (pure functions).
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import {
    legActionLabel,
    isRollOrder,
    netDebitCreditLabel,
    buildLegRows,
    applyBagVisibility,
} from './ordersViewUtils.js';

// ---------------------------------------------------------------------------
// ibkr-orders-012 — Helpers: legActionLabel, isRollOrder, netDebitCreditLabel
// ---------------------------------------------------------------------------

test('ibkr-orders-012: legActionLabel labels BUY as BUY-to-close in a 2-leg combo', () => {
    const buyLeg = { action: 'BUY', ratio: 1, conid: 111 };
    const sellLeg = { action: 'SELL', ratio: 1, conid: 222 };
    assert.equal(legActionLabel(buyLeg, [buyLeg, sellLeg]), 'BUY-to-close');
    assert.equal(legActionLabel(sellLeg, [buyLeg, sellLeg]), 'SELL-to-open');
});

test('ibkr-orders-012: legActionLabel returns plain action for same-direction legs', () => {
    const leg1 = { action: 'BUY', ratio: 1 };
    const leg2 = { action: 'BUY', ratio: 2 };
    assert.equal(legActionLabel(leg1, [leg1, leg2]), 'BUY');
});

test('ibkr-orders-012: legActionLabel returns plain action for non-2-leg combos', () => {
    const leg1 = { action: 'BUY', ratio: 1 };
    const leg2 = { action: 'SELL', ratio: 1 };
    const leg3 = { action: 'SELL', ratio: 1 };
    assert.equal(legActionLabel(leg1, [leg1, leg2, leg3]), 'BUY');
});

test('ibkr-orders-012: isRollOrder true for BAG with BUY+SELL legs', () => {
    const order = {
        security_type: 'BAG',
        comboLegs: [
            { action: 'BUY', ratio: 1, conid: 10 },
            { action: 'SELL', ratio: 1, conid: 20 },
        ],
    };
    assert.equal(isRollOrder(order), true);
});

test('ibkr-orders-012: isRollOrder false for non-BAG orders', () => {
    const order = {
        security_type: 'OPT',
        comboLegs: [
            { action: 'BUY', ratio: 1, conid: 10 },
            { action: 'SELL', ratio: 1, conid: 20 },
        ],
    };
    assert.equal(isRollOrder(order), false);
});

test('ibkr-orders-012: isRollOrder false when both legs are the same direction', () => {
    const order = {
        security_type: 'BAG',
        comboLegs: [
            { action: 'SELL', ratio: 1 },
            { action: 'SELL', ratio: 1 },
        ],
    };
    assert.equal(isRollOrder(order), false);
});

test('ibkr-orders-012: isRollOrder false when no comboLegs', () => {
    assert.equal(isRollOrder({ security_type: 'BAG' }), false);
    assert.equal(isRollOrder({ security_type: 'BAG', comboLegs: [] }), false);
});

test('ibkr-orders-012: netDebitCreditLabel returns debit label for negative price', () => {
    assert.equal(netDebitCreditLabel(-0.45), 'Net debit $0.45');
    assert.equal(netDebitCreditLabel(0), 'Net debit $0.00');
});

test('ibkr-orders-012: netDebitCreditLabel returns credit label for positive price', () => {
    assert.equal(netDebitCreditLabel(0.75), 'Net credit $0.75');
});

test('ibkr-orders-012: netDebitCreditLabel returns null for missing/invalid price', () => {
    assert.equal(netDebitCreditLabel(null), null);
    assert.equal(netDebitCreditLabel(undefined), null);
    assert.equal(netDebitCreditLabel(NaN), null);
    assert.equal(netDebitCreditLabel(Infinity), null);
});

// ---------------------------------------------------------------------------
// ibkr-orders-012 — buildLegRows
// ---------------------------------------------------------------------------

test('ibkr-orders-012: buildLegRows returns 2 child rows for a 2-leg BAG order', () => {
    const parent = {
        order_key: 'perm:9001',
        security_type: 'BAG',
        account_id: 'U1',
        underlying_ticker: 'AMD',
        source: 'tws_open_order',
        status: 'Submitted',
        comboLegs: [
            { action: 'BUY', ratio: 1, conid: 111, exchange: 'CBOE' },
            { action: 'SELL', ratio: 1, conid: 222, exchange: 'CBOE' },
        ],
    };

    const legRows = buildLegRows(parent);
    assert.equal(legRows.length, 2, 'Should build exactly 2 leg rows');
    for (const row of legRows) {
        assert.equal(row._rowType, 'bag_leg');
        assert.equal(row._parentKey, 'perm:9001');
        assert.ok(['BUY', 'SELL'].includes(row.action), `action should be BUY or SELL, got ${row.action}`);
        assert.ok(row.action_label, 'action_label should be set');
    }
});

test('ibkr-orders-012: buildLegRows BUY leg has action_label "BUY-to-close"', () => {
    const parent = {
        order_key: 'perm:9002',
        security_type: 'BAG',
        account_id: 'U1',
        comboLegs: [
            { action: 'BUY', ratio: 1, conid: 11 },
            { action: 'SELL', ratio: 1, conid: 22 },
        ],
    };
    const legRows = buildLegRows(parent);
    const buyRow = legRows.find(r => r.action === 'BUY');
    const sellRow = legRows.find(r => r.action === 'SELL');
    assert.equal(buyRow.action_label, 'BUY-to-close');
    assert.equal(sellRow.action_label, 'SELL-to-open');
});

test('ibkr-orders-012: buildLegRows returns empty array when no comboLegs', () => {
    const parent = {
        order_key: 'perm:9003',
        security_type: 'BAG',
    };
    assert.deepEqual(buildLegRows(parent), []);
});

// ---------------------------------------------------------------------------
// ibkr-orders-013 — applyBagVisibility toggles
// ---------------------------------------------------------------------------

const BAG_ORDER = {
    order_key: 'perm:1001',
    security_type: 'BAG',
    is_bag: true,
    account_id: 'U1',
    comboLegs: [
        { action: 'BUY', ratio: 1, conid: 10 },
        { action: 'SELL', ratio: 1, conid: 20 },
    ],
};

const OPT_ORDER = {
    order_key: 'perm:1002',
    security_type: 'OPT',
    account_id: 'U1',
    comboLegs: null,
};

const STK_ORDER = {
    order_key: 'perm:1003',
    security_type: 'STK',
    account_id: 'U1',
};

test('ibkr-orders-013: default (showBagParents=true, showLegsOnly=false) returns BAG parent row', () => {
    const rows = applyBagVisibility([BAG_ORDER, OPT_ORDER], true, false);
    assert.equal(rows.length, 2);
    assert.ok(rows.some(r => r.order_key === 'perm:1001'), 'BAG parent should be present');
});

test('ibkr-orders-013: showBagParents=false hides BAG parent row, keeps non-BAG rows', () => {
    const rows = applyBagVisibility([BAG_ORDER, OPT_ORDER, STK_ORDER], false, false);
    assert.equal(rows.length, 2, 'Only non-BAG rows should remain');
    assert.ok(rows.every(r => r.security_type !== 'BAG'), 'No BAG rows should be present');
    assert.ok(rows.some(r => r.order_key === 'perm:1002'));
    assert.ok(rows.some(r => r.order_key === 'perm:1003'));
});

test('ibkr-orders-013: showLegsOnly=true replaces BAG parent with decomposed leg rows', () => {
    const rows = applyBagVisibility([BAG_ORDER, OPT_ORDER], false, true);
    // BAG parent with 2 legs => 2 leg rows; OPT row stays
    assert.equal(rows.length, 3, 'Should have 2 leg rows + 1 OPT row');
    const legRows = rows.filter(r => r._rowType === 'bag_leg');
    assert.equal(legRows.length, 2, 'Should have 2 leg rows from the BAG order');
    assert.ok(rows.some(r => r.order_key === 'perm:1002'), 'OPT row should still be present');
});

test('ibkr-orders-013: showLegsOnly=true flat leg rows have correct parent key', () => {
    const rows = applyBagVisibility([BAG_ORDER], false, true);
    const legRows = rows.filter(r => r._rowType === 'bag_leg');
    assert.equal(legRows.length, 2);
    for (const leg of legRows) {
        assert.equal(leg._parentKey, 'perm:1001');
    }
});

test('ibkr-orders-013: showLegsOnly=true BAG with no comboLegs falls back to parent row', () => {
    const bagNoLegs = {
        order_key: 'perm:2001',
        security_type: 'BAG',
        is_bag: true,
        comboLegs: [],
    };
    const rows = applyBagVisibility([bagNoLegs], false, true);
    // No legs -> falls back to parent row
    assert.equal(rows.length, 1);
    assert.equal(rows[0].order_key, 'perm:2001');
    assert.equal(rows[0]._rowType, undefined);
});

test('ibkr-orders-013: non-BAG orders pass through unchanged in all toggle modes', () => {
    for (const [showParents, showLegs] of [
        [true, false],
        [false, false],
        [false, true],
    ]) {
        const rows = applyBagVisibility([OPT_ORDER, STK_ORDER], showParents, showLegs);
        assert.ok(rows.some(r => r.order_key === 'perm:1002'), `OPT should pass through (${showParents},${showLegs})`);
        assert.ok(rows.some(r => r.order_key === 'perm:1003'), `STK should pass through (${showParents},${showLegs})`);
    }
});
