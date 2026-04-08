import test from 'node:test';
import assert from 'node:assert/strict';

import { STOCK_GRID_AVERAGE_FIELDS_ORDER, STOCK_GRID_REQUIRED_FIELDS } from './stockGridConfig.js';

test('stock-analysis grid required fields include calculated F-R contract columns', () => {
    const required = [
        'Ticker',
        'Current Price',
        'Call/Put Skew',
        '1D % Change',
        'YoY Price %',
        'TSMOM_60',
        'RSI_14',
        'EMA_20',
        'HMA_20',
        'MA_30',
        'MA_60',
        'MA_120',
        'MA_200',
        'Annual Yield Put Prem',
        '3-mo Call Yield',
        '6-mo Call Yield',
        '1-yr Call Yield',
        'Div Yield',
    ];

    for (const field of required) {
        assert.ok(STOCK_GRID_REQUIRED_FIELDS.includes(field), `missing required grid field: ${field}`);
    }
});

test('stock-analysis average columns are ordered short-to-long', () => {
    assert.deepEqual(STOCK_GRID_AVERAGE_FIELDS_ORDER, ['EMA_20', 'HMA_20', 'MA_30', 'MA_60', 'MA_120', 'MA_200']);
});
