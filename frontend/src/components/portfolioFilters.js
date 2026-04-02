export const DEFAULT_PORTFOLIO_FILTERS = Object.freeze({
    coverage: 'all',
    pendingEffect: 'all',
    account: 'all',
    expiringOnly: false,
    nearMoneyOnly: false,
    dteLimit: 6,
    nearMoneyPercent: 8,
    showStocks: true,
});

const normalizeNumber = (value) => {
    if (value === null || value === undefined || value === '') return null;
    const numeric = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(numeric) ? numeric : null;
};

const getSecurityType = (row) => {
    const rawType = row.security_type || row.asset_class || row.secType || row.sec_type;
    return String(rawType || '').toUpperCase();
};

const isOptionRow = (row) => {
    const type = getSecurityType(row);
    return type === 'OPT' || type === 'FOP';
};

const isStockRow = (row) => getSecurityType(row) === 'STK';

const getUnderlyingGroupKey = (row) => {
    const accountId = row.account_id || 'UNKNOWN';
    const underlying = row.underlying_symbol || row.underlying || row.symbol || '';
    return `${accountId}:${String(underlying).toUpperCase()}`;
};

const hasOptionFocusedFilter = (filterState) => filterState.expiringOnly || filterState.nearMoneyOnly;

const matchesPendingEffectFilter = (row, pendingEffect) => {
    if (pendingEffect === 'all') return true;
    const effect = String(row.pending_order_effect || 'none').toLowerCase();
    if (pendingEffect === 'pending_cover') return effect === 'covering_uncovered';
    if (pendingEffect === 'pending_btc') return effect === 'buying_to_close';
    if (pendingEffect === 'pending_roll') return effect === 'rolling';
    return true;
};

const matchesTickerFilter = (row, filterTicker) => {
    if (!filterTicker) return true;

    const filter = filterTicker.toUpperCase().trim();
    if (!filter) return true;

    const symbol = String(row.symbol || '').toUpperCase();
    const underlying = String(row.underlying_symbol || '').toUpperCase();
    return symbol.includes(filter) || underlying === filter;
};

export const rowMatchesPortfolioFilters = (row, filterState, filterTicker = '') => {
    if (!matchesTickerFilter(row, filterTicker)) {
        return false;
    }

    if (filterState.account !== 'all' && row.account_id !== filterState.account) {
        return false;
    }

    if (filterState.coverage !== 'all' && row.coverage_status !== filterState.coverage) {
        return false;
    }

    if (!matchesPendingEffectFilter(row, filterState.pendingEffect)) {
        return false;
    }

    if (filterState.expiringOnly) {
        const dte = normalizeNumber(row.dte);
        if (dte === null || dte > filterState.dteLimit) {
            return false;
        }
    }

    if (filterState.nearMoneyOnly) {
        const distance = normalizeNumber(row.dist_to_strike_pct);
        const threshold = normalizeNumber(filterState.nearMoneyPercent);
        const maxDistance = threshold === null ? 0.08 : threshold / 100;
        if (distance === null || distance >= maxDistance) {
            return false;
        }
    }

    return true;
};

export const applyPortfolioFilters = (rows, filterState, filterTicker = '') => {
    const matchedRows = rows.filter((row) => rowMatchesPortfolioFilters(row, filterState, filterTicker));
    const showStocks = filterState.showStocks !== false;

    if (!hasOptionFocusedFilter(filterState)) {
        if (!showStocks) {
            return matchedRows.filter((row) => !isStockRow(row));
        }
        return matchedRows;
    }

    const matchedOptionKeys = new Set(
        matchedRows.filter((row) => isOptionRow(row)).map((row) => getUnderlyingGroupKey(row)),
    );

    if (matchedOptionKeys.size === 0) {
        if (!showStocks) {
            return matchedRows.filter((row) => !isStockRow(row));
        }
        return matchedRows;
    }

    const finalRows = rows.filter((row) => {
        if (matchedRows.includes(row)) {
            return true;
        }

        return isStockRow(row) && matchedOptionKeys.has(getUnderlyingGroupKey(row));
    });

    if (!showStocks) {
        return finalRows.filter((row) => !isStockRow(row));
    }

    return finalRows;
};
