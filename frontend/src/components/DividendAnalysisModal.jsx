import React from 'react';
import { X, Check, TrendingUp, AlertTriangle, ArrowRight, DollarSign, Calendar } from 'lucide-react';

const DividendAnalysisModal = ({ isOpen, onClose, opportunity, onSelect }) => {
    if (!isOpen || !opportunity) return null;

    const handleSelect = () => {
        onSelect(opportunity);
        onClose();
    };

    const exDate = new Date(opportunity.ex_date).toLocaleDateString();

    // Calculate basic metrics if not pre-calculated
    const dividend = opportunity.dividend_amount || 0;
    const price = opportunity.current_price || 0;
    const yieldPct = opportunity.yield_annual || ((dividend * 4) / price * 100).toFixed(2);
    const score = opportunity.score || 0;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 z-[60] flex items-center justify-center p-4">
            <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-2xl flex flex-col border border-gray-700 relative animate-in fade-in zoom-in duration-200">

                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-800 bg-gray-850 rounded-t-lg">
                    <div className="flex items-center gap-3">
                        <div className="bg-green-900/50 p-2 rounded-lg border border-green-700">
                            <DollarSign className="w-6 h-6 text-green-300" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                                Dividend Capture
                                <span className="text-sm font-mono bg-gray-800 px-2 py-0.5 rounded text-gray-400 border border-gray-700">
                                    {opportunity.symbol}
                                </span>
                            </h2>
                            <div className="text-sm text-gray-400 mt-1">
                                Target Ex-Date: <span className="text-yellow-300 font-bold">{exDate}</span>
                            </div>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6">
                    {/* Metrics Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div className="bg-gray-800 p-3 rounded border border-gray-700">
                            <div className="text-xs text-gray-400 uppercase">Dividend</div>
                            <div className="text-xl font-mono text-green-400">${dividend.toFixed(2)}</div>
                        </div>
                        <div className="bg-gray-800 p-3 rounded border border-gray-700">
                            <div className="text-xs text-gray-400 uppercase">Yield (Ann)</div>
                            <div className="text-xl font-mono text-white">{yieldPct}%</div>
                        </div>
                        <div className="bg-gray-800 p-3 rounded border border-gray-700">
                            <div className="text-xs text-gray-400 uppercase">Stock Price</div>
                            <div className="text-xl font-mono text-white">${price.toFixed(2)}</div>
                        </div>
                        <div className="bg-gray-800 p-3 rounded border border-gray-700">
                            <div className="text-xs text-gray-400 uppercase">Score</div>
                            <div className={`text-xl font-bold ${score >= 80 ? 'text-green-400' : score >= 50 ? 'text-yellow-400' : 'text-gray-400'}`}>
                                {score}
                            </div>
                        </div>
                    </div>

                    {/* Strategy Description */}
                    <div className="bg-gray-800/50 p-4 rounded border border-gray-700">
                        <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-blue-400" />
                            Strategy: Buy-Write / Capture
                        </h3>
                        <p className="text-sm text-gray-300 leading-relaxed">
                            Start a Buy-Write position or Buy shares to capture the upcoming dividend of <strong>${dividend.toFixed(2)}</strong>.
                            Ensure holding period requirements are met for qualified taxation if applicable.
                        </p>
                        {score < 50 && (
                            <div className="mt-3 flex items-start gap-2 text-yellow-500 text-xs bg-yellow-900/20 p-2 rounded">
                                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                                <span>Caution: Low score suggests high risk or low efficiency for this capture. Check liquidity and downside risk.</span>
                            </div>
                        )}
                    </div>

                    {/* Action Footer */}
                    <div className="flex justify-end pt-4 border-t border-gray-800">
                        <button
                            onClick={handleSelect}
                            className="px-6 py-3 bg-green-600 hover:bg-green-700 text-white rounded font-bold transition-colors flex items-center gap-2 shadow-lg shadow-green-900/20"
                        >
                            Select Strategy <ArrowRight className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DividendAnalysisModal;
