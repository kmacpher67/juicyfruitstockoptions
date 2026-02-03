import React, { useMemo, useState } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
ModuleRegistry.registerModules([AllCommunityModule]);
import "ag-grid-community/styles/ag-theme-alpine.css";

const PortfolioGrid = ({ data, filterTicker, onTickerClick }) => {
    const colDefs = useMemo(() => [
        {
            field: "account_id",
            headerName: "Account",
            width: 90,
            sort: 'asc',
            sortIndex: 0
        },
        {
            field: "symbol",
            headerName: "Ticker",
            sortable: true,
            filter: true,
            width: 200,
            pinned: 'left',
            sort: 'asc',
            sortIndex: 1,
            cellRenderer: (params) => {
                const sym = params.value;
                if (!sym) return null;
                const cleanSym = sym.split(" ")[0];
                const googleUrl = `https://www.google.com/finance/quote/${cleanSym}:NASDAQ`;
                const yahooUrl = `https://finance.yahoo.com/quote/${cleanSym}/options`;

                return (
                    <div className="flex items-center gap-2">
                        <span
                            className="font-bold cursor-pointer hover:text-blue-400 hover:underline"
                            onClick={() => params.context.onTickerClick && params.context.onTickerClick(sym)}
                        >
                            {sym}
                        </span>
                        <div className="flex gap-1 text-xs opacity-50 hover:opacity-100 transition-opacity">
                            <a href={googleUrl} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">G</a>
                            <a href={yahooUrl} target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300">Y</a>
                        </div>
                    </div>
                );
            }
        },
        { field: "quantity", headerName: "Qty", sortable: true, width: 70, type: 'numericColumn' },
        { field: "market_price", headerName: "Price", sortable: true, width: 90, valueFormatter: p => `$${p.value?.toFixed(2)}` },
        { field: "market_value", headerName: "Value", sortable: true, width: 100, valueFormatter: p => `$${p.value?.toLocaleString(undefined, { maximumFractionDigits: 0 })}` },
        { field: "cost_basis", headerName: "Basis", sortable: true, width: 90, valueFormatter: p => `$${p.value?.toFixed(2)}` },
        {
            field: "unrealized_pnl",
            headerName: "Unrealized P&L",
            sortable: true,
            width: 120,
            cellClass: params => params.value >= 0 ? 'text-green-400 font-bold' : 'text-red-400 font-bold',
            valueFormatter: p => `$${p.value?.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
        },
        {
            field: "percent_of_nav",
            headerName: "% NAV",
            sortable: true,
            width: 80,
            valueFormatter: p => `${(p.value * 100).toFixed(2)}%`
        },
        {
            field: "asset_class",
            headerName: "Type",
            sortable: true,
            width: 70,
            valueGetter: params => {
                const d = params.data;
                if (d.asset_class) return d.asset_class;
                if (d.secType) return d.secType;
                if (d.symbol && d.symbol.length > 6 && /\s/.test(d.symbol)) return "OPT"; // Heuristic
                return "STK";
            }
        }
    ], []);

    // Filter Logic
    const rowData = useMemo(() => {
        let processed = [...data];

        if (filterTicker) {
            const f = filterTicker.toUpperCase().trim();
            processed = processed.filter(row => {
                const sym = (row.symbol || "").toUpperCase();
                const und = (row.underlying_symbol || "").toUpperCase();
                // IBKR Options with spaces: "AAPL  250117C..."
                // Split by double space or just startswith
                const matchesSym = sym.includes(f);
                const matchesUnd = und === f;

                return matchesSym || matchesUnd;
            });
        }

        return processed;
    }, [data, filterTicker]);

    const defaultColDef = {
        // flex: 1, // Removed flex: 1 to respect manual widths and prevent squishing
        minWidth: 60,
        resizable: true,
    };

    return (
        <div className="ag-theme-alpine-dark h-full w-full">
            <AgGridReact
                rowData={rowData}
                columnDefs={colDefs}
                defaultColDef={defaultColDef}
                animateRows={true}
                context={{ onTickerClick }}
            />
        </div>
    );
};

export default PortfolioGrid;
