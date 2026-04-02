import test from 'node:test';
import assert from 'node:assert/strict';

import { buildTickerHeaderModel } from './tickerModalHeader.js';

test('buildTickerHeaderModel includes descriptor, normalized price/change, and timestamp label', () => {
    const model = buildTickerHeaderModel({
        ticker: 'oln',
        tickerData: {
            company_name: 'Olin Corporation',
            data: {
                'Current Price': '23.41',
                '1D % Change': '-0.93',
                'Last Update': '2026-04-02T13:44:12Z',
            },
        },
    });

    assert.equal(model.ticker, 'OLN');
    assert.equal(model.descriptor, 'Olin Corporation');
    assert.equal(model.priceText, '$23.41');
    assert.equal(model.changeText, '-0.93%');
    assert.equal(model.changeTone, 'text-red-400');
    assert.ok(model.lastUpdateText.startsWith('Last update: '));
});

test('buildTickerHeaderModel falls back to profile description when company name is unavailable', () => {
    const model = buildTickerHeaderModel({
        ticker: 'SE',
        tickerData: {
            profile: {
                description: 'Sea Limited is a leading global consumer internet company focused on e-commerce and digital financial services.',
            },
            data: {
                'Current Price': 55,
                '1D % Change': 1.2,
            },
        },
    });

    assert.equal(model.ticker, 'SE');
    assert.ok(model.descriptor.startsWith('Sea Limited'));
    assert.equal(model.priceText, '$55.00');
    assert.equal(model.changeText, '1.20%');
    assert.equal(model.changeTone, 'text-green-400');
});

test('buildTickerHeaderModel avoids duplicate percent symbols and handles invalid numerics safely', () => {
    const model = buildTickerHeaderModel({
        ticker: 'AMD',
        tickerData: {
            data: {
                'Current Price': 'not-a-number',
                '1D % Change': '-0.93%',
                'Last Update': 'n/a',
            },
        },
    });

    assert.equal(model.priceText, null);
    assert.equal(model.changeText, '-0.93%');
    assert.equal(model.lastUpdateText, 'Last update: n/a');
});
