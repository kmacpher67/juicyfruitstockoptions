import test from 'node:test';
import assert from 'node:assert/strict';

import { buildTimeframeSubtitle, normalizeAccountScopeParam } from './navStatsUtils.js';

test('normalizeAccountScopeParam omits account for all/blank', () => {
    assert.deepEqual(normalizeAccountScopeParam('all'), {});
    assert.deepEqual(normalizeAccountScopeParam('ALL'), {});
    assert.deepEqual(normalizeAccountScopeParam(''), {});
    assert.deepEqual(normalizeAccountScopeParam(undefined), {});
});

test('normalizeAccountScopeParam includes account_id for concrete account', () => {
    assert.deepEqual(normalizeAccountScopeParam('DU123456'), { account_id: 'DU123456' });
});

test('buildTimeframeSubtitle anchors 1d to COB date', () => {
    const subtitle = buildTimeframeSubtitle('1d', {
        '1d': {
            end_date_source: 'flex_close',
            end_date: '2026-04-01',
        },
    });

    assert.match(subtitle, /^as of COB \d{2}\/\d{2}$/);
});

test('buildTimeframeSubtitle shows ET time for tws_rt timeframes', () => {
    const subtitle = buildTimeframeSubtitle('7d', {
        '7d': {
            end_date_source: 'tws_rt',
            end_date: '2026-04-02T14:41:00+00:00',
        },
    });

    assert.match(subtitle, /^as of \d{2}:\d{2} ET$/);
});

test('buildTimeframeSubtitle shows date for flex_report timeframes', () => {
    const subtitle = buildTimeframeSubtitle('mtd', {
        mtd: {
            end_date_source: 'flex_report',
            end_date: '2026-04-01',
        },
    });

    assert.match(subtitle, /^as of \d{2}\/\d{2}$/);
});
