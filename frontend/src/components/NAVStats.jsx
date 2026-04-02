import React, { useEffect, useMemo, useState } from 'react';
import api from '../api/axios';
import { buildTimeframeSubtitle, normalizeAccountScopeParam } from './navStatsUtils';

const REPORT_MAP = {
    "1 Day": "NAV1D",
    "7 Day": "Nav7D",
    "30 Day": "Nav30D",
    "MTD": "NAVMTD",
    "YTD": "NAVYTD",
    "1 Year": "NAV1Y"
};

const StatCard = ({ label, value, isCurrency = false, isPercent = false, startValue, endDate, mtmTot, subtitle, onClick, loading }) => {
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
        const displayDate = formatTooltipDate(endDate);
        if (displayDate) tooltip += `End Date: ${displayDate}\n`;
        if (mtmTot !== null && mtmTot !== undefined) tooltip += `MTM tot: $${mtmTot.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }

    return (
        <div
            onClick={onClick}
            className={`
                bg-gray-800 px-2 py-1 rounded flex flex-col items-center justify-center
                border ${loading ? 'border-yellow-500 animate-pulse' : 'border-gray-700 hover:border-blue-500'} 
                transition-all cursor-pointer relative group h-[62px] w-full select-none
            `}
            title={tooltip}
        >
            <span className="text-gray-400 text-[10px] uppercase font-semibold">{label}</span>
            <span className={`text-sm lg:text-base font-bold ${colorClass} font-mono`}>
                {displayValue}
            </span>
            {subtitle ? (
                <span className="mt-0.5 text-center text-[9px] text-gray-500">{subtitle}</span>
            ) : null}
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

const formatCurrency = (value) => (
    value === null || value === undefined
        ? '--.--'
        : `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
);

const formatTooltipDate = (value) => {
    if (!value) return null;

    const parsed = typeof value === 'string' && !value.includes('T')
        ? new Date(`${value}T00:00:00`)
        : new Date(value);

    if (Number.isNaN(parsed.getTime())) return null;
    return parsed.toLocaleDateString();
};

