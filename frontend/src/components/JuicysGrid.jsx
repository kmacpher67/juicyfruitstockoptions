import React, { useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';
import { withHeaderTooltips } from './uiHelpTooltips';

ModuleRegistry.registerModules([AllCommunityModule]);

const formatNumber = (value, digits = 2) => {
    if (value === null || value === undefined || value === '') return '-';
    const n = Number(value);
    if (!Number.isFinite(n)) return '-';
    return n.toFixed(digits);
};

const formatDateTime = (value) => {
    if (!value) return '-';
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return String(value);
    return dt.toLocaleString();
};

const TickerCell = (params) => {
    const ticker = params.data?.symbol;
    const onTickerClick = params.context?.onTickerClick;
    if (!ticker) return '-';
    return (
        <button
            type="button"
            className="text-[#1976d2] hover:text-[#1565c0] hover:underline font-semibold"
            onClick={() => onTickerClick && onTickerClick(ticker)}
            title={`Open ${ticker} details`}
        >
            {ticker}
        </button>
    );
};

const JuicysGrid = ({ rows, onTickerClick }) => {
    const colDefs = useMemo(() => withHeaderTooltips([
        { field: 'symbol', headerName: 'Ticker', pinned: 'left', width: 110, sortable: true, filter: true, cellRenderer: TickerCell },
        { field: 'as_of', headerName: 'As Of', width: 180, sortable: true, filter: true, valueFormatter: (p) => formatDateTime(p.value) },
        { field: 'strategy', headerName: 'Strategy', width: 180, sortable: true, filter: true },
        { field: 'wheel_phase', headerName: 'Wheel', width: 145, sortable: true, filter: true, valueFormatter: (p) => (p.value ? p.value.replaceAll('_', ' ') : '-') },
        { field: 'type', headerName: 'Type', width: 90, sortable: true, filter: true },
        { field: 'action', headerName: 'Action', width: 100, sortable: true, filter: true },
        { field: 'timeframe_bucket', headerName: 'Bucket', width: 95, sortable: true, filter: true },
        { field: 'dte', headerName: 'DTE', width: 90, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter' },
        { field: 'strike', headerName: 'Strike', width: 100, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter', valueFormatter: (p) => formatNumber(p.value, 2) },
        { field: 'premium', headerName: 'Premium', width: 110, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter', valueFormatter: (p) => formatNumber(p.value, 2) },
        { field: 'yield_pct', headerName: 'Yield %', width: 110, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter', valueFormatter: (p) => (p.value === null || p.value === undefined ? '-' : `${formatNumber(p.value, 2)}%`) },
        { field: 'annualized_return_pct', headerName: 'ARIF %', width: 100, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter', valueFormatter: (p) => (p.value === null || p.value === undefined ? '-' : `${formatNumber(p.value, 2)}%`) },
        { field: 'volume', headerName: 'Vol', width: 90, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter' },
        { field: 'open_interest', headerName: 'OI', width: 90, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter' },
        { field: 'liquidity_grade', headerName: 'Liq', width: 80, sortable: true, filter: true },
        {
            field: 'score',
            headerName: 'Score',
            width: 95,
            type: 'numericColumn',
            sortable: true,
            filter: 'agNumberColumnFilter',
            cellClass: (params) => (params.data?.assignment_risk_warning ? 'text-[#d32f2f] font-bold' : ''),
            cellRenderer: (params) => (
                <span title={params.data?.assignment_risk_warning ? 'Critical Warning: assignment risk' : undefined}>
                    {params.value}
                </span>
            ),
        },
        {
            field: 'assignment_risk_label',
            headerName: 'Risk',
            width: 140,
            sortable: true,
            filter: true,
            cellRenderer: (params) => {
                if (!params.value) return '-';
                return (
                    <span className="inline-flex items-center rounded-full border border-[#d32f2f]/60 bg-[#d32f2f]/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#ff8a80]">
                        {params.value}
                    </span>
                );
            },
        },
        { field: 'reason_summary', headerName: 'Reason', minWidth: 220, flex: 1, sortable: true, filter: true },
        { field: 'create_date', headerName: 'Create Date', width: 170, sortable: true, filter: true, valueFormatter: (p) => formatDateTime(p.value) },
        { field: 'last_updated', headerName: 'Last Updated', width: 170, sortable: true, filter: true, valueFormatter: (p) => formatDateTime(p.value) },
    ]), []);

    return (
        <div className="ag-theme-quartz-dark h-[650px] w-full">
            <AgGridReact
                rowData={rows}
                columnDefs={colDefs}
                defaultColDef={{
                    sortable: true,
                    filter: true,
                    resizable: true,
                    minWidth: 100,
                }}
                animateRows
                context={{ onTickerClick }}
            />
        </div>
    );
};

export default JuicysGrid;
