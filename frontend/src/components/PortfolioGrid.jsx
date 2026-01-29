import React from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
ModuleRegistry.registerModules([AllCommunityModule]);
import "ag-grid-community/styles/ag-theme-alpine.css";

const PortfolioGrid = ({ data }) => {
    const columnDefs = [
        { field: "symbol", headerName: "Symbol", sortable: true, filter: true, width: 100 },
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
