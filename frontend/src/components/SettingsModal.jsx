import React, { useState, useEffect } from 'react';
import { X, Save, CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react';

const SettingsModal = ({ isOpen, onClose, onSave, currentSettings, columns, userRole }) => {
    // --- General Settings ---
    const [settings, setSettings] = useState(currentSettings);

    // --- Automation (Admin) ---
    const [scheduleTime, setScheduleTime] = useState("10:00");
    const [loadingSchedule, setLoadingSchedule] = useState(false);

    // --- IBKR Integration (Admin) ---
    const [ibkrStatus, setIbkrStatus] = useState({ configured: false, masked: '' });
    const [newToken, setNewToken] = useState("");
    const [queryIdHoldings, setQueryIdHoldings] = useState("");
    const [queryIdTrades, setQueryIdTrades] = useState("");
    const [testingConnection, setTestingConnection] = useState(false);
    const [testResult, setTestResult] = useState(null); // { success: bool, message: str }

    useEffect(() => {
        setSettings(currentSettings);
        if (isOpen) {
            fetchSchedule();
            if (userRole === 'admin') {
                fetchIBKR();
            }
        }
    }, [currentSettings, isOpen, userRole]);

    const fetchSchedule = async () => {
        setLoadingSchedule(true);
        try {
            const api = (await import('../api/axios')).default;
            const res = await api.get('/schedule');
            const { hour, minute } = res.data;
            setScheduleTime(`${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`);
        } catch (error) {
            console.error("Failed to fetch schedule", error);
        } finally {
            setLoadingSchedule(false);
        }
    };

    const fetchIBKR = async () => {
        try {
            const api = (await import('../api/axios')).default;
            const res = await api.get('/integrations/ibkr');
            setIbkrStatus({
                configured: res.data.configured,
                masked: res.data.flex_token_masked
            });
            setQueryIdHoldings(res.data.query_id_holdings || "");
            setQueryIdTrades(res.data.query_id_trades || "");
        } catch (error) {
            console.error("Failed to fetch IBKR status", error);
        }
    };

    const handleSaveIBKR = async () => {
        try {
            const api = (await import('../api/axios')).default;
            const payload = {
                query_id_holdings: queryIdHoldings,
                query_id_trades: queryIdTrades
            };
            if (newToken) payload.flex_token = newToken;

            await api.post('/integrations/ibkr', payload);
            setNewToken(""); // Clear after save
            await fetchIBKR(); // Refresh status
            setTestResult({ success: true, message: "Configuration Updated" });
        } catch (error) {
            console.error("Failed to save IBKR", error);
            setTestResult({ success: false, message: "Failed to save configuration" });
        }
    };

    const handleTestConnection = async () => {
        setTestingConnection(true);
        setTestResult(null);
        try {
            const api = (await import('../api/axios')).default;
            const res = await api.post('/integrations/ibkr/test');
            setTestResult(res.data);
        } catch (error) {
            setTestResult({ success: false, message: "Connection Failed" });
        } finally {
            setTestingConnection(false);
        }
    };

    if (!isOpen) return null;

    const handleChange = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    const handleSave = async () => {
        // Save Remote Schedule (Automation)
        if (userRole === 'admin') {
            try {
                const [h, m] = scheduleTime.split(':').map(Number);
                const api = (await import('../api/axios')).default;
                await api.post('/schedule', { hour: h, minute: m });
            } catch (error) {
                console.error("Failed to save schedule", error);
            }
        }

        // Save Local Settings (Appearance)
        onSave(settings); // Dashboard handles API call for these
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
            <div className="bg-gray-800 border border-gray-700 p-6 rounded-lg w-[32rem] shadow-xl max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold text-white">Dashboard Settings</h2>
                    <button onClick={onClose} className="text-gray-400 hover:text-white">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="space-y-8">
                    {/* Section: Appearance */}
                    <div className="space-y-4">
                        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Appearance</h3>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-gray-300 mb-1 text-sm">Rows per Page</label>
                                <select
                                    className="w-full bg-gray-700 text-white p-2 rounded border border-gray-600 focus:border-green-500"
                                    value={settings.pageSize}
                                    onChange={(e) => handleChange('pageSize', parseInt(e.target.value))}
                                >
                                    {[20, 50, 100, 500].map(n => <option key={n} value={n}>{n}</option>)}
                                </select>
                            </div>
                            <div>
                                <label className="block text-gray-300 mb-1 text-sm">Sort By</label>
                                <select
                                    className="w-full bg-gray-700 text-white p-2 rounded border border-gray-600 focus:border-green-500"
                                    value={settings.sortColumn}
                                    onChange={(e) => handleChange('sortColumn', e.target.value)}
                                >
                                    <option value="">None</option>
                                    {columns.map(col => (
                                        <option key={col.field} value={col.field}>{col.headerName || col.field}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    </div>

                    <div className="border-t border-gray-700"></div>

                    {/* Admin Sections */}
                    {userRole === 'admin' && (
                        <>
                            {/* Section: Automation */}
                            <div className="space-y-4">
                                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Automation</h3>
                                <div>
                                    <label className="block text-gray-300 mb-1 text-sm">Daily Run Time (EST)</label>
                                    <input
                                        type="time"
                                        className="w-full bg-gray-700 text-white p-2 rounded border border-gray-600 focus:border-green-500"
                                        value={scheduleTime}
                                        onChange={(e) => setScheduleTime(e.target.value)}
                                        disabled={loadingSchedule}
                                    />
                                    <p className="text-xs text-gray-500 mt-1">Automatic analysis triggers daily at this time.</p>
                                </div>
                            </div>

                            <div className="border-t border-gray-700"></div>

                            {/* Section: Integrations (IBKR) */}
                            <div className="space-y-4">
                                <div className="flex justify-between items-center">
                                    <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">IBKR Integration</h3>
                                    <div className={`flex items-center gap-1 text-xs ${ibkrStatus.configured ? 'text-green-400' : 'text-red-400'}`}>
                                        {ibkrStatus.configured ? <CheckCircle className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                                        {ibkrStatus.configured ? 'Configured' : 'Not Configured'}
                                    </div>
                                </div>

                                <div className="bg-gray-900 p-4 rounded border border-gray-700 space-y-3">
                                    <div>
                                        <label className="block text-gray-400 text-xs mb-1">Flex Token</label>
                                        <div className="flex gap-2">
                                            <input
                                                type="text"
                                                placeholder={ibkrStatus.masked || "Enter Token"}
                                                className="flex-1 bg-gray-800 text-white text-sm p-2 rounded border border-gray-600"
                                                value={newToken}
                                                onChange={(e) => setNewToken(e.target.value)}
                                            />
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-2 gap-3">
                                        <div>
                                            <label className="block text-gray-400 text-xs mb-1">Holdings Query ID</label>
                                            <input
                                                type="text"
                                                placeholder="Query ID"
                                                className="w-full bg-gray-800 text-white text-sm p-2 rounded border border-gray-600"
                                                value={queryIdHoldings}
                                                onChange={(e) => setQueryIdHoldings(e.target.value)}
                                            />
                                        </div>
                                        <div>
                                            <label className="block text-gray-400 text-xs mb-1">Trades Query ID</label>
                                            <input
                                                type="text"
                                                placeholder="Query ID"
                                                className="w-full bg-gray-800 text-white text-sm p-2 rounded border border-gray-600"
                                                value={queryIdTrades}
                                                onChange={(e) => setQueryIdTrades(e.target.value)}
                                            />
                                        </div>
                                    </div>

                                    <div className="flex justify-between pt-2">
                                        <button
                                            onClick={handleTestConnection}
                                            disabled={testingConnection}
                                            className="text-xs flex items-center gap-1 text-blue-400 hover:text-blue-300"
                                        >
                                            <RefreshCw className={`w-3 h-3 ${testingConnection ? 'animate-spin' : ''}`} />
                                            Test Connection
                                        </button>
                                        <button
                                            onClick={handleSaveIBKR}
                                            className="text-xs bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded"
                                        >
                                            Update IBKR
                                        </button>
                                    </div>

                                    {testResult && (
                                        <div className={`text-xs p-2 rounded ${testResult.success ? 'bg-green-900 text-green-200' : 'bg-red-900 text-red-200'}`}>
                                            {testResult.message}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </>
                    )}
                </div>

                <div className="mt-8 flex justify-end gap-2 border-t border-gray-700 pt-4">
                    <button onClick={onClose} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-white text-sm">Close</button>
                    <button onClick={handleSave} className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-white text-sm">
                        <Save className="w-4 h-4" />
                        Save All
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SettingsModal;
