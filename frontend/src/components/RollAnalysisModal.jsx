import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { X, RotateCcw, TrendingUp, AlertTriangle, ArrowRight, Info, Check, Clock, PauseCircle, Ban } from 'lucide-react';

const RollAnalysisModal = ({ isOpen, onClose, opportunity }) => {
    const [loading, setLoading] = useState(false);
    const [rollData, setRollData] = useState(null);
    const [error, setError] = useState(null);
    const [toast, setToast] = useState(null); // { message, type: 'success'|'error' }

    useEffect(() => {
        if (isOpen && opportunity) {
            fetchRollAnalysis();
        } else {
            setRollData(null);
            setError(null);
            setToast(null);
        }
    }, [isOpen, opportunity]);

    // Clear toast after 3s
    useEffect(() => {
        if (toast) {
            const timer = setTimeout(() => setToast(null), 3000);
            return () => clearTimeout(timer);
        }
    }, [toast]);

    const fetchRollAnalysis = async () => {
        setLoading(true);
        setError(null);
        try {
            const type = opportunity.context?.right || opportunity.proposal?.right || 'call';
            const payload = {
                symbol: opportunity.symbol,
                strike: parseFloat(opportunity.proposal?.strike || opportunity.context?.strike || 0),
                expiration: opportunity.proposal?.expiry || opportunity.context?.expiry,
                position_type: type.toLowerCase()
            };

            const res = await api.post('/analysis/roll', payload);
            setRollData(res.data);
        } catch (err) {
            console.error("Roll Analysis Failed:", err);
            setError(err.response?.data?.detail || "Failed to analyze rolls");
        } finally {
            setLoading(false);
        }
    };

    const handleSelectRoll = (roll) => {
        console.log("Selected Roll:", roll);
        setToast({ message: `Roll Selected: ${roll.expiration} @ $${roll.strike}`, type: 'success' });
        // Future: Save to TradePlan or trigger IBKR execution
    };

    const getYieldMetrics = (roll, currentPrice) => {
        // Simple Yield: Net Credit / Strike (assuming Covered Call)
        // If it's a spread or put, logic might vary, but this is a good baseline proxy for "ROIC" on the roll
        const netCredit = roll.net_credit || 0;
        const strike = roll.strike || 1;
        const yieldPct = (netCredit / strike) * 100;

        // Annualized: Yield * (365 / Days Extended)
        // Guard against zero days
        const days = roll.days_extended > 0 ? roll.days_extended : 7;
        const annualized = yieldPct * (365 / days);

        // Protection: Net Credit / Current Price (How much buffer?)
        const protection = currentPrice ? (netCredit / currentPrice) * 100 : 0;

        // Breakeven
        const breakeven = strike - netCredit;

        return {
            yieldPct: yieldPct.toFixed(2),
            annualized: annualized.toFixed(1),
            protection: protection.toFixed(2),
            breakeven: breakeven.toFixed(2)
        };
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 z-[60] flex items-center justify-center p-4">
            <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] flex flex-col border border-gray-700 relative">

                {/* Toast Notification */}
                {toast && (
                    <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-50 bg-green-600 text-white px-4 py-2 rounded shadow-lg flex items-center gap-2 animate-bounce">
                        <Check className="w-4 h-4" />
                        {toast.message}
                    </div>
                )}

                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-800 bg-gray-850 rounded-t-lg">
                    <div className="flex items-center gap-3">
                        <div className="bg-indigo-900/50 p-2 rounded-lg border border-indigo-700">
                            <RotateCcw className="w-6 h-6 text-indigo-300" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                                Smart Roll Analysis
                                <span className="text-sm font-mono bg-gray-800 px-2 py-0.5 rounded text-gray-400 border border-gray-700">
                                    {opportunity?.symbol}
                                </span>
                            </h2>
                            {/* Original Position Details (Header Context) */}
                            <div className="text-sm text-gray-400 flex flex-wrap items-center gap-x-4 mt-1">
                                <div className="flex items-center gap-1">
                                    <span>Origin:</span>
                                    <span className="text-white font-mono font-bold">
                                        {opportunity?.proposal?.expiry} | {opportunity?.proposal?.strike} {opportunity?.context?.right || 'C'}
                                    </span>
                                </div>
                                {opportunity?.context?.unrealized_pnl && (
                                    <div className="flex items-center gap-1">
                                        <span>Unrealized P/L:</span>
                                        <span className={`font-mono font-bold ${opportunity.context.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            ${opportunity.context.unrealized_pnl}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto flex-1 bg-gray-900 custom-scrollbar">
                    {loading ? (
                        <div className="flex flex-col items-center justify-center h-64 gap-4">
                            <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                            <p className="text-gray-400 animate-pulse">Calculating Optimal Rolls & Scenarios...</p>
                        </div>
                    ) : error ? (
                        <div className="flex flex-col items-center justify-center h-64 text-red-400 gap-2">
                            <AlertTriangle className="w-8 h-8" />
                            <p>{error}</p>
                            <button onClick={fetchRollAnalysis} className="text-sm underline hover:text-red-300">Retry</button>
                        </div>
                    ) : rollData ? (
                        <div className="space-y-6">

                            {/* Market Context Bar */}
                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                                <div className="bg-gray-800 p-3 rounded border border-gray-700">
                                    <div className="text-xs text-gray-400 uppercase">Underlying Price</div>
                                    <div className="text-lg font-mono text-white">${rollData.current_price?.toFixed(2)}</div>
                                </div>
                                <div className="bg-gray-800 p-3 rounded border border-gray-700">
                                    <div className="text-xs text-gray-400 uppercase">1D Change</div>
                                    <div className={`text-lg font-mono ${rollData.one_day_change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        {rollData.one_day_change > 0 && '+'}{rollData.one_day_change}%
                                    </div>
                                </div>
                                <div className="bg-gray-800 p-3 rounded border border-gray-700">
                                    <div className="text-xs text-gray-400 uppercase">Cost to Close (BTC)</div>
                                    <div className="text-lg font-mono text-red-300">-${rollData.cost_to_close?.toFixed(2)}</div>
                                </div>
                                <div className="bg-gray-800 p-3 rounded border border-gray-700 flex flex-col justify-center">
                                    <div className="text-xs text-gray-500 italic">Strategy Goal: Net Credit using Diagonal or Calendar Rolls</div>
                                </div>
                            </div>

                            {/* Suggestions List */}
                            <div>
                                <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                    <TrendingUp className="w-5 h-5 text-green-400" />
                                    Recommended Rolls
                                </h3>

                                {rollData.rolls && rollData.rolls.length > 0 ? (
                                    <div className="space-y-3">
                                        <div className="text-xs text-gray-500 mb-2 flex gap-2 items-center">
                                            <Info className="w-3 h-3" />
                                            <span>Sequence: <strong>Buy to Close</strong> existing position + <strong>Sell to Open</strong> new position = <strong>Net Credit</strong> shown.</span>
                                        </div>

                                        {rollData.rolls.map((roll, idx) => {
                                            const metrics = getYieldMetrics(roll, rollData.current_price);
                                            return (
                                                <div key={idx} className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-indigo-500 transition-colors group">
                                                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">

                                                        {/* Left: Roll Details */}
                                                        <div className="flex-1">
                                                            <div className="flex items-center gap-3 mb-2">
                                                                <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wide border
                                                                    ${roll.roll_type === 'Up & Out' ? 'bg-green-900/50 border-green-700 text-green-300' :
                                                                        roll.net_credit > 0 ? 'bg-blue-900/50 border-blue-700 text-blue-300' :
                                                                            'bg-gray-700 border-gray-600 text-gray-300'}`}>
                                                                    {roll.roll_type}
                                                                </span>
                                                                <div className="flex items-center gap-2 font-mono text-white text-lg">
                                                                    <span className="font-bold">{roll.expiration}</span>
                                                                    <span className="text-gray-500">@</span>
                                                                    <span className="font-bold text-yellow-300">${roll.strike}</span>
                                                                </div>
                                                            </div>

                                                            <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-2 text-sm text-gray-300">
                                                                <div className="flex flex-col">
                                                                    <span className="text-[10px] text-gray-500 uppercase">Net Credit</span>
                                                                    <span className={`font-mono font-bold text-base ${roll.net_credit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                        {roll.net_credit >= 0 ? '+' : ''}{roll.net_credit.toFixed(2)}
                                                                    </span>
                                                                </div>
                                                                <div className="flex flex-col" title={`Annualized: ${metrics.annualized}%`}>
                                                                    <span className="text-[10px] text-gray-500 uppercase">Yield (Roll)</span>
                                                                    <span className="font-mono text-green-300">{metrics.yieldPct}%</span>
                                                                    <span className="text-[10px] text-gray-600">Ann: {metrics.annualized}%</span>
                                                                </div>
                                                                <div className="flex flex-col">
                                                                    <span className="text-[10px] text-gray-500 uppercase">Breakeven</span>
                                                                    <span className="font-mono">${metrics.breakeven}</span>
                                                                </div>
                                                                <div className="flex flex-col">
                                                                    <span className="text-[10px] text-gray-500 uppercase">Time Ext.</span>
                                                                    <span className="flex items-center gap-1">
                                                                        <RotateCcw className="w-3 h-3" /> +{roll.days_extended}d
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        </div>

                                                        {/* Right: Score & Action */}
                                                        <div className="flex items-center gap-4 border-l border-gray-700 pl-4">
                                                            <div className="text-center min-w-[60px]">
                                                                <div className={`text-2xl font-bold leading-none ${roll.score >= 80 ? 'text-green-400' :
                                                                    roll.score >= 50 ? 'text-yellow-400' : 'text-red-400'
                                                                    }`}>
                                                                    {Math.round(roll.score)}
                                                                </div>
                                                                <div className="text-[10px] text-gray-500 uppercase font-bold">Score</div>
                                                            </div>

                                                            <button
                                                                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-sm font-medium transition-colors flex items-center gap-2 whitespace-nowrap"
                                                                onClick={() => handleSelectRoll(roll)}
                                                            >
                                                                Select <ArrowRight className="w-4 h-4" />
                                                            </button>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        <div className="text-center py-8 bg-gray-800/50 rounded-lg border border-gray-700 border-dashed">
                                            <p className="text-gray-400 mb-2">No suitable rolls found matching criteria.</p>
                                            <p className="text-xs text-gray-500">Consider alternative actions:</p>
                                        </div>

                                        {/* Alternative Action Cards */}
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                            <div className="bg-gray-800 p-4 rounded border border-gray-700 hover:bg-gray-750 cursor-pointer transition-colors"
                                                onClick={() => setToast({ message: "Wait action logged.", type: "success" })}>
                                                <div className="flex items-center gap-2 mb-2">
                                                    <Clock className="w-5 h-5 text-blue-400" />
                                                    <h4 className="font-bold text-blue-100">Wait</h4>
                                                </div>
                                                <p className="text-xs text-gray-400">Time decay (Theta) accelerates in the final 7 days. Monitor for price improvement.</p>
                                            </div>

                                            <div className="bg-gray-800 p-4 rounded border border-gray-700 hover:bg-gray-750 cursor-pointer transition-colors"
                                                onClick={() => setToast({ message: "Hold action logged.", type: "success" })}>
                                                <div className="flex items-center gap-2 mb-2">
                                                    <PauseCircle className="w-5 h-5 text-yellow-400" />
                                                    <h4 className="font-bold text-yellow-100">Hold</h4>
                                                </div>
                                                <p className="text-xs text-gray-400">If OTM, let it expire worthless to keep full premium. Risk: Assignment if ITM.</p>
                                            </div>

                                            <div className="bg-gray-800 p-4 rounded border border-gray-700 hover:bg-gray-750 cursor-pointer transition-colors"
                                                onClick={() => setToast({ message: "Close action logged.", type: "success" })}>
                                                <div className="flex items-center gap-2 mb-2">
                                                    <Ban className="w-5 h-5 text-red-400" />
                                                    <h4 className="font-bold text-red-100">Close</h4>
                                                </div>
                                                <p className="text-xs text-gray-400">Buy to Close (BTC) now to lock in partial profit or limit loss. Cost: ${rollData.cost_to_close?.toFixed(2)}</p>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : null}
                </div>
            </div>
        </div>
    );
};

export default RollAnalysisModal;
