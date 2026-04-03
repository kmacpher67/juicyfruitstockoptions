export const buildFrontendErrorLogPayload = ({ error, errorInfo, boundaryName }) => ({
    level: 'error',
    source: 'frontend',
    boundary: boundaryName || 'unknown',
    message: error?.message || 'Unknown frontend error',
    stack: error?.stack || null,
    componentStack: errorInfo?.componentStack || null,
    timestamp: new Date().toISOString(),
});

export const logFrontendError = (payload) => {
    if (!payload) return;
    // Keep this robust and dependency-free for now; backend forwarding can be added later.
    console.error('FrontendErrorBoundary', payload);
};
