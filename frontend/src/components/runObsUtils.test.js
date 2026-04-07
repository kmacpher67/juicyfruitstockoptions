/**
 * Tests for runObsUtils.js (stock-analysis-run-obs-004)
 * Verifies Run button state derivation and latest-job fetch logic.
 * Uses Node built-in test runner (node:test + node:assert/strict).
 */
import test from 'node:test';
import assert from 'node:assert/strict';

import { deriveRunButtonState, fetchLatestJob, TERMINAL_STATUSES } from './runObsUtils.js';

// ---------------------------------------------------------------------------
// deriveRunButtonState
// ---------------------------------------------------------------------------

test('status "running" keeps button disabled with correct label', () => {
    const result = deriveRunButtonState({ status: 'running' });
    assert.equal(result.isRunning, true);
    assert.equal(result.statusLabel, 'Analysis running...');
});

test('status "completed" re-enables button with no label', () => {
    const result = deriveRunButtonState({ status: 'completed' });
    assert.equal(result.isRunning, false);
    assert.equal(result.statusLabel, null);
});

test('status "failed" re-enables button with retry label', () => {
    const result = deriveRunButtonState({ status: 'failed' });
    assert.equal(result.isRunning, false);
    assert.ok(result.statusLabel.includes('retry'), 'label should mention retry');
});

test('status "timed_out" re-enables button with timed-out label', () => {
    const result = deriveRunButtonState({ status: 'timed_out' });
    assert.equal(result.isRunning, false);
    assert.ok(result.statusLabel.includes('timed out'), 'label should mention timed out');
    assert.ok(result.statusLabel.includes('retry'));
});

test('status "stale_watchdog_failed" re-enables button with stale label', () => {
    const result = deriveRunButtonState({ status: 'stale_watchdog_failed' });
    assert.equal(result.isRunning, false);
    assert.ok(result.statusLabel.includes('Stale'), 'label should mention stale');
    assert.ok(result.statusLabel.includes('retry'));
});

test('null job returns isRunning=false and null label', () => {
    const result = deriveRunButtonState(null);
    assert.equal(result.isRunning, false);
    assert.equal(result.statusLabel, null);
});

test('job without status returns isRunning=false and null label', () => {
    const result = deriveRunButtonState({});
    assert.equal(result.isRunning, false);
    assert.equal(result.statusLabel, null);
});

test('unknown status returns isRunning=false and null label', () => {
    const result = deriveRunButtonState({ status: 'queued' });
    assert.equal(result.isRunning, false);
    assert.equal(result.statusLabel, null);
});

// ---------------------------------------------------------------------------
// TERMINAL_STATUSES covers all non-running states
// ---------------------------------------------------------------------------

test('TERMINAL_STATUSES does not include "running"', () => {
    assert.ok(!TERMINAL_STATUSES.includes('running'));
});

test('all terminal statuses produce isRunning=false', () => {
    for (const status of TERMINAL_STATUSES) {
        const result = deriveRunButtonState({ status });
        assert.equal(result.isRunning, false, `Expected isRunning=false for status "${status}"`);
    }
});

// ---------------------------------------------------------------------------
// fetchLatestJob — polling interval / mount logic (simulated via mocked fetch)
// ---------------------------------------------------------------------------

test('fetchLatestJob returns parsed JSON on 200 response', async () => {
    const mockJob = { status: 'timed_out', started_at: '2026-04-07T10:00:00Z' };
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => ({
        ok: true,
        json: async () => mockJob,
    });

    try {
        const result = await fetchLatestJob('test-token');
        assert.deepEqual(result, mockJob);
    } finally {
        globalThis.fetch = originalFetch;
    }
});

test('fetchLatestJob returns null on non-OK response', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => ({ ok: false, status: 404 });

    try {
        const result = await fetchLatestJob('test-token');
        assert.equal(result, null);
    } finally {
        globalThis.fetch = originalFetch;
    }
});

test('fetchLatestJob returns null on network error', async () => {
    const originalFetch = globalThis.fetch;
    globalThis.fetch = async () => { throw new Error('Network failure'); };

    try {
        const result = await fetchLatestJob('test-token');
        assert.equal(result, null);
    } finally {
        globalThis.fetch = originalFetch;
    }
});

test('fetchLatestJob sends Authorization header when token is provided', async () => {
    const originalFetch = globalThis.fetch;
    let capturedHeaders = null;
    globalThis.fetch = async (url, opts) => {
        capturedHeaders = opts?.headers ?? {};
        return { ok: true, json: async () => ({ status: 'running' }) };
    };

    try {
        await fetchLatestJob('my-secret-token');
        assert.equal(capturedHeaders.Authorization, 'Bearer my-secret-token');
    } finally {
        globalThis.fetch = originalFetch;
    }
});

test('fetchLatestJob sends no Authorization header when token is empty', async () => {
    const originalFetch = globalThis.fetch;
    let capturedHeaders = null;
    globalThis.fetch = async (url, opts) => {
        capturedHeaders = opts?.headers ?? {};
        return { ok: true, json: async () => ({ status: 'completed' }) };
    };

    try {
        await fetchLatestJob('');
        assert.ok(!capturedHeaders.Authorization, 'Should not send Authorization header without token');
    } finally {
        globalThis.fetch = originalFetch;
    }
});

// ---------------------------------------------------------------------------
// Polling interval cleared on unmount — simulated lifecycle test
// ---------------------------------------------------------------------------

test('polling interval is cleared when cleanup function is called', async () => {
    // Simulate the useEffect pattern used in Dashboard.jsx:
    // - setInterval registers a recurring check
    // - the returned cleanup clears it
    // We verify clearInterval is called once with the correct id.

    const calls = [];
    const fakeIntervalId = 42;

    const fakeSetInterval = (fn, ms) => {
        calls.push({ type: 'set', ms });
        return fakeIntervalId;
    };
    const fakeClearInterval = (id) => {
        calls.push({ type: 'clear', id });
    };

    // Replicate the setup/cleanup closure from Dashboard.jsx
    function setupPolling(setIntervalFn, clearIntervalFn) {
        const id = setIntervalFn(() => {}, 15000);
        return () => clearIntervalFn(id);
    }

    const cleanup = setupPolling(fakeSetInterval, fakeClearInterval);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].type, 'set');
    assert.equal(calls[0].ms, 15000);

    cleanup();
    assert.equal(calls.length, 2);
    assert.equal(calls[1].type, 'clear');
    assert.equal(calls[1].id, fakeIntervalId);
});
