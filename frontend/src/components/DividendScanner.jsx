import React, { useEffect, useState } from 'react';

const DividendScanner = () => {
    const [opportunities, setOpportunities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);

    const fetchOpps = async (force = false) => {
        if (force) setRefreshing(true);
        try {
            const token = localStorage.getItem('token');
            const url = force
                ? '/api/analysis/dividend-capture?force_scan=true'
                : '/api/analysis/dividend-capture';

            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch dividend opportunities');
            }

            const data = await response.json();
            setOpportunities(data);
            setLastUpdated(new Date());
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        fetchOpps();
    }, []);

    if (loading && !opportunities.length) return <div className="p-4 text-gray-300">Loading Opportunities...</div>;
    if (error) return <div className="p-4 text-red-400">Error: {error}</div>;
    if (opportunities.length === 0 && !loading && !refreshing) return null;

    return (
        <div className="bg-gray-800 rounded-lg p-6 mb-6 shadow-lg border border-gray-700">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-green-400 flex items-center gap-2">
                    <span className="text-2xl">💰</span> Dividend Capture Opportunities
                </h2>
                <div className="flex items-center gap-4">
                    {lastUpdated && <span className="text-xs text-gray-500">Updated: {lastUpdated.toLocaleTimeString()}</span>}
                    <button
                        onClick={() => fetchOpps(true)}
                        disabled={refreshing}
                        className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm flex items-center gap-2 disabled:opacity-50"
                    >
                        {refreshing && <svg className="animate-spin h-4 w-4 text-white" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>}
                        {refreshing ? 'Scanning...' : 'Refresh'}
                    </button>
                </div>
            </div>

            <div className="overflow-x-auto">
                <table className="min-w-full bg-gray-900 rounded-lg overflow-hidden">
                    <thead className="bg-gray-800 text-gray-300">
                        <tr>
                            <th className="px-4 py-3 text-left">Ticker</th>
                            <th className="px-4 py-3 text-left">Ex-Date</th>
                            <th className="px-4 py-3 text-right">Est. Div</th>
                            <th className="px-4 py-3 text-right">Yield (Ann)</th>
                            <th className="px-4 py-3 text-right">Price</th>
                            <th className="px-4 py-3 text-center">Score</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                        {opportunities.map((opp, idx) => (
                            <tr key={idx} className="hover:bg-gray-700 transition-colors">
                                <td className="px-4 py-3 font-semibold text-white">{opp.symbol}</td>
                                <td className="px-4 py-3 text-yellow-300">{opp.ex_date}</td>
                                <td className="px-4 py-3 text-right text-green-300">${opp.dividend_amount?.toFixed(2)}</td>
                                <td className="px-4 py-3 text-right">{opp.yield_annual}%</td>
                                <td className="px-4 py-3 text-right">${opp.current_price?.toFixed(2)}</td>
                                <td className="px-4 py-3 text-center">
                                    <span className="bg-green-900 text-green-200 py-1 px-2 rounded text-xs">
                                        {opp.score}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <p className="text-xs text-gray-500 mt-2 italic">
                * Strategy: Buy Stock provided covered call premium + dividend &gt; risk.
            </p>
        </div>
    );
};

export default DividendScanner;
