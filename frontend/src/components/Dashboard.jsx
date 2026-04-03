import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import { RefreshCw, LogOut, Play, Download, FileText, Settings } from 'lucide-react';
import { Plus, Trash2, ExternalLink } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import StockGrid from './StockGrid';
import SettingsModal from './SettingsModal';
import NAVStats from './NAVStats';
import PortfolioGrid from './PortfolioGrid';
import TradeHistory from './TradeHistory';
import OrdersGrid from './OrdersGrid';
import TickerModal from './TickerModal';
import RollAnalysisModal from './RollAnalysisModal';
// import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const formatRelativeTime = (value) => {
    if (!value) return 'update pending';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return 'update pending';

    const diffSeconds = Math.max(0, Math.floor((Date.now() - parsed.getTime()) / 1000));
    if (diffSeconds < 5) return 'updated just now';
    if (diffSeconds < 60) return `updated ${diffSeconds}s ago`;
    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) return `updated ${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `updated ${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `updated ${diffDays}d ago`;
};

const AVAILABLE_COLUMNS = [
    { field: "Ticker", headerName: "Ticker" },
    { field: "Current Price", headerName: "Price" },
    { field: "Call/Put Skew", headerName: "Call/Put Skew" },
    { field: "1D % Change", headerName: "Change" },
    { field: "YoY Price %", headerName: "YoY %" },
    { field: "TSMOM_60", headerName: "TSMOM 60" },
    { field: "Ticker Health", headerName: "Ticker Health" },
    { field: "MA_200", headerName: "200 MA" },
    { field: "EMA_20", headerName: "EMA 20" },
    { field: "HMA_20", headerName: "HMA 20" },
    { field: "Div Yield", headerName: "Div Yield" }
];


