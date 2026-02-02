import React, { useEffect, useState } from 'react';

const DividendScanner = () => {
    const [opportunities, setOpportunities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchOpps = async () => {
            try {
                const token = localStorage.getItem('token');
                const response = await fetch('/api/analysis/dividend-capture', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch dividend opportunities');
                }

                const data = await response.json();
                setOpportunities(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchOpps();
    }, []);

    if (loading) return <div className="p-4 text-gray-300">Scanning for Dividend Capture Opportunities...</div>;
    if (error) return <div className="p-4 text-red-400">Error: {error}</div>;
    if (opportunities.length === 0) return null; // Hide if empty

    return (
        <div className="bg-gray-800 rounded-lg p-6 mb-6 shadow-lg border border-gray-700">
            <h2 className="text-xl font-bold text-green-400 mb-4 flex items-center gap-2">
                <span className="text-2xl">💰</span> Dividend Capture Opportunities
            </h2>
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
