import React, { useState, useMemo, useEffect } from 'react';
import { AgGridReact } from 'ag-grid-react'; // React Data Grid Component
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import "ag-grid-community/styles/ag-grid.css"; // Mandatory CSS
import "ag-grid-community/styles/ag-theme-quartz.css"; // Optional Theme applied to the grid

// Register all Community features
ModuleRegistry.registerModules([AllCommunityModule]);

import { Trash2, ExternalLink, CheckCircle } from 'lucide-react';

// Register all Community features
ModuleRegistry.registerModules([AllCommunityModule]);

const LinkRenderer = (params) => {
    if (!params.value) return null;
    // Use query search as requested by user
    const url = `https://www.google.com/finance?q=${params.value}`;
    return (
        <a href={url} target="_blank" rel="noopener noreferrer" className="flex items-center hover:text-blue-400 group">
            <span className="font-bold">{params.value}</span>
            <ExternalLink className="w-3 h-3 ml-1 opacity-0 group-hover:opacity-100 transition-opacity" />
        </a>
    );
};

const OptionsLinkRenderer = (params) => {
    if (params.value === null || params.value === undefined) return null;
    const ticker = params.data.Ticker;
    const url = `https://finance.yahoo.com/quote/${ticker}/options`;
    return (
        <a href={url} target="_blank" rel="noopener noreferrer" className="flex items-center hover:text-blue-400 underline decoration-dotted">
            {parseFloat(params.value).toFixed(2)}
        </a>
    );
};

const PortfolioRenderer = (params) => {
    if (!params.value) return null;
    return (
        <div className="flex items-center justify-center h-full">
            <CheckCircle className="w-4 h-4 text-green-500" />
        </div>
    );
};

const ActionsRenderer = (params) => {
    const { onDelete, portfolioTickers } = params.context;
    const ticker = params.data.Ticker;
    const isPortfolioItem = portfolioTickers && portfolioTickers.has(ticker);

    if (isPortfolioItem) {
        return (
            <div className="flex items-center justify-center h-full opacity-30 cursor-not-allowed" title="In Portfolio (Cannot Delete)">
                <CheckCircle className="w-4 h-4 text-gray-500" />
            </div>
        );
    }

    return (
        <div className="flex items-center justify-center h-full">
            <button
                onClick={() => onDelete(ticker)}
                className="p-1 text-gray-500 hover:text-red-500 hover:bg-gray-800 rounded transition-colors"
                title="Stop Tracking"
            >
                <Trash2 className="w-4 h-4" />
            </button>
        </div>
    );
};

const StockGrid = ({ data, pageSize = 100, defaultSort = {}, onDelete, portfolioTickers, hasPortfolioAccess }) => {

    // Inject custom data into Row Data so we can filter/sort on it? 
    // Or just use ValueGetter. ValueGetter is better.

    // Column Definitions
    const [colDefs, setColDefs] = useState([]);

    useEffect(() => {
        const baseDefs = [
            {
                field: "Ticker",
                filter: true,
                sortable: true,
                checkboxSelection: true,
                pinned: 'left',
                maxWidth: 110,
                cellRenderer: LinkRenderer
            },
            { field: "Current Price", headerName: "Price", filter: "agNumberColumnFilter", sortable: true, valueFormatter: p => p.value ? `$${parseFloat(p.value).toFixed(2)}` : '' },
            {
                field: "Call/Put Skew",
                headerName: "Options Skew",
                filter: "agNumberColumnFilter",
                cellRenderer: OptionsLinkRenderer
            },
            {
                field: "1D % Change", headerName: "Change", cellClassRules: {
                    'text-green-400': p => p.value && p.value.includes('+'),
                    'text-red-400': p => p.value && p.value.includes('-')
                }
            },
            { field: "YoY Price %", headerName: "YoY %" },
            {
                field: "TSMOM_60", headerName: "TSMOM 60", filter: "agNumberColumnFilter", cellClassRules: {
                    'text-green-400': p => p.value > 0,
                    'text-red-400': p => p.value < 0
                }
            },
            { field: "MA_200", headerName: "200 MA", filter: "agNumberColumnFilter" },
            { field: "EMA_20", headerName: "EMA 20" },
            { field: "HMA_20", headerName: "HMA 20" },
            { field: "Div Yield", headerName: "Div Yield", valueFormatter: p => p.value ? `${p.value}%` : '' },
            // { field: "Last Update" } 
        ];

        // Conditional Columns
        // User requested removing "In Port" column and using Checkbox selection instead.
        // if (hasPortfolioAccess) { ... }

        if (onDelete) {
            baseDefs.push({
                headerName: "",
                field: "actions",
                maxWidth: 60,
                pinned: 'right',
                cellRenderer: ActionsRenderer,
                sortable: false,
                filter: false
            });
        }

        setColDefs(baseDefs);

    }, [hasPortfolioAccess, portfolioTickers, onDelete]);

    const [gridApi, setGridApi] = useState(null);

    const onGridReady = (params) => {
        setGridApi(params.api);
    };

    // Pre-Select rows that are in Portfolio
    useEffect(() => {
        if (gridApi && hasPortfolioAccess && portfolioTickers) {
            // We need to wait for data to be loaded in the grid? 
            // setRowData happens via prop.
            // ag-grid fires 'rowDataUpdated' event, or we can just iterate whenever props change.
            gridApi.forEachNode((node) => {
                if (node.data && portfolioTickers.has(node.data.Ticker)) {
                    node.setSelected(true);
                } else {
                    node.setSelected(false);
                }
            });
        }
    }, [gridApi, hasPortfolioAccess, portfolioTickers, data]);

    // Apply sort when defaultSort or gridApi changes
    useEffect(() => {
        if (gridApi && defaultSort && defaultSort.colId) {
            gridApi.applyColumnState({
                state: [
                    { colId: defaultSort.colId, sort: defaultSort.sortOrder }
                ],
                defaultState: { sort: null }
            });
        }
    }, [defaultSort, gridApi]);

    return (
        <div
            className="ag-theme-quartz-dark h-[600px] w-full"
            style={{}}
        >
            <AgGridReact
                rowData={data}
                columnDefs={colDefs}
                pagination={true}
                paginationPageSize={pageSize}
                defaultColDef={{
                    flex: 1,
                    minWidth: 100,
                    filter: true,
                }}
                rowSelection="multiple" // Enable multiple selection for the checkboxes
                enableCellTextSelection={true}
                onGridReady={onGridReady}
                context={{ onDelete, portfolioTickers }} // Pass context to access inside Renderer
            />
        </div>
    );
};

export default StockGrid;
