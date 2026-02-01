import React, { useState, useEffect, useMemo } from 'react';
import api from '../api/axios';
import { AgGridReact } from 'ag-grid-react';
import { ModuleRegistry, AllCommunityModule } from 'ag-grid-community';
import { TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react';
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

    const [colDefs] = useState([
        { field: "date_time", headerName: "Date/Time", sort: "desc", sortable: true, filter: true },
        { field: "symbol", headerName: "Symbol", filter: true, sortable: true },
        {
            field: "quantity",
            headerName: "Quantity",
            type: "numericColumn",
            cellClassRules: {
                'text-green-400': p => p.value > 0,
                'text-red-400': p => p.value < 0
            }
        },
        {
            field: "trade_price",
            headerName: "Price",
            valueFormatter: p => p.value ? `$${parseFloat(p.value).toFixed(2)}` : ''
        },
        {
            field: "ib_commission",
            headerName: "Comm",
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
        { field: "asset_class", headerName: "Type", width: 90 }
    ]);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const res = await api.get('/trades/analysis'); // Returns { trades: [], metrics: {} }
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
