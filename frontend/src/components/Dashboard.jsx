import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import { RefreshCw, LogOut, Play, Download, FileText, Settings } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import StockGrid from './StockGrid';
import SettingsModal from './SettingsModal';
import NAVStats from './NAVStats';
import PortfolioGrid from './PortfolioGrid';
import AlertsDashboard from './AlertsDashboard';

const AVAILABLE_COLUMNS = [
    { field: "Ticker", headerName: "Ticker" },
    { field: "Current Price", headerName: "Price" },
    { field: "Call/Put Skew", headerName: "Call/Put Skew" },
    { field: "1D % Change", headerName: "Change" },
    { field: "YoY Price %", headerName: "YoY %" },
    { field: "TSMOM_60", headerName: "TSMOM 60" },
    { field: "MA_200", headerName: "200 MA" },
    { field: "EMA_20", headerName: "EMA 20" },
    { field: "HMA_20", headerName: "HMA 20" },
    { field: "Div Yield", headerName: "Div Yield" }
];


const Dashboard = () => {
    const [searchParams, setSearchParams] = useSearchParams();

    // State initialized from URL
    const [viewMode, setViewMode] = useState(searchParams.get('view') === 'PORTFOLIO' ? 'PORTFOLIO' : 'ANALYSIS');
    const [selectedReport, setSelectedReport] = useState(searchParams.get('report') || '');

    const [data, setData] = useState([]);
    const [reports, setReports] = useState([]);

    // Sync URL when state changes
    useEffect(() => {
        const params = {};
        if (viewMode === 'PORTFOLIO') params.view = 'PORTFOLIO';
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

    const loadPortfolioData = async () => {
        setLoading(true);
        try {
            const [statsRes, holdingsRes] = await Promise.all([
                api.get('/portfolio/stats'),
                api.get('/portfolio/holdings')
            ]);
            setPortfolioStats(statsRes.data);
            setPortfolioHoldings(holdingsRes.data);
        } catch (error) {
            console.error("Failed to load portfolio:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (viewMode === 'PORTFOLIO') {
            loadPortfolioData();
        }
    }, [viewMode]);

    return (
        <div className="min-h-screen bg-gray-900 text-white p-6">
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
                            <button
                                onClick={() => setViewMode('PORTFOLIO')}
                                className={`px-3 py-1 text-sm rounded ${viewMode === 'PORTFOLIO' ? 'bg-gray-700 text-white shadow' : 'text-gray-400 hover:text-white'}`}
                            >
                                My Portfolio
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
                    <NAVStats stats={portfolioStats} />
                    <div className="mb-4">
                        {/* Dynamically load Alerts */}
                        <AlertsDashboard />
                    </div>
                    <div className="bg-gray-800 rounded-lg p-1 shadow-lg overflow-hidden border border-gray-700 h-[650px]">
                        <PortfolioGrid data={portfolioHoldings} />
                    </div>
                </>
            ) : (
                <>
                    {/* Controls Bar */}
                    <div className="mb-6 flex flex-wrap items-center gap-4 bg-gray-800 p-4 rounded-lg shadow">

                        {/* Report Selector */}
                        <div className="flex items-center gap-2">
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
                            />
                        )}
                    </div>
                </>
            )}

            <SettingsModal
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                onSave={handleSaveSettings}
                currentSettings={settings}
                columns={AVAILABLE_COLUMNS}
                userRole={user?.role}
            />
        </div>
    );
};

export default Dashboard;
