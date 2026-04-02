import React, { useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import { ExternalLink } from 'lucide-react';
import "ag-grid-community/styles/ag-theme-alpine.css";

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

const OrdersGrid = ({ data, onTickerClick }) => {
    const colDefs = useMemo(() => [
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
            width: 250,
            pinned: 'left',
            sort: 'asc',
            sortIndex: 1,
            cellRenderer: (params) => {
                const row = params.data || {};
                const label = params.value || row.symbol || row.underlying_ticker;
                const ticker = row.underlying_ticker || row.symbol;
                if (!label) return null;

                const googleUrl = ticker ? `https://www.google.com/finance/quote/${ticker}:NASDAQ` : '#';
                const yahooUrl = ticker ? `https://finance.yahoo.com/quote/${ticker}/options` : '#';
                const detailLabel = ticker ? `Open stock analysis detail for ${ticker}` : 'Open stock analysis detail';

                return (
                    <div className="flex items-center gap-2">
                        <span
                            className="font-bold cursor-pointer hover:text-blue-400 group flex items-center"
                            onClick={() => ticker && params.context.onTickerClick && params.context.onTickerClick(ticker)}
                            title={detailLabel}
                            aria-label={detailLabel}
                        >
                            {label}
                            <ExternalLink
                                className="w-3 h-3 ml-1 text-slate-300 opacity-70 group-hover:opacity-100 group-hover:text-sky-300 transition-all"
                                aria-hidden="true"
                            />
                        </span>
                        <div className="flex gap-1 text-xs opacity-50 hover:opacity-100 transition-opacity">
                            <button
                                onClick={() => ticker && params.context.onTickerClick && params.context.onTickerClick(ticker)}
                                className="text-emerald-400 hover:text-emerald-300"
                                title="Detail"
                            >
                                D
                            </button>
                            <a href={googleUrl} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">G</a>
                            <a href={yahooUrl} target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300">Y</a>
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
        },
        {
            field: "action",
            headerName: "Action",
            width: 90,
            sortable: true,
            cellClass: (params) => params.value === 'BUY' ? 'text-green-400 font-bold' : 'text-red-400 font-bold',
        },
        { field: "status", headerName: "Status", width: 120, sortable: true },
        {
            field: "remaining_quantity",
            headerName: "Remaining",
            width: 105,
            sortable: true,
            valueFormatter: p => formatNumber(p.value, 2),
        },
        {
            field: "total_quantity",
            headerName: "Total Qty",
            width: 95,
            sortable: true,
            valueFormatter: p => formatNumber(p.value, 2),
        },
        {
            field: "filled_quantity",
            headerName: "Filled",
            width: 90,
            sortable: true,
            valueFormatter: p => formatNumber(p.value, 2),
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
            valueFormatter: p => formatCurrency(p.value, 2),
        },
        {
            field: "last_price",
            headerName: "Last",
            width: 95,
            sortable: true,
            valueFormatter: p => formatCurrency(p.value, 2),
        },
        {
            field: "day_change_pct",
            headerName: "1D %",
            width: 85,
            sortable: true,
            valueFormatter: p => formatPercent(p.value, 2),
            cellClass: (params) => (getNumericValue(params.value) || 0) >= 0 ? 'text-green-400' : 'text-red-400',
        },
        {
            field: "call_put_skew",
            headerName: "Skew",
            width: 85,
            sortable: true,
            valueFormatter: p => formatNumber(p.value, 2),
        },
        {
            field: "tsmom_60",
            headerName: "TSMOM 60",
            width: 100,
            sortable: true,
            valueFormatter: p => formatNumber(p.value, 2),
        },
        {
            field: "ma_200",
            headerName: "200 MA",
            width: 90,
            sortable: true,
            valueFormatter: p => formatCurrency(p.value, 2),
        },
        {
            field: "ema_20",
            headerName: "EMA 20",
            width: 90,
            sortable: true,
            valueFormatter: p => formatCurrency(p.value, 2),
        },
        {
            field: "hma_20",
            headerName: "HMA 20",
            width: 90,
            sortable: true,
            valueFormatter: p => formatCurrency(p.value, 2),
        },
        {
            field: "source",
            headerName: "Source",
            width: 110,
            sortable: true,
            cellRenderer: (params) => <SourceBadge source={params.value} />,
        },
        {
            field: "last_update",
            headerName: "Last Update",
            width: 190,
            sortable: true,
        },
    ], []);

    const defaultColDef = {
        minWidth: 70,
        resizable: true,
        sortable: true,
        filter: true,
    };

    return (
        <div className="ag-theme-alpine-dark h-full w-full">
            <AgGridReact
                rowData={data}
                columnDefs={colDefs}
                defaultColDef={defaultColDef}
                animateRows={true}
                context={{ onTickerClick }}
            />
        </div>
    );
};

export default OrdersGrid;
