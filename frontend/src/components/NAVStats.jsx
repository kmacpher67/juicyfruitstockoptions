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

const StatCard = ({ label, value, isCurrency = false, isPercent = false, startValue, endDate, mtmTot, onClick, loading }) => {
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
    let tooltip = "Click to Update";
    if (startValue !== null && startValue !== undefined) {
        tooltip = `Start Val: $${startValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}\n`;
        // Fix: Append T00:00:00 to force local time interpretation, preventing UTC rollback to previous day
        if (endDate) tooltip += `End Date: ${new Date(endDate + 'T00:00:00').toLocaleDateString()}\n`;
        if (mtmTot !== null && mtmTot !== undefined) tooltip += `MTM tot: $${mtmTot.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

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
    const [localStats, setLocalStats] = useState({});

    // Merge props stats with local overrides
    const mergedStats = { ...stats, ...localStats };

    const handleWidgetClick = async (reportType) => {
        if (!reportType || loadingStates[reportType]) return;

        // Set Loading
        setLoadingStates(prev => ({ ...prev, [reportType]: true }));

        try {
            // Trigger Backend Fetch (Simple GET as requested)
            const res = await api.get(`/nav/report/${reportType}`);

            if (res.data.status === 'available' && res.data.stats) {
                // Determine keys based on report type for local override
                // We need to map the generic stats result back to the props expected (change_7d, start_7d etc)
                // The API returns { change, start, end, mtm, date }

                // Helper to map report type to suffix
                const suffixMap = {
                    [REPORT_MAP["1 Day"]]: "1d",
                    [REPORT_MAP["7 Day"]]: "7d",
                    [REPORT_MAP["30 Day"]]: "30d",
                    [REPORT_MAP["MTD"]]: "mtd",
                    [REPORT_MAP["YTD"]]: "ytd",
                    [REPORT_MAP["1 Year"]]: "yoy",
                };

                const s = suffixMap[reportType];
                if (s) {
                    setLocalStats(prev => ({
                        ...prev,
                        [`change_${s}`]: res.data.stats.change,
                        [`start_${s}`]: res.data.stats.start,
                        [`mtm_${s}`]: res.data.stats.mtm,
                        [`date_${s}`]: res.data.stats.date,
                    }));
                }
            }
            // If fetching, we strictly respect "get whatever returns". 
            // If it returns 'fetching', it means no data yet. We just stop loading.
            // User can click again later.
        } catch (e) {
            console.error("Failed to update widget", e);
        } finally {
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
        Promise.all(allTypes.map(t => handleWidgetClick(t)))
            .finally(() => setLoadingStates({}));
        // Note: handleWidgetClick handles its own loading state removal, 
        // but this ensures cleanup if something goes wrong.
    };

    if (!mergedStats) return null;

    return (
        <div className="mb-4">
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 items-center w-full">
                {/* Current NAV */}
                <div className="w-full">
                    <StatCard label="Current NAV" value={mergedStats.current_nav} isCurrency />
                </div>

                {/* Histograms */}
                <div className="w-full">
                    <StatCard
                        label="1 Day"
                        value={mergedStats.change_1d}
                        isPercent
                        startValue={mergedStats.start_1d}
                        endDate={mergedStats.date_1d}
                        mtmTot={mergedStats.mtm_1d}
                        onClick={() => handleWidgetClick(REPORT_MAP["1 Day"])}
                        loading={loadingStates[REPORT_MAP["1 Day"]]}
                    />
                </div>
                <div className="w-full">
                    <StatCard
                        label="7 Day"
                        value={mergedStats.change_7d}
                        isPercent
                        startValue={mergedStats.start_7d}
                        endDate={mergedStats.date_7d}
                        mtmTot={mergedStats.mtm_7d}
                        onClick={() => handleWidgetClick(REPORT_MAP["7 Day"])}
                        loading={loadingStates[REPORT_MAP["7 Day"]]}
                    />
                </div>
                <div className="w-full">
                    <StatCard
                        label="30 Day"
                        value={mergedStats.change_30d}
                        isPercent
                        startValue={mergedStats.start_30d}
                        endDate={mergedStats.date_30d}
                        mtmTot={mergedStats.mtm_30d}
                        onClick={() => handleWidgetClick(REPORT_MAP["30 Day"])}
                        loading={loadingStates[REPORT_MAP["30 Day"]]}
                    />
                </div>
                <div className="w-full">
                    <StatCard
                        label="MTD"
                        value={mergedStats.change_mtd}
                        isPercent
                        startValue={mergedStats.start_mtd}
                        endDate={mergedStats.date_mtd}
                        mtmTot={mergedStats.mtm_mtd}
                        onClick={() => handleWidgetClick(REPORT_MAP["MTD"])}
                        loading={loadingStates[REPORT_MAP["MTD"]]}
                    />
                </div>
                <div className="w-full">
                    <StatCard
                        label="YTD"
                        value={mergedStats.change_ytd}
                        isPercent
                        startValue={mergedStats.start_ytd}
                        endDate={mergedStats.date_ytd}
                        mtmTot={mergedStats.mtm_ytd}
                        onClick={() => handleWidgetClick(REPORT_MAP["YTD"])}
                        loading={loadingStates[REPORT_MAP["YTD"]]}
                    />
                </div>
                <div className="w-full">
                    <StatCard
                        label="1 Year"
                        value={mergedStats.change_yoy}
                        isPercent
                        startValue={mergedStats.start_yoy}
                        endDate={mergedStats.date_yoy}
                        mtmTot={mergedStats.mtm_yoy}
                        onClick={() => handleWidgetClick(REPORT_MAP["1 Year"])}
                        loading={loadingStates[REPORT_MAP["1 Year"]]}
                    />
                </div>

                {/* Sync Button */}
                <div className="w-full">
                    <button
                        onClick={handleLiveSync}
                        className={`
                            h-20 w-full px-4 rounded border border-gray-600 bg-gray-800 hover:bg-gray-700 
                            text-[10px] font-bold uppercase tracking-wider transition-colors 
                            flex flex-col items-center justify-center gap-1
                        `}
                        title="Force Live Update All"
                    >
                        <div className={`w-3 h-3 rounded-full ${Object.values(loadingStates).some(x => x) ? 'bg-yellow-400 animate-pulse' : 'bg-green-500'}`}></div>
                        <span>SYNC ALL</span>
                    </button>
                </div>
            </div>
        </div>
    );
};

export default NAVStats;
