export const DEFAULT_PORTFOLIO_FILTERS = Object.freeze({
    coverage: 'all',
    account: 'all',
    expiringOnly: false,
    nearMoneyOnly: false,
    dteLimit: 6,
});

const normalizeNumber = (value) => {
    if (value === null || value === undefined || value === '') return null;
    const numeric = typeof value === 'number' ? value : Number(value);
    return Number.isFinite(numeric) ? numeric : null;
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

    if (filterState.expiringOnly) {
        const dte = normalizeNumber(row.dte);
        if (dte === null || dte > filterState.dteLimit) {
            return false;
        }
    }

    if (filterState.nearMoneyOnly) {
        const distance = normalizeNumber(row.dist_to_strike_pct);
        if (distance === null || distance >= 0.05) {
            return false;
        }
    }

    return true;
};

export const applyPortfolioFilters = (rows, filterState, filterTicker = '') =>
    rows.filter((row) => rowMatchesPortfolioFilters(row, filterState, filterTicker));
