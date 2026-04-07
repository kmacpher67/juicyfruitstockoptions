/**
 * ordersViewUtils.js
 *
 * Pure-function utilities for the Orders view BAG/combo leg decomposition
 * and visibility filtering.  Kept framework-free so they can be exercised
 * by node:test without a React environment.
 */

/**
 * Determine a human-readable label for a combo leg action in a 2-leg roll.
 *
 * For a standard roll order the buy leg closes an existing short option
 * (BUY-to-close) and the sell leg opens a new short option (SELL-to-open).
 * We label them accordingly when the parent is a 2-leg option combo.
 *
 * @param {Object} leg      - Raw combo leg object from comboLegs array.
 * @param {Object[]} allLegs - All legs in the combo (used to infer context).
 * @returns {string}
 */
export function legActionLabel(leg, allLegs) {
    const action = (leg.action || '').toUpperCase();
    if (allLegs.length === 2) {
        const hasOpposite = allLegs.some(
            l => (l.action || '').toUpperCase() !== action
        );
        if (hasOpposite) {
            return action === 'BUY' ? 'BUY-to-close' : 'SELL-to-open';
        }
    }
    return action;
}

/**
 * Return true if the given order is a 2-leg roll: secType BAG with exactly
 * two legs where one is BUY and one is SELL.
 *
 * @param {Object} order - Normalized order row from the API.
 * @returns {boolean}
 */
export function isRollOrder(order) {
    if (!order || order.security_type !== 'BAG') return false;
    const legs = order.comboLegs;
    if (!Array.isArray(legs) || legs.length !== 2) return false;
    const actions = legs.map(l => (l.action || '').toUpperCase());
    return actions.includes('BUY') && actions.includes('SELL');
}

/**
 * Given a bag order's limit_price and comboLegs, derive a net debit/credit
 * label string (e.g. "Net debit $0.45" or "Net credit $0.45").
 *
 * For BAG orders IBKR reports lmtPrice as the net combo price; negative
 * means the combo pays a debit (costs money), positive means a credit
 * (receives money).
 *
 * @param {number|null} limitPrice - Limit price from the BAG parent row.
 * @returns {string|null}
 */
export function netDebitCreditLabel(limitPrice) {
    if (limitPrice === null || limitPrice === undefined) return null;
    const val = Number(limitPrice);
    if (!Number.isFinite(val)) return null;
    const abs = Math.abs(val).toFixed(2);
    return val <= 0 ? `Net debit $${abs}` : `Net credit $${abs}`;
}

/**
 * Build synthetic "leg row" objects for display from a BAG parent order.
 * Each leg row is a plain object that the Orders table can render as a
 * visually-indented child of the parent.
 *
 * @param {Object}   parentOrder - The BAG parent row.
 * @param {number}   index       - Zero-based leg index (used for row keys).
 * @returns {Object[]}
 */
export function buildLegRows(parentOrder, index = 0) {
    const legs = parentOrder.comboLegs;
    if (!Array.isArray(legs) || legs.length === 0) return [];

    return legs.map((leg, i) => ({
        _rowType: 'bag_leg',
        _parentKey: parentOrder.order_key || String(index),
        _legIndex: i,
        account_id: parentOrder.account_id,
        display_symbol: leg.conid ? `conid:${leg.conid}` : '-',
        action: leg.action || '-',
        action_label: legActionLabel(leg, legs),
        ratio: leg.ratio ?? 1,
        exchange: leg.exchange || '-',
        open_close: leg.open_close ?? 0,
        conid: leg.conid,
        underlying_ticker: parentOrder.underlying_ticker,
        source: parentOrder.source,
        status: parentOrder.status,
    }));
}

/**
 * Filter and/or flatten orders for display based on toolbar toggle state.
 *
 * Modes:
 *  - showBagParents=true,  showLegsOnly=false  -> default grouped view
 *    Returns parent rows (BAG and non-BAG). Leg expansion is handled inline.
 *  - showBagParents=false, showLegsOnly=false  -> hide BAG parents, show
 *    non-BAG orders only (BAG legs appear via expand in parent but parent row
 *    is hidden).
 *  - showLegsOnly=true  (either showBagParents value)  -> suppress all BAG
 *    parent rows and inject synthetic leg rows in their place.
 *
 * @param {Object[]} orders         - Full flat array of normalized order rows.
 * @param {boolean}  showBagParents - Whether to show BAG parent rows.
 * @param {boolean}  showLegsOnly   - Whether to replace BAG parents with legs.
 * @returns {Object[]} Display rows.
 */
export function applyBagVisibility(orders, showBagParents, showLegsOnly) {
    const result = [];
    for (const order of orders) {
        const isBag = order.security_type === 'BAG' || order.is_bag === true;

        if (!isBag) {
            result.push(order);
            continue;
        }

        if (showLegsOnly) {
            // Replace the parent row with its decomposed leg rows.
            const legRows = buildLegRows(order);
            if (legRows.length > 0) {
                result.push(...legRows);
            } else {
                // No legs available; fall back to the parent row.
                result.push(order);
            }
            continue;
        }

        if (showBagParents) {
            result.push(order);
        }
        // When showBagParents=false and showLegsOnly=false, BAG parent rows
        // are hidden entirely (user hid them without requesting flat legs).
    }
    return result;
}
