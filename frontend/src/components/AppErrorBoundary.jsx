import React from 'react';
import { buildFrontendErrorLogPayload, logFrontendError } from './errorLogging';

class AppErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError() {
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        const payload = buildFrontendErrorLogPayload({
            error,
            errorInfo,
            boundaryName: this.props.name || 'app',
        });
        logFrontendError(payload);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-gray-900 text-gray-100 flex items-center justify-center px-6">
                    <div className="max-w-xl text-center space-y-3">
                        <h1 className="text-xl font-semibold">Something went wrong in the dashboard.</h1>
                        <p className="text-sm text-gray-400">
                            The error was logged for diagnostics. Please refresh the page and retry.
                        </p>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}

export default AppErrorBoundary;
