export const buildFrontendErrorLogPayload = ({ error, errorInfo, boundaryName }) => ({
    level: 'error',
    source: 'frontend',
    boundary: boundaryName || 'unknown',
    message: error?.message || 'Unknown frontend error',
    stack: error?.stack || null,
    componentStack: errorInfo?.componentStack || null,
    timestamp: new Date().toISOString(),
    path: typeof window !== 'undefined' ? window.location?.pathname || null : null,
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent || null : null,
});

const getAuthHeaders = () => {
    const headers = { 'Content-Type': 'application/json' };
    try {
        const token = localStorage.getItem('token');
        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }
    } catch (_) {
        // Ignore storage access failures and continue best-effort.
    }
    return headers;
};

export const logFrontendError = async (payload) => {
    if (!payload) return;
    console.error('FrontendErrorBoundary', payload);
    try {
        await fetch('/api/logs/frontend', {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(payload),
            keepalive: true,
        });
    } catch (error) {
        console.error('FrontendErrorBoundary transport failed', error);
    }
};
