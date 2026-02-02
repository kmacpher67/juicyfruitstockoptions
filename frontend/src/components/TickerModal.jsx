import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { X, TrendingUp, AlertTriangle, Lightbulb } from 'lucide-react';

const TickerModal = ({ ticker, isOpen, onClose }) => {
    const [activeTab, setActiveTab] = useState('analytics');
    const [loading, setLoading] = useState(false);
    const [tickerData, setTickerData] = useState(null);
    const [opportunityData, setOpportunityData] = useState(null);
    const [optimizerData, setOptimizerData] = useState(null);

    // Reset state when ticker changes
    useEffect(() => {
        if (isOpen && ticker) {
            setLoading(true);
            setTickerData(null);
            setOpportunityData(null);
            setOptimizerData(null);
            setActiveTab('analytics');
            fetchData();
        }
    }, [isOpen, ticker]);

    const fetchData = async () => {
        setLoading(true);
        try {
            // Parallel fetch for all data derived from this ticker
            // Note: In a real app, you might fetch only the active tab's data.
            // But since these are lightweight, we fetch all for responsiveness.
            const [tickerRes, oppRes, optRes] = await Promise.all([
                api.get(`/ticker/${ticker}`),
                api.get(`/opportunity/${ticker}`),
                api.get(`/portfolio/optimizer/${ticker}`)
            ]);

            setTickerData(tickerRes.data);
            setOpportunityData(oppRes.data);
            setOptimizerData(optRes.data);
        } catch (error) {
            console.error("Failed to fetch ticker data", error);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col border border-gray-700">
                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-800 bg-gray-850 rounded-t-lg">
                    <div className="flex items-baseline gap-3">
                        <h2 className="text-3xl font-bold text-white">{ticker}</h2>
                        {tickerData?.data ? (
                            <>
                                <span className="text-xl font-mono text-blue-400">${tickerData?.data?.['Current Price']}</span>
                                <span className={`text-sm ${tickerData?.data?.['1D % Change'] >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    {tickerData?.data?.['1D % Change']}%
                                </span>
                            </>
                        ) : (
                            <span className="text-sm text-gray-500">Loading price...</span>
                        )}
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-gray-800 bg-gray-800">
                    <button
                        onClick={() => setActiveTab('analytics')}
                        className={`flex-1 py-4 text-sm font-medium uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${activeTab === 'analytics' ? 'bg-gray-700 text-blue-400 border-b-2 border-blue-400' : 'text-gray-400 hover:text-white hover:bg-gray-750'}`}
                    >
                        <TrendingUp className="w-4 h-4" /> Analytics
                    </button>
                    <button
                        onClick={() => setActiveTab('opportunity')}
                        className={`flex-1 py-4 text-sm font-medium uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${activeTab === 'opportunity' ? 'bg-gray-700 text-yellow-400 border-b-2 border-yellow-400' : 'text-gray-400 hover:text-white hover:bg-gray-750'}`}
                    >
                        <Lightbulb className="w-4 h-4" /> Opportunity
                    </button>
                    <button
                        onClick={() => setActiveTab('optimizer')}
                        className={`flex-1 py-4 text-sm font-medium uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${activeTab === 'optimizer' ? 'bg-gray-700 text-green-400 border-b-2 border-green-400' : 'text-gray-400 hover:text-white hover:bg-gray-750'}`}
                    >
                        <AlertTriangle className="w-4 h-4" /> Optimizer
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto flex-1 bg-gray-900 custom-scrollbar">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center h-64 gap-4">
                            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                            <p className="text-gray-400 animate-pulse">Analyzing {ticker}...</p>
                        </div>
                    ) : (
                        <>
                            {activeTab === 'analytics' && <AnalyticsView data={tickerData} />}
                            {activeTab === 'opportunity' && <OpportunityView data={opportunityData} />}
                            {activeTab === 'optimizer' && <OptimizerView data={optimizerData} />}
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

// --- Sub Views ---

const AnalyticsView = ({ data }) => {
    if (!data?.found) return <div className="text-center text-gray-400 py-12">No data found for this ticker.</div>;
    const s = data.data; // stock data object

    // Helper for rows
    const Row = ({ label, value }) => (
        <div className="flex justify-between py-2 border-b border-gray-800 last:border-0 hover:bg-gray-800 px-2 rounded transition-colors">
            <span className="text-gray-400">{label}</span>
            <span className="text-white font-mono">{value?.toString() || '-'}</span>
        </div>
    );

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div>
                <h3 className="text-lg font-bold text-white mb-4 border-b border-gray-700 pb-2">Price Action</h3>
                <Row label="Current Price" value={s['Current Price']} />
                <Row label="1D % Change" value={`${s['1D % Change']}%`} />
                <Row label="50 Day MA" value={s['MA_50']} />
                <Row label="200 Day MA" value={s['MA_200']} />
                <Row label="52 Week High" value={s['52 Week High']} />
                <Row label="52 Week Low" value={s['52 Week Low']} />
            </div>
            <div>
                <h3 className="text-lg font-bold text-white mb-4 border-b border-gray-700 pb-2">Fundamentals & Volatility</h3>
                <Row label="IV Rank" value={s['IV Rank']} />
                <Row label="Implied Vol" value={s['Implied Volatility']} />
                <Row label="Call/Put Skew" value={s['Call/Put Skew']} />
                <Row label="Dividend Yield" value={`${s['Div Yield']}%`} />
                <Row label="Market Cap" value={s['Market Cap'] || '-'} />
                <Row label="PE Ratio" value={s['PE Ratio'] || '-'} />
            </div>
        </div>
    );
};

const OpportunityView = ({ data }) => {
    if (!data) return null;
    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4 bg-gray-800 p-6 rounded-lg border border-gray-700">
                <div className={`
                    w-24 h-24 rounded-full flex items-center justify-center text-3xl font-bold border-4
                    ${data.juicy_score >= 80 ? 'border-green-500 text-green-400' :
                        data.juicy_score >= 50 ? 'border-yellow-500 text-yellow-400' : 'border-gray-600 text-gray-500'}
                `}>
                    {data.juicy_score}
                </div>
                <div>
                    <h3 className="text-xl font-bold text-white">Juicy Score</h3>
                    <p className="text-gray-400">
                        Evaluates probability of profit for premium selling strategies.
                    </p>
                </div>
            </div>

            {/* Drivers Section (Restored) */}
            <div>
                <h3 className="text-lg font-bold text-white mb-4">Drivers</h3>
                <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {data.reasons && data.reasons.length > 0 ? (
                        data.reasons.map((r, i) => (
                            <li key={i} className="bg-gray-800 p-3 rounded flex items-center gap-2 text-green-300">
                                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                                {r}
                            </li>
                        ))
                    ) : (
                        <li className="text-gray-500 italic">No specific positive drivers identified.</li>
                    )}
                </ul>
            </div>

            {/* Risk Warnings */}
            {data.risks && data.risks.length > 0 && (
                <div>
                    <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-red-500" />
                        Risk Warnings
                    </h3>
                    <div className="space-y-2">
                        {data.risks.map((risk, i) => (
                            <div key={i} className={`p-3 rounded border-l-4 ${risk.level === 'danger' ? 'bg-red-900 border-red-500 text-red-100' : 'bg-yellow-900 border-yellow-500 text-yellow-100'}`}>
                                <div className="font-bold text-sm uppercase">{risk.type}</div>
                                <div className="text-sm">{risk.message}</div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Metrics */}
            <div>
                <h3 className="text-lg font-bold text-white mb-2">Metrics</h3>
                <div className="grid grid-cols-3 gap-4">
                    <div className="bg-black bg-opacity-30 p-3 rounded text-center">
                        <div className="text-xs text-gray-400 uppercase">IV Rank</div>
                        <div className="text-xl font-mono text-white">{data.metrics?.iv_rank}</div>
                    </div>
                    <div className="bg-black bg-opacity-30 p-3 rounded text-center">
                        <div className="text-xs text-gray-400 uppercase">Liquidity</div>
                        <div className="text-xl font-mono text-white">{data.metrics?.liquidity}</div>
                    </div>
                    <div className="bg-black bg-opacity-30 p-3 rounded text-center">
                        <div className="text-xs text-gray-400 uppercase">Skew</div>
                        <div className="text-xl font-mono text-white">{data.metrics?.call_put_skew}</div>
                    </div>
                    <div className="bg-black bg-opacity-30 p-3 rounded text-center">
                        <div className="text-xs text-gray-400 uppercase">RSI (14)</div>
                        <div className={`text-xl font-mono ${data.metrics?.rsi_14 > 70 ? 'text-red-400' : data.metrics?.rsi_14 < 30 ? 'text-green-400' : 'text-white'}`}>
                            {data.metrics?.rsi_14}
                        </div>
                    </div>
                    <div className="bg-black bg-opacity-30 p-3 rounded text-center">
                        <div className="text-xs text-gray-400 uppercase">ATR (14)</div>
                        <div className="text-xl font-mono text-white">{data.metrics?.atr_14}</div>
                    </div>
                </div>
            </div>
        </div>
    );
};

const OptimizerView = ({ data }) => {
    if (!data || data.length === 0) return <div className="text-center text-gray-400 py-12">No optimization strategies found.</div>;

    return (
        <div className="grid grid-cols-1 gap-4">
            {data.map((strat, i) => (
                <div key={i} className="bg-gray-800 border-l-4 border-green-500 p-4 rounded shadow hover:bg-gray-750 transition-colors">
                    <div className="flex justify-between items-start mb-2">
                        <h4 className="text-lg font-bold text-white">{strat.strategy}</h4>
                        <span className="px-2 py-1 bg-green-900 text-green-300 text-xs rounded uppercase font-bold tracking-wider">
                            {strat.action}
                        </span>
                    </div>
                    <div className="flex justify-between items-center">
                        <div>
                            <p className="text-gray-300 text-sm mb-1">{strat.reason}</p>
                            {strat.strike_target && (
                                <p className="text-xs text-gray-500">Target Strike: <span className="text-white font-mono">${strat.strike_target}</span></p>
                            )}
                        </div>
                        <button className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded">
                            Analyze
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
};

export default TickerModal;
