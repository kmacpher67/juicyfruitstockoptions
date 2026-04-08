import React, { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
ModuleRegistry.registerModules([AllCommunityModule]);
import "ag-grid-community/styles/ag-theme-alpine.css";
import { ExternalLink } from 'lucide-react';
import { applyPortfolioFilters, DEFAULT_PORTFOLIO_FILTERS } from './portfolioFilters';
import { getNumericValue, formatCurrency, formatPercent } from './portfolioGridFormatters';
import { getDetailTicker, getDisplaySymbol, getVisibleRowCounterLabel, resolveSecurityTypeLabel } from './portfolioPresentation';

const getPendingEffectUi = (effect) => {
    switch (effect) {
        case 'covering_uncovered':
            return { label: 'Pending Cover', tone: 'text-[#2e7d32] border-[#2e7d32]/50 bg-[#2e7d32]/10' };
        case 'buying_to_close':
            return { label: 'Pending BTC', tone: 'text-amber-200 border-amber-500/50 bg-amber-500/10' };
        case 'rolling':
            return { label: 'Pending Roll', tone: 'text-sky-200 border-sky-500/50 bg-sky-500/10' };
        default:
            return null;
    }
};

const toCsvCell = (value) => {
    if (value === undefined || value === null) return '';
    return `"${String(value).replace(/"/g, '""')}"`;
};

const PortfolioGrid = ({ data, filterTicker, onTickerClick, selectedAccount = 'all', onSelectedAccountChange }) => {
    const [searchParams, setSearchParams] = useSearchParams();

    const [filters, setFilters] = useState(() => {
        const init = { ...DEFAULT_PORTFOLIO_FILTERS, account: selectedAccount || 'all' };
        
        const cov = searchParams.get('coverage');
        if (cov) init.coverage = cov;
        
        const pe = searchParams.get('pendingEffect');
        if (pe) init.pendingEffect = pe;
        
        if (searchParams.get('expiringOnly') === 'true') init.expiringOnly = true;
        if (searchParams.get('nearMoneyOnly') === 'true') init.nearMoneyOnly = true;
        if (searchParams.get('showStocks') === 'true') init.showStocks = true;
        
        const dteLimit = searchParams.get('dteLimit');
        if (dteLimit) init.dteLimit = Number(dteLimit);
        
        const nmPct = searchParams.get('nearMoneyPercent');
        if (nmPct) init.nearMoneyPercent = Number(nmPct);
        
        return init;
    });

    useEffect(() => {
        setFilters((current) => ({ ...current, account: selectedAccount || 'all' }));
    }, [selectedAccount]);

    // Sync filters to URL
    useEffect(() => {
        setSearchParams(prev => {
            const next = new URLSearchParams(prev);
            
            if (filters.coverage !== 'all') next.set('coverage', filters.coverage);
            else next.delete('coverage');
            
            if (filters.pendingEffect !== 'all') next.set('pendingEffect', filters.pendingEffect);
            else next.delete('pendingEffect');
            
            if (filters.expiringOnly) next.set('expiringOnly', 'true');
            else next.delete('expiringOnly');
            
            if (filters.nearMoneyOnly) next.set('nearMoneyOnly', 'true');
            else next.delete('nearMoneyOnly');
            
            if (filters.showStocks) next.set('showStocks', 'true');
            else next.delete('showStocks');
            
            if (filters.dteLimit !== DEFAULT_PORTFOLIO_FILTERS.dteLimit) next.set('dteLimit', filters.dteLimit);
            else next.delete('dteLimit');
            
            if (filters.nearMoneyPercent !== DEFAULT_PORTFOLIO_FILTERS.nearMoneyPercent) next.set('nearMoneyPercent', filters.nearMoneyPercent);
            else next.delete('nearMoneyPercent');
            
            return next;
        }, { replace: true });
    }, [
        filters.coverage, filters.pendingEffect, filters.expiringOnly, 
        filters.nearMoneyOnly, filters.showStocks, filters.dteLimit, 
        filters.nearMoneyPercent, setSearchParams
    ]);

    const colDefs = useMemo(() => [
        {
            field: "account_id",
            headerName: "Account",
            width: 90,
            sort: 'asc',
            sortIndex: 0
        },
        {
            field: "display_symbol",
            headerName: "Ticker",
            sortable: true,
            filter: true,
            width: 300,
            pinned: 'left',
            sort: 'asc',
            sortIndex: 1,
            valueGetter: (params) => getDisplaySymbol(params.data),
            cellRenderer: (params) => {
                const row = params.data || {};
                const sym = params.value;
                if (!sym) return null;
                const cleanSym = getDetailTicker(row, sym);
                const googleUrl = `https://www.google.com/finance/quote/${cleanSym}:NASDAQ`;
                const yahooUrl = `https://finance.yahoo.com/quote/${cleanSym}/options`;
                const detailLabel = `Open stock analysis detail for ${cleanSym}`;

                return (
                    <div className="flex items-center gap-2">
                        <span
                            className="font-bold cursor-pointer hover:text-[#1976d2] group flex items-center"
                            onClick={() => params.context.onTickerClick && params.context.onTickerClick(cleanSym)}
                            title={detailLabel}
                            aria-label={detailLabel}
                        >
                            {sym}
                            <ExternalLink
                                className="w-3 h-3 ml-1 text-slate-300 opacity-90 group-hover:opacity-100 group-hover:text-[#1976d2] transition-all"
                                aria-hidden="true"
                            />
                        </span>
                        <div className="flex gap-1 text-xs opacity-100">
                            <a href={googleUrl} target="_blank" rel="noopener noreferrer" className="text-[#1976d2] hover:text-[#1565c0] font-semibold">G</a>
                            <a href={yahooUrl} target="_blank" rel="noopener noreferrer" className="text-[#1976d2] hover:text-[#1565c0] font-semibold">Y</a>
                        </div>
                    </div>
                );
            }
        },
        {
            field: "coverage_status",
            headerName: "Coverage",
            width: 220,
            sortable: true,
            cellRenderer: (params) => {
                const status = params.value || '';
                const pendingUi = getPendingEffectUi(params.data?.pending_order_effect);
                const statusClass = status === 'Covered'
                    ? 'text-[#2e7d32] font-bold'
                    : (status === 'Uncovered' || status === 'Naked')
                        ? 'text-[#d32f2f] font-bold'
                        : 'text-slate-300';

                return (
                    <div className="flex items-center gap-2">
                        <span className={statusClass}>{status || '-'}</span>
                        {pendingUi && (
                            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${pendingUi.tone}`}>
                                {pendingUi.label}
                            </span>
                        )}
                    </div>
                );
            },
        },
        {
            field: "dte",
            headerName: "DTE",
            width: 70,
            sortable: true,
            type: 'numericColumn',
            cellClass: params => (params.data.is_expiring_soon) ? 'bg-red-900/30 text-[#d32f2f] font-bold' : '',
            valueFormatter: p => getNumericValue(p.value) ?? '-'
        },
        {
            field: "dist_to_strike_pct",
            headerName: "NtM %",
            width: 80,
            sortable: true,
            valueFormatter: p => formatPercent(p.value, 1),
            cellClass: params => {
                if (getNumericValue(params.value) !== null && params.value < 0.05) return 'text-orange-400 font-bold';
                return '';
            }
        },
        { field: "quantity", headerName: "Qty", sortable: true, width: 70, type: 'numericColumn' },
        { field: "market_price", headerName: "Price", sortable: true, width: 90, valueFormatter: p => formatCurrency(p.value, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) },
        { field: "market_value", headerName: "Value", sortable: true, width: 100, valueFormatter: p => formatCurrency(p.value, { maximumFractionDigits: 0 }) },
        { field: "cost_basis", headerName: "Basis", sortable: true, width: 90, valueFormatter: p => formatCurrency(p.value, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) },
        {
            field: "unrealized_pnl",
            headerName: "Unrealized P&L",
            sortable: true,
            width: 120,
            cellClass: params => {
                const numeric = getNumericValue(params.value);
                if (numeric === null) return '';
                return numeric >= 0 ? 'text-[#2e7d32] font-bold' : 'text-[#d32f2f] font-bold';
            },
            valueFormatter: p => formatCurrency(p.value, { maximumFractionDigits: 0 })
        },
        {
            field: "divs_earned",
            headerName: "Divs",
            sortable: true,
            width: 80,
            cellClass: params => getNumericValue(params.value) > 0 ? 'text-[#2e7d32] font-bold' : '',
            valueFormatter: p => formatCurrency(p.value, { maximumFractionDigits: 0 })
        },
        {
            field: "total_return",
            headerName: "Total Return",
            sortable: true,
            width: 110,
            cellClass: params => {
                const numeric = getNumericValue(params.value);
                if (numeric === null) return '';
                return numeric >= 0 ? 'text-[#2e7d32] font-bold' : 'text-[#d32f2f] font-bold';
            },
            valueFormatter: p => formatCurrency(p.value, { maximumFractionDigits: 0 })
        },
        {
            field: "true_yield",
            headerName: "True Yield",
            sortable: true,
            width: 90,
            cellClass: params => getNumericValue(params.value) > 0 ? 'text-[#2e7d32] font-bold' : '',
            valueFormatter: p => formatPercent(p.value, 2)
        },
        {
            field: "percent_of_nav",
            headerName: "% NAV",
            sortable: true,
            width: 80,
            valueFormatter: p => formatPercent(p.value, 2)
        },
        {
            field: "security_type",
            headerName: "Type",
            sortable: true,
            width: 90,
            valueGetter: params => resolveSecurityTypeLabel(params.data),
            cellRenderer: (params) => {
                const typeLabel = params.value;
                const d = params.data;
                const accountId = d.account_id;

                // Extract clean ticker symbol
                let ticker = d.underlying_symbol || d.symbol;
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
                            className="opacity-0 group-hover:opacity-100 text-[#1976d2] hover:text-[#1565c0] transition-opacity"
                            title="Ask Trading Agent"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
                            </svg>
                        </a>
                    </div>
                );
            }
        },
        {
            field: "pending_buy_to_close_contracts",
            headerName: "P.BTC",
            headerTooltip: "Pending Buy-to-Close",
            width: 82,
            pinned: 'right',
            sortable: true,
            valueGetter: (params) => {
                const contracts = getNumericValue(params.data?.pending_buy_to_close_contracts);
                return contracts && contracts > 0 ? contracts : null;
            },
            cellRenderer: (params) => {
                if (!params.value) return '';
                return (
                    <span className="inline-flex items-center rounded-full border border-amber-500/50 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-200">
                        BTC {params.value}
                    </span>
                );
            },
        }
    ], []);

    // Unique account list for dropdown
    const accountList = useMemo(() => {
        const set = new Set();
        data.forEach(r => {
            if (r.account_id) set.add(r.account_id);
        });
        return Array.from(set);
    }, [data]);

    // Filter Logic
    const rowData = useMemo(() => {
        return applyPortfolioFilters(data, filters, filterTicker);
    }, [data, filterTicker, filters]);

    const defaultColDef = {
        // flex: 1, // Removed flex: 1 to respect manual widths and prevent squishing
        minWidth: 60,
        resizable: true,
    };

    const setCoverageFilter = (coverage) => {
        setFilters((current) => ({ ...current, coverage }));
    };

    const toggleBooleanFilter = (key) => {
        setFilters((current) => ({ ...current, [key]: !current[key] }));
    };

    const resetFilters = () => {
        const next = { ...DEFAULT_PORTFOLIO_FILTERS };
        setFilters(next);
        if (onSelectedAccountChange) {
            onSelectedAccountChange(next.account);
        }
    };

    const Button = ({ label, active, onClick }) => (
        <button
            onClick={onClick}
            className={`px-3 py-1 text-xs font-bold rounded transiton-colors ${
                active
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' 
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
        >
            {label}
        </button>
    );

    // CSV Export for current view
    const handleExportCSV = () => {
        const headers = [
            'Account',
            'Ticker',
            'Coverage',
            'Pending Effect',
            'DTE',
            'NtM %',
            'Qty',
            'Price',
            'Value',
            'Basis',
            'Unrealized P&L',
            'Divs',
            'Total Return',
            'True Yield',
            '% NAV',
            'Type',
        ];
        const rows = rowData.map((row) => [
            row.account_id || '',
            getDisplaySymbol(row),
            row.coverage_status || '',
            row.pending_order_effect || 'none',
            getNumericValue(row.dte) ?? '',
            formatPercent(row.dist_to_strike_pct, 1),
            getNumericValue(row.quantity) ?? '',
            formatCurrency(row.market_price, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
            formatCurrency(row.market_value, { maximumFractionDigits: 0 }),
            formatCurrency(row.cost_basis, { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
            formatCurrency(row.unrealized_pnl, { maximumFractionDigits: 0 }),
            formatCurrency(row.divs_earned, { maximumFractionDigits: 0 }),
            formatCurrency(row.total_return, { maximumFractionDigits: 0 }),
            formatPercent(row.true_yield, 2),
            formatPercent(row.percent_of_nav, 2),
            resolveSecurityTypeLabel(row),
        ]);
        let csv = headers.map(toCsvCell).join(',') + '\n';
        rows.forEach((r) => {
            csv += r.map(toCsvCell).join(',') + '\n';
        });
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'portfolio_filtered.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className="flex flex-col h-full w-full gap-2">
            <div className="flex flex-wrap items-center gap-4 pl-2 pb-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Focus:</span>
                <Button label="All" active={filters.coverage === 'all' && !filters.expiringOnly && !filters.nearMoneyOnly && filters.account === 'all'} onClick={resetFilters} />
                <Button label="Uncovered" active={filters.coverage === 'Uncovered'} onClick={() => setCoverageFilter('Uncovered')} />
                <Button label="Naked" active={filters.coverage === 'Naked'} onClick={() => setCoverageFilter('Naked')} />
                <Button label="Covered" active={filters.coverage === 'Covered'} onClick={() => setCoverageFilter('Covered')} />
                <Button label='Pending Cover' active={filters.pendingEffect === 'pending_cover'} onClick={() => setFilters((current) => ({ ...current, pendingEffect: current.pendingEffect === 'pending_cover' ? 'all' : 'pending_cover' }))} />
                <Button label='Pending BTC' active={filters.pendingEffect === 'pending_btc'} onClick={() => setFilters((current) => ({ ...current, pendingEffect: current.pendingEffect === 'pending_btc' ? 'all' : 'pending_btc' }))} />
                <Button label='Pending Roll' active={filters.pendingEffect === 'pending_roll'} onClick={() => setFilters((current) => ({ ...current, pendingEffect: current.pendingEffect === 'pending_roll' ? 'all' : 'pending_roll' }))} />
                <Button label={`Expiring (<${filters.dteLimit}D)`} active={filters.expiringOnly} onClick={() => toggleBooleanFilter('expiringOnly')} />
                <Button label={`Near Money (<${filters.nearMoneyPercent}%)`} active={filters.nearMoneyOnly} onClick={() => toggleBooleanFilter('nearMoneyOnly')} />
                <Button label={'Show "STK ?"'} active={filters.showStocks} onClick={() => toggleBooleanFilter('showStocks')} />

                <span className="ml-4 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Account:</span>
                <select
                    className="bg-gray-700 text-white text-xs rounded px-2 py-1 border border-gray-600"
                    value={filters.account}
                    onChange={e => {
                        const nextAccount = e.target.value;
                        setFilters((current) => ({ ...current, account: nextAccount }));
                        if (onSelectedAccountChange) {
                            onSelectedAccountChange(nextAccount);
                        }
                    }}
                >
                    <option value="all">All</option>
                    {accountList.map(acc => (
                        <option key={acc} value={acc}>{acc}</option>
                    ))}
                </select>

                <span className="ml-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Last Price:</span>
                <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={filters.lastPriceMin}
                    placeholder="Min"
                    onChange={e => setFilters((current) => ({ ...current, lastPriceMin: e.target.value }))}
                    className="w-16 bg-gray-700 text-white text-xs rounded px-1 py-0.5 border border-gray-600"
                />
                <span className="text-xs text-slate-500">to</span>
                <input
                    type="number"
                    min={0}
                    step="0.01"
                    value={filters.lastPriceMax}
                    placeholder="Max"
                    onChange={e => setFilters((current) => ({ ...current, lastPriceMax: e.target.value }))}
                    className="w-16 bg-gray-700 text-white text-xs rounded px-1 py-0.5 border border-gray-600"
                />

                {filters.expiringOnly && (
                    <span className="flex items-center gap-1 ml-2">
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">DTE:</span>
                        <input
                            type="number"
                            min={1}
                            max={60}
                            value={filters.dteLimit}
                            onChange={e => setFilters((current) => ({ ...current, dteLimit: Number(e.target.value) }))}
                            className="w-12 bg-gray-700 text-white text-xs rounded px-1 py-0.5 border border-gray-600"
                        />
                    </span>
                )}

                {filters.nearMoneyOnly && (
                    <span className="flex items-center gap-1 ml-2">
                        <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">NM %:</span>
                        <input
                            type="number"
                            min={0}
                            max={20}
                            value={filters.nearMoneyPercent}
                            onChange={e => setFilters((current) => ({ ...current, nearMoneyPercent: Number(e.target.value) }))}
                            className="w-12 bg-gray-700 text-white text-xs rounded px-1 py-0.5 border border-gray-600"
                        />
                    </span>
                )}

                <button
                    onClick={handleExportCSV}
                    className="ml-4 px-3 py-1 text-xs font-bold rounded bg-green-700 hover:bg-green-600 text-white shadow"
                >
                    Export CSV
                </button>

                <span className="ml-2 text-xs font-bold text-slate-300">
                    {getVisibleRowCounterLabel(rowData.length)}
                </span>
            </div>
            <div className="ag-theme-alpine-dark flex-grow w-full">
                <AgGridReact
                    rowData={rowData}
                    columnDefs={colDefs}
                    defaultColDef={defaultColDef}
                    animateRows={true}
                    context={{ onTickerClick }}
                />
            </div>
        </div>
    );
};

export default PortfolioGrid;
