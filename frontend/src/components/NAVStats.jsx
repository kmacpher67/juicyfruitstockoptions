import React, { useState, useEffect, useCallback } from 'react';
import api from '../api/axios';

const REPORT_MAP = {
    "1 Day": "NAV1D",
    "7 Day": "Nav7D",
    "30 Day": "Nav30D",
    "MTD": "NAVMTD",
    "YTD": "NAVYTD",
    "1 Year": "NAV1Y"
};

const StatCard = ({ label, value, isCurrency = false, isPercent = false, startValue, onClick, loading }) => {
    let colorClass = "text-white";
    if (isPercent && value !== null && value !== undefined) {
        colorClass = value > 0 ? "text-green-400" : value < 0 ? "text-red-400" : "text-gray-400";
    }

    const displayValue = (loading || value === null || value === undefined)
        ? "--.--"
        : isCurrency
            ? `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : isPercent
                ? `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
                : value;

    // Tooltip Text
    const tooltip = startValue !== null && startValue !== undefined
        ? `Starting Value: $${startValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
        : "Click to Update";

    return (
        <div
            onClick={onClick}
            className={`
                bg-gray-800 p-2 rounded flex flex-col items-center justify-center 
                border ${loading ? 'border-yellow-500 animate-pulse' : 'border-gray-700 hover:border-blue-500'} 
                transition-all cursor-pointer relative group h-20 w-full select-none
            `}
            title={tooltip}
        >
            <span className="text-gray-400 text-[10px] uppercase font-semibold">{label}</span>
            <span className={`text-lg font-bold ${colorClass} font-mono`}>
                {displayValue}
            </span>
            {/* Loading Indicator Overlay */}
            {loading && (
                <div className="absolute inset-0 bg-black bg-opacity-20 flex items-center justify-center rounded">
                    <div className="w-2 h-2 bg-yellow-400 rounded-full animate-ping"></div>
                </div>
            )}
        </div>
    );
};

const NAVStats = ({ stats, onRefreshRequest }) => {
    const [loadingStates, setLoadingStates] = useState({});

    // Poll for updates if any widget is loading
    useEffect(() => {
        const activeLoaders = Object.entries(loadingStates).filter(([_, isLoading]) => isLoading);
        if (activeLoaders.length === 0) return;

        const interval = setInterval(async () => {
            // Check status of each loading report
            let changed = false;
            const newStates = { ...loadingStates };

            for (const [reportType, isLoading] of activeLoaders) {
                if (!isLoading) continue;
                try {
                    const res = await api.get(`/nav/report/${reportType}`);
                    if (res.data.status === 'available') {
                        newStates[reportType] = false;
                        changed = true;
                    }
                } catch (e) {
                    console.error(`Poll failed for ${reportType}`, e);
                    newStates[reportType] = false; // Stop on error
                    changed = true;
                }
            }

            if (changed) {
                setLoadingStates(newStates);
                // If any finished, trigger global refresh
                if (onRefreshRequest) onRefreshRequest();
            }
        }, 2000); // Poll every 2s

        return () => clearInterval(interval);
    }, [loadingStates, onRefreshRequest]);

    const handleWidgetClick = async (reportType) => {
        if (!reportType || loadingStates[reportType]) return;

        // Set Loading
        setLoadingStates(prev => ({ ...prev, [reportType]: true }));

        try {
            // Trigger Backend Fetch
            const res = await api.get(`/nav/report/${reportType}`);
            if (res.data.status === 'available') {
                // Already have data, just stop loading
                setLoadingStates(prev => ({ ...prev, [reportType]: false }));
            }
            // If 'fetching', the Effect hook will take over polling
        } catch (e) {
            console.error("Failed to trigger update", e);
            setLoadingStates(prev => ({ ...prev, [reportType]: false }));
        }
    };

    const handleLiveSync = async () => {
        // Trigger all
        const allTypes = Object.values(REPORT_MAP);
        // Mark all as loading
        const newLoading = {};
        allTypes.forEach(t => newLoading[t] = true);
        setLoadingStates(prev => ({ ...prev, ...newLoading }));

        // Fire off requests in parallel
        allTypes.forEach(t => api.get(`/nav/report/${t}`).catch(e => console.error(e)));
    };

    if (!stats) return null;

    return (
        <div className="mb-4">
            <div className="flex flex-wrap lg:flex-nowrap gap-2 items-center">
                {/* Current NAV (No specific report type? Maybe generic or just static) */}
                <div className="flex-grow min-w-[120px]">
                    <StatCard label="Current NAV" value={stats.current_nav} isCurrency />
                </div>

                {/* Histograms */}
                <div className="flex-grow min-w-[100px]">
                    <StatCard
                        label="1 Day"
                        value={stats.change_1d}
                        isPercent
                        startValue={stats.start_1d}
                        onClick={() => handleWidgetClick(REPORT_MAP["1 Day"])}
                        loading={loadingStates[REPORT_MAP["1 Day"]]}
                    />
                </div>
                <div className="flex-grow min-w-[100px]">
                    <StatCard
                        label="7 Day"
                        value={stats.change_7d}
                        isPercent
                        startValue={stats.start_7d}
                        onClick={() => handleWidgetClick(REPORT_MAP["7 Day"])}
                        loading={loadingStates[REPORT_MAP["7 Day"]]}
                    />
                </div>
                <div className="flex-grow min-w-[100px]">
                    <StatCard
                        label="30 Day"
                        value={stats.change_30d}
                        isPercent
                        startValue={stats.start_30d}
                        onClick={() => handleWidgetClick(REPORT_MAP["30 Day"])}
                        loading={loadingStates[REPORT_MAP["30 Day"]]}
                    />
                </div>
                <div className="flex-grow min-w-[100px]">
                    <StatCard
                        label="MTD"
                        value={stats.change_mtd}
                        isPercent
                        startValue={stats.start_mtd}
                        onClick={() => handleWidgetClick(REPORT_MAP["MTD"])}
                        loading={loadingStates[REPORT_MAP["MTD"]]}
                    />
                </div>
                <div className="flex-grow min-w-[100px]">
                    <StatCard
                        label="YTD"
                        value={stats.change_ytd}
                        isPercent
                        startValue={stats.start_ytd}
                        onClick={() => handleWidgetClick(REPORT_MAP["YTD"])}
                        loading={loadingStates[REPORT_MAP["YTD"]]}
                    />
                </div>
                <div className="flex-grow min-w-[100px]">
                    <StatCard
                        label="1 Year"
                        value={stats.change_yoy}
                        isPercent
                        startValue={stats.start_yoy}
                        onClick={() => handleWidgetClick(REPORT_MAP["1 Year"])}
                        loading={loadingStates[REPORT_MAP["1 Year"]]}
                    />
                </div>

                {/* Sync Button */}
                <button
                    onClick={handleLiveSync}
                    className={`
                        h-20 px-4 rounded border border-gray-600 bg-gray-800 hover:bg-gray-700 
                        text-[10px] font-bold uppercase tracking-wider transition-colors 
                        flex flex-col items-center justify-center gap-1
                        min-w-[80px]
                    `}
                    title="Force Live Update All"
                >
                    <div className={`w-3 h-3 rounded-full ${Object.values(loadingStates).some(x => x) ? 'bg-yellow-400 animate-pulse' : 'bg-green-500'}`}></div>
                    <span>SYNC ALL</span>
                </button>
            </div>
        </div>
    );
};

export default NAVStats;
