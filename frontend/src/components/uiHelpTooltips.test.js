import test from 'node:test';
import assert from 'node:assert/strict';

import {
    UI_HELP_HEADER_KEYS,
    resolveControlTooltip,
    resolveHeaderTooltip,
    resolveQuickLinkTooltip,
    withHeaderTooltips,
} from './uiHelpTooltips.js';

test('header tooltip dictionary includes key portfolio/trade/order abbreviations', () => {
    const required = ['dte', 'ntm %', 'p.btc', 'comm', 'tif', 'oi', 'liq'];
    for (const key of required) {
        assert.ok(UI_HELP_HEADER_KEYS.includes(key), `missing header help key: ${key}`);
    }
});

test('resolveHeaderTooltip handles header or field fallback', () => {
    assert.equal(resolveHeaderTooltip('DTE', 'dte'), 'Days to expiration for the option contract.');
    assert.equal(resolveHeaderTooltip('', 'ticker'), 'Tradable symbol. Click ticker for detail modal.');
    assert.equal(resolveHeaderTooltip('Unknown Header', 'unknown_field'), null);
});

test('withHeaderTooltips adds help text when missing and preserves explicit tooltip', () => {
    const defs = [
        { field: 'dte', headerName: 'DTE' },
        { field: 'custom', headerName: 'Custom', headerTooltip: 'Explicit help' },
    ];

    const next = withHeaderTooltips(defs);
    assert.equal(next[0].headerTooltip, 'Days to expiration for the option contract.');
    assert.equal(next[1].headerTooltip, 'Explicit help');
});

test('resolveControlTooltip covers dynamic focus buttons', () => {
    assert.equal(resolveControlTooltip('Expiring (<6D)'), 'Toggle positions with options expiring within selected DTE.');
    assert.equal(resolveControlTooltip('Near Money (<8%)'), 'Toggle options near the money by strike distance %.');
    assert.equal(resolveControlTooltip('Uncovered'), 'Show positions with uncovered shares.');
});

test('resolveQuickLinkTooltip formats concise link help', () => {
    assert.equal(resolveQuickLinkTooltip('google', 'AAPL'), 'Open AAPL on Google Finance');
    assert.equal(resolveQuickLinkTooltip('yahoo', 'MSFT'), 'Open MSFT option chain on Yahoo Finance');
});
