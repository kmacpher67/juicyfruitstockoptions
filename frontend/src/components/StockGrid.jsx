import React, { useState, useEffect, useMemo } from 'react';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import 'ag-grid-community/styles/ag-grid.css';
import 'ag-grid-community/styles/ag-theme-quartz.css';
import { Trash2, ExternalLink, CheckCircle } from 'lucide-react';
import { computeTickerHealthScore, getTickerHealthLabel, getTickerHealthTone } from './stockAnalysisPresentation';
import { STOCK_GRID_AVERAGE_FIELDS_ORDER } from './stockGridConfig';
import { resolveQuickLinkTooltip, withHeaderTooltips } from './uiHelpTooltips';

ModuleRegistry.registerModules([AllCommunityModule]);

const toFiniteNumber = (value) => {
    if (value === null || value === undefined) return null;
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    const normalized = String(value).replace('%', '').trim();
    if (!normalized || normalized.toLowerCase() === 'nan') return null;
    const parsed = Number.parseFloat(normalized);
    return Number.isFinite(parsed) ? parsed : null;
};

const formatNumber = (value, digits = 2) => {
    const parsed = toFiniteNumber(value);
    if (parsed === null) return '-';
    return parsed.toFixed(digits);
};

const formatPercent = (value, digits = 2) => {
    const parsed = toFiniteNumber(value);
    if (parsed === null) return '-';
    return `${parsed.toFixed(digits)}%`;
};

const formatMaybePercent = (value, digits = 2) => {
    if (typeof value === 'string' && value.includes('%')) {
        return formatPercent(value, digits);
    }
    const parsed = toFiniteNumber(value);
    if (parsed === null) return '-';
    return `${parsed.toFixed(digits)}%`;
};

const formatCurrency = (value) => {
    const parsed = toFiniteNumber(value);
    if (parsed === null) return '-';
    return `$${parsed.toFixed(2)}`;
};

const LinkRenderer = (params) => {
    if (!params.value) return null;
    const onTickerClick = params.context.onTickerClick;
    const ticker = params.value;
    const googleUrl = `https://www.google.com/finance/quote/${ticker}:NASDAQ`;
    const yahooUrl = `https://finance.yahoo.com/quote/${ticker}/options`;

    return (
        <div className="flex items-center gap-2">
            <span
                className="font-bold cursor-pointer hover:text-[#1976d2] group flex items-center"
                onClick={() => onTickerClick && onTickerClick(ticker)}
                title={`Open stock analysis detail for ${ticker}`}
            >
                {ticker}
                <ExternalLink className="w-3 h-3 ml-1 text-slate-200 opacity-90 group-hover:opacity-100 group-hover:text-[#1976d2] transition-all" />
            </span>
            <div className="flex gap-1 text-xs opacity-100">
                <a href={googleUrl} target="_blank" rel="noopener noreferrer" className="text-[#1976d2] hover:text-[#1565c0] font-semibold" title={resolveQuickLinkTooltip('google', ticker)} aria-label={resolveQuickLinkTooltip('google', ticker)}>G</a>
                <a href={yahooUrl} target="_blank" rel="noopener noreferrer" className="text-[#1976d2] hover:text-[#1565c0] font-semibold" title={resolveQuickLinkTooltip('yahoo', ticker)} aria-label={resolveQuickLinkTooltip('yahoo', ticker)}>Y</a>
            </div>
        </div>
    );
};

const OptionsLinkRenderer = (params) => {
    const parsed = toFiniteNumber(params.value);
    if (parsed === null) return '-';
    const ticker = params.data.Ticker;
    const url = `https://finance.yahoo.com/quote/${ticker}/options`;
    return (
        <a href={url} target="_blank" rel="noopener noreferrer" className="flex items-center text-[#1976d2] hover:text-[#1565c0] underline decoration-dotted" title={resolveQuickLinkTooltip('yahoo', ticker)} aria-label={resolveQuickLinkTooltip('yahoo', ticker)}>
            {parsed.toFixed(2)}
        </a>
    );
};

