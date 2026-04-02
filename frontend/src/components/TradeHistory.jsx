import React, { useState, useEffect, useMemo } from 'react';
import api from '../api/axios';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import { TrendingUp, TrendingDown, DollarSign, Activity, Calendar, Radio } from 'lucide-react';
import { ExternalLink } from 'lucide-react';
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

ModuleRegistry.registerModules([AllCommunityModule]);

// Component for a Single Metric Card
const MetricCard = ({ title, value, icon: Icon, trend, colorClass = "text-white" }) => (
    <div className="bg-gray-800 p-4 rounded-lg shadow border border-gray-700 flex items-center justify-between">
        <div>
            <p className="text-gray-400 text-sm mb-1">{title}</p>
            <div className={`text-2xl font-bold ${colorClass}`}>{value}</div>
        </div>
        <div className={`p-3 rounded-full bg-gray-700 ${colorClass}`}>
            <Icon className="w-6 h-6" />
        </div>
    </div>
);

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

const formatStatusTimestamp = (value) => {
    if (!value) return 'timestamp unavailable';

    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;

    return `${parsed.toLocaleString()} (${formatRelativeTime(value)})`;
};

const getLiveStatusTone = (state) => {
    switch (state) {
        case 'connected':
            return {
                dotClass: 'bg-green-400',
                pillClass: 'border-green-500/40 bg-green-500/10 text-green-200',
                label: 'TWS live',
            };
        case 'handshake_failed':
            return {
                dotClass: 'bg-amber-400',
                pillClass: 'border-amber-500/40 bg-amber-500/10 text-amber-200',
                label: 'Handshake failed',
            };
        case 'socket_unreachable':
            return {
                dotClass: 'bg-red-400',
                pillClass: 'border-red-500/40 bg-red-500/10 text-red-200',
                label: 'Socket unreachable',
            };
        case 'disconnected':
            return {
                dotClass: 'bg-yellow-400',
                pillClass: 'border-yellow-500/40 bg-yellow-500/10 text-yellow-200',
                label: 'Disconnected',
            };
        case 'disabled':
            return {
                dotClass: 'bg-gray-500',
                pillClass: 'border-gray-600 bg-gray-900 text-gray-300',
                label: 'Live disabled',
            };
        case 'unavailable':
            return {
                dotClass: 'bg-gray-500',
                pillClass: 'border-gray-600 bg-gray-900 text-gray-300',
                label: 'ibapi missing',
            };
        default:
            return {
                dotClass: 'bg-gray-500',
                pillClass: 'border-gray-600 bg-gray-900 text-gray-300',
                label: 'Status unknown',
            };
    }
};

