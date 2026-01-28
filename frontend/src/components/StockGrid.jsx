import React, { useState, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react'; // React Data Grid Component
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import "ag-grid-community/styles/ag-grid.css"; // Mandatory CSS
import "ag-grid-community/styles/ag-theme-quartz.css"; // Optional Theme applied to the grid

// Register all Community features
ModuleRegistry.registerModules([AllCommunityModule]);

const StockGrid = ({ data }) => {

    // Column Definitions: Defines the columns to be displayed.
    const [colDefs, setColDefs] = useState([
        { field: "Ticker", filter: true, sortable: true, checkboxSelection: true, pinned: 'left' },
        { field: "Current Price", headerName: "Price", filter: "agNumberColumnFilter", sortable: true, valueFormatter: p => p.value ? `$${parseFloat(p.value).toFixed(2)}` : '' },
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
        { field: "Call/Put Skew", headerName: "Call/Put Skew", filter: "agNumberColumnFilter", valueFormatter: p => p.value ? parseFloat(p.value).toFixed(2) : '' },
        { field: "Last Update" }
    ]);

    // Apply Tailwind Dark Mode logic to AG Grid theme
    // We use "ag-theme-quartz-dark" provided by the library or custom CSS
    // create a wrapper div with the theme class

    return (
        <div
            className="ag-theme-quartz-dark h-[600px] w-full"
            style={{}}
        >
            <AgGridReact
                rowData={data}
                columnDefs={colDefs}
                pagination={true}
                paginationPageSize={20}
                defaultColDef={{
                    flex: 1,
                    minWidth: 100,
                    filter: true,
                }}
                enableCellTextSelection={true}
            />
        </div>
    );
};

export default StockGrid;
