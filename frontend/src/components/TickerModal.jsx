import React, { useState, useEffect, useRef } from 'react';
import api from '../api/axios';
import { X, TrendingUp, AlertTriangle, Lightbulb, Activity, RotateCcw, Building2 } from 'lucide-react';
import { buildTickerHeaderModel } from './tickerModalHeader';
import { ANALYTICS_FIELD_GROUPS } from './stockAnalysisPresentation';

const TickerModal = ({ ticker, isOpen, onClose }) => {
    const [activeTab, setActiveTab] = useState('analytics');
    const [loading, setLoading] = useState(false);
    const [tickerData, setTickerData] = useState(null);
    const [opportunityData, setOpportunityData] = useState(null);
    const [optimizerData, setOptimizerData] = useState(null);
    const [smartRollsData, setSmartRollsData] = useState(null);
    const [signalData, setSignalData] = useState(null);
    const requestSeq = useRef(0);

    // Reset state when ticker changes
    useEffect(() => {
        if (isOpen && ticker) {
            setLoading(true);
            setTickerData(null);
            setOpportunityData(null);
            setOptimizerData(null);
            setSmartRollsData(null);
            setSignalData(null);
            setActiveTab('analytics');
            fetchData();
        }
    }, [isOpen, ticker]);

    const fetchData = async () => {
        setLoading(true);
        requestSeq.current += 1;
        const seq = requestSeq.current;
        const timeoutMs = 12000;
        const hardStopMs = 15000;
        const hardStop = setTimeout(() => {
            if (requestSeq.current !== seq) return;
            setLoading(false);
            setTickerData((current) => current ?? { found: false, symbol: ticker, data: null });
        }, hardStopMs);
        try {
            if (typeof navigator !== 'undefined' && navigator.onLine === false) {
                setTickerData({ found: false, symbol: ticker, data: null });
                setOpportunityData({ symbol: ticker, juicy_score: 0, reasons: [], risks: [], metrics: {} });
                setOptimizerData([]);
                setSmartRollsData([]);
                setSignalData(null);
                return;
            }

            // Do not block the entire modal on slow secondary endpoints.
            // We render as soon as ticker data lands, then hydrate other tabs.
            api.get(`/ticker/${ticker}`, { timeout: timeoutMs })
                .then((res) => {
                    if (requestSeq.current !== seq) return;
                    setTickerData(res.data);
                })
                .catch(() => {
                    if (requestSeq.current !== seq) return;
                    setTickerData({ found: false, symbol: ticker, data: null });
                })
                .finally(() => {
                    if (requestSeq.current !== seq) return;
                    setLoading(false);
                });

            api.get(`/opportunity/${ticker}`, { timeout: timeoutMs })
                .then((res) => {
                    if (requestSeq.current !== seq) return;
                    setOpportunityData(res.data);
                })
                .catch(() => {
                    if (requestSeq.current !== seq) return;
                    setOpportunityData({ symbol: ticker, juicy_score: 0, reasons: [], risks: [], metrics: {} });
                });

            api.get(`/portfolio/optimizer/${ticker}`, { timeout: timeoutMs })
                .then((res) => {
                    if (requestSeq.current !== seq) return;
                    setOptimizerData(res.data);
                })
                .catch(() => {
                    if (requestSeq.current !== seq) return;
                    setOptimizerData([]);
                });

            api.get(`/analysis/rolls/${ticker}`, { timeout: timeoutMs })
                .then((res) => {
                    if (requestSeq.current !== seq) return;
                    setSmartRollsData(res.data);
                })
                .catch(() => {
                    if (requestSeq.current !== seq) return;
                    setSmartRollsData([]);
                });

            api.get(`/analysis/signals/${ticker}`, { timeout: timeoutMs })
                .then((res) => {
                    if (requestSeq.current !== seq) return;
                    setSignalData(res.data);
                })
                .catch(() => {
                    if (requestSeq.current !== seq) return;
                    setSignalData(null);
                });
        } catch (error) {
            console.error("Failed to fetch ticker data", error);
        } finally {
            clearTimeout(hardStop);
        }
    };

    if (!isOpen) return null;

    const headerModel = buildTickerHeaderModel({ ticker, tickerData });

    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 z-50 flex items-center justify-center p-4">
            <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col border border-gray-700">
                {/* Header — Ticker (→Google Finance), Company Name (→Yahoo Finance), Price, Change, Last Update */}
                <div className="flex justify-between items-center p-6 border-b border-gray-800 bg-gray-850 rounded-t-lg">
                    <div className="flex items-baseline gap-3 flex-wrap">
                        <a
                            href={`https://www.google.com/finance/quote/${headerModel.ticker}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-3xl font-bold text-blue-400 hover:text-blue-300 hover:underline transition-colors"
                            title={`View ${headerModel.ticker} on Google Finance`}
                        >
                            {headerModel.ticker}
                        </a>
                        {headerModel.descriptor && headerModel.descriptor !== headerModel.ticker && (
                            <a
                                href={`https://finance.yahoo.com/quote/${headerModel.ticker}/`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-sm text-gray-400 hover:text-yellow-400 hover:underline transition-colors"
                                title={`View ${headerModel.descriptor} on Yahoo Finance`}
                            >
                                {headerModel.descriptor}
                            </a>
                        )}
                        {tickerData?.data ? (
                            <>
                                {headerModel.priceText && <span className="text-xl font-mono text-blue-400">{headerModel.priceText}</span>}
                                {headerModel.changeText && (
                                    <span className={`text-sm ${headerModel.changeTone}`}>
                                        {headerModel.changeText}
                                    </span>
                                )}
                                <span className="text-xs text-gray-500" title="Last data update">
                                    {headerModel.lastUpdateText}
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
                        onClick={() => setActiveTab('signals')}
                        className={`flex-1 py-4 text-sm font-medium uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${activeTab === 'signals' ? 'bg-gray-700 text-pink-400 border-b-2 border-pink-400' : 'text-gray-400 hover:text-white hover:bg-gray-750'}`}
                    >
                        <Activity className="w-4 h-4" /> Signals
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
                    <button
                        onClick={() => setActiveTab('price_action')}
                        className={`flex-1 py-4 text-sm font-medium uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${activeTab === 'price_action' ? 'bg-gray-700 text-purple-400 border-b-2 border-purple-400' : 'text-gray-400 hover:text-white hover:bg-gray-750'}`}
                    >
                        <Activity className="w-4 h-4" /> Price Action
                    </button>
                    {(smartRollsData && !smartRollsData.error && smartRollsData.length > 0) && (
                        <button
                            onClick={() => setActiveTab('smart_rolls')}
                            className={`flex-1 py-4 text-sm font-medium uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${activeTab === 'smart_rolls' ? 'bg-gray-700 text-indigo-400 border-b-2 border-indigo-400' : 'text-gray-400 hover:text-white hover:bg-gray-750'}`}
                        >
                            <RotateCcw className="w-4 h-4" /> Smart Rolls
                        </button>
                    )}
                    <button
                        onClick={() => setActiveTab('profile')}
                        className={`flex-1 py-4 text-sm font-medium uppercase tracking-wider flex items-center justify-center gap-2 transition-colors ${activeTab === 'profile' ? 'bg-gray-700 text-teal-400 border-b-2 border-teal-400' : 'text-gray-400 hover:text-white hover:bg-gray-750'}`}
                    >
                        <Building2 className="w-4 h-4" /> Profile
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
                            {activeTab === 'signals' && <SignalView data={signalData} />}
                            {activeTab === 'opportunity' && <OpportunityView data={opportunityData} />}
                            {activeTab === 'optimizer' && <OptimizerView data={optimizerData} />}
                            {activeTab === 'price_action' && <PriceActionView data={tickerData} />}
                            {activeTab === 'smart_rolls' && <SmartRollView data={smartRollsData} />}
                            {activeTab === 'profile' && <ProfileView data={tickerData} ticker={ticker} />}
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
            {ANALYTICS_FIELD_GROUPS.map((group) => (
                <div key={group.title}>
                    <h3 className="text-lg font-bold text-white mb-4 border-b border-gray-700 pb-2">{group.title}</h3>
                    {group.fields.map(([label, field]) => {
                        const raw = s?.[field];
                        const value = raw === undefined || raw === null || raw === '' ? '-' : raw;
                        return <Row key={field} label={label} value={value} />;
                    })}
                </div>
            ))}
            <div className="md:col-span-2">
                <h3 className="text-lg font-bold text-white mb-4 border-b border-gray-700 pb-2">Price Action Snapshot</h3>
                <pre className="bg-gray-800 rounded p-3 text-xs text-gray-200 overflow-auto max-h-40">
                    {JSON.stringify(s?.['Price Action'] || {}, null, 2)}
                </pre>
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



const SignalView = ({ data }) => {
    if (!data) return <div className="text-center text-gray-400 py-12">No signal data available.</div>;
    const { kalman, markov, advice } = data;

    return (
        <div className="space-y-6">
            {/* Advice Header */}
            <div className={`p-4 rounded-lg border-l-4 flex justify-between items-center ${advice?.recommendation === 'ROLL' ? 'bg-indigo-900 border-indigo-500' : advice?.recommendation === 'HOLD' ? 'bg-yellow-900 border-yellow-500' : 'bg-gray-800 border-gray-500'}`}>
                <div>
                    <h3 className="text-xl font-bold text-white uppercase tracking-wider">{advice?.recommendation} Recommendation</h3>
                    <p className="text-gray-300 text-sm mt-1">{advice?.reason}</p>
                </div>
                <div className="text-right">
                    <div className="text-2xl font-bold text-white">{advice?.confidence}%</div>
                    <div className="text-xs uppercase text-gray-400">Confidence</div>
                </div>
            </div>

            {/* Kalman Trend */}
            <div className="bg-gray-800 p-4 rounded border border-gray-700">
                <h4 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                    <Activity className="w-5 h-5 text-blue-400" /> Kalman Filter Trend
                </h4>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <div className="text-xs text-gray-500 uppercase">Signal</div>
                        <div className="text-white font-mono text-lg">{kalman?.signal || 'N/A'}</div>
                    </div>
                    <div>
                        <div className="text-xs text-gray-500 uppercase">Trend Mean</div>
                        <div className="text-white font-mono">${kalman?.kalman_mean?.toFixed(2)}</div>
                    </div>
                </div>
            </div>

            {/* Markov Probabilities */}
            <div className="bg-gray-800 p-4 rounded border border-gray-700">
                <h4 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-pink-400" /> Markov Chain Probabilities
                </h4>
                <div className="mb-2 text-sm text-gray-400">
                    Current State: <span className="font-bold text-white">{markov?.current_state}</span>
                </div>
                {markov?.transitions && (
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                        {Object.entries(markov.transitions).map(([state, prob]) => (
                            <div key={state} className="bg-gray-900 p-2 rounded flex justify-between items-center">
                                <span className="text-gray-300 text-xs">{state}</span>
                                <span className={`font-mono font-bold ${state.includes('UP') ? 'text-green-400' : 'text-red-400'}`}>
                                    {(prob * 100).toFixed(1)}%
                                </span>
                            </div>
                        ))}
                    </div>
                )}
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

const PriceActionView = ({ data }) => {
    if (!data?.data || !data.data["Price Action"]) return <div className="text-center text-gray-400 py-12">No Price Action data available.</div>;
    const pa = data.data["Price Action"];
    const structure = pa.structure || [];
    const obs = pa.order_blocks || [];
    const fvgs = pa.fvgs || [];

    return (
        <div className="space-y-6">
            {/* Trend Header */}
            <div className={`p-4 rounded-lg border-l-4 ${pa.trend === 'Bullish' ? 'bg-green-900 border-green-500' : pa.trend === 'Bearish' ? 'bg-red-900 border-red-500' : 'bg-gray-800 border-gray-500'}`}>
                <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <Activity className="w-6 h-6" />
                    Trend: <span className={pa.trend === 'Bullish' ? 'text-green-300' : pa.trend === 'Bearish' ? 'text-red-300' : 'text-gray-300'}>{pa.trend}</span>
                </h3>
            </div>

            {/* Structure Points */}
            <div>
                <h4 className="text-lg font-bold text-white mb-3">Recent Market Structure</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {structure.slice(-4).reverse().map((s, i) => (
                        <div key={i} className="bg-gray-800 p-3 rounded text-center">
                            <div className={`text-sm font-bold ${s.label.includes('H') && !s.label.includes('L') ? 'text-green-400' : s.label.includes('L') && !s.label.includes('H') ? 'text-red-400' : 'text-blue-400'}`}>
                                {s.label}
                            </div>
                            <div className="text-white font-mono">${s.value}</div>
                            <div className="text-xs text-gray-500">{new Date(s.date).toLocaleDateString()}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Order Blocks */}
            <div>
                <h4 className="text-lg font-bold text-white mb-3">Order Blocks</h4>
                {obs.length > 0 ? (
                    <div className="space-y-2">
                        {obs.slice(-3).reverse().map((ob, i) => (
                            <div key={i} className={`flex justify-between items-center p-3 rounded bg-gray-800 border-l-2 ${ob.type === 'Bullish' ? 'border-green-500' : 'border-red-500'}`}>
                                <div>
                                    <div className={`font-bold ${ob.type === 'Bullish' ? 'text-green-400' : 'text-red-400'}`}>{ob.type} OB</div>
                                    <div className="text-xs text-gray-500">Origin of BOS at idx {ob.associated_bos_index}</div>
                                </div>
                                <div className="text-white font-mono text-sm">
                                    ${ob.bottom} - ${ob.top}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-gray-500 italic">No recent Order Blocks detected.</div>
                )}
            </div>

            {/* FVGs */}
            <div>
                <h4 className="text-lg font-bold text-white mb-3">Fair Value Gaps</h4>
                {fvgs.length > 0 ? (
                    <div className="space-y-2">
                        {fvgs.slice(-3).reverse().map((fvg, i) => (
                            <div key={i} className={`flex justify-between items-center p-3 rounded bg-gray-800 border-l-2 ${fvg.type === 'Bullish' ? 'border-green-500' : 'border-red-500'}`}>
                                <div>
                                    <div className={`font-bold ${fvg.type === 'Bullish' ? 'text-green-400' : 'text-red-400'}`}>{fvg.type} FVG</div>
                                    <div className="text-xs text-gray-500">{new Date(fvg.date).toLocaleDateString()}</div>
                                </div>
                                <div className="text-white font-mono text-sm">
                                    ${fvg.bottom} - ${fvg.top}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-gray-500 italic">No active FVG detected.</div>
                )}
            </div>
        </div>
    );
};

const SmartRollView = ({ data }) => {
    if (!data || data.length === 0) return <div className="text-center text-gray-400 py-12">No smart roll opportunities found.</div>;

    return (
        <div className="space-y-4">
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <RotateCcw className="w-6 h-6 text-indigo-400" />
                Smart Roll Suggestions
            </h3>
            <div className="grid grid-cols-1 gap-4">
                {data.map((roll, i) => {
                    const isClosePosition = roll.roll_type === "CLOSE POSITION";
                    const scoreColor = roll.score >= 80 ? 'bg-green-900 text-green-300' :
                        roll.score >= 50 ? 'bg-yellow-900 text-yellow-300' :
                            'bg-red-900 text-red-300';

                    const borderColor = isClosePosition ? 'border-red-500' : 'border-gray-700';
                    const bgClass = isClosePosition ? 'bg-red-900 bg-opacity-20' : 'bg-gray-800 hover:bg-gray-750';

                    return (
                        <div key={i} className={`${bgClass} p-4 rounded border ${borderColor} transition-colors`}>
                            <div className="flex justify-between items-start mb-2">
                                <div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-lg font-bold text-white">
                                            {isClosePosition ? "CLOSE POSITION (BTC)" : `${roll.strike} ${roll.type}`}
                                        </span>
                                        {!isClosePosition && (
                                            <span className="text-sm text-gray-400">
                                                Exp: {roll.expiration}
                                            </span>
                                        )}
                                        {isClosePosition && (
                                            <span className="px-2 py-0.5 rounded bg-red-600 text-white text-xs font-bold uppercase">
                                                Defensive
                                            </span>
                                        )}
                                    </div>
                                    <div className="text-sm text-indigo-300 mt-1">
                                        {isClosePosition ? (
                                            <span>Cost to Close: <span className="font-mono font-bold text-white">${roll.cost_to_close?.toFixed(2)}</span></span>
                                        ) : (
                                            <span>Net Credit: <span className="font-mono font-bold text-white">${roll.net_credit?.toFixed(2)}</span></span>
                                        )}
                                    </div>

                                    {!isClosePosition && (
                                        <div className="text-xs text-gray-500 mt-1 flex flex-wrap gap-2">
                                            <span title="Yield from Premium / Stock Price">Stat Yield: {roll.static_yield_pct}%</span>
                                            <span className="text-gray-600">|</span>
                                            <span title="Return if Stock rises to new Strike">Up Return: {roll.up_return_pct}%</span>
                                            <span className="text-gray-600">|</span>
                                            <span title="Total Potential Return (Premium + Cap Gain)">Total Yield: <span className="text-green-300 font-bold">{roll.total_yield_pct}%</span></span>
                                        </div>
                                    )}

                                    {/* Reasoning */}
                                    {roll.reasons && roll.reasons.length > 0 && (
                                        <div className="flex flex-wrap gap-1 mt-2">
                                            {roll.reasons.map((r, ri) => (
                                                <span key={ri} className={`px-1.5 py-0.5 rounded text-[10px] border ${r.includes("Risk") || r.includes("Penalty") ? "bg-red-900 text-red-300 border-red-700" : "bg-gray-700 text-gray-300 border-gray-600"}`}>
                                                    {r}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                                <div className={`
                                    px-3 py-1 rounded text-sm font-bold
                                    ${scoreColor}
                                `}>
                                    Score: {Math.round(roll.score)}
                                </div>
                            </div>

                            {/* Dividend Risk Warning */}
                            {roll.score <= 30 && (
                                <div className="mt-2 text-xs text-red-400 flex items-center gap-1">
                                    <AlertTriangle className="w-3 h-3" />
                                    High Assignment Risk / Low Efficiency
                                </div>
                            )}

                            <div className="mt-3 flex gap-2">
                                <button className={`flex-1 text-white text-xs py-2 rounded transition-colors ${isClosePosition ? 'bg-red-600 hover:bg-red-700' : 'bg-indigo-600 hover:bg-indigo-700'}`}>
                                    {isClosePosition ? "Execute Buy-To-Close" : "Execute Roll (Paper)"}
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

const ProfileView = ({ data, ticker }) => {
    const [descExpanded, setDescExpanded] = useState(false);
    const profile = data?.profile;

    if (!profile) return <div className="text-center text-gray-400 py-12">Profile data unavailable. Run Live Comparison to populate.</div>;

    const recColor = {
        strong_buy: 'bg-green-700 text-green-100',
        buy: 'bg-green-800 text-green-200',
        hold: 'bg-yellow-800 text-yellow-200',
        sell: 'bg-red-800 text-red-200',
        strong_sell: 'bg-red-700 text-red-100',
    }[profile.recommendation?.toLowerCase()] || 'bg-gray-700 text-gray-300';

    const fmtPct = (v) => v != null ? `${(v * 100).toFixed(1)}%` : '-';
    const fmtNum = (v, dec = 2) => v != null ? v.toFixed(dec) : '-';
    const fmtInt = (v) => v != null ? v.toLocaleString() : '-';

    const profileGrid = [
        ['Sector', profile.sector],
        ['Industry', profile.industry],
        ['Style / Type', [profile.style, profile.category].filter(Boolean).join(' · ') || null],
        ['Exchange', profile.exchange],
        ['Country', profile.country],
        ['Employees', profile.employees != null ? fmtInt(profile.employees) : null],
    ].filter(([, v]) => v);

    const fundamentals = [
        ['Beta', fmtNum(profile.beta)],
        ['Fwd P/E', fmtNum(profile.forward_pe)],
        ['Price/Book', fmtNum(profile.price_to_book)],
        ['ROE', fmtPct(profile.roe)],
        ['Debt/Equity', fmtNum(profile.debt_to_equity)],
        ['EPS Growth', fmtPct(profile.earnings_growth)],
        ['Rev Growth', fmtPct(profile.revenue_growth)],
        ['# Analysts', profile.analyst_opinions != null ? String(profile.analyst_opinions) : null],
    ].filter(([, v]) => v && v !== '-');

    return (
        <div className="space-y-5">
            {/* Quick links */}
            <div className="flex flex-wrap gap-2">
                <a
                    href={`https://finance.yahoo.com/quote/${ticker}/news/`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-3 py-1.5 bg-yellow-700 hover:bg-yellow-600 text-yellow-100 rounded text-sm font-medium transition-colors"
                >
                    Yahoo Finance News ↗
                </a>
                {profile.website && (
                    <a
                        href={profile.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded text-sm transition-colors"
                    >
                        {profile.website.replace(/^https?:\/\//, '')} ↗
                    </a>
                )}
            </div>

            {/* Profile identity grid */}
            {profileGrid.length > 0 && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {profileGrid.map(([label, value]) => (
                        <div key={label} className="bg-gray-800 rounded p-3">
                            <p className="text-xs text-gray-400 uppercase tracking-wider">{label}</p>
                            <p className="text-white font-medium mt-1 text-sm">{value}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* Analyst recommendation + fundamentals */}
            <div className="space-y-3">
                {profile.recommendation && (
                    <div className="flex items-center gap-3">
                        <span className={`px-3 py-1 rounded text-sm font-bold uppercase tracking-wider ${recColor}`}>
                            {profile.recommendation.replace('_', ' ')}
                        </span>
                        {profile.analyst_opinions != null && (
                            <span className="text-gray-400 text-sm">{profile.analyst_opinions} analyst opinions</span>
                        )}
                    </div>
                )}
                {fundamentals.length > 0 && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                        {fundamentals.map(([label, value]) => (
                            <div key={label} className="bg-gray-800 rounded p-2 text-center">
                                <p className="text-xs text-gray-400 uppercase tracking-wider">{label}</p>
                                <p className="text-white font-mono mt-0.5">{value}</p>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            {/* Description */}
            {profile.description && (
                <div className="bg-gray-800 rounded p-4">
                    <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">About</p>
                    <p className={`text-gray-300 text-sm leading-relaxed ${!descExpanded ? 'line-clamp-3' : ''}`}>
                        {profile.description}
                    </p>
                    <button
                        onClick={() => setDescExpanded(!descExpanded)}
                        className="text-teal-400 text-xs mt-2 hover:text-teal-300 transition-colors"
                    >
                        {descExpanded ? 'Show less ▲' : 'Show more ▼'}
                    </button>
                </div>
            )}

            {/* Recent news */}
            {profile.news && profile.news.length > 0 && (
                <div>
                    <h4 className="text-sm font-bold text-gray-300 uppercase tracking-wider mb-2">Recent News</h4>
                    <div className="space-y-2">
                        {profile.news.map((item, i) => (
                            <a
                                key={i}
                                href={item.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-start gap-2 p-3 bg-gray-800 rounded hover:bg-gray-750 transition-colors group"
                            >
                                <span className="text-teal-500 mt-0.5 flex-shrink-0">●</span>
                                <div className="min-w-0">
                                    <p className="text-gray-200 text-sm group-hover:text-white transition-colors leading-snug">
                                        {item.title}
                                    </p>
                                    <p className="text-gray-500 text-xs mt-0.5">
                                        {item.publisher}{item.published_at ? ` · ${item.published_at}` : ''}
                                    </p>
                                </div>
                            </a>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default TickerModal;
