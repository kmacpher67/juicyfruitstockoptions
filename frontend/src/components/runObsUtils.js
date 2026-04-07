/**
 * runObsUtils.js
 * Utilities for Run Live Analysis button state recovery (stock-analysis-run-obs-004).
 *
 * Provides pure logic for mapping a latest-job API status to a button label
 * and enabled/disabled state so both Dashboard.jsx and tests can share the logic.
 */

/**
 * Terminal statuses — job is no longer running; button should be re-enabled.
 * @type {string[]}
 */
export const TERMINAL_STATUSES = ['completed', 'failed', 'timed_out', 'stale_watchdog_failed'];

/**
 * Derive button state from a latest-job API response object.
 *
 * @param {object|null} job  - The job object returned by GET /api/jobs/latest/stock-live-comparison
 * @returns {{ isRunning: boolean, statusLabel: string|null }}
 *   isRunning  — true when the job is actively running (button disabled)
 *   statusLabel — short reason string to display near the button, or null when idle
 */
export function deriveRunButtonState(job) {
    if (!job || !job.status) {
        return { isRunning: false, statusLabel: null };
    }

    switch (job.status) {
        case 'running':
            return { isRunning: true, statusLabel: 'Analysis running...' };
        case 'completed':
            return { isRunning: false, statusLabel: null };
        case 'failed':
            return { isRunning: false, statusLabel: 'Previous run failed — ready to retry' };
        case 'timed_out':
            return { isRunning: false, statusLabel: 'Previous run timed out — ready to retry' };
        case 'stale_watchdog_failed':
            return { isRunning: false, statusLabel: 'Stale run cleared — ready to retry' };
        default:
            return { isRunning: false, statusLabel: null };
    }
}

/**
 * Fetch the latest stock-live-comparison job from the backend.
 * Returns null on network error to allow graceful fallback.
 *
 * @param {string} token  - Bearer auth token (from localStorage)
 * @returns {Promise<object|null>}
 */
export async function fetchLatestJob(token) {
    try {
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        const res = await fetch('/api/jobs/latest/stock-live-comparison', { headers });
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}
