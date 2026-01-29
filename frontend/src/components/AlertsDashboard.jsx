import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { AlertTriangle, CheckCircle, TrendingUp, X } from 'lucide-react';

const AlertsDashboard = () => {
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchAlerts();
    }, []);

    const fetchAlerts = async () => {
        setLoading(true);
        try {
            const res = await api.get('/portfolio/alerts');
            setAlerts(res.data);
        } catch (error) {
            console.error("Failed to fetch alerts", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="p-4 text-gray-400 text-sm">Loading risks...</div>;
    if (alerts.length === 0) return null; // Hide if empty

    // Grouping or simple list? Simple list for now.

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
                    label = 'Strong Opp';
                } else if (score >= 50) {
                    style = 'bg-yellow-900/40 border-yellow-600 text-yellow-300';
                    label = 'Med Opp';
                }
                return { color: style, icon: CheckCircle, label: label };
            case 'PROFIT_TAKE':
                return { color: 'bg-green-900/50 border-green-700 text-green-200', icon: TrendingUp, label: 'Take Profit' };
            default:
                return { color: 'bg-gray-800 border-gray-700 text-gray-300', icon: CheckCircle, label: 'Info' };
        }
    };

    return (
        <div className="mb-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {alerts.map((alert, idx) => {
                const { color, icon: Icon, label } = getTypeConfig(alert.type, alert.score || 0);
                return (
                    <div key={idx} className={`p-4 rounded border ${color} flex items-start gap-3 shadow-sm`}>
                        <div className="mt-1">
                            <Icon className="w-5 h-5" />
                        </div>
                        <div>
                            <div className="flex items-center gap-2 mb-1">
                                <span className="text-xs font-bold uppercase tracking-wider opacity-75">{label}</span>
                                <span className="font-mono text-sm font-bold">{alert.symbol}</span>
                                {alert.score > 0 && <span className="text-xs bg-black/20 px-1 rounded">Score: {alert.score}</span>}
                            </div>
                            <p className="text-sm leading-snug opacity-90">{alert.message}</p>
                            {alert.type === 'PROFIT_TAKE' && (
                                <p className="text-xs mt-2 font-mono">
                                    PnL: ${alert.pnl?.toFixed(0)} ({(alert.profit_pct * 100).toFixed(1)}%)
                                </p>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
};

export default AlertsDashboard;
