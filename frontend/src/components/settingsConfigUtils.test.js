import test from 'node:test';
import assert from 'node:assert/strict';

import {
    DEFAULT_DATA_FRESHNESS_CONFIG,
    normalizeDataFreshnessConfig,
    buildDataFreshnessPayload,
} from './settingsConfigUtils.js';

test('normalizeDataFreshnessConfig returns defaults when input is missing', () => {
    assert.deepEqual(normalizeDataFreshnessConfig(null), DEFAULT_DATA_FRESHNESS_CONFIG);
});

test('normalizeDataFreshnessConfig coerces invalid values to positive integers', () => {
    const normalized = normalizeDataFreshnessConfig({
        price_open_min: '12.9',
        price_closed_min: 0,
        mixed_open_min: -1,
        mixed_closed_min: 'bad',
        profile_open_min: 100.7,
        profile_closed_min: 2,
    });
    assert.equal(normalized.price_open_min, 12);
    assert.equal(normalized.price_closed_min, 1);
    assert.equal(normalized.mixed_open_min, 1);
    assert.equal(normalized.mixed_closed_min, DEFAULT_DATA_FRESHNESS_CONFIG.mixed_closed_min);
    assert.equal(normalized.profile_open_min, 100);
    assert.equal(normalized.profile_closed_min, 2);
});

test('buildDataFreshnessPayload delegates to normalized positive values', () => {
    const payload = buildDataFreshnessPayload({ price_open_min: 5, mixed_open_min: '6' });
    assert.equal(payload.price_open_min, 5);
    assert.equal(payload.mixed_open_min, 6);
    assert.equal(payload.profile_closed_min, DEFAULT_DATA_FRESHNESS_CONFIG.profile_closed_min);
});
