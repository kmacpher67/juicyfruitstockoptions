import test from 'node:test';
import assert from 'node:assert/strict';

import { buildFrontendErrorLogPayload } from './errorLogging.js';

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
