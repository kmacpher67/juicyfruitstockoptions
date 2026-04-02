import test from 'node:test';
import assert from 'node:assert/strict';

import { formatCurrency, formatPercent, getNumericValue } from './portfolioGridFormatters.js';

test('getNumericValue returns null for undefined-like values and non-finite numbers', () => {
    assert.equal(getNumericValue(undefined), null);
    assert.equal(getNumericValue(null), null);
    assert.equal(getNumericValue(''), null);
    assert.equal(getNumericValue('undefined'), null);
    assert.equal(getNumericValue('NaN'), null);
    assert.equal(getNumericValue(Number.NaN), null);
    assert.equal(getNumericValue(Infinity), null);
    assert.equal(getNumericValue('-Infinity'), null);
});

test('portfolio-live-grid-001 currency formatter never renders literal undefined or NaN', () => {
    assert.equal(formatCurrency(undefined), '-');
    assert.equal(formatCurrency('undefined'), '-');
    assert.equal(formatCurrency('NaN'), '-');
    assert.equal(formatCurrency(Number.NaN), '-');
});

test('portfolio-live-grid-002 percent formatter never renders NaN%', () => {
    assert.equal(formatPercent(undefined), '-');
    assert.equal(formatPercent('undefined'), '-');
    assert.equal(formatPercent('NaN'), '-');
    assert.equal(formatPercent(Number.NaN), '-');
    assert.equal(formatPercent(Infinity), '-');
});

test('formatters still render valid numeric values correctly', () => {
    assert.equal(formatCurrency(1234.56, { minimumFractionDigits: 2, maximumFractionDigits: 2 }), '$1,234.56');
    assert.equal(formatPercent(0.125, 2), '12.50%');
});
