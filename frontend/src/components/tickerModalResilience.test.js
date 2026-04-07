/**
 * tickerModalResilience.test.js
 *
 * resilience-005: regression tests for TickerModal degraded-state logic.
 *
 * Tests cover:
 *  - classifyTabError: timeout, offline, endpoint, network error classifications
 *  - getBadgeText: correct human-readable text per reason code
 *  - Watchdog-style scenario: null error (watchdog exit) classified as timeout
 *  - Partial render scenario: 4 of 5 tabs succeed, 1 fails → error reason set correctly
 *  - Offline scenario: offline flag overrides error content → 'offline' reason
 */

import test from 'node:test';
import assert from 'node:assert/strict';

import { classifyTabError, getBadgeText, TAB_ERROR_REASON } from './tickerModalResilience.js';

// ---------------------------------------------------------------------------
// classifyTabError
// ---------------------------------------------------------------------------

test('classifyTabError: offline flag always returns offline reason regardless of error', () => {
    // offline with no error
    assert.equal(classifyTabError(true, null), TAB_ERROR_REASON.OFFLINE);
    // offline even when error looks like a timeout
    const timeoutErr = new Error('timeout of 12000ms exceeded');
    timeoutErr.code = 'ECONNABORTED';
    assert.equal(classifyTabError(true, timeoutErr), TAB_ERROR_REASON.OFFLINE);
    // offline with 500 HTTP error
    const httpErr = new Error('Request failed with status code 500');
    httpErr.response = { status: 500 };
    assert.equal(classifyTabError(true, httpErr), TAB_ERROR_REASON.OFFLINE);
});

test('classifyTabError: null error (watchdog exit / hard stop) returns timeout', () => {
    // When no error object exists the caller passes null — treat as timeout
    assert.equal(classifyTabError(false, null), TAB_ERROR_REASON.TIMEOUT);
    assert.equal(classifyTabError(false, undefined), TAB_ERROR_REASON.TIMEOUT);
});

test('classifyTabError: axios timeout error returns timeout reason', () => {
    const err = new Error('timeout of 12000ms exceeded');
    err.code = 'ECONNABORTED';
    assert.equal(classifyTabError(false, err), TAB_ERROR_REASON.TIMEOUT);
});

test('classifyTabError: error message containing "timeout" returns timeout reason', () => {
    const err = new Error('request timeout');
    assert.equal(classifyTabError(false, err), TAB_ERROR_REASON.TIMEOUT);
});

test('classifyTabError: network error (no response) returns endpoint reason', () => {
    const err = new Error('Network Error');
    assert.equal(classifyTabError(false, err), TAB_ERROR_REASON.ENDPOINT);
});

test('classifyTabError: ECONNREFUSED returns endpoint reason', () => {
    const err = new Error('connect ECONNREFUSED 127.0.0.1:8000');
    assert.equal(classifyTabError(false, err), TAB_ERROR_REASON.ENDPOINT);
});

test('classifyTabError: HTTP 4xx/5xx with response object returns endpoint reason', () => {
    const err404 = new Error('Request failed with status code 404');
    err404.response = { status: 404 };
    assert.equal(classifyTabError(false, err404), TAB_ERROR_REASON.ENDPOINT);

    const err503 = new Error('Request failed with status code 503');
    err503.response = { status: 503 };
    assert.equal(classifyTabError(false, err503), TAB_ERROR_REASON.ENDPOINT);
});

test('classifyTabError: unknown error defaults to endpoint reason', () => {
    const err = new Error('Something weird happened');
    assert.equal(classifyTabError(false, err), TAB_ERROR_REASON.ENDPOINT);
});

// ---------------------------------------------------------------------------
// getBadgeText
// ---------------------------------------------------------------------------

