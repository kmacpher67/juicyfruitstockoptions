import React from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
ModuleRegistry.registerModules([AllCommunityModule]);
import "ag-grid-community/styles/ag-theme-alpine.css";

const PortfolioGrid = ({ data }) => {
    const columnDefs = [
        { field: "account_id", headerName: "Account", sortable: true, filter: true, width: 100 },
        {
            field: "symbol",
            headerName: "Symbol",
            sortable: true,
            filter: true,
            width: 120,
            cellRenderer: (params) => {
                const sym = params.value;
                if (!sym) return null;
                // Parse underlying for options (e.g. "AAPL 250117...") -> "AAPL"
                // Simple parsing: split by space, take first part.
                const underlying = sym.split(" ")[0];
                const cleanSym = underlying.replace(/[^A-Za-z]/g, ""); // basic cleanup

                const googleUrl = `https://www.google.com/finance/quote/${cleanSym}:NASDAQ`; // Naive exchange assumption
                const yahooUrl = `https://finance.yahoo.com/quote/${cleanSym}/options`;

                return (
                    <div className="flex items-center gap-2">
                        <span className="font-bold">{sym}</span>
                        <div className="flex gap-1 text-xs opacity-50 hover:opacity-100 transition-opacity">
                            <a href={googleUrl} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">G</a>
                            <a href={yahooUrl} target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300">Y</a>
                        </div>
                    </div>
                );
            }
        },
        { field: "asset_class", headerName: "Type", sortable: true, width: 90 },
        {
            field: "quantity",
            headerName: "Qty",
            sortable: true,
            type: "rightAligned",
            valueFormatter: p => p.value.toLocaleString()
        },
        {
            field: "market_price",
            headerName: "Price",
            sortable: true,
            type: "rightAligned",
            valueFormatter: p => `$${p.value.toFixed(2)}`
        },
        {
            field: "market_value",
            headerName: "Value",
            sortable: true,
            type: "rightAligned",
            valueFormatter: p => `$${p.value.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
        },
        {
            field: "cost_basis",
            headerName: "Cost Basis",
            sortable: true,
            type: "rightAligned",
            valueFormatter: p => `$${p.value.toFixed(2)}`
        },
        {
            field: "unrealized_pnl",
            headerName: "Unrealized P&L",
            sortable: true,
            type: "rightAligned",
            cellStyle: params => params.value >= 0 ? { color: '#4ade80' } : { color: '#f87171' },
            valueFormatter: p => `$${p.value.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
        },
        {
            field: "percent_of_nav",
            headerName: "% NAV",
            sortable: true,
            type: "rightAligned",
            valueFormatter: p => `${(p.value * 100).toFixed(2)}%`
        }
    ];

    const defaultColDef = {
        flex: 1,
        minWidth: 100,
        resizable: true,
    };

    return (
        <div className="ag-theme-alpine-dark h-full w-full">
            <AgGridReact
                rowData={data}
                columnDefs={columnDefs}
                defaultColDef={defaultColDef}
                animateRows={true}
            />
        </div>
    );
};

export default PortfolioGrid;
