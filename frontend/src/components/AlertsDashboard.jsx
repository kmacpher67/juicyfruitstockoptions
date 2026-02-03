import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { AlertTriangle, CheckCircle, TrendingUp, X } from 'lucide-react';

const AlertsDashboard = ({ onSelectTicker, onAnalyzeRoll }) => {
    const [alerts, setAlerts] = useState([]);
    const [expirations, setExpirations] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchAlerts();
    }, []);

    const fetchAlerts = async () => {
        setLoading(true);
        try {
            // Parallel fetch: Options Alerts (Routes) and ExpirationScanner Opportunities
            const [alertsRes, expirationsRes] = await Promise.all([
                api.get('/portfolio/alerts'),
                api.get('/api/opportunities?source=ExpirationScanner&limit=20') // Limit so we don't flood
            ]);

            setAlerts(alertsRes.data);
            setExpirations(expirationsRes.data);
        } catch (error) {
            console.error("Failed to fetch alerts", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="p-4 text-gray-400 text-sm">Loading risks...</div>;
    if (alerts.length === 0 && expirations.length === 0) return null;

    const getTypeConfig = (type, score) => {
        switch (type) {
            case 'NAKED_OPTION':
                return { color: 'bg-red-900/50 border-red-700 text-red-200', icon: AlertTriangle, label: 'High Risk' };
            case 'UNCOVERED_SHARES':
                // Color code based on strength score
                let style = 'bg-yellow-900/50 border-yellow-700 text-yellow-200';
                let label = 'Opportunity';
                if (score >= 80) {
                    style = 'bg-green-900/40 border-green-600 text-green-300';
                    label = 'Strong Opt Sell Signal';
                } else if (score >= 50) {
                    style = 'bg-yellow-900/40 border-yellow-600 text-yellow-300';
                    label = 'Opt Sell Signal';
                }
                return { color: style, icon: CheckCircle, label: label };
            case 'PROFIT_TAKE':
                return { color: 'bg-green-900/50 border-green-700 text-green-200', icon: TrendingUp, label: 'Take Profit' };
            default:
                return { color: 'bg-gray-800 border-gray-700 text-gray-300', icon: CheckCircle, label: 'Info' };
        }
    };

    return (
        <div className="mb-4">
            {/* Mixed Grid of Alerts & Expirations */}
            <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3">
                {/* 1. Portfolio Alerts */}
                {alerts.map((alert, idx) => {
                    const { color, icon: Icon, label } = getTypeConfig(alert.type, alert.score || 0);
                    return (
                        <div
                            key={`alert-${idx}`}
                            onClick={() => onSelectTicker && onSelectTicker(alert.symbol)}
                            className={`p-2 pl-3 rounded text-sm border ${color} flex items-center gap-2 shadow-sm cursor-pointer hover:brightness-110 transition-all active:scale-[0.98]`}
                        >
                            <div className="flex-shrink-0">
                                <Icon className="w-4 h-4 opacity-80" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex justify-between items-center mb-0.5">
                                    <div className="flex items-center gap-1.5">
                                        <span className="font-bold font-mono">{alert.symbol}</span>
                                        <span className="text-[10px] uppercase font-bold opacity-70 border border-current px-1 rounded-sm">{label}</span>
                                    </div>
                                    {alert.score > 0 && <span className="text-[10px] font-mono bg-black/20 px-1.5 rounded">{alert.score}</span>}
                                </div>
                                <p className="text-xs leading-tight opacity-90 truncate hover:whitespace-normal" title={alert.message}>{alert.message}</p>
                                {alert.type === 'PROFIT_TAKE' && (
                                    <p className="text-[10px] mt-0.5 font-mono opacity-80">
                                        PnL: ${alert.pnl?.toFixed(0)} ({(alert.profit_pct * 100).toFixed(1)}%)
                                    </p>
                                )}
                            </div>
                        </div>
                    );
                })}

                {/* 2. Expiration Alerts */}
                {expirations.map((opp, idx) => (
                    <div
                        key={`exp-${idx}`}
                        className="p-2 pl-3 rounded text-sm border bg-indigo-900/30 border-indigo-700 text-indigo-200 flex items-center gap-2 shadow-sm"
                    >
                        <div className="flex-shrink-0">
                            {/* Clock Icon inline */}
                            <svg className="w-4 h-4 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </div>
                        <div className="flex-1 min-w-0">
                            <div className="flex justify-between items-center mb-0.5">
                                <div className="flex items-center gap-1.5">
                                    <span className="font-bold font-mono text-white">{opp.symbol}</span>
                                    <span className="text-[10px] uppercase font-bold opacity-70 bg-indigo-900 px-1 rounded text-white border border-indigo-500">Expiring</span>
                                </div>
                                <span className={`text-[10px] font-mono px-1.5 rounded font-bold ${opp.context?.days_to_exp <= 3 ? 'bg-red-900 text-red-200' : 'bg-black/20'}`}>
                                    {opp.context?.days_to_exp}d
                                </span>
                            </div>
                            <div className="flex justify-between items-center mt-1">
                                <p className="text-xs opacity-90 truncate" title={opp.proposal?.reason}>
                                    {opp.proposal?.expiry} | {opp.proposal?.strike}
                                </p>
                                <button
                                    onClick={() => onAnalyzeRoll && onAnalyzeRoll(opp)}
                                    className="text-[10px] bg-indigo-600 hover:bg-indigo-500 text-white px-2 py-0.5 rounded transition-colors"
                                >
                                    Roll?
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default AlertsDashboard;
