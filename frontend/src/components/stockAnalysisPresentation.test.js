import test from 'node:test';
import assert from 'node:assert/strict';

import {
    ANALYTICS_FIELD_GROUPS,
    computeTickerHealthScore,
    getTickerHealthLabel,
    getTickerHealthTone,
} from './stockAnalysisPresentation.js';

test('analytics field groups include the full stock-analysis column set', () => {
    const fieldKeys = ANALYTICS_FIELD_GROUPS.flatMap((group) => group.fields.map((entry) => entry[1]));
    const required = [
        'Current Price',
        '1D % Change',
        'Market Cap (T$)',
        'P/E',
        'YoY Price %',
        'EMA_20',
        'HMA_20',
        'TSMOM_60',
        'RSI_14',
        'ATR_14',
        'MA_30',
        'MA_60',
        'MA_120',
        'MA_200',
        'EMA_20_highlight',
        'HMA_20_highlight',
        'TSMOM_60_highlight',
        'Ex-Div Date',
        'Div Yield',
        'Analyst 1-yr Target',
        '1-yr 6% OTM PUT Price',
        'Annual Yield Put Prem',
        '3-mo Call Yield',
        '6-mo Call Yield',
        '1-yr Call Yield',
        'Annual Yield Call Prem',
        'Call/Put Skew',
        '6-mo Call Strike',
        'Error',
        'Last Update',
        '_PutExpDate_365',
        '_CallExpDate_365',
        '_CallExpDate_90',
        '_CallExpDate_180',
        'MA_30_highlight',
        'MA_60_highlight',
        'MA_120_highlight',
        'MA_200_highlight',
    ];
    for (const key of required) {
        assert.ok(fieldKeys.includes(key), `Missing analytics field: ${key}`);
    }
});

test('composite health score yields strong/weak classifications', () => {
    const strong = computeTickerHealthScore({
        'TSMOM_60': 0.85,
        'Call/Put Skew': 1.4,
        'RSI_14': 55,
        '1D % Change': 1.8,
        'YoY Price %': 22.1,
    });
    assert.ok(strong >= 70);
    assert.equal(getTickerHealthLabel(strong), 'Strong');
    assert.equal(getTickerHealthTone(strong), 'text-green-400');

    const weak = computeTickerHealthScore({
        'TSMOM_60': -0.9,
        'Call/Put Skew': 0.5,
        'RSI_14': 87,
        '1D % Change': -4.2,
        'YoY Price %': -28,
    });
    assert.ok(weak <= 44);
    assert.equal(getTickerHealthLabel(weak), 'Weak');
    assert.equal(getTickerHealthTone(weak), 'text-red-400');
});

test('composite health score returns null when no numeric inputs exist', () => {
    assert.equal(computeTickerHealthScore({}), null);
    assert.equal(computeTickerHealthScore(null), null);
});
