import React from 'react';
import { TrendingUp, TrendingDown, DollarSign, Calendar } from 'lucide-react';

const StatCard = ({ title, value, isCurrency = false, isPercent = false }) => {
    let colorClass = "text-white";
    let Icon = Calendar; // Default

    if (isPercent) {
        if (value > 0) {
            colorClass = "text-green-400";
            Icon = TrendingUp;
        } else if (value < 0) {
            colorClass = "text-red-400";
            Icon = TrendingDown;
        }
    } else if (isCurrency) {
        Icon = DollarSign;
    }

    const formattedValue = isCurrency
        ? `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
        : isPercent
            ? `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
            : value;

    return (
        <div className="bg-gray-800 p-4 rounded-lg border border-gray-700 shadow-md flex items-center justify-between">
            <div>
                <p className="text-gray-400 text-xs uppercase tracking-wider">{title}</p>
                <p className={`text-xl font-bold mt-1 ${colorClass}`}>{formattedValue}</p>
            </div>
            <div className={`p-2 rounded-full bg-gray-700/50 ${colorClass}`}>
                <Icon className="w-5 h-5" />
            </div>
        </div>
    );
};

const NAVStats = ({ stats }) => {
    if (!stats) return null;

    return (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <StatCard title="Current NAV" value={stats.current_nav} isCurrency={true} />
            <StatCard title="1 Day" value={stats.change_1d} isPercent={true} />
            <StatCard title="30 Day" value={stats.change_30d} isPercent={true} />
            <StatCard title="YTD" value={stats.change_ytd} isPercent={true} />
            <StatCard title="YoY" value={stats.change_yoy} isPercent={true} />
        </div>
    );
};

export default NAVStats;
