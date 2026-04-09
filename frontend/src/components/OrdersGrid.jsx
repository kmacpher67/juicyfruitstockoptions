import React, { useMemo, useState, useCallback } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import { ExternalLink, ChevronRight, ChevronDown } from 'lucide-react';
import "ag-grid-community/styles/ag-theme-alpine.css";
import { applyBagVisibility, buildLegRows, netDebitCreditLabel } from './ordersViewUtils.js';
import { resolveQuickLinkTooltip, withHeaderTooltips } from './uiHelpTooltips';

ModuleRegistry.registerModules([AllCommunityModule]);

const getNumericValue = (value) => {
    if (value === null || value === undefined || value === '') return null;
    const numeric = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(numeric) ? numeric : null;
};

const formatNumber = (value, digits = 2) => {
    const numeric = getNumericValue(value);
    if (numeric === null) return '-';
    return numeric.toFixed(digits);
};

const formatCurrency = (value, digits = 2) => {
    const numeric = getNumericValue(value);
    if (numeric === null) return '-';
    return `$${numeric.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits })}`;
};

const formatPercent = (value, digits = 2) => {
    const numeric = getNumericValue(value);
    if (numeric === null) return '-';
    return `${numeric.toFixed(digits)}%`;
};

const SourceBadge = ({ source }) => {
    const isTws = source === 'tws_open_order';
    return (
        <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
            isTws
                ? 'border-green-500/40 bg-green-500/10 text-green-200'
                : 'border-gray-600 bg-gray-900 text-gray-300'
        }`}>
            {isTws ? 'TWS Open' : 'Flex Hist'}
        </span>
    );
};

/**
 * Toolbar checkbox for BAG visibility toggles.
 */
const BagToggle = ({ id, label, checked, onChange }) => (
    <label
        htmlFor={id}
        className="flex items-center gap-1.5 text-xs text-gray-300 cursor-pointer select-none"
    >
        <input
            id={id}
            type="checkbox"
            checked={checked}
            onChange={e => onChange(e.target.checked)}
            title={label}
            aria-label={label}
            className="accent-blue-500 cursor-pointer"
            data-testid={id}
        />
        {label}
    </label>
);

/**
 * OrdersGrid — flat + BAG-expand open-orders table.
 *
 * Props:
 *   data          {Object[]}  Normalized order rows from /api/orders/open
 *   onTickerClick {Function}  Called with underlying ticker symbol on click
 */
const OrdersGrid = ({ data, onTickerClick }) => {
    const [expandedBagKeys, setExpandedBagKeys] = useState(new Set());
    const [showBagParents, setShowBagParents] = useState(true);
    const [showLegsOnly, setShowLegsOnly] = useState(false);

    const toggleExpand = useCallback((orderKey) => {
        setExpandedBagKeys(prev => {
            const next = new Set(prev);
            if (next.has(orderKey)) {
                next.delete(orderKey);
            } else {
                next.add(orderKey);
            }
            return next;
        });
    }, []);

    /**
     * Build the display rows:
     * 1. Apply BAG parent visibility filter.
     * 2. For each visible BAG parent that is expanded (and not in legs-only
     *    mode), inject its leg rows immediately after the parent row.
     */
    const displayRows = useMemo(() => {
        const filtered = applyBagVisibility(data || [], showBagParents, showLegsOnly);
        if (showLegsOnly) {
            // Legs are already flat; no expansion needed.
            return filtered;
        }

        const result = [];
        for (const row of filtered) {
            result.push(row);
            const isBag = row.security_type === 'BAG' || row.is_bag === true;
            if (isBag && expandedBagKeys.has(row.order_key)) {
                const legRows = buildLegRows(row);
                result.push(...legRows);
            }
        }
        return result;
    }, [data, showBagParents, showLegsOnly, expandedBagKeys]);

    const bagCount = useMemo(
        () => (data || []).filter(r => r.security_type === 'BAG' || r.is_bag).length,
        [data]
    );

    const colDefs = useMemo(() => withHeaderTooltips([
        {
            field: "account_id",
            headerName: "Account",
            sortable: true,
            width: 110,
            sort: 'asc',
            sortIndex: 0,
        },
        {
            field: "display_symbol",
            headerName: "Order Ticker",
            sortable: true,
            width: 260,
            pinned: 'left',
            sort: 'asc',
            sortIndex: 1,
            cellRenderer: (params) => {
                const row = params.data || {};
                const isLegRow = row._rowType === 'bag_leg';
                const isBag = row.security_type === 'BAG' || row.is_bag === true;
                const orderKey = row.order_key;
                const isExpanded = expandedBagKeys.has(orderKey);
                const label = params.value || row.symbol || row.underlying_ticker;
                const ticker = row.underlying_ticker || row.symbol;

                if (isLegRow) {
                    return (
                        <div className="flex items-center gap-1 pl-6 border-l-2 border-blue-600/40">
                            <span className="text-blue-300 text-[10px] font-semibold uppercase mr-1">
                                {row.action_label || row.action}
                            </span>
                            <span className="text-gray-300 text-xs">
                                {row.display_symbol || '-'}
                            </span>
                            {row.conid && <span className="text-gray-500 text-[10px]">conid:{row.conid}</span>}
                            {row.ratio && row.ratio !== 1 && (
                                <span className="text-gray-500 text-[10px] ml-1">x{row.ratio}</span>
                            )}
                        </div>
                    );
                }

                if (!label) return null;

                const googleUrl = ticker ? `https://www.google.com/finance/quote/${ticker}:NASDAQ` : '#';
                const yahooUrl = ticker ? `https://finance.yahoo.com/quote/${ticker}/options` : '#';
                const detailLabel = ticker ? `Open stock analysis detail for ${ticker}` : 'Open stock analysis detail';

                return (
                    <div className="flex items-center gap-2">
                        {isBag && (
                            <button
                                aria-label={isExpanded ? 'Collapse legs' : 'Expand legs'}
                                data-testid={`bag-expand-${orderKey}`}
                                onClick={() => toggleExpand(orderKey)}
                                className="text-gray-400 hover:text-[#1976d2] transition-colors flex-shrink-0"
                                title={isExpanded ? 'Collapse combo leg rows' : 'Expand combo leg rows'}
                            >
                                {isExpanded
                                    ? <ChevronDown className="w-3.5 h-3.5" />
                                    : <ChevronRight className="w-3.5 h-3.5" />
                                }
                            </button>
                        )}
                        <span
                            className="font-bold cursor-pointer hover:text-[#1976d2] group flex items-center"
                            onClick={() => ticker && params.context.onTickerClick && params.context.onTickerClick(ticker)}
                            title={detailLabel}
                            aria-label={detailLabel}
                        >
                            {label}
                            {isBag && (
                                <span className="ml-1 text-[10px] text-[#1976d2] font-normal">[COMBO]</span>
                            )}
                            <ExternalLink
                                className="w-3 h-3 ml-1 text-slate-300 opacity-90 group-hover:opacity-100 group-hover:text-[#1976d2] transition-all"
                                aria-hidden="true"
                            />
                        </span>
                        <div className="flex gap-1 text-xs opacity-100">
                            <button
                                onClick={() => ticker && params.context.onTickerClick && params.context.onTickerClick(ticker)}
                                className="text-[#1976d2] hover:text-[#1565c0] font-semibold"
                                title={resolveQuickLinkTooltip('detail', ticker)}
                                aria-label={resolveQuickLinkTooltip('detail', ticker)}
                            >
                                D
                            </button>
                            <a href={googleUrl} target="_blank" rel="noopener noreferrer" className="text-[#1976d2] hover:text-[#1565c0] font-semibold" title={resolveQuickLinkTooltip('google', ticker)} aria-label={resolveQuickLinkTooltip('google', ticker)}>G</a>
                            <a href={yahooUrl} target="_blank" rel="noopener noreferrer" className="text-[#1976d2] hover:text-[#1565c0] font-semibold" title={resolveQuickLinkTooltip('yahoo', ticker)} aria-label={resolveQuickLinkTooltip('yahoo', ticker)}>Y</a>
                        </div>
                    </div>
                );
            },
        },
        {
            field: "security_type",
            headerName: "Type",
            width: 80,
            sortable: true,
            cellRenderer: (params) => {
                const row = params.data || {};
                if (row._rowType === 'bag_leg') return null;
                return params.value || '-';
            },
        },
        {
            field: "order_sub_type",
            headerName: "Sub Type",
            width: 95,
            sortable: true,
            cellRenderer: (params) => {
                const row = params.data || {};
                if (row._rowType === 'bag_leg') return params.value || '-';
                return params.value || '-';
            },
        },
        {
            field: "action",
            headerName: "Action",
            width: 90,
            sortable: true,
            cellRenderer: (params) => {
                const row = params.data || {};
                if (row._rowType === 'bag_leg') {
                    return (
                        <span className={
                            row.action === 'BUY'
                                ? 'text-[#2e7d32] font-bold text-xs'
                                : 'text-[#d32f2f] font-bold text-xs'
                        }>
                            {row.action_label || row.action}
                        </span>
                    );
                }
                return (
                    <span className={params.value === 'BUY' ? 'text-[#2e7d32] font-bold' : 'text-[#d32f2f] font-bold'}>
                        {params.value}
                    </span>
                );
            },
        },
        { field: "status", headerName: "Status", width: 120, sortable: true },
        {
            field: "remaining_quantity",
            headerName: "Remaining",
            width: 105,
            sortable: true,
            valueFormatter: p => {
                const row = p.data || {};
                if (row._rowType === 'bag_leg') {
                    return row.ratio != null ? `x${row.ratio}` : '-';
                }
                return formatNumber(p.value, 2);
            },
        },
        {
            field: "total_quantity",
            headerName: "Total Qty",
            width: 95,
            sortable: true,
            valueFormatter: p => {
                if ((p.data || {})._rowType === 'bag_leg') return '-';
                return formatNumber(p.value, 2);
            },
        },
        {
            field: "filled_quantity",
            headerName: "Filled",
            width: 90,
            sortable: true,
            valueFormatter: p => {
                if ((p.data || {})._rowType === 'bag_leg') return '-';
                return formatNumber(p.value, 2);
            },
        },
        {
            field: "order_type",
            headerName: "Order Type",
            width: 110,
            sortable: true,
        },
        { field: "tif", headerName: "TIF", width: 75, sortable: true },
        {
            field: "limit_price",
            headerName: "Limit",
            width: 95,
            sortable: true,
            cellRenderer: (params) => {
                const row = params.data || {};
                if (row._rowType !== 'bag_leg' && (row.security_type === 'BAG' || row.is_bag)) {
                    const label = netDebitCreditLabel(params.value);
                    return label ? (
                        <span className={params.value <= 0 ? 'text-red-300 text-xs' : 'text-green-300 text-xs'}>
                            {label}
                        </span>
                    ) : formatCurrency(params.value);
                }
                return formatCurrency(params.value);
            },
        },
        {
            field: "last_price",
            headerName: "Last",
            width: 95,
            sortable: true,
            valueFormatter: p => {
                if ((p.data || {})._rowType === 'bag_leg') return '-';
                return formatCurrency(p.value, 2);
            },
        },
        {
            field: "day_change_pct",
            headerName: "1D %",
            width: 85,
            sortable: true,
            valueFormatter: p => {
                if ((p.data || {})._rowType === 'bag_leg') return '-';
                return formatPercent(p.value, 2);
            },
            cellClass: (params) => {
                if ((params.data || {})._rowType === 'bag_leg') return '';
                return (getNumericValue(params.value) || 0) >= 0 ? 'text-[#2e7d32]' : 'text-[#d32f2f]';
            },
        },
        {
            field: "call_put_skew",
            headerName: "Skew",
            width: 85,
            sortable: true,
            valueFormatter: p => {
                if ((p.data || {})._rowType === 'bag_leg') return '-';
                return formatNumber(p.value, 2);
            },
        },
        {
            field: "tsmom_60",
            headerName: "TSMOM 60",
            width: 100,
            sortable: true,
            valueFormatter: p => {
                if ((p.data || {})._rowType === 'bag_leg') return '-';
                return formatNumber(p.value, 2);
            },
        },
        {
            field: "ma_200",
            headerName: "200 MA",
            width: 90,
            sortable: true,
            valueFormatter: p => {
                if ((p.data || {})._rowType === 'bag_leg') return '-';
                return formatCurrency(p.value, 2);
            },
        },
        {
            field: "ema_20",
            headerName: "EMA 20",
            width: 90,
            sortable: true,
            valueFormatter: p => {
                if ((p.data || {})._rowType === 'bag_leg') return '-';
                return formatCurrency(p.value, 2);
            },
        },
        {
            field: "hma_20",
            headerName: "HMA 20",
            width: 90,
            sortable: true,
            valueFormatter: p => {
                if ((p.data || {})._rowType === 'bag_leg') return '-';
                return formatCurrency(p.value, 2);
            },
        },
        {
            field: "source",
            headerName: "Source",
            width: 110,
            sortable: true,
            cellRenderer: (params) => {
                const row = params.data || {};
                if (row._rowType === 'bag_leg') return null;
                return <SourceBadge source={params.value} />;
            },
        },
        {
            field: "last_update",
            headerName: "Last Update",
            width: 190,
            sortable: true,
            valueFormatter: p => {
                if ((p.data || {})._rowType === 'bag_leg') return '-';
                return p.value || '-';
            },
        },
    ]), [expandedBagKeys, toggleExpand]);

    const defaultColDef = {
        minWidth: 70,
        resizable: true,
        sortable: true,
        filter: true,
    };

    const getRowClass = useCallback((params) => {
        const row = params.data || {};
        if (row._rowType === 'bag_leg') {
            return 'bg-gray-900/60 text-gray-400 border-l-2 border-blue-600/30';
        }
        if (row.security_type === 'BAG' || row.is_bag) {
            return 'bg-blue-950/20';
        }
        return '';
    }, []);

    return (
        <div className="flex flex-col h-full">
            {/* BAG visibility toolbar strip */}
            {bagCount > 0 && (
                <div
                    className="flex items-center gap-4 px-3 py-1.5 bg-gray-850 border-b border-gray-700 text-xs"
                    data-testid="bag-toolbar"
                >
                    <span className="text-gray-500 uppercase tracking-wide text-[10px]">
                        BAG / Combo
                    </span>
                    <BagToggle
                        id="toggle-show-bag-parents"
                        label="Show BAG parents"
                        checked={showBagParents}
                        onChange={(val) => {
                            setShowBagParents(val);
                            if (!val) setShowLegsOnly(false);
                        }}
                    />
                    <BagToggle
                        id="toggle-show-legs-only"
                        label="Show decomposed legs only"
                        checked={showLegsOnly}
                        onChange={(val) => {
                            setShowLegsOnly(val);
                            if (val) setShowBagParents(false);
                        }}
                    />
                    <span className="text-gray-600 text-[10px]">
                        {bagCount} combo order{bagCount !== 1 ? 's' : ''}
                    </span>
                </div>
            )}
            <div className="ag-theme-alpine-dark flex-1 w-full">
                <AgGridReact
                    rowData={displayRows}
                    columnDefs={colDefs}
                    defaultColDef={defaultColDef}
                    animateRows={true}
                    context={{ onTickerClick }}
                    getRowClass={getRowClass}
                />
            </div>
        </div>
    );
};

export default OrdersGrid;
