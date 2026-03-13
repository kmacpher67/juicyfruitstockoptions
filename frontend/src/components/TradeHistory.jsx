import React, { useState, useEffect, useMemo } from 'react';
import api from '../api/axios';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import { TrendingUp, TrendingDown, DollarSign, Activity, Calendar } from 'lucide-react';
import "ag-grid-community/styles/ag-grid.css";
import "ag-grid-community/styles/ag-theme-quartz.css";

ModuleRegistry.registerModules([AllCommunityModule]);

// Component for a Single Metric Card
const MetricCard = ({ title, value, icon: Icon, trend, colorClass = "text-white" }) => (
    <div className="bg-gray-800 p-4 rounded-lg shadow border border-gray-700 flex items-center justify-between">
        <div>
            <p className="text-gray-400 text-sm mb-1">{title}</p>
            <p className={`text-2xl font-bold ${colorClass}`}>{value}</p>
        </div>
        <div className={`p-3 rounded-full bg-gray-700 ${colorClass}`}>
            <Icon className="w-6 h-6" />
        </div>
    </div>
);

const TradeHistory = () => {
    const [rowData, setRowData] = useState([]);
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState('ALL');

    const calculateDateRange = (range) => {
        const now = new Date();
        let startDate = null;

        if (range === 'ALL') return { start: null, end: null };

        if (range === 'MTD') {
            startDate = new Date(now.getFullYear(), now.getMonth(), 1);
        } else if (range === 'YTD') {
            startDate = new Date(now.getFullYear(), 0, 1);
        } else if (range === '1D') {
            startDate = new Date();
            startDate.setDate(now.getDate() - 1);
        } else if (range === '1W') {
            startDate = new Date();
            startDate.setDate(now.getDate() - 7);
        } else if (range === '1M') {
            startDate = new Date();
            startDate.setMonth(now.getMonth() - 1);
        } else if (range === '3M') {
            startDate = new Date();
            startDate.setMonth(now.getMonth() - 3);
        } else if (range === '6M') {
            startDate = new Date();
            startDate.setMonth(now.getMonth() - 6);
        } else if (range === '1Y') {
            startDate = new Date();
            startDate.setFullYear(now.getFullYear() - 1);
        } else if (range === '5Y') {
            startDate = new Date();
            startDate.setFullYear(now.getFullYear() - 5);
        }

        // Format YYYY-MM-DD
        const startStr = startDate.toISOString().split('T')[0];
        const endStr = now.toISOString().split('T')[0];
        return { start: startStr, end: endStr };
    };


    const [colDefs] = useState([
        {
            field: "date_time",
            headerName: "Date/Time",
            sort: "desc",
            sortable: true,
            filter: true,
            valueGetter: p => p.data.date_time || p.data.DateTime
        },
        {
            field: "symbol",
            headerName: "Symbol",
            filter: true,
            sortable: true,
            valueGetter: p => p.data.symbol || p.data.Symbol
        },
        {
            headerName: "Action",
            width: 90,
            valueGetter: p => {
                const qty = p.data.quantity !== undefined ? p.data.quantity : p.data.Quantity;
                if (!qty) return "-";
                return qty > 0 ? "BUY" : "SELL";
            },
            cellClassRules: {
                'text-green-400 font-bold': p => p.value === 'BUY',
                'text-red-400 font-bold': p => p.value === 'SELL'
            }
        },
        {
            field: "quantity",
            headerName: "Quantity",
            type: "numericColumn",
            width: 90,
            valueGetter: p => Math.abs(p.data.quantity !== undefined ? p.data.quantity : p.data.Quantity),
        },
        {
            field: "trade_price",
            headerName: "Price",
            valueGetter: p => p.data.trade_price !== undefined ? p.data.trade_price : p.data.TradePrice,
            valueFormatter: p => p.value ? `$${parseFloat(p.value).toFixed(2)}` : ''
        },
        {
            field: "ib_commission",
            headerName: "Comm",
            valueGetter: p => p.data.ib_commission !== undefined ? p.data.ib_commission : p.data.IBCommission,
            valueFormatter: p => p.value ? `$${Math.abs(parseFloat(p.value)).toFixed(2)}` : ''
        },
        {
            field: "realized_pl",
            headerName: "Realized P&L",
            type: "numericColumn",
            valueFormatter: p => p.value !== undefined && p.value !== null ? `$${parseFloat(p.value).toFixed(2)}` : '-',
            cellClassRules: {
                'text-green-400': p => p.value > 0,
                'text-red-400': p => p.value < 0,
                'text-gray-500': p => p.value === 0
            }
        },
        {
            field: "asset_class",
            headerName: "Type",
            width: 80,
            valueGetter: p => {
                let ac = p.data.asset_class || p.data.AssetClass;
                const sym = p.data.symbol || p.data.Symbol || "";

                if (!ac) {
                    if (sym.includes("  ") || (sym.length > 5 && /\d/.test(sym) && (sym.endsWith("C") || sym.endsWith("P")))) ac = "OPT";
                    else ac = "STK";
                }

                if (ac === "OPT" || ac === "FOP") return "Option";
                if (ac === "STK") return "Stock";
                return ac;
            }
        }
    ]);

    useEffect(() => {
        loadData();
    }, [timeRange]);

    const loadData = async () => {
        setLoading(true);
        try {
            const { start, end } = calculateDateRange(timeRange);
            const params = {};
            if (start) params.start_date = start;
            if (end) params.end_date = end;

            const res = await api.get('/trades/analysis', { params }); // Returns { trades: [], metrics: {} }
            setRowData(res.data.trades);
            setMetrics(res.data.metrics);
        } catch (error) {
            console.error("Failed to load trade history:", error);
        } finally {
            setLoading(false);
        }
    };

    const defaultColDef = useMemo(() => ({
        flex: 1,
        minWidth: 100,
        filter: true,
        sortable: true
    }), []);

    return (
        <div className="flex flex-col gap-6">
            {/* Controls */}
            <div className="flex justify-end items-center gap-2">
                <div className="flex items-center gap-2 bg-gray-800 p-1 rounded border border-gray-700">
                    <Calendar className="w-4 h-4 text-gray-400 ml-2" />
                    {['ALL', 'MTD', '1D', '1W', '1M', '3M', '6M', 'YTD', '1Y', '5Y'].map(range => (
                        <button
                            key={range}
                            onClick={() => setTimeRange(range)}
                            className={`px-3 py-1 text-sm rounded transition-colors ${timeRange === range ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white hover:bg-gray-700'}`}
                        >
                            {range}
                        </button>
                    ))}
                </div>
            </div>

            {/* Metrics Section */}
            {metrics && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <MetricCard
                        title="Total P&L"
                        value={`$${metrics.total_pl.toFixed(2)}`}
                        icon={DollarSign}
                        colorClass={metrics.total_pl >= 0 ? "text-green-400" : "text-red-400"}
                    />
                    <MetricCard
                        title="Win Rate"
                        value={`${metrics.win_rate}%`}
                        icon={Activity}
                        colorClass="text-blue-400"
                    />
                    <MetricCard
                        title="Profit Factor"
                        value={metrics.profit_factor}
                        icon={TrendingUp}
                        colorClass="text-yellow-400"
                    />
                    <MetricCard
                        title="Total Trades"
                        value={metrics.total_trades}
                        icon={TrendingDown}
                        colorClass="text-purple-400"
                    />
                </div>
            )}

            {/* Grid Section */}
            <div className="bg-gray-800 rounded-lg p-1 shadow-lg overflow-hidden border border-gray-700 h-[650px] w-full ag-theme-quartz-dark">
                <AgGridReact
                    rowData={rowData}
                    columnDefs={colDefs}
                    defaultColDef={defaultColDef}
                    pagination={true}
                    paginationPageSize={100}
                />
            </div>
        </div>
    );
};

export default TradeHistory;
