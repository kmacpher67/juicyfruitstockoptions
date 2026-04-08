import React, { useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';

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
            className="text-blue-300 hover:text-blue-200 hover:underline font-semibold"
            onClick={() => onTickerClick && onTickerClick(ticker)}
            title={`Open ${ticker} details`}
        >
            {ticker}
        </button>
    );
};

const JuicysGrid = ({ rows, onTickerClick }) => {
    const colDefs = useMemo(() => [
        { field: 'symbol', headerName: 'Ticker', pinned: 'left', width: 110, sortable: true, filter: true, cellRenderer: TickerCell },
        { field: 'as_of', headerName: 'As Of', width: 180, sortable: true, filter: true, valueFormatter: (p) => formatDateTime(p.value) },
        { field: 'strategy', headerName: 'Strategy', width: 180, sortable: true, filter: true },
        { field: 'type', headerName: 'Type', width: 90, sortable: true, filter: true },
        { field: 'action', headerName: 'Action', width: 100, sortable: true, filter: true },
        { field: 'dte', headerName: 'DTE', width: 90, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter' },
        { field: 'strike', headerName: 'Strike', width: 100, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter', valueFormatter: (p) => formatNumber(p.value, 2) },
        { field: 'premium', headerName: 'Premium', width: 110, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter', valueFormatter: (p) => formatNumber(p.value, 2) },
        { field: 'yield_pct', headerName: 'Yield %', width: 110, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter', valueFormatter: (p) => (p.value === null || p.value === undefined ? '-' : `${formatNumber(p.value, 2)}%`) },
        { field: 'score', headerName: 'Score', width: 95, type: 'numericColumn', sortable: true, filter: 'agNumberColumnFilter' },
        { field: 'reason_summary', headerName: 'Reason', minWidth: 280, flex: 1, sortable: true, filter: true },
        { field: 'create_date', headerName: 'Create Date', width: 170, sortable: true, filter: true, valueFormatter: (p) => formatDateTime(p.value) },
        { field: 'last_updated', headerName: 'Last Updated', width: 170, sortable: true, filter: true, valueFormatter: (p) => formatDateTime(p.value) },
    ], []);

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
