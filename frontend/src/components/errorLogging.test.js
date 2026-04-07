import test from 'node:test';
import assert from 'node:assert/strict';

import { buildFrontendErrorLogPayload, logFrontendError } from './errorLogging.js';

test('buildFrontendErrorLogPayload produces structured diagnostic payload', () => {
    const error = new Error('boom');
    const payload = buildFrontendErrorLogPayload({
        error,
        errorInfo: { componentStack: '\n in Dashboard' },
        boundaryName: 'dashboard',
    });

    assert.equal(payload.level, 'error');
    assert.equal(payload.source, 'frontend');
    assert.equal(payload.boundary, 'dashboard');
    assert.equal(payload.message, 'boom');
    assert.ok(payload.stack.includes('boom'));
    assert.equal(payload.componentStack, '\n in Dashboard');
    assert.ok(payload.timestamp);
});

test('logFrontendError posts payload to backend transport endpoint', async () => {
    const originalFetch = global.fetch;
    const originalLocalStorage = global.localStorage;
    const originalConsoleError = console.error;

    const calls = [];
    global.fetch = async (url, options) => {
        calls.push({ url, options });
        return { ok: true };
    };
    global.localStorage = {
        getItem: (key) => (key === 'token' ? 'abc123' : null),
    };
    console.error = () => {};

    const payload = { level: 'error', message: 'boom', source: 'frontend' };
    await logFrontendError(payload);

    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, '/api/logs/frontend');
    assert.equal(calls[0].options.method, 'POST');
    assert.equal(calls[0].options.headers.Authorization, 'Bearer abc123');
    assert.equal(calls[0].options.headers['Content-Type'], 'application/json');
    assert.equal(calls[0].options.body, JSON.stringify(payload));

    global.fetch = originalFetch;
    global.localStorage = originalLocalStorage;
    console.error = originalConsoleError;
});
