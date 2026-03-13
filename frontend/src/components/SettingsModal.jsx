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
    const [queryIdDividends, setQueryIdDividends] = useState("");

    // Detailed NAV Query IDs
    const [queryIds, setQueryIds] = useState({
        nav_1d: "",
        nav_7d: "",
        nav_30d: "",
        nav_mtd: "",
        nav_ytd: "",
        nav_1y: ""
    });

    const [testingConnection, setTestingConnection] = useState(false);
    const [testResult, setTestResult] = useState(null); // { success: bool, message: str }

    // --- Account Settings (Admin) ---
    const [accounts, setAccounts] = useState([]); // [{account_id, taxable, alias}]

    useEffect(() => {
        setSettings(currentSettings);
        if (isOpen) {
            fetchSchedule();
            if (userRole === 'admin') {
                fetchIBKR();
                fetchAccounts();
            }
        }
    }, [currentSettings, isOpen, userRole]);

    const fetchAccounts = async () => {
        try {
            const api = (await import('../api/axios')).default;
            const res = await api.get('/settings/accounts');
            setAccounts(res.data);
        } catch (error) {
            console.error("Failed to fetch accounts", error);
        }
    };

    const handleAccountChange = (index, field, value) => {
        const newAccounts = [...accounts];
        newAccounts[index][field] = value;
        setAccounts(newAccounts);
    };

    const saveAccounts = async () => {
        try {
            const api = (await import('../api/axios')).default;
            await api.post('/settings/accounts', accounts);
        } catch (error) {
            console.error("Failed to save accounts", error);
        }
    };

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
                masked: res.data.flex_token_masked,
                last_sync: res.data.last_sync
            });
            setQueryIdHoldings(res.data.query_id_holdings || "");
            setQueryIdTrades(res.data.query_id_trades || "");
            setQueryIdDividends(res.data.query_id_dividends || "");

            // Populate detailed IDs
            setQueryIds({
                nav_1d: res.data.query_id_nav_1d || "",
                nav_7d: res.data.query_id_nav_7d || "",
                nav_30d: res.data.query_id_nav_30d || "",
                nav_mtd: res.data.query_id_nav_mtd || "",
                nav_ytd: res.data.query_id_nav_ytd || "",
                nav_1y: res.data.query_id_nav_1y || ""
            });
        } catch (error) {
            console.error("Failed to fetch IBKR status", error);
        }
    };

    const handleSaveIBKR = async () => {
        try {
            const api = (await import('../api/axios')).default;
            const payload = {
                query_id_holdings: queryIdHoldings,
                query_id_trades: queryIdTrades,
                query_id_dividends: queryIdDividends,
                query_id_nav_1d: queryIds.nav_1d,
                query_id_nav_7d: queryIds.nav_7d,
                query_id_nav_30d: queryIds.nav_30d,
                query_id_nav_mtd: queryIds.nav_mtd,
                query_id_nav_ytd: queryIds.nav_ytd,
                query_id_nav_1y: queryIds.nav_1y
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

                // Save Account Configs
                await saveAccounts(); // New function
            } catch (error) {
                console.error("Failed to save settings", error);
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
                                <div className="flex gap-2">
                                    <select
                                        className="flex-grow bg-gray-700 text-white p-2 rounded border border-gray-600 focus:border-green-500"
                                        value={settings.sortColumn}
                                        onChange={(e) => handleChange('sortColumn', e.target.value)}
                                    >
                                        <option value="">None</option>
                                        {columns.map(col => (
                                            <option key={col.field} value={col.field}>{col.headerName || col.field}</option>
                                        ))}
                                    </select>
                                    <select
                                        className="w-24 bg-gray-700 text-white p-2 rounded border border-gray-600 focus:border-green-500"
                                        value={settings.sortOrder}
                                        onChange={(e) => handleChange('sortOrder', e.target.value)}
                                    >
                                        <option value="asc">Asc</option>
                                        <option value="desc">Desc</option>
                                    </select>
                                </div>
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

                            {/* Section: Account Management */}
                            <div className="space-y-4">
                                <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider">Account Taxonomy</h3>
                                {accounts.length === 0 ? (
                                    <p className="text-gray-500 text-xs italic">No accounts discovered yet. Sync data first.</p>
                                ) : (
                                    <div className="bg-gray-900 rounded border border-gray-700 overflow-hidden">
                                        <table className="w-full text-xs text-left">
                                            <thead className="bg-gray-800 text-gray-400">
                                                <tr>
                                                    <th className="p-2">Account ID</th>
                                                    <th className="p-2">Alias</th>
                                                    <th className="p-2 text-center">Taxable</th>
                                                </tr>
                                            </thead>
                                            <tbody className="divide-y divide-gray-700">
                                                {accounts.map((acc, idx) => (
                                                    <tr key={acc.account_id}>
                                                        <td className="p-2 text-white font-mono">{acc.account_id}</td>
                                                        <td className="p-2">
                                                            <input
                                                                type="text"
                                                                className="bg-gray-800 text-white p-1 rounded border border-gray-600 w-full"
                                                                placeholder="Optional"
                                                                value={acc.alias}
                                                                onChange={(e) => handleAccountChange(idx, 'alias', e.target.value)}
                                                            />
                                                        </td>
                                                        <td className="p-2 text-center">
                                                            <input
                                                                type="checkbox"
                                                                className="rounded bg-gray-700 border-gray-600 text-green-500 focus:ring-green-500"
                                                                checked={acc.taxable}
                                                                onChange={(e) => handleAccountChange(idx, 'taxable', e.target.checked)}
                                                            />
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                )}
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
                                        <div>
                                            <label className="block text-gray-400 text-xs mb-1">Dividends Query ID</label>
                                            <input
                                                type="text"
                                                placeholder="Query ID"
                                                className="w-full bg-gray-800 text-white text-sm p-2 rounded border border-gray-600"
                                                value={queryIdDividends}
                                                onChange={(e) => setQueryIdDividends(e.target.value)}
                                            />
                                        </div>
                                        <div className="col-span-2 space-y-2">
                                            <h4 className="text-gray-400 text-xs font-semibold uppercase tracking-wider">NAV History Query IDs</h4>
                                            <div className="grid grid-cols-3 gap-2">
                                                {[
                                                    { id: 'nav_1d', label: '1 Day (Live)' },
                                                    { id: 'nav_7d', label: '7 Day' },
                                                    { id: 'nav_30d', label: '30 Day' },
                                                    { id: 'nav_mtd', label: 'MTD' },
                                                    { id: 'nav_ytd', label: 'YTD' },
                                                    { id: 'nav_1y', label: '1 Year' },
                                                ].map(({ id, label }) => (
                                                    <div key={id}>
                                                        <label className="block text-gray-500 text-[10px] mb-0.5">{label}</label>
                                                        <input
                                                            type="text"
                                                            placeholder="Query ID"
                                                            className="w-full bg-gray-800 text-white text-xs p-1.5 rounded border border-gray-600 focus:border-blue-500"
                                                            value={queryIds[id]}
                                                            onChange={(e) => setQueryIds(prev => ({ ...prev, [id]: e.target.value }))}
                                                        />
                                                    </div>
                                                ))}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex justify-between pt-2">
                                        <div className="flex gap-2">
                                            <button
                                                onClick={handleTestConnection}
                                                disabled={testingConnection}
                                                className="text-xs flex items-center gap-1 text-blue-400 hover:text-blue-300"
                                            >
                                                <RefreshCw className={`w-3 h-3 ${testingConnection ? 'animate-spin' : ''}`} />
                                                Test Token
                                            </button>
                                            <button
                                                onClick={async () => {
                                                    try {
                                                        const api = (await import('../api/axios')).default;
                                                        await api.post('/integrations/ibkr/sync');
                                                        setTestResult({ success: true, message: "Sync Started..." });
                                                        // Poll for status update after 2 seconds
                                                        setTimeout(() => fetchIBKR(), 2000);
                                                    } catch (e) {
                                                        setTestResult({ success: false, message: "Sync Failed" });
                                                    }
                                                }}
                                                className="text-xs flex items-center gap-1 text-yellow-400 hover:text-yellow-300"
                                            >
                                                <RefreshCw className="w-3 h-3" />
                                                Sync Data
                                            </button>
                                        </div>
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

                                    {/* Last Sync Status Display */}
                                    {ibkrStatus.last_sync && (
                                        <div className={`text-xs p-2 rounded border ${ibkrStatus.last_sync.status === 'success' ? 'bg-green-900/30 border-green-800 text-green-300' :
                                            ibkrStatus.last_sync.status === 'failed' ? 'bg-red-900/30 border-red-800 text-red-300' :
                                                'bg-blue-900/30 border-blue-800 text-blue-300'
                                            }`}>
                                            <p className="font-semibold mb-1">Last Sync: <span className="uppercase">{ibkrStatus.last_sync.status}</span></p>
                                            <p>{ibkrStatus.last_sync.message}</p>
                                            <p className="text-gray-500 mt-1 text-[10px]">
                                                {new Date(ibkrStatus.last_sync.timestamp).toLocaleString()}
                                            </p>
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