const hasMeaningfulLiveSnapshot = (snapshot) => (
    Boolean(snapshot) && (
        snapshot.last_updated_rt !== null && snapshot.last_updated_rt !== undefined ||
        snapshot.current_nav_rt !== null && snapshot.current_nav_rt !== undefined && snapshot.current_nav_rt !== 0
    )
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

const NAVStats = ({ stats, selectedAccount = 'all' }) => {
    const [loadingStates, setLoadingStates] = useState({});
    const [localStats, setLocalStats] = useState({});
    const scopedParams = useMemo(() => normalizeAccountScopeParam(selectedAccount), [selectedAccount]);

    useEffect(() => {
        setLocalStats({});
        setLoadingStates({});
    }, [selectedAccount]);

    // Merge props stats with local overrides
    const mergedStats = { ...stats, ...localStats };
    const rtAvailable = useMemo(() => hasMeaningfulLiveSnapshot(mergedStats), [mergedStats]);

    const handleWidgetClick = async (reportType) => {
        if (!reportType || loadingStates[reportType]) return;

        // Set Loading
        setLoadingStates(prev => ({ ...prev, [reportType]: true }));

        try {
            // Trigger Backend Fetch (Simple GET as requested)
            const res = await api.get(`/nav/report/${reportType}`, { params: scopedParams });

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
            api.get('/portfolio/nav/live', { params: scopedParams }),
            api.get('/portfolio/live-status'),
        ])
            .then((results) => {
                const liveNav = results[allTypes.length]?.data;
                const liveStatus = results[allTypes.length + 1]?.data;
                const start1d = mergedStats.start_1d ?? localStats.start_1d;
                const hasLiveNav = Boolean(liveNav && (liveNav.last_tws_update || liveNav.timestamp));
                const liveCurrentNav = hasLiveNav ? liveNav?.total_nav : null;

                setLocalStats((prev) => ({
                    ...prev,
                    current_nav_rt: liveCurrentNav ?? prev.current_nav_rt ?? null,
                    data_source: hasLiveNav && liveNav?.source === 'tws' ? 'tws_live' : prev.data_source,
                    last_updated:
                        (hasLiveNav && (
                            liveNav?.last_tws_update ||
                            liveNav?.timestamp
                        )) ||
                        prev.last_updated ||
                        liveStatus?.last_account_value_update ||
                        liveStatus?.last_position_update,
                    last_updated_rt:
                        (hasLiveNav && (
                            liveNav?.last_tws_update ||
                            liveNav?.timestamp
                        )) ||
                        prev.last_updated_rt,
                    rt_unrealized_pnl:
                        hasLiveNav
                            ? liveNav?.unrealized_pnl ?? prev.rt_unrealized_pnl ?? null
                            : prev.rt_unrealized_pnl ?? null,
                    rt_realized_pnl:
                        hasLiveNav
                            ? liveNav?.realized_pnl ?? prev.rt_realized_pnl ?? null
                            : prev.rt_realized_pnl ?? null,
                    live_connected: liveStatus?.connected ?? prev.live_connected,
                    tws_enabled: liveStatus?.tws_enabled ?? prev.tws_enabled,
                    connection_state: liveStatus?.connection_state ?? prev.connection_state,
                    diagnosis: liveStatus?.diagnosis ?? prev.diagnosis,
                    start_rt:
                        hasLiveNav && start1d !== null && start1d !== undefined
                            ? start1d
                            : prev.start_rt ?? null,
                    mtm_rt:
                        hasLiveNav && start1d !== null && start1d !== undefined && liveCurrentNav !== null
                            ? liveCurrentNav - start1d
                            : prev.mtm_rt ?? null,
                    change_rt:
                        hasLiveNav && start1d
                            ? ((liveCurrentNav - start1d) / start1d) * 100
                            : prev.change_rt ?? null,
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
    const freshnessText = formatRelativeTime(mergedStats.last_updated_rt || mergedStats.last_updated);
    const statusDetail = mergedStats.live_connected
        ? freshnessText
        : mergedStats.diagnosis || 'Live updates are currently unavailable.';
    const sourceLabel = 'Flex EOD';
    const rtSubtitle = rtAvailable
        ? `U ${formatCurrency(mergedStats.rt_unrealized_pnl)}`
        : mergedStats.live_connected
            ? 'Waiting for TWS NAV'
            : 'RT unavailable';
    const currentNavValue = mergedStats.current_nav;
    const rtTooltipMtm = rtAvailable ? mergedStats.mtm_rt : null;

    return (
        <div className="mb-4 w-full">
            <div className="grid grid-cols-2 md:grid-cols-5 lg:grid-cols-9 gap-2 items-center w-full">
                <div className="col-span-2 md:col-span-2 lg:col-span-2 w-full">
                    <button
                        onClick={handleLiveSync}
                        className={`
                            h-[62px] w-full rounded border border-gray-600 bg-gray-800 px-3 text-left transition-colors
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
                                <div className="text-[9px] uppercase tracking-wide text-gray-400">Current NAV</div>
                                <div className="font-mono text-base lg:text-lg font-bold text-white leading-tight">
                                    {formatCurrency(currentNavValue)}
                                </div>
                                <div
                                    className="text-[10px] text-gray-400"
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
                        label="RT"
                        value={rtAvailable ? mergedStats.change_rt : null}
                        isPercent
                        startValue={rtAvailable ? mergedStats.start_rt : null}
                        endDate={rtAvailable ? mergedStats.last_updated_rt : null}
                        mtmTot={rtTooltipMtm}
                        subtitle={rtSubtitle}
                        onClick={handleLiveSync}
                        loading={Object.values(loadingStates).some(x => x)}
                    />
                </div>

                <div className="w-full">
                    <StatCard
                        label="1 Day"
                        value={mergedStats.change_1d}
                        isPercent
                        startValue={mergedStats.start_1d}
                        endDate={mergedStats.date_1d}
                        mtmTot={mergedStats.mtm_1d}
                        subtitle={buildTimeframeSubtitle('1d', mergedStats.timeframe_meta)}
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
                        subtitle={buildTimeframeSubtitle('7d', mergedStats.timeframe_meta)}
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
                        subtitle={buildTimeframeSubtitle('30d', mergedStats.timeframe_meta)}
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
                        subtitle={buildTimeframeSubtitle('mtd', mergedStats.timeframe_meta)}
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
                        subtitle={buildTimeframeSubtitle('ytd', mergedStats.timeframe_meta)}
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
                        subtitle={buildTimeframeSubtitle('yoy', mergedStats.timeframe_meta)}
                        onClick={() => handleWidgetClick(REPORT_MAP["1 Year"])}
                        loading={loadingStates[REPORT_MAP["1 Year"]]}
                    />
                </div>
            </div>
        </div>
    );
};

export default NAVStats;