const Dashboard = () => {
    const [searchParams, setSearchParams] = useSearchParams();

    // State initialized from URL
    const [viewMode, setViewMode] = useState(() => {
        const v = searchParams.get('view');
        if (v === 'PORTFOLIO') return 'PORTFOLIO';
        if (v === 'TRADES') return 'TRADES';
        if (v === 'ORDERS') return 'ORDERS';
        return 'ANALYSIS';
    });
    const [selectedReport, setSelectedReport] = useState(searchParams.get('report') || '');

    // Quick Add Ticker State
    const [newTicker, setNewTicker] = useState("");
    const [addingTicker, setAddingTicker] = useState(false);

    const [data, setData] = useState([]);
    const [reports, setReports] = useState([]);

    // Sync URL when state changes
    useEffect(() => {
        const params = {};
        if (viewMode === 'PORTFOLIO') params.view = 'PORTFOLIO';
        if (viewMode === 'TRADES') params.view = 'TRADES';
        if (viewMode === 'ORDERS') params.view = 'ORDERS';
        if (selectedReport) params.report = selectedReport;
        setSearchParams(params, { replace: true });
    }, [viewMode, selectedReport, setSearchParams]);
    const [loading, setLoading] = useState(false);
    const [running, setRunning] = useState(false);

    // Settings State
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [settings, setSettings] = useState({
        pageSize: 100,
        sortColumn: 'Ticker',
        sortOrder: 'asc'
    });

    const [selectedTicker, setSelectedTicker] = useState(null);


    const { logout, user } = useAuth();
    const navigate = useNavigate();

    // Initial Load (Reports + Settings)
    useEffect(() => {
        loadReports();
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            const res = await api.get('/settings');
            // If the API returns valid data, use it.
            // Our API returns default object if empty, so it's safe.
            if (res.data) {
                setSettings(res.data);
            }
        } catch (error) {
            console.error("Failed to load settings:", error);
        }
    };

    // When report selection changes, load that report's data
    useEffect(() => {
        if (selectedReport) {
            loadReportData(selectedReport);
        }
    }, [selectedReport]);

    const loadReports = async () => {
        try {
            const response = await api.get('/reports');
            const fileList = response.data;
            setReports(fileList);

            // Auto-select latest if available
            if (fileList.length > 0) {
                setSelectedReport(fileList[0]);
            } else {
                // Fallback: Try to load from MongoDB if no reports exist? 
                // Or just show empty. The user generally wants to see the LAST RUN.
                // We'll leave data empty or fetch from /stocks as fallback
                loadLiveStocks();
            }
        } catch (error) {
            console.error("Failed to load reports list:", error);
        }
    };

    const loadLiveStocks = async () => {
        setLoading(true);
        try {
            const response = await api.get('/stocks');
            setData(response.data);
        } catch (error) {
            console.error("Failed to load live stocks:", error);
        } finally {
            setLoading(false);
        }
    }

    const loadReportData = async (filename) => {
        setLoading(true);
        try {
            const response = await api.get(`/reports/${filename}/data`);
            setData(response.data);
        } catch (error) {
            console.error(`Failed to load report ${filename}:`, error);
            alert(`Failed to load data for ${filename}`);
        } finally {
            setLoading(false);
        }
    };

    const runAnalysis = async () => {
        setRunning(true);
        try {
            // Start Job
            const response = await api.post('/run/stock-live-comparison');
            const jobId = response.data.job_id;

            // Poll Status every 2 seconds
            const pollInterval = setInterval(async () => {
                try {
                    const statusRes = await api.get(`/jobs/${jobId}`);
                    const job = statusRes.data;

                    if (job.status === 'completed') {
                        clearInterval(pollInterval);
                        setRunning(false);
                        // alert("Analysis Complete. Refreshing reports...");
                        await loadReports();
                    } else if (job.status === 'failed') {
                        clearInterval(pollInterval);
                        setRunning(false);
                        alert(`Analysis Failed: ${job.error}`);
                    }
                } catch (err) {
                    console.error("Polling error", err);
                    clearInterval(pollInterval);
                    setRunning(false);
                    alert("Lost connection to server during polling.");
                }
            }, 2000);

        } catch (error) {
            console.error(error);
            alert("Failed to start analysis");
            setRunning(false);
        }
    };

    const downloadCurrentReport = async () => {
        if (!selectedReport) return;
        try {
            const response = await api.get(`/reports/${selectedReport}/download`, { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', selectedReport);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            console.error("Download failed:", error);
        }
    };

    const downloadICS = async () => {
        try {
            const response = await api.get('/calendar/dividends.ics', { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'dividends.ics');
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error("ICS Download failed:", error);
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/login');
    }

    const handleSaveSettings = async (newSettings) => {
        // Save to API
        try {
            await api.post('/settings', newSettings);
        } catch (error) {
            console.error("Failed to save settings to server:", error);
            // Optionally alert user
        }
        setSettings(newSettings);
        setIsSettingsOpen(false);
    };

    // --- Portfolio View Logic ---
    // viewMode state moved to top for Deep Linking
    const [portfolioStats, setPortfolioStats] = useState(null);
    const [portfolioHoldings, setPortfolioHoldings] = useState([]);
    const [selectedPortfolioAccount, setSelectedPortfolioAccount] = useState('all');
    const [openOrders, setOpenOrders] = useState([]);
    const [filterTicker, setFilterTicker] = useState(null);
    const [liveStatus, setLiveStatus] = useState(null);
    const [toast, setToast] = useState(null);

    const loadPortfolioData = async () => {
        setLoading(true);
        try {
            const statsParams = selectedPortfolioAccount && selectedPortfolioAccount !== 'all'
                ? { account_id: selectedPortfolioAccount }
                : undefined;
            const [statsRes, holdingsRes, liveStatusRes] = await Promise.all([
                api.get('/portfolio/stats', { params: statsParams }),
                api.get('/portfolio/holdings'),
                api.get('/portfolio/live-status')
            ]);
            setPortfolioStats({
                ...statsRes.data,
                live_connected: liveStatusRes.data.connected,
                live_position_count: liveStatusRes.data.position_count,
                tws_enabled: liveStatusRes.data.tws_enabled,
                connection_state: liveStatusRes.data.connection_state,
                diagnosis: liveStatusRes.data.diagnosis,
                last_position_update: liveStatusRes.data.last_position_update,
                last_account_value_update: liveStatusRes.data.last_account_value_update,
                last_updated:
                    statsRes.data.last_updated ||
                    liveStatusRes.data.last_account_value_update ||
                    liveStatusRes.data.last_position_update,
            });
            setPortfolioHoldings(holdingsRes.data);
            setLiveStatus(liveStatusRes.data);
        } catch (error) {
            console.error("Failed to load portfolio:", error);
        } finally {
            setLoading(false);
        }
    };

    const loadOrdersData = async () => {
        setLoading(true);
        try {
            const [ordersRes, liveStatusRes] = await Promise.all([
                api.get('/orders/open'),
                api.get('/orders/live-status')
            ]);
            setOpenOrders(ordersRes.data || []);
            setLiveStatus(liveStatusRes.data || null);
        } catch (error) {
            console.error("Failed to load orders:", error);
            setOpenOrders([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (viewMode !== 'ORDERS') return undefined;

        let cancelled = false;
        const pollOrders = async () => {
            try {
                const [ordersRes, liveStatusRes] = await Promise.all([
                    api.get('/orders/open'),
                    api.get('/orders/live-status')
                ]);
                if (cancelled) return;
                setOpenOrders(ordersRes.data || []);
                setLiveStatus(liveStatusRes.data || null);
            } catch (error) {
                console.error('Failed to poll orders:', error);
            }
        };

        const intervalId = window.setInterval(pollOrders, 30000);
        pollOrders();

        return () => {
            cancelled = true;
            window.clearInterval(intervalId);
        };
    }, [viewMode]);

    useEffect(() => {
        if (viewMode !== 'PORTFOLIO') return undefined;

        let cancelled = false;
        const pollLiveStatus = async () => {
            try {
                const res = await api.get('/portfolio/live-status');
                if (cancelled) return;

                setLiveStatus((prev) => {
                    if (prev?.connected && !res.data.connected) {
                        setToast({
                            message: 'TWS live connection dropped. Portfolio data has fallen back to the latest available snapshot.',
                            type: 'warning',
                        });
                    }
                    return res.data;
                });

                setPortfolioStats((prev) => {
                    if (!prev) return prev;
                    return {
                        ...prev,
                        live_connected: res.data.connected,
                        live_position_count: res.data.position_count,
                        tws_enabled: res.data.tws_enabled,
                        connection_state: res.data.connection_state,
                        diagnosis: res.data.diagnosis,
                        last_position_update: res.data.last_position_update,
                        last_account_value_update: res.data.last_account_value_update,
                        last_updated:
                            res.data.connected && (res.data.last_account_value_update || res.data.last_position_update)
                                ? (res.data.last_account_value_update || res.data.last_position_update)
                                : prev.last_updated ||
                                  res.data.last_account_value_update ||
                                  res.data.last_position_update,
                    };
                });
            } catch (error) {
                console.error('Failed to poll live status:', error);
            }
        };

        const intervalId = window.setInterval(pollLiveStatus, 60000);
        pollLiveStatus();

        return () => {
            cancelled = true;
            window.clearInterval(intervalId);
        };
    }, [viewMode]);

    useEffect(() => {
        if (!toast) return undefined;
        const timeoutId = window.setTimeout(() => setToast(null), 5000);
        return () => window.clearTimeout(timeoutId);
    }, [toast]);

    const triggerAutoSync = async () => {
        try {
            // Auto-sync if data is older than 4 hours
            await api.post('/integrations/ibkr/sync', null, { params: { stale_hours: 4 } });
        } catch (e) {
            console.error("Auto-sync check failed", e);
        }
    };

    // Load Portfolio Holdings even in Analysis View if use has access, so we can show "In Portfolio" badge
    useEffect(() => {
        if (viewMode === 'PORTFOLIO') {
            loadPortfolioData();
            triggerAutoSync();
        } else if (viewMode === 'ORDERS') {
            loadOrdersData();
        } else {
            // If in analysis mode, we still might want the holdings for the indicator
            if (user?.role === 'admin' || user?.role === 'portfolio') {
                // Silent load
                api.get('/portfolio/holdings').then(res => setPortfolioHoldings(res.data)).catch(e => console.error("Silent portfolio fetch failed", e));
            }
        }
    }, [viewMode, user, selectedPortfolioAccount]);

    // Derived Portfolio Tickers set
    const portfolioTickers = React.useMemo(() => {
        if (!portfolioHoldings) return new Set();
        return new Set(portfolioHoldings.map(h => h.symbol || h.Symbol || h.Ticker)); // Handles lowercase symbol
    }, [portfolioHoldings]);


    const handleAddTicker = async (e) => {
        e.preventDefault();
        if (!newTicker) return;
        setAddingTicker(true);
        try {
            const res = await api.post('/stocks/tracked', { ticker: newTicker });
            setNewTicker("");

            // If backend returned a job_id, poll for it
            const jobId = res.data.job_id;
            if (jobId) {
                // Poll Status every 1s
                const pollInterval = setInterval(async () => {
                    try {
                        const statusRes = await api.get(`/jobs/${jobId}`);
                        const job = statusRes.data;

                        if (job.status === 'completed') {
                            clearInterval(pollInterval);
                            setAddingTicker(false);
                            // Refresh reports to pick up the new file
                            await loadReports();
                        } else if (job.status === 'failed') {
                            clearInterval(pollInterval);
                            setAddingTicker(false);
                            alert(`Failed to Fetch Data: ${job.error}`);
                        }
                    } catch (err) {
                        console.error("Polling error", err);
                        clearInterval(pollInterval);
                        setAddingTicker(false);
                    }
                }, 1000);
            } else {
                // Fallback for immediate return (legacy behavior)
                alert(`Added ${newTicker}. Data is fetching in background.`);
                setTimeout(() => {
                    loadLiveStocks();
                    setAddingTicker(false);
                }, 2000);
            }

        } catch (error) {
            console.error("Failed to add ticker:", error);
            alert("Failed to add ticker");
            setAddingTicker(false);
        }
    };

    const handleDeleteTicker = async (ticker) => {
        if (!window.confirm(`Stop tracking ${ticker}?`)) return;
        try {
            await api.delete(`/stocks/tracked/${ticker}`);
            // Optimistic update or refresh
            setData(prev => prev.filter(r => r.Ticker !== ticker));
        } catch (error) {
            console.error("Failed to delete ticker:", error);
            alert("Failed to delete ticker");
        }
    };

    const exportPortfolio = async () => {
        try {
            console.log("Starting export via fetch...");
            const token = localStorage.getItem('token');
            const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

            const response = await fetch('/api/portfolio/export/csv', {
                method: 'GET',
                headers: headers
            });

            if (!response.ok) {
                const text = await response.text();
                throw new Error(`Server returned ${response.status}: ${text}`);
            }

            const text = await response.text();

            // Open a new window
            const win = window.open('', '_blank', 'width=800,height=600');
            if (win) {
                win.document.write(`
                    <html>
                        <head><title>Portfolio Export</title></head>
                        <body style="font-family: monospace; white-space: pre-wrap; padding: 20px;">
                            ${text}
                        </body>
                    </html>
                `);
                win.document.close();
            } else {
                alert('Pop-up blocked! Please allow pop-ups for this site.');
            }

        } catch (error) {
            console.error("Export failed:", error);
            alert(`Failed to export CSV: ${error.message}`);
        }
    };

    const createOneTimeDownload = async () => {
        try {
            console.log('Requesting one-time download URL...');
            const res = await api.post('/portfolio/export/url');
            const { url, expires_in } = res.data;
            console.log('Received one-time URL', url, 'expires_in', expires_in);
            // Open the URL in a new tab/window to trigger native download behavior
            const a = document.createElement('a');
            a.href = url;
            a.target = '_blank';
            a.rel = 'noopener';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } catch (err) {
            console.error('Failed to create one-time download URL:', err);
            alert('Failed to create download URL');
        }
    };

    const syncAllPortfolio = async () => {
        try {
            // Force Sync (stale_hours=0)
            await api.post('/integrations/ibkr/sync', null, { params: { stale_hours: 0 } });
            alert("Sync started. Data will update shortly.");
            // Optionally reload page or poll? For now just alert.
        } catch (error) {
            console.error("Sync failed:", error);
            alert("Failed to trigger sync");
        }
    };

    // --- Roll Analysis Logic ---
    const [selectedRollOpportunity, setSelectedRollOpportunity] = useState(null);
    const orderUpdateLabel = formatRelativeTime(liveStatus?.last_order_update);
    const orderAgeSeconds = liveStatus?.last_order_update
        ? Math.max(0, Math.floor((Date.now() - new Date(liveStatus.last_order_update).getTime()) / 1000))
        : null;
    const isOrderFeedStale = orderAgeSeconds !== null && orderAgeSeconds > 90;

    return (
        <div className="min-h-screen w-full bg-gray-900 px-4 py-5 text-white lg:px-6">
            <header className="flex justify-between items-center mb-8">
                <div className="flex items-center gap-4">
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-green-400 to-blue-500">
                        Juicy Fruit Dashboard
                    </h1>
                    {/* View Switcher */}
                    {(user?.role === 'admin' || user?.role === 'portfolio') && (
                        <div className="flex bg-gray-800 rounded p-1 ml-4 border border-gray-700">
                            <button
                                onClick={() => setViewMode('ANALYSIS')}
                                className={`px-3 py-1 text-sm rounded ${viewMode === 'ANALYSIS' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                            >
                                Analysis
                            </button>
                            <div className="relative group">
                                <button
                                    onClick={() => setViewMode('PORTFOLIO')}
                                    className={`px-3 py-1 text-sm rounded ${viewMode === 'PORTFOLIO' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                                >
                                    My Portfolio
                                </button>
                                {/* Dropdown Menu */}
                                <div className="absolute left-0 pt-2 w-48 z-50 hidden group-hover:block">
                                    <div className="bg-gray-800 border border-gray-700 rounded shadow-xl">
                                        <a
                                            href="/api/portfolio/export/csv"
                                            onClick={(e) => {
                                                const token = localStorage.getItem('token');
                                                if (token) {
                                                    // If we have an auth token, prevent default and use the fetch-based download
                                                    e.preventDefault();
                                                    exportPortfolio();
                                                }
                                                // If no token, allow the browser to follow the link (use cookies/browser auth)
                                            }}
                                            className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors border-b border-gray-700 rounded-t"
                                        >
                                            <Download className="inline-block w-3 h-3 mr-2" />
                                            Export CSV
                                        </a>
                                        <button
                                            onClick={downloadICS}
                                            className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors border-b border-gray-700"
                                        >
                                            <span className="inline-block w-3 h-3 mr-2">📅</span>
                                            Export Calendar (.ics)
                                        </button>
                                        <button
                                            onClick={syncAllPortfolio}
                                            className="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors rounded-b"
                                        >
                                            <RefreshCw className="inline-block w-3 h-3 mr-2" />
                                            Sync All
                                        </button>
                                    </div>
                                </div>
                            </div>
                            <button
                                onClick={() => setViewMode('TRADES')}
                                className={`px-3 py-1 text-sm rounded ${viewMode === 'TRADES' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                            >
                                Trade History
                            </button>
                            <button
                                onClick={() => setViewMode('ORDERS')}
                                className={`px-3 py-1 text-sm rounded ${viewMode === 'ORDERS' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                            >
                                Orders
                            </button>
                        </div>
                    )}
                </div>
                <div className="flex items-center gap-4">
                    <span className="text-gray-400">Welcome, {user?.username}</span>
                    <button onClick={() => setIsSettingsOpen(true)} className="p-2 hover:bg-gray-800 rounded text-gray-400 hover:text-white transition-colors">
                        <Settings className="h-5 w-5" />
                    </button>
                    <button onClick={handleLogout} className="p-2 hover:bg-gray-800 rounded">
                        <LogOut className="h-5 w-5 text-red-400" />
                    </button>
                </div>
            </header>

            {/* Render Based on Mode */}
            {viewMode === 'PORTFOLIO' ? (
                <>
                    {toast && (
                        <div className="mb-4 rounded border border-yellow-500/40 bg-yellow-500/10 px-4 py-3 text-sm text-yellow-100 shadow-lg">
                            {toast.message}
                        </div>
                    )}
                    <div className="mb-4 w-full">
                        <NAVStats stats={portfolioStats} selectedAccount={selectedPortfolioAccount} />
                    </div>


                    {/* Filter Indicator */}
                    {filterTicker && (
                        <div className="mb-2 flex items-center gap-2">
                            <span className="text-sm text-gray-400">Filtering for: <span className="text-white font-bold">{filterTicker}</span></span>
                            <button onClick={() => setFilterTicker(null)} className="text-xs text-blue-400 hover:underline">Clear</button>
                        </div>
                    )}
                    <div className="bg-gray-800 rounded-lg p-1 shadow-lg overflow-hidden border border-gray-700 h-[650px]">
                        <PortfolioGrid
                            data={portfolioHoldings}
                            filterTicker={filterTicker}
                            onTickerClick={(ticker) => setSelectedTicker(ticker)}
                            selectedAccount={selectedPortfolioAccount}
                            onSelectedAccountChange={setSelectedPortfolioAccount}
                        />
                    </div>
                </>
            ) : viewMode === 'TRADES' ? (
                <TradeHistory onTickerClick={(ticker) => setSelectedTicker(ticker)} />
            ) : viewMode === 'ORDERS' ? (
                <div className="space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-3 bg-gray-800 rounded-lg px-4 py-3 border border-gray-700">
                        <div className="flex items-center gap-3">
                            <button
                                onClick={loadOrdersData}
                                disabled={loading}
                                className="flex items-center gap-2 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-sm disabled:opacity-50 transition-colors"
                            >
                                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                                Refresh Orders
                            </button>
                            <span className="text-xs text-gray-400">
                                Open Orders: <span className="font-semibold text-gray-200">{openOrders.length}</span>
                            </span>
                        </div>
                        <div className={`text-xs px-3 py-1 rounded border ${
                            liveStatus?.connected
                                ? (isOrderFeedStale ? 'border-amber-500/40 bg-amber-500/10 text-amber-200' : 'border-green-500/40 bg-green-500/10 text-green-200')
                                : 'border-gray-600 bg-gray-900 text-gray-300'
                        }`}>
                            <span className="font-semibold mr-2">
                                {liveStatus?.connected ? (isOrderFeedStale ? 'TWS Connected (Stale)' : 'TWS Live') : 'TWS Not Live'}
                            </span>
                            <span>{orderUpdateLabel}</span>
                        </div>
                    </div>
                    <div className="bg-gray-800 rounded-lg p-1 shadow-lg overflow-hidden border border-gray-700 h-[650px]">
                        <OrdersGrid
                            data={openOrders}
                            onTickerClick={(ticker) => setSelectedTicker(ticker)}
                        />
                    </div>
                </div>
            ) : (
                <>
                    {/* Controls Bar */}
                    <div className="mb-6 flex flex-wrap items-center gap-4 bg-gray-800 p-4 rounded-lg shadow">

                        {/* Report Selector */}
                        <div className="flex items-center gap-2">
                            {/* Add Ticker Input */}
                            <form onSubmit={handleAddTicker} className="flex items-center gap-2 mr-4 border-r border-gray-600 pr-4">
                                <input
                                    type="text"
                                    value={newTicker}
                                    onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                                    placeholder="Add Ticker..."
                                    className="bg-gray-700 text-white p-2 rounded border border-gray-600 w-32 focus:w-48 transition-all outline-none focus:border-green-500 uppercase"
                                />
                                <button
                                    type="submit"
                                    disabled={addingTicker || !newTicker}
                                    className="p-2 bg-green-700 hover:bg-green-600 rounded disabled:opacity-50"
                                >
                                    <Plus className="h-4 w-4" />
                                </button>
                            </form>

                            <FileText className="text-gray-400 h-5 w-5" />
                            <select
                                className="bg-gray-700 text-white p-2 rounded border border-gray-600 focus:border-green-500 outline-none"
                                value={selectedReport}
                                onChange={(e) => setSelectedReport(e.target.value)}
                            >
                                {reports.length === 0 && <option value="">No Reports Found</option>}
                                {reports.map(file => (
                                    <option key={file} value={file}>{file}</option>
                                ))}
                            </select>
                        </div>

                        <div className="h-6 w-px bg-gray-600 mx-2"></div>

                        <button
                            onClick={() => selectedReport ? loadReportData(selectedReport) : loadReports()}
                            disabled={loading}
                            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded disabled:opacity-50 transition-colors"
                        >
                            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                            Refresh
                        </button>

                        <button
                            onClick={downloadCurrentReport}
                            disabled={!selectedReport}
                            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded transition-colors disabled:opacity-50 disabled:bg-gray-600"
                        >
                            <Download className="h-4 w-4" />
                            Download
                        </button>

                        <div className="flex-grow"></div>

                        <button
                            onClick={runAnalysis}
                            disabled={running}
                            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded disabled:opacity-50 transition-colors"
                        >
                            <Play className="h-4 w-4" />
                            {running ? 'Running Analysis...' : 'Run Live Comparison'}
                        </button>
                    </div>

                    <div className="bg-gray-800 rounded-lg p-1 shadow-lg overflow-hidden border border-gray-700 h-[650px]">
                        {data.length === 0 && !loading ? (
                            <div className="text-center text-gray-500 py-12">Select a report to view data.</div>
                        ) : (
                            <StockGrid
                                data={data}
                                pageSize={settings.pageSize}
                                defaultSort={{ colId: settings.sortColumn, sortOrder: settings.sortOrder }}
                                onDelete={handleDeleteTicker}
                                portfolioTickers={portfolioTickers}
                                hasPortfolioAccess={user?.role === 'admin' || user?.role === 'portfolio'}
                                onTickerClick={(ticker) => setSelectedTicker(ticker)}
                            />
                        )}
                    </div>
                </>
            )
            }

            <TickerModal
                ticker={selectedTicker}
                isOpen={!!selectedTicker}
                onClose={() => setSelectedTicker(null)}
            />

            <RollAnalysisModal
                opportunity={selectedRollOpportunity}
                isOpen={!!selectedRollOpportunity}
                onClose={() => setSelectedRollOpportunity(null)}
            />

            <SettingsModal
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                onSave={handleSaveSettings}
                currentSettings={settings}
                columns={AVAILABLE_COLUMNS}
                userRole={user?.role}
            />
        </div >
    );
};

export default Dashboard;