const TickerHealthRenderer = (params) => {
    const score = params.value;
    const tone = getTickerHealthTone(score);
    const label = getTickerHealthLabel(score);
    return (
        <div className={`flex items-center gap-2 font-mono ${tone}`}>
            <span className="font-semibold">{score ?? '-'}</span>
            <span className="text-xs uppercase opacity-90">{label}</span>
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

const buildStockGridColumnDefs = ({ onDelete }) => {
    const averageHeaderByField = {
        EMA_20: 'EMA 20',
        HMA_20: 'HMA 20',
        MA_30: 'MA 30',
        MA_60: 'MA 60',
        MA_120: 'MA 120',
        MA_200: 'MA 200',
    };
    const averageColumns = STOCK_GRID_AVERAGE_FIELDS_ORDER.map((field) => ({
        field,
        headerName: averageHeaderByField[field] || field,
        filter: 'agNumberColumnFilter',
        sortable: true,
        valueFormatter: (p) => formatNumber(p.value, 2),
        width: field === 'MA_120' || field === 'MA_200' ? 95 : 90,
    }));

    const baseDefs = [
        {
            field: 'Ticker',
            filter: true,
            sortable: true,
            checkboxSelection: true,
            pinned: 'left',
            width: 220,
            cellRenderer: LinkRenderer,
        },
        { field: 'Current Price', headerName: 'Price', filter: 'agNumberColumnFilter', sortable: true, valueFormatter: (p) => formatCurrency(p.value), width: 110 },
        { field: 'Call/Put Skew', headerName: 'Options Skew', filter: 'agNumberColumnFilter', sortable: true, cellRenderer: OptionsLinkRenderer, width: 120 },
        {
            field: '1D % Change',
            headerName: 'Change',
            sortable: true,
            valueFormatter: (p) => formatMaybePercent(p.value, 2),
            cellClassRules: {
                'text-[#2e7d32] font-semibold': (p) => (toFiniteNumber(p.value) ?? 0) > 0,
                'text-[#d32f2f] font-semibold': (p) => (toFiniteNumber(p.value) ?? 0) < 0,
            },
            width: 100,
        },
        { field: 'YoY Price %', headerName: 'YoY %', sortable: true, valueFormatter: (p) => formatMaybePercent(p.value, 1), width: 90 },
        {
            field: 'TSMOM_60',
            headerName: 'TSMOM 60',
            filter: 'agNumberColumnFilter',
            sortable: true,
            valueFormatter: (p) => formatPercent(p.value, 2),
            cellClassRules: {
                'text-[#2e7d32] font-semibold': (p) => (toFiniteNumber(p.value) ?? 0) > 0,
                'text-[#d32f2f] font-semibold': (p) => (toFiniteNumber(p.value) ?? 0) < 0,
            },
            width: 100,
        },
        {
            field: 'Ticker Health',
            headerName: 'Ticker Health',
            filter: 'agNumberColumnFilter',
            sortable: true,
            valueGetter: (params) => computeTickerHealthScore(params.data),
            cellRenderer: TickerHealthRenderer,
            width: 160,
        },
        {
            field: 'RSI_14',
            headerName: 'RSI 14',
            filter: 'agNumberColumnFilter',
            sortable: true,
            valueFormatter: (p) => formatNumber(p.value, 2),
            cellClassRules: {
                'text-[#2e7d32] font-semibold': (p) => (toFiniteNumber(p.value) ?? 0) > 50,
                'text-[#d32f2f] font-semibold': (p) => {
                    const val = toFiniteNumber(p.value);
                    return val !== null && val < 50;
                },
            },
            width: 90,
        },
        ...averageColumns,
        { field: 'Annual Yield Put Prem', headerName: '1Y Put Prem %', filter: 'agNumberColumnFilter', sortable: true, valueFormatter: (p) => formatPercent(p.value, 2), width: 120 },
        { field: '3-mo Call Yield', headerName: '3M Call %', filter: 'agNumberColumnFilter', sortable: true, valueFormatter: (p) => formatPercent(p.value, 2), width: 105 },
        { field: '6-mo Call Yield', headerName: '6M Call %', filter: 'agNumberColumnFilter', sortable: true, valueFormatter: (p) => formatPercent(p.value, 2), width: 105 },
        { field: '1-yr Call Yield', headerName: '1Y Call %', filter: 'agNumberColumnFilter', sortable: true, valueFormatter: (p) => formatPercent(p.value, 2), width: 105 },
        { field: 'Div Yield', headerName: 'Div Yield', sortable: true, valueFormatter: (p) => formatPercent(p.value, 2), width: 100 },
    ];

    if (onDelete) {
        baseDefs.push({
            headerName: '',
            field: 'actions',
            maxWidth: 60,
            pinned: 'right',
            cellRenderer: ActionsRenderer,
            sortable: false,
            filter: false,
        });
    }
    return withHeaderTooltips(baseDefs);
};

const StockGrid = ({ data, pageSize = 100, defaultSort = {}, onDelete, portfolioTickers, hasPortfolioAccess, onTickerClick }) => {
    const colDefs = useMemo(() => buildStockGridColumnDefs({ onDelete }), [onDelete]);

    const [gridApi, setGridApi] = useState(null);

    const onGridReady = (params) => {
        setGridApi(params.api);
    };

    useEffect(() => {
        if (gridApi && hasPortfolioAccess && portfolioTickers) {
            gridApi.forEachNode((node) => {
                if (node.data && portfolioTickers.has(node.data.Ticker)) {
                    node.setSelected(true);
                } else {
                    node.setSelected(false);
                }
            });
        }
    }, [gridApi, hasPortfolioAccess, portfolioTickers, data]);

    useEffect(() => {
        if (gridApi && defaultSort && defaultSort.colId) {
            gridApi.applyColumnState({
                state: [{ colId: defaultSort.colId, sort: defaultSort.sortOrder }],
                defaultState: { sort: null },
            });
        }
    }, [defaultSort, gridApi]);

    return (
        <div className="ag-theme-quartz-dark h-[600px] w-full">
            <AgGridReact
                rowData={data}
                columnDefs={colDefs}
                pagination
                paginationPageSize={pageSize}
                defaultColDef={{
                    minWidth: 95,
                    filter: true,
                    resizable: true,
                }}
                rowSelection="multiple"
                enableCellTextSelection
                onGridReady={onGridReady}
                context={{ onDelete, portfolioTickers, onTickerClick }}
            />
        </div>
    );
};

export default StockGrid;
