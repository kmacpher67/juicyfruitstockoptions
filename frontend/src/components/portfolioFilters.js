export const DEFAULT_PORTFOLIO_FILTERS = Object.freeze({
    coverage: 'all',
    account: 'all',
    expiringOnly: false,
    nearMoneyOnly: false,
    dteLimit: 6,
    nearMoneyPercent: 8,
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

    if (!hasOptionFocusedFilter(filterState)) {
        return matchedRows;
    }

    const matchedOptionKeys = new Set(
        matchedRows.filter((row) => isOptionRow(row)).map((row) => getUnderlyingGroupKey(row)),
    );

    if (matchedOptionKeys.size === 0) {
        return matchedRows;
    }

    return rows.filter((row) => {
        if (matchedRows.includes(row)) {
            return true;
        }

        return isStockRow(row) && matchedOptionKeys.has(getUnderlyingGroupKey(row));
    });
};
