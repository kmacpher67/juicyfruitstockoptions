import React, { useState } from 'react';
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
                bg-gray-800 px-2 py-1.5 rounded flex flex-col items-center justify-center 
                border ${loading ? 'border-yellow-500 animate-pulse' : 'border-gray-700 hover:border-blue-500'} 
                transition-all cursor-pointer relative group h-[74px] w-full select-none
            `}
            title={tooltip}
        >
            <span className="text-gray-400 text-[10px] uppercase font-semibold">{label}</span>
            <span className={`text-base lg:text-lg font-bold ${colorClass} font-mono`}>
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

const formatRelativeTime = (value) => {
    if (!value) return 'update pending';

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return 'update pending';

    const diffSeconds = Math.max(0, Math.floor((Date.now() - parsed.getTime()) / 1000));
    if (diffSeconds < 5) return 'updated just now';
    if (diffSeconds < 60) return `updated ${diffSeconds}s ago`;

    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) return `updated ${diffMinutes}m ago`;

    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `updated ${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    return `updated ${diffDays}d ago`;
};

const StatusPill = ({ dotClass, label }) => (
    <div className="inline-flex items-center gap-2 rounded-full border border-gray-700 bg-gray-900/70 px-2.5 py-1">
        <span className={`h-2.5 w-2.5 rounded-full ${dotClass}`}></span>
        <span className="text-[11px] font-semibold uppercase tracking-wide text-gray-100">{label}</span>
    </div>
);

const getStatusConfig = (stats) => {
    switch (stats.connection_state) {
        case 'connected':
            return { dotClass: 'bg-green-400', label: 'TWS live' };
        case 'handshake_failed':
            return { dotClass: 'bg-amber-400', label: 'Handshake failed' };
        case 'socket_unreachable':
            return { dotClass: 'bg-red-400', label: 'Socket unreachable' };
        case 'disconnected':
            return { dotClass: 'bg-yellow-400', label: 'Disconnected' };
        case 'disabled':
            return { dotClass: 'bg-gray-500', label: 'Live disabled' };
        case 'unavailable':
            return { dotClass: 'bg-gray-500', label: 'ibapi missing' };
        default:
            return stats.tws_enabled
                ? stats.live_connected
                    ? { dotClass: 'bg-green-400', label: 'TWS live' }
                    : { dotClass: 'bg-yellow-400', label: 'EOD only' }
                : { dotClass: 'bg-gray-500', label: 'Live disabled' };
    }
};

const NAVStats = ({ stats }) => {
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
        Promise.all([
            ...allTypes.map(t => handleWidgetClick(t)),
            api.get('/portfolio/nav/live'),
            api.get('/portfolio/live-status'),
        ])
            .then((results) => {
                const liveNav = results[allTypes.length]?.data;
                const liveStatus = results[allTypes.length + 1]?.data;
                const start1d = mergedStats.start_1d ?? localStats.start_1d;
                const liveCurrentNav = liveNav?.total_nav;

                setLocalStats((prev) => ({
                    ...prev,
                    current_nav: liveCurrentNav ?? prev.current_nav,
                    data_source: liveNav?.source === 'tws' ? 'tws_live' : prev.data_source,
                    last_updated:
                        liveNav?.last_tws_update ||
                        liveNav?.timestamp ||
                        liveStatus?.last_account_value_update ||
                        liveStatus?.last_position_update ||
                        prev.last_updated,
                    live_connected: liveStatus?.connected ?? prev.live_connected,
                    tws_enabled: liveStatus?.tws_enabled ?? prev.tws_enabled,
                    connection_state: liveStatus?.connection_state ?? prev.connection_state,
                    diagnosis: liveStatus?.diagnosis ?? prev.diagnosis,
                    mtm_1d:
                        start1d !== null && start1d !== undefined && liveCurrentNav !== null && liveCurrentNav !== undefined
                            ? liveCurrentNav - start1d
                            : prev.mtm_1d,
                    change_1d:
                        start1d && liveCurrentNav !== null && liveCurrentNav !== undefined
                            ? ((liveCurrentNav - start1d) / start1d) * 100
                            : prev.change_1d,
                    date_1d:
                        liveNav?.last_tws_update ||
                        liveNav?.timestamp ||
                        prev.date_1d,
                }));
            })
            .catch((error) => {
                console.error('Failed to refresh live TWS state', error);
            })
            .finally(() => setLoadingStates({}));
        // Note: handleWidgetClick handles its own loading state removal, 
        // but this ensures cleanup if something goes wrong.
    };

    if (!mergedStats) return null;

    const statusConfig = getStatusConfig(mergedStats);
    const freshnessText = formatRelativeTime(mergedStats.last_updated);
    const statusDetail = mergedStats.live_connected
        ? freshnessText
        : mergedStats.diagnosis || 'Live updates are currently unavailable.';
    const sourceLabel = mergedStats.data_source === 'tws_live' ? 'TWS intraday' : 'Flex EOD';

    return (
        <div className="mb-4 w-full">
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2 items-center w-full">
                <div className="col-span-2 md:col-span-2 lg:col-span-2 w-full">
                    <button
                        onClick={handleLiveSync}
                        className={`
                            h-[74px] w-full rounded border border-gray-600 bg-gray-800 px-3 text-left transition-colors
                            hover:bg-gray-700
                        `}
                        title="Refresh NAV widgets and live TWS status"
                    >
                        <div className="flex h-full items-center justify-between gap-2">
                            <div className="min-w-0">
                                <div className="mb-1 flex flex-wrap items-center gap-1.5">
                                    <StatusPill dotClass={statusConfig.dotClass} label={statusConfig.label} />
                                    <span className="text-[10px] uppercase tracking-wide text-gray-500">
                                        {sourceLabel}
                                    </span>
                                </div>
                                <div className="text-[10px] uppercase tracking-wide text-gray-400">Current NAV</div>
                                <div className="font-mono text-lg lg:text-[1.55rem] font-bold text-white leading-tight">
                                    {mergedStats.current_nav === null || mergedStats.current_nav === undefined
                                        ? '--.--'
                                        : `$${mergedStats.current_nav.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                                </div>
                                <div
                                    className="text-[11px] text-gray-400"
                                    title={mergedStats.diagnosis || ''}
                                >
                                    {statusDetail}
                                </div>
                            </div>
                            <div className="flex flex-col items-center justify-center gap-1 text-[10px] font-bold uppercase tracking-wider text-gray-100 shrink-0">
                                <div className={`h-3 w-3 rounded-full ${Object.values(loadingStates).some(x => x) ? 'bg-yellow-400 animate-pulse' : 'bg-green-500'}`}></div>
                                <span>Sync All</span>
                            </div>
                        </div>
                    </button>
                </div>

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
            </div>
        </div>
    );
};

export default NAVStats;
