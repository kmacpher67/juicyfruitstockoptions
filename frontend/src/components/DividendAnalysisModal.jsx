import React from 'react';
import { X, Check, TrendingUp, AlertTriangle, ArrowRight, DollarSign, Calendar } from 'lucide-react';

const DividendAnalysisModal = ({ isOpen, onClose, opportunity, onSelect }) => {
    const [strategies, setStrategies] = React.useState([]);
    const [holdings, setHoldings] = React.useState([]);
    const [rolls, setRolls] = React.useState([]);
    const [loading, setLoading] = React.useState(false);
    const [error, setError] = React.useState(null);

    React.useEffect(() => {
        if (isOpen && opportunity) {
            fetchAnalysis();
        }
    }, [isOpen, opportunity]);

    const fetchAnalysis = async () => {
        setLoading(true);
        setError(null);
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`/api/analysis/dividend-capture/${opportunity.symbol}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) throw new Error("Failed to fetch analysis");
            const data = await res.json();
            // Handle both legacy (list) and new (dict) response
            if (Array.isArray(data)) {
                setStrategies(data);
                setHoldings([]);
                setRolls([]);
            } else {
                setStrategies(data.strategies || []);
                setHoldings(data.holdings_context || []);
                setRolls(data.rolls || []);
            }
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (!isOpen || !opportunity) return null;

    const handleSelect = (strategy) => {
        onSelect({ ...opportunity, strategyDetails: strategy });
        onClose();
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 z-[60] flex items-center justify-center p-4">
            <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-5xl h-[85vh] flex flex-col border border-gray-700 relative animate-in fade-in zoom-in duration-200">

                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-800 bg-gray-850 rounded-t-lg">
                    <div className="flex items-center gap-3">
                        <div className="bg-green-900/50 p-2 rounded-lg border border-green-700">
                            <TrendingUp className="w-6 h-6 text-green-300" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                                Dividend Capture Analysis
                                <span className="text-sm font-mono bg-gray-800 px-2 py-0.5 rounded text-gray-400 border border-gray-700">
                                    {opportunity.symbol}
                                </span>
                            </h2>
                            <p className="text-sm text-gray-400">Select a Buy-Write strategy to execute.</p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto custom-scrollbar flex-1">

                    {/* Holdings Context */}
                    {holdings.length > 0 && (
                        <div className="mb-6 bg-gray-800/50 p-4 rounded border border-gray-700">
                            <h4 className="text-sm font-bold text-gray-400 mb-2 uppercase flex items-center gap-2">
                                <DollarSign className="w-4 h-4" /> Current Positions
                            </h4>
                            <div className="flex flex-wrap gap-4">
                                {holdings.map((h, i) => (
                                    <div key={i} className="bg-gray-900 px-3 py-1.5 rounded border border-gray-600 text-sm">
                                        <span className="text-gray-400 mr-2">{h.account}:</span>
                                        <span className={`font-mono font-bold ${h.quantity > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                            {h.quantity} {h.asset_class}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {loading ? (
                        <div className="flex items-center justify-center h-40">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-500"></div>
                        </div>
                    ) : error ? (
                        <div className="text-red-400 text-center p-8 bg-red-900/20 rounded border border-red-800">
                            {error} <br /> <button onClick={() => fetchAnalysis()} className="underline mt-2">Retry</button>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            {strategies.map((strat, idx) => (
                                <div key={idx} className="bg-gray-800 rounded-lg border border-gray-700 hover:border-green-600 transition-colors flex flex-col shadow-lg overflow-hidden group">
                                    <div className={`p-4 border-b border-gray-700 font-bold text-lg flex justify-between items-center
                                        ${strat.type === 'Protective' ? 'bg-blue-900/20 text-blue-300' :
                                            strat.type === 'Balanced' ? 'bg-green-900/20 text-green-300' : 'bg-orange-900/20 text-orange-300'}`}>
                                        {strat.type}
                                        <span className="text-xs px-2 py-0.5 rounded bg-gray-900 text-gray-300 border border-gray-600">
                                            {strat.type === 'Protective' ? 'ITM' : strat.type === 'Balanced' ? 'ATM' : 'OTM'}
                                        </span>
                                    </div>

                                    <div className="p-5 space-y-4 flex-1">
                                        <div className="flex justify-between items-end border-b border-gray-700 pb-3">
                                            <div>
                                                <div className="text-xs text-gray-400">Strike / Exp</div>
                                                <div className="text-xl font-mono text-white">${strat.strike}</div>
                                                <div className="text-xs text-gray-500">{strat.expiry}</div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-xs text-gray-400">Max Return</div>
                                                <div className="text-2xl font-bold text-green-400">+{strat.max_return}%</div>
                                            </div>
                                        </div>

                                        <div className="grid grid-cols-2 gap-2 text-sm">
                                            <div>
                                                <div className="text-gray-500 text-xs">Net Cost</div>
                                                <div className="font-mono text-gray-300">${strat.net_cost}</div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-gray-500 text-xs">Breakeven</div>
                                                <div className="font-mono text-yellow-300">${strat.breakeven}</div>
                                            </div>
                                            <div>
                                                <div className="text-gray-500 text-xs">Downside Prot.</div>
                                                <div className="font-mono text-gray-300">{strat.downside_protection}%</div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-gray-500 text-xs">Premium</div>
                                                <div className="font-mono text-green-300">${strat.premium}</div>
                                            </div>
                                        </div>
                                    </div>

                                    <div className="p-4 bg-gray-800/50 border-t border-gray-700">
                                        <button
                                            onClick={() => handleSelect(strat)}
                                            className="w-full py-2 bg-gray-700 hover:bg-green-600 text-white rounded font-bold transition-colors group-hover:shadow-lg"
                                        >
                                            <span className="flex items-center justify-center gap-2">
                                                Select <ArrowRight className="w-4 h-4" />
                                            </span>
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Available Rolls */}
                    {!loading && rolls.length > 0 && (
                        <div className="mt-8">
                            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                                <TrendingUp className="w-5 h-5 text-purple-400" />
                                Available Smart Rolls
                            </h3>
                            <div className="grid grid-cols-1 gap-3">
                                {rolls.map((roll, idx) => (
                                    <div key={idx} className="bg-gray-800 p-4 rounded border border-gray-700 flex justify-between items-center">
                                        <div>
                                            <div className="text-sm font-bold text-gray-200">
                                                Roll {roll.current_strike} ({roll.current_expiry}) <ArrowRight className="inline w-3 h-3 text-gray-500 mx-1" /> {roll.new_strike} ({roll.new_expiry})
                                            </div>
                                            <div className="text-xs text-gray-400 mt-1">
                                                Credit: <span className="text-green-400">${roll.net_credit}</span> • Score: {roll.score}
                                            </div>
                                        </div>
                                        <button className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-xs rounded text-white border border-gray-600">
                                            Analyze
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {!loading && strategies.length === 0 && rolls.length === 0 && !error && (
                        <div className="text-gray-500 text-center p-10">
                            No strategies or rolls found suitable for this ticker.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DividendAnalysisModal;
