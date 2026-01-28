import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import { RefreshCw, LogOut, Play, Download, FileText } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import StockGrid from './StockGrid';

const Dashboard = () => {
    const [data, setData] = useState([]);
    const [reports, setReports] = useState([]);
    const [selectedReport, setSelectedReport] = useState('');
    const [loading, setLoading] = useState(false);
    const [running, setRunning] = useState(false);
    const { logout, user } = useAuth();
    const navigate = useNavigate();

    // Initial Load
    useEffect(() => {
        loadReports();
    }, []);

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

    return (
        <div className="min-h-screen bg-gray-900 text-white p-6">
            <header className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-green-400 to-blue-500">
                    Juicy Fruit Dashboard
                </h1>
                <div className="flex items-center gap-4">
                    <span className="text-gray-400">Welcome, {user?.username}</span>
                    <button onClick={handleLogout} className="p-2 hover:bg-gray-800 rounded">
                        <LogOut className="h-5 w-5 text-red-400" />
                    </button>
                </div>
            </header>

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
                    <StockGrid data={data} />
                )}
            </div>
        </div>
    );
};

export default Dashboard;