const SourceBadge = ({ source }) => {
    const normalized = source === 'tws_live' ? 'tws_live' : 'flex_history';
    const isLive = normalized === 'tws_live';

    return (
        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
            isLive
                ? 'border-green-500/40 bg-green-500/10 text-green-200'
                : 'border-gray-600 bg-gray-900 text-gray-300'
        }`}>
            {isLive ? 'TWS Live' : 'Flex'}
        </span>
    );
};

const TradeHistory = ({ onTickerClick }) => {
    const [rowData, setRowData] = useState([]);
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState('YTD');
    const [liveStatus, setLiveStatus] = useState(null);

    const calculateDateRange = (range) => {
        const now = new Date();
        let startDate = null;

        if (range === 'ALL') return { start: null, end: null };
        if (range === 'RT') {
            const today = now.toISOString().split('T')[0];
            return { start: today, end: today };
        }

        if (range === 'MTD') {
            startDate = new Date(now.getFullYear(), now.getMonth(), 1);
        } else if (range === 'YTD') {
            startDate = new Date(now.getFullYear(), 0, 1);
        } else if (range === '1D') {
            startDate = new Date();
            startDate.setDate(now.getDate() - 1);
        } else if (range === '1W') {
            startDate = new Date();
            startDate.setDate(now.getDate() - 7);
        } else if (range === '1M') {
            startDate = new Date();
            startDate.setMonth(now.getMonth() - 1);
        } else if (range === '3M') {
            startDate = new Date();
            startDate.setMonth(now.getMonth() - 3);
        } else if (range === '6M') {
            startDate = new Date();
            startDate.setMonth(now.getMonth() - 6);
        } else if (range === '1Y') {
            startDate = new Date();
            startDate.setFullYear(now.getFullYear() - 1);
        } else if (range === '5Y') {
            startDate = new Date();
            startDate.setFullYear(now.getFullYear() - 5);
        }

        // Format YYYY-MM-DD
        const startStr = startDate.toISOString().split('T')[0];
        const endStr = now.toISOString().split('T')[0];
        return { start: startStr, end: endStr };
    };


    const [colDefs] = useState([
        {
            field: "date_time",
            headerName: "Date/Time",
            sortable: true,
            filter: true,
            valueGetter: p => p.data.date_time || p.data.DateTime
        },
        {
            field: "symbol",
            headerName: "Ticker",
            filter: true,
            sortable: true,
            sort: "asc",
            sortIndex: 1,
            width: 330,
            valueGetter: p => p.data.symbol || p.data.Symbol,
            cellRenderer: (params) => {
                const row = params.data || {};
                const symbol = params.value;
                if (!symbol) return null;
                const cleanSym = row.underlying_symbol || String(symbol).split(" ")[0];
                const googleUrl = `https://www.google.com/finance/quote/${cleanSym}:NASDAQ`;
                const yahooUrl = `https://finance.yahoo.com/quote/${cleanSym}/options`;
                const detailLabel = `Open stock analysis detail for ${cleanSym}`;

                return (
                    <div className="flex items-center gap-2">
                        <span
                            className="font-bold cursor-pointer hover:text-blue-400 group flex items-center"
                            onClick={() => onTickerClick && onTickerClick(cleanSym)}
                            title={detailLabel}
                            aria-label={detailLabel}
                        >
                            {symbol}
                            <ExternalLink
                                className="w-3 h-3 ml-1 text-slate-300 opacity-70 group-hover:opacity-100 group-hover:text-sky-300 transition-all"
                                aria-hidden="true"
                            />
                        </span>
                        <div className="flex gap-1 text-xs opacity-50 hover:opacity-100 transition-opacity">
                            <a href={googleUrl} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">G</a>
                            <a href={yahooUrl} target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300">Y</a>
                        </div>
                    </div>
                );
            },
        },
        {
            field: "account",
            headerName: "Account",
            filter: true,
            sortable: true,
            sort: "asc",
            sortIndex: 0,
            width: 120,
            valueGetter: p => p.data.account_id || p.data.AccountId || p.data.account || "Unknown"
        },
        {
            headerName: "Action",
            width: 100,
            valueGetter: p => {
                if (p.data.buy_sell === "DIVIDEND") return "DIVIDEND";
                const side = (p.data.buy_sell || '').toUpperCase();
                if (side === 'BUY' || side === 'BOT') return 'BUY';
                if (side === 'SELL' || side === 'SLD') return 'SELL';
                const qty = p.data.quantity !== undefined ? p.data.quantity : p.data.Quantity;
                if (!qty) return "-";
                return qty > 0 ? "BUY" : "SELL";
            },
            cellClassRules: {
                'text-green-400 font-bold': p => p.value === 'BUY' || p.value === 'DIVIDEND',
                'text-red-400 font-bold': p => p.value === 'SELL'
            }
        },
        {
            field: "quantity",
            headerName: "Quantity",
            type: "numericColumn",
            width: 90,
            valueGetter: p => Math.abs(p.data.quantity !== undefined ? p.data.quantity : p.data.Quantity),
        },
        {
            field: "trade_price",
            headerName: "Price",
            valueGetter: p => {
                if (p.data.price !== undefined && p.data.price !== null) return p.data.price;
                if (p.data.trade_price !== undefined) return p.data.trade_price;
                return p.data.TradePrice;
            },
            valueFormatter: p => p.value ? `$${parseFloat(p.value).toFixed(2)}` : ''
        },
        {
            field: "ib_commission",
            headerName: "Comm",
            valueGetter: p => {
                if (p.data.commission !== undefined && p.data.commission !== null) return p.data.commission;
                if (p.data.ib_commission !== undefined) return p.data.ib_commission;
                return p.data.IBCommission;
            },
            valueFormatter: p => p.value ? `$${Math.abs(parseFloat(p.value)).toFixed(2)}` : ''
        },
        {
            field: "realized_pl",
            headerName: "Realized P&L",
            type: "numericColumn",
            valueFormatter: p => p.value !== undefined && p.value !== null ? `$${parseFloat(p.value).toFixed(2)}` : '-',
            cellClassRules: {
                'text-green-400': p => p.value > 0,
                'text-red-400': p => p.value < 0,
                'text-gray-500': p => p.value === 0
            }
        },
        {
            field: "asset_class",
            headerName: "Type",
            width: 80,
            valueGetter: p => {
                let ac = p.data.asset_class || p.data.AssetClass;
                const sym = p.data.symbol || p.data.Symbol || "";

                if (!ac) {
                    if (sym.includes("  ") || (sym.length > 5 && /\d/.test(sym) && (sym.endsWith("C") || sym.endsWith("P")))) ac = "OPT";
                    else ac = "STK";
                }

                if (ac === "OPT" || ac === "FOP") return "Option";
                if (ac === "STK") return "Stock";
                return ac;
            }
        },
        {
            field: "source",
            headerName: "Source",
            width: 115,
            sortable: true,
            valueGetter: p => p.data.source || 'flex_history',
            cellRenderer: p => <SourceBadge source={p.value} />
        }
    ]);

    useEffect(() => {
        loadData();
    }, [timeRange]);

    const loadData = async () => {
        setLoading(true);
        try {
            if (timeRange === 'RT') {
                const [liveTradesRes, liveStatusRes] = await Promise.all([
                    api.get('/trades/live'),
                    api.get('/trades/live-status'),
                ]);
                setRowData(liveTradesRes.data || []);
                setMetrics(null);
                setLiveStatus(liveStatusRes.data);
            } else {
                const { start, end } = calculateDateRange(timeRange);
                const params = {};
                if (start) params.start_date = start;
                if (end) params.end_date = end;

                const [analysisRes, liveStatusRes] = await Promise.all([
                    api.get('/trades/analysis', { params }),
                    api.get('/trades/live-status'),
                ]);

                setRowData(analysisRes.data.trades || []);
                setMetrics(analysisRes.data.metrics);
                setLiveStatus(liveStatusRes.data);
            }
        } catch (error) {
            console.error("Failed to load trade history:", error);
            setLiveStatus(null);
            setRowData([]);
            setMetrics(null);
        } finally {
            setLoading(false);
        }
    };

    const defaultColDef = useMemo(() => ({
        flex: 1,
        minWidth: 100,
        filter: true,
        sortable: true
    }), []);

    const isRtMode = timeRange === 'RT';
    const liveTone = getLiveStatusTone(liveStatus?.connection_state);
    const liveFreshness = formatRelativeTime(liveStatus?.latest_live_trade_at || liveStatus?.last_execution_update);
    const rtUnavailable = isRtMode && liveStatus && liveStatus.connection_state !== 'connected';
    const displayMetrics = isRtMode ? null : metrics;
    const rtSummary = !liveStatus
        ? 'Loading live status...'
        : liveStatus.connection_state === 'connected'
            ? liveStatus.today_live_trade_count > 0
                ? `${liveStatus.today_live_trade_count} live trade${liveStatus.today_live_trade_count === 1 ? '' : 's'} today`
                : 'Connected. No live executions yet today'
            : liveStatus.diagnosis || 'Live trades unavailable';
    const failureTimestamp = formatStatusTimestamp(liveStatus?.last_failure_at);
    const statusSummary = isRtMode ? rtSummary : 'Historical mode uses stored trade history';

    return (
        <div className="flex flex-col gap-6">
            {/* Controls */}
            <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
                <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2 rounded-lg border border-gray-700 bg-gray-800/90 px-3 py-2">
                    <span className={`inline-flex h-8 items-center gap-2 rounded-full border px-3 text-[11px] font-semibold uppercase tracking-wide ${liveTone.pillClass}`}>
                        <span className={`h-2.5 w-2.5 rounded-full ${liveTone.dotClass}`}></span>
                        {liveTone.label}
                    </span>
                    <span className="text-sm text-gray-200">
                        {statusSummary}
                    </span>
                    {liveStatus && (
                        <>
                            <span className="hidden text-gray-600 md:inline">|</span>
                            <span className="text-xs text-gray-400">
                                Last execution: {liveStatus.last_execution_update ? liveFreshness : 'update pending'}
                            </span>
                            <span className="text-xs text-gray-400">
                                Live rows today: {liveStatus.today_live_trade_count ?? 0}
                            </span>
                        </>
                    )}
                </div>
                <div className="flex items-center gap-2 bg-gray-800 p-1 rounded border border-gray-700 flex-wrap justify-end">
                    <Calendar className="w-4 h-4 text-gray-400 ml-2" />
                    {['ALL', 'MTD', 'RT', '1D', '1W', '1M', '3M', '6M', 'YTD', '1Y', '5Y'].map(range => (
                        <button
                            key={range}
                            onClick={() => setTimeRange(range)}
                            title={range === 'RT' ? 'Current-day TWS live executions only' : undefined}
                            className={`px-3 py-1 text-sm rounded transition-colors inline-flex items-center gap-1.5 ${timeRange === range ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white hover:bg-gray-700'}`}
                        >
                            {range === 'RT' && <Radio className="w-3.5 h-3.5" />}
                            {range}
                        </button>
                    ))}
                </div>
            </div>

            {rtUnavailable && (
                <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                    RT trades are unavailable. {liveStatus?.diagnosis}
                    <div className="mt-2 text-xs text-amber-200/90">
                        Latest backend failure: {liveStatus?.last_failure_reason || liveStatus?.diagnosis || 'Unknown failure'}.
                    </div>
                    <div className="mt-1 text-xs text-amber-200/75">
                        Failure time: {failureTimestamp}
                    </div>
                </div>
            )}

            {/* Metrics Section */}
            {displayMetrics && (
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                    <MetricCard
                        title="Realized P&L"
                        value={
                            <div className="text-xs font-normal leading-tight opacity-90 break-words max-w-[150px] md:max-w-full">
                                <div>All: ${(displayMetrics.total_pl || 0).toFixed(2)}</div>
                                {displayMetrics.account_metrics && Object.entries(displayMetrics.account_metrics).map(([acc, stats]) => (
                                    <div key={acc}>{acc}: ${(stats.total_pl || 0).toFixed(2)}</div>
                                ))}
                            </div>
                        }
                        icon={DollarSign}
                        colorClass={displayMetrics.total_pl >= 0 ? "text-green-400" : "text-red-400"}
                    />
                    <MetricCard
                        title="Unrealized P&L"
                        value={
                            <div className="text-xs font-normal leading-tight opacity-90 break-words max-w-[150px] md:max-w-full">
                                <div>All: ${((displayMetrics.unrealized_profit || 0) - (displayMetrics.unrealized_loss || 0)).toFixed(2)}</div>
                                {displayMetrics.account_metrics && Object.entries(displayMetrics.account_metrics).map(([acc, stats]) => {
                                    const netUPL = (stats.unrealized_profit || 0) - (stats.unrealized_loss || 0);
                                    return <div key={acc}>{acc}: ${netUPL.toFixed(2)}</div>;
                                })}
                            </div>
                        }
                        icon={Activity}
                        colorClass={(displayMetrics.unrealized_profit - displayMetrics.unrealized_loss) >= 0 ? "text-green-400" : "text-red-400"}
                    />
                    <MetricCard
                        title="Win Rate"
                        value={
                            <div className="text-xs font-normal leading-tight opacity-90 break-words max-w-[150px] md:max-w-full">
                                <div>All: {(displayMetrics.win_rate || 0).toFixed(0)}%</div>
                                {displayMetrics.account_metrics && Object.entries(displayMetrics.account_metrics).map(([acc, stats]) => (
                                    <div key={acc}>{acc}: {(stats.win_rate || 0).toFixed(0)}%</div>
                                ))}
                            </div>
                        }
                        icon={Activity}
                        colorClass="text-blue-400"
                    />
                    <MetricCard
                        title="Profit Factor"
                        value={
                            <div className="text-xs font-normal leading-tight opacity-90 break-words max-w-[150px] md:max-w-full">
                                <div>All: {Number(displayMetrics.profit_factor || 0).toFixed(2)}</div>
                                {displayMetrics.account_metrics && Object.entries(displayMetrics.account_metrics).map(([acc, stats]) => (
                                    <div key={acc}>{acc}: {Number(stats.profit_factor || 0).toFixed(2)}</div>
                                ))}
                            </div>
                        }
                        icon={TrendingUp}
                        colorClass="text-yellow-400"
                    />
                    <MetricCard
                        title="Trade Count"
                        value={
                            <div className="text-xs font-normal leading-tight opacity-90 break-words max-w-[150px] md:max-w-full">
                                <div>All T:{displayMetrics.total_trades} O:{displayMetrics.open_trades} C:{displayMetrics.closed_trades}</div>
                                {displayMetrics.account_metrics && Object.entries(displayMetrics.account_metrics).map(([acc, stats]) => (
                                    <div key={acc}>{acc} T:{stats.total || 0} O:{stats.open || 0} C:{stats.closed || 0}</div>
                                ))}
                            </div>
                        }
                        icon={TrendingDown}
                        colorClass="text-purple-400"
                    />
                </div>
            )}

            {isRtMode && (
                <div className="text-sm text-gray-400">
                    RT mode shows current-day `tws_live` execution rows only. Historical P&amp;L widgets stay on the non-RT ranges so we don’t mix live intraday data with Flex-based aggregates.
                </div>
            )}

            {/* Grid Section */}
            <div className="bg-gray-800 rounded-lg p-1 shadow-lg overflow-hidden border border-gray-700 h-[650px] w-full ag-theme-quartz-dark">
                <AgGridReact
                    rowData={rowData}
                    columnDefs={colDefs}
                    defaultColDef={defaultColDef}
                    pagination={true}
                    paginationPageSize={100}
                />
            </div>
        </div>
    );
};

export default TradeHistory;
