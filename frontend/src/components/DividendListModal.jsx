import React from 'react';
import { X, Calendar, DollarSign, ChevronRight, Download } from 'lucide-react';
import api from '../api/axios'; // Or standard fetch, aligning with project

const DividendListModal = ({ isOpen, onClose, opportunities, onSelectOpportunity }) => {
    const [sortField, setSortField] = React.useState('ex_date');
    const [sortDirection, setSortDirection] = React.useState('asc');

    if (!isOpen) return null;

    const handleSort = (field) => {
        if (sortField === field) {
            setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
        } else {
            setSortField(field);
            setSortDirection('asc');
        }
    };

    const sortedOpportunities = [...opportunities].sort((a, b) => {
        let valA = a[sortField];
        let valB = b[sortField];

        // Handle string vs number sorting
        if (typeof valA === 'string') valA = valA.toLowerCase();
        if (typeof valB === 'string') valB = valB.toLowerCase();

        // Handle Dates
        if (sortField === 'ex_date') {
            valA = new Date(a.ex_date).getTime();
            valB = new Date(b.ex_date).getTime();
        }

        if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
        if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
        return 0;
    });

    const handleDownloadICS = async () => {
        try {
            const response = await api.get('/calendar/dividends.ics', { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'dividends.ics');
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (error) {
            console.error("Download failed:", error);
        }
    };

    const SortIcon = ({ field }) => {
        if (sortField !== field) return <span className="opacity-20 ml-1">↕</span>;
        return <span className="ml-1 text-blue-400">{sortDirection === 'asc' ? '↑' : '↓'}</span>;
    };

    const Th = ({ field, children, align = 'left' }) => (
        <th
            className={`px-4 py-3 font-semibold cursor-pointer hover:text-white transition-colors text-${align}`}
            onClick={() => handleSort(field)}
        >
            <div className={`flex items-center justify-${align === 'right' ? 'end' : align === 'center' ? 'center' : 'start'}`}>
                {children} <SortIcon field={field} />
            </div>
        </th>
    );

    return (
        <div className="fixed inset-0 bg-black bg-opacity-75 z-[50] flex items-center justify-center p-4">
            <div className="bg-gray-900 rounded-lg shadow-xl w-full max-w-6xl h-[85vh] flex flex-col border border-gray-700 animate-in fade-in zoom-in duration-200">

                {/* Header */}
                <div className="flex justify-between items-center p-6 border-b border-gray-800 bg-gray-850 rounded-t-lg">
                    <div className="flex items-center gap-3">
                        <div className="bg-blue-900/50 p-2 rounded-lg border border-blue-700">
                            <Calendar className="w-6 h-6 text-blue-300" />
                        </div>
                        <div>
                            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                                Dividend Feed
                                <span className="text-sm bg-gray-800 px-2 py-0.5 rounded text-gray-400 border border-gray-700 rounded-full">
                                    {opportunities.length} Found
                                </span>
                            </h2>
                            <p className="text-sm text-gray-400">Analyze & Capture upcoming dividends. Sortable feed.</p>
                        </div>
                    </div>
                    <div className="flex gap-4">
                        <button
                            onClick={handleDownloadICS}
                            className="bg-gray-800 hover:bg-gray-700 text-gray-300 px-4 py-2 rounded flex items-center gap-2 text-sm border border-gray-600 transition-colors"
                        >
                            <Download className="w-4 h-4" /> Export ICS
                        </button>
                        <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                            <X className="w-6 h-6" />
                        </button>
                    </div>
                </div>

                {/* Table Content */}
                <div className="p-0 overflow-y-auto flex-1 custom-scrollbar">
                    {opportunities.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-gray-500">
                            <Calendar className="w-12 h-12 mb-4 opacity-20" />
                            <p>No upcoming dividend opportunities found.</p>
                        </div>
                    ) : (
                        <table className="w-full text-left border-collapse">
                            <thead className="bg-gray-800/50 sticky top-0 backdrop-blur-sm z-10">
                                <tr className="text-xs uppercase text-gray-400 border-b border-gray-700">
                                    <Th field="ex_date">Ex-Date</Th>
                                    <Th field="symbol">Ticker</Th>
                                    <Th field="accounts_held">Holdings</Th>
                                    <Th field="current_price" align="right">Price</Th>
                                    <Th field="predicted_price" align="right">Pred</Th>
                                    <Th field="analyst_target" align="right">Target</Th>
                                    <Th field="dividend_amount" align="right">Div</Th>
                                    <Th field="return_pct" align="right">Return</Th>
                                    <Th field="yield_annual" align="right">Yield</Th>
                                    <Th field="days_to_ex" align="center">Days</Th>
                                    <Th field="score" align="center">Score</Th>
                                    <th className="px-4 py-3"></th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-800">
                                {sortedOpportunities.map((opp, idx) => (
                                    <tr
                                        key={idx}
                                        onClick={() => onSelectOpportunity(opp)}
                                        className="hover:bg-gray-800/50 cursor-pointer transition-colors group"
                                    >
                                        <td className="px-4 py-3 text-yellow-300 font-mono text-sm whitespace-nowrap">
                                            {opp.ex_date}
                                        </td>
                                        <td className="px-4 py-3 font-bold text-white text-base">
                                            <a
                                                href={`https://finance.yahoo.com/quote/${opp.symbol}`}
                                                target="_blank"
                                                rel="noopener noreferrer"
                                                className="hover:text-green-400 hover:underline"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                {opp.symbol}
                                            </a>
                                        </td>
                                        <td className="px-4 py-3">
                                            {opp.accounts_held && opp.accounts_held !== '-' ? (
                                                <div className="flex flex-col gap-0.5">
                                                    {opp.accounts_held.split(',').map((h, i) => (
                                                        <div key={i} className="text-[10px] font-mono text-cyan-300 leading-tight whitespace-nowrap">
                                                            {h.trim()}
                                                        </div>
                                                    ))}
                                                </div>
                                            ) : (
                                                <span className="text-gray-600 text-xs">-</span>
                                            )}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-gray-300">
                                            ${opp.current_price?.toFixed(2)}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-blue-300" title="Markov Projected @ Ex-Date">
                                            ${opp.predicted_price?.toFixed(2)}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-purple-300">
                                            ${opp.analyst_target > 0 ? opp.analyst_target?.toFixed(2) : '-'}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-green-300">
                                            ${opp.dividend_amount?.toFixed(2)}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-cyan-300">
                                            {opp.return_pct}%
                                        </td>
                                        <td className="px-4 py-3 text-right text-gray-300">
                                            {opp.yield_annual}%
                                        </td>
                                        <td className="px-4 py-3 text-center text-gray-500 text-xs">
                                            {opp.days_to_ex}d
                                        </td>
                                        <td className="px-4 py-3 text-center">
                                            <span className={`px-2 py-0.5 rounded text-xs font-bold
                                                ${opp.score >= 80 ? 'bg-green-900 text-green-300' :
                                                    opp.score >= 50 ? 'bg-yellow-900 text-yellow-300' :
                                                        'bg-gray-800 text-gray-500'}`}>
                                                {opp.score}
                                            </span>
                                        </td>
                                        <td className="px-4 py-3 text-right text-gray-600 group-hover:text-blue-400 transition-colors">
                                            <ChevronRight className="w-5 h-5 ml-auto" />
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DividendListModal;
