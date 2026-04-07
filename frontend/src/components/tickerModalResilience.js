/**
 * tickerModalResilience.js
 *
 * Pure-function helpers for per-tab degraded-state badge logic in TickerModal.
 * Kept separate from the React component so they are unit-testable with node:test.
 */

/**
 * Tab error reason codes — one per degraded state type.
 * These are the canonical values stored/compared in tab error state.
 */
export const TAB_ERROR_REASON = {
    TIMEOUT: 'timeout',
    OFFLINE: 'offline',
    ENDPOINT: 'endpoint',
    STALE: 'stale',
};

/**
 * Classify the error reason for a tab fetch failure.
 *
 * @param {boolean} isOffline - true when navigator.onLine === false at fetch time
 * @param {Error|null} error - the caught error object (may be null for watchdog exit)
 * @returns {string} one of TAB_ERROR_REASON values
 */
export const classifyTabError = (isOffline, error) => {
    if (isOffline) return TAB_ERROR_REASON.OFFLINE;
    if (!error) return TAB_ERROR_REASON.TIMEOUT;
    const msg = String(error?.message || error?.code || '').toLowerCase();
    // axios timeout surfaces as ECONNABORTED or includes 'timeout'
    if (msg.includes('timeout') || msg.includes('econnaborted')) return TAB_ERROR_REASON.TIMEOUT;
    // network errors (no response)
    if (msg.includes('network') || msg.includes('econnrefused') || msg.includes('failed to fetch')) {
        return TAB_ERROR_REASON.ENDPOINT;
    }
    // http 4xx/5xx — axios attaches response to the error
    if (error?.response?.status) return TAB_ERROR_REASON.ENDPOINT;
    return TAB_ERROR_REASON.ENDPOINT;
};

/**
 * Map a reason code to the human-readable badge text shown in the tab body.
 *
 * @param {string} reason - one of TAB_ERROR_REASON values
 * @returns {string} user-visible badge text
 */
export const getBadgeText = (reason) => {
    switch (reason) {
        case TAB_ERROR_REASON.TIMEOUT:
            return 'Timed out — data unavailable';
        case TAB_ERROR_REASON.OFFLINE:
            return 'Offline — no network';
        case TAB_ERROR_REASON.ENDPOINT:
            return 'Endpoint unavailable';
        case TAB_ERROR_REASON.STALE:
            return 'Showing cached data';
        default:
            return 'Data unavailable';
    }
};

/**
 * Build standardized freshness banner content from API freshness metadata.
 *
 * @param {object|null|undefined} freshness
 * @returns {{ tone: 'stale' | 'fresh', text: string } | null}
 */
export const getFreshnessBannerModel = (freshness) => {
    if (!freshness || typeof freshness !== 'object' || !('is_stale' in freshness)) return null;
    if (freshness.is_stale) {
        return {
            tone: 'stale',
            text: `Stale DB snapshot (${freshness.stale_reason || 'stale'}).${freshness.refresh_queued ? ' Refresh queued.' : ' Refresh pending.'}`,
        };
    }
    return {
        tone: 'fresh',
        text: `Fresh DB snapshot${freshness.last_updated ? ` as of ${freshness.last_updated}` : ''}.`,
    };
};
