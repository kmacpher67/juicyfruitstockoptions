import React, { useState, useEffect } from 'react';
import api from '../api/axios';
import { X, RotateCcw, TrendingUp, AlertTriangle, ArrowRight, DollarSign } from 'lucide-react';

const RollAnalysisModal = ({ isOpen, onClose, opportunity }) => {
    const [loading, setLoading] = useState(false);
    const [rollData, setRollData] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen && opportunity) {
            fetchRollAnalysis();
        } else {
            setRollData(null);
            setError(null);
        }
    }, [isOpen, opportunity]);

    const fetchRollAnalysis = async () => {
        setLoading(true);
        setError(null);
        try {
            // Infer type from opportunity context or default to Call
            // If opportunity came from ExpirationScanner, we might not have 'right' explicitly in proposal
            // We'll default to 'call' but maybe we should try to detect
            // TODO: Enhance ExpirationScanner to pass 'right' (C/P)
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

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 z-[60] flex items-center justify-center p-4">
            <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col border border-gray-700">

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
                            <div className="text-sm text-gray-400 flex items-center gap-2 mt-1">
                                <span>Current:</span>
                                <span className="text-white font-mono font-bold">
                                    {opportunity?.proposal?.expiry} | {opportunity?.proposal?.strike}
                                </span>
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
                            <p className="text-gray-400 animate-pulse">Calculating Optimal Rolls...</p>
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
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
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
                                    <div className="text-xs text-gray-400 uppercase">Cost to Close</div>
                                    <div className="text-lg font-mono text-red-300">-${rollData.cost_to_close?.toFixed(2)}</div>
                                </div>
                                <div className="bg-gray-800 p-3 rounded border border-gray-700 flex flex-col justify-center">
                                    <div className="text-xs text-gray-500 italic">Target: Net Credit or Strike Imp.</div>
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
                                        {rollData.rolls.map((roll, idx) => (
                                            <div key={idx} className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-indigo-500 transition-colors group">
                                                <div className="flex items-center justify-between">

                                                    {/* Left: Roll Details */}
                                                    <div className="flex-1">
                                                        <div className="flex items-center gap-3 mb-1">
                                                            <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wide border
                                                                ${roll.roll_type === 'Up & Out' ? 'bg-green-900/50 border-green-700 text-green-300' :
                                                                    roll.net_credit > 0 ? 'bg-blue-900/50 border-blue-700 text-blue-300' :
                                                                        'bg-gray-700 border-gray-600 text-gray-300'}`}>
                                                                {roll.roll_type}
                                                            </span>
                                                            <div className="flex items-center gap-2 font-mono text-white">
                                                                <span className="font-bold">{roll.expiration}</span>
                                                                <span className="text-gray-500">@</span>
                                                                <span className="font-bold text-yellow-300">${roll.strike}</span>
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center gap-4 text-xs text-gray-400 mt-2">
                                                            <span title="Net Credit/Debit">
                                                                Net: <span className={`font-mono font-bold text-base ${roll.net_credit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                                    {roll.net_credit >= 0 ? '+' : ''}{roll.net_credit.toFixed(2)}
                                                                </span>
                                                            </span>
                                                            <span title="Days Extended" className="flex items-center gap-1">
                                                                <RotateCcw className="w-3 h-3" /> +{roll.days_extended} Days
                                                            </span>
                                                            {roll.delta && <span>Delta: {roll.delta.toFixed(2)}</span>}
                                                        </div>
                                                    </div>

                                                    {/* Right: Score & Action */}
                                                    <div className="flex items-center gap-4">

                                                        {/* Score Badge */}
                                                        <div className="text-center">
                                                            <div className={`text-2xl font-bold leading-none ${roll.score >= 80 ? 'text-green-400' :
                                                                    roll.score >= 50 ? 'text-yellow-400' : 'text-red-400'
                                                                }`}>
                                                                {Math.round(roll.score)}
                                                            </div>
                                                            <div className="text-[10px] text-gray-500 uppercase font-bold">Score</div>
                                                        </div>

                                                        <button
                                                            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-sm font-medium transition-colors flex items-center gap-2"
                                                            onClick={() => console.log("Selected Roll:", roll)}
                                                        >
                                                            Select <ArrowRight className="w-4 h-4" />
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-12 text-gray-500">
                                        No suitable rolls found for this position.
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
