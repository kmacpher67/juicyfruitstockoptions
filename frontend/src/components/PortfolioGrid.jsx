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
            width: 90,
            valueGetter: params => {
                const d = params.data;
                let type = d.asset_class || d.secType;

                if (!type) {
                    if (d.symbol && d.symbol.length > 6 && /\s/.test(d.symbol)) type = "OPT";
                    else type = "STK";
                }

                if (type === "OPT" || type === "FOP") return "Option";
                if (type === "STK") return "Stock";
                return type;
            },
            cellRenderer: (params) => {
                const typeLabel = params.value;
                const d = params.data;
                const accountId = d.account_id;

                // Extract clean ticker symbol
                let ticker = d.symbol;
                if (d.underlying_symbol) ticker = d.underlying_symbol;
                else if (d.symbol && d.symbol.includes(" ")) ticker = d.symbol.split(" ")[0]; // Simple split for OPT

                // Construct Agent URL
                // /agent/analysis?ticker=MX&context=STK&account=U12345
                const agentUrl = `/agent/analysis?ticker=${ticker}&context=${typeLabel === "Option" ? "OPT" : "STK"}&account=${accountId}`;

                return (
                    <div className="flex items-center gap-2 group">
                        <span>{typeLabel}</span>
                        <a
                            href={agentUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="opacity-0 group-hover:opacity-100 text-green-400 hover:text-green-300 transition-opacity"
                            title="Ask Trading Agent"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
                            </svg>
                        </a>
                    </div>
                );
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
