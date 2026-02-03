import React, { useEffect, useState } from 'react';
import { DollarSign, ChevronRight } from 'lucide-react';
import DividendListModal from './DividendListModal';
import DividendAnalysisModal from './DividendAnalysisModal';

const DividendScanner = () => {
    const [opportunities, setOpportunities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);

    // UI State
    const [showList, setShowList] = useState(false);
    const [selectedOpp, setSelectedOpp] = useState(null); // Triggers Analysis Modal if not null
    const [toast, setToast] = useState(null);

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

    const handleSelectOpportunity = (opp) => {
        // Close list, open analysis (or keep list open behind? Let's close list for cleaner focus, or stack them)
        // User user request: "Intermediate screen lists... Clicking... brings up analysis"
        // Usually analysis is on top of list.
        // My implementation of DividendListModal covers screen. 
        // If I open Analysis on top, it needs higher Z-index.
        // DividendListModal is z-[50]. DividendAnalysisModal is z-[60]. Stacked is fine.
        setSelectedOpp(opp);
    };

    const handleConfirmStrategy = (opp) => {
        console.log("Strategy Selected:", opp);
        setToast(`Strategy Selected for ${opp.symbol}`);
        setTimeout(() => setToast(null), 3000);
        setSelectedOpp(null); // Close analysis
        // Optionally close list too? No, keep list open to select others.
    };

    if (loading && !opportunities.length) return (
        <div className="bg-gray-800 p-4 rounded-lg animate-pulse h-24"></div>
    );

    return (
        <>
            {/* 1. Compact Widget */}
            {/* 1. Compact Widget (Grid Compatible) */}
            <div
                onClick={() => setShowList(true)}
                className="p-1.5 pl-2 rounded text-xs border bg-green-900/30 border-green-700 text-green-200 flex items-center gap-2 shadow-sm cursor-pointer hover:bg-green-800/40 transition-colors h-full"
            >
                <div className="flex-shrink-0">
                    <DollarSign className="w-4 h-4 text-green-300 opacity-80" />
                </div>

                <div className="flex-1 min-w-0">
                    <div className="flex justify-between items-center mb-0.5">
                        <span className="font-bold font-mono text-white text-xs tracking-wide">Dividend Cap</span>
                    </div>

                    <div className="flex items-center justify-between mt-1">
                        <div className="flex items-baseline gap-1.5">
                            <span className="text-lg font-bold text-white leading-none">{opportunities.length}</span>
                            <span className="text-[10px] uppercase text-green-400 font-semibold">Opps</span>
                        </div>
                        {refreshing ? (
                            <span className="text-[9px] animate-pulse text-green-400">Scan...</span>
                        ) : (
                            <ChevronRight className="w-3 h-3 text-green-500 opacity-70" />
                        )}
                    </div>
                </div>

                {toast && (
                    <div className="absolute top-full left-0 right-0 z-50 mt-1 bg-green-800 text-white text-[10px] p-1 rounded shadow text-center">
                        {toast}
                    </div>
                )}
            </div>

            {/* 2. Intermediate List Modal */}
            <DividendListModal
                isOpen={showList}
                onClose={() => setShowList(false)}
                opportunities={opportunities}
                onSelectOpportunity={handleSelectOpportunity}
            />

            {/* 3. Analysis Detail Modal (Stacked) */}
            <DividendAnalysisModal
                isOpen={!!selectedOpp}
                onClose={() => setSelectedOpp(null)}
                opportunity={selectedOpp}
                onSelect={handleConfirmStrategy}
            />
        </>
    );
};

export default DividendScanner;