test('getBadgeText: returns correct text for each known reason code', () => {
    assert.equal(getBadgeText(TAB_ERROR_REASON.TIMEOUT), 'Timed out — data unavailable');
    assert.equal(getBadgeText(TAB_ERROR_REASON.OFFLINE), 'Offline — no network');
    assert.equal(getBadgeText(TAB_ERROR_REASON.ENDPOINT), 'Endpoint unavailable');
    assert.equal(getBadgeText(TAB_ERROR_REASON.STALE), 'Showing cached data');
});

test('getBadgeText: unknown/null reason falls back to generic message', () => {
    assert.equal(getBadgeText(null), 'Data unavailable');
    assert.equal(getBadgeText(undefined), 'Data unavailable');
    assert.equal(getBadgeText('unknown_code'), 'Data unavailable');
});

// ---------------------------------------------------------------------------
// Scenario: Watchdog-style tab exit (simulating hard stop)
// When the watchdog fires and clears loading state without an error object,
// classifyTabError(false, null) must yield TIMEOUT so the badge reads correctly.
// ---------------------------------------------------------------------------

test('scenario: watchdog hard-stop produces timeout badge text', () => {
    // Simulate watchdog exit: no error, not offline
    const reason = classifyTabError(false, null);
    const text = getBadgeText(reason);
    assert.equal(reason, TAB_ERROR_REASON.TIMEOUT);
    assert.ok(text.includes('Timed out'), `Expected timeout badge text, got: "${text}"`);
});

// ---------------------------------------------------------------------------
// Scenario: Partial render — 4 tabs succeed, 1 fails
// Each tab has its own reason; successful tabs have no reason set.
// The test simulates the per-tab error reason accumulation without React.
// ---------------------------------------------------------------------------

test('scenario: partial render — 4 tabs succeed, 1 rejects → only failed tab has error reason', () => {
    const tabs = ['signals', 'opportunity', 'optimizer', 'smart_rolls'];
    const failingTab = 'signals';
    const networkErr = new Error('Network Error');

    // Simulate what fetchTabData does: accumulate error reasons per tab
    const tabErrorReasons = {};
    for (const tab of tabs) {
        if (tab === failingTab) {
            tabErrorReasons[tab] = classifyTabError(false, networkErr);
        } else {
            tabErrorReasons[tab] = null; // success: no reason set
        }
    }

    // Only the failing tab has an error reason
    assert.equal(tabErrorReasons[failingTab], TAB_ERROR_REASON.ENDPOINT);
    // All successful tabs have null (no badge should be shown)
    for (const tab of tabs) {
        if (tab !== failingTab) {
            assert.equal(tabErrorReasons[tab], null);
        }
    }
    // Badge text for the failing tab is correct
    const badgeText = getBadgeText(tabErrorReasons[failingTab]);
    assert.equal(badgeText, 'Endpoint unavailable');
});

// ---------------------------------------------------------------------------
// Scenario: Offline — all tabs get offline reason
// ---------------------------------------------------------------------------

test('scenario: offline flag causes all tab errors to classify as offline', () => {
    const tabs = ['signals', 'opportunity', 'optimizer', 'smart_rolls'];
    const someErr = new Error('Network Error');

    for (const tab of tabs) {
        const reason = classifyTabError(true, someErr);
        assert.equal(reason, TAB_ERROR_REASON.OFFLINE, `Tab ${tab} should be offline`);
        assert.equal(getBadgeText(reason), 'Offline — no network');
    }
});

// ---------------------------------------------------------------------------
// Scenario: Timeout badge — per-request timeout produces correct badge
// ---------------------------------------------------------------------------

test('scenario: per-request timeout error produces timeout badge text', () => {
    const timeoutErr = new Error('timeout of 12000ms exceeded');
    timeoutErr.code = 'ECONNABORTED';

    const reason = classifyTabError(false, timeoutErr);
    assert.equal(reason, TAB_ERROR_REASON.TIMEOUT);
    assert.equal(getBadgeText(reason), 'Timed out — data unavailable');
});
